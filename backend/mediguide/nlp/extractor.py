"""Rule-based symptom extraction (Module 3).

Pipeline for one message:
  1. clean + spelling correction            (preprocess.py)
  2. tokenise + split sentences             (spaCy blank pipeline + sentencizer)
  3. find concept mentions                  (token Matcher, longest match wins)
  4. find cue words                         (negation, hedges, severity, onset, ...)
  5. negation + hedge detection             (NegEx-style scopes, see _negate)
  6. attach attributes to mentions          (nearest symptom / same clause)
  7. duration, pain score, age (regex)      (attributes.py)
  8. merge mentions into one Finding per concept

Why rules and not a trained NER model? We have no labelled Telugu/Hindi/English symptom
corpus. Rules are transparent, testable and easy to explain, and every safety decision can
be traced back to the exact words that triggered it.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import spacy
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Span
from spacy.util import filter_spans

from mediguide.knowledge import KNOWLEDGE_DIR, Knowledge, load_knowledge, load_yaml
from mediguide.multilingual.normalise import normalise
from mediguide.nlp import attributes
from mediguide.nlp.preprocess import SpellingCorrector, clean
from mediguide.nlp.schema import SEVERITY_ORDER, Extraction, Finding, Mention

_INDIC = re.compile(r"[\u0900-\u097F\u0C00-\u0C7F]")
_LIST_KEYS = ("pre", "post", "pseudo", "terminate")


@lru_cache(maxsize=None)
def load_cues(directory: Path = KNOWLEDGE_DIR) -> dict:
    return load_yaml(directory / "nlp_cues.yaml")


class SymptomExtractor:
    def __init__(self, lang: str = "en", kb: Knowledge | None = None, cues: dict | None = None):
        self.lang = lang
        self.kb = kb or load_knowledge()
        all_cues = cues or load_cues()
        self.cues = self._merge_cues(all_cues, lang)
        self.nlp = spacy.blank("en" if lang == "en" else "xx")
        self.nlp.add_pipe("sentencizer")
        # grammar helpers (language-specific, from nlp_cues.yaml)
        self.scope_filler = set(self.cues.get("scope_filler", []))
        self.clause_words = set(self.cues.get("clause_words", []))
        self.clause_starters = set(self.cues.get("clause_starters", []))
        self.negators = set(self.cues.get("negators", []))
        suffixes = sorted(self.cues.get("suffixes", []), key=len, reverse=True)
        self._suffix_re = "|".join(map(re.escape, suffixes))

        # Token patterns instead of exact phrases, so an optional side/position word may sit
        # between the words of a term: "can't move my arm" also matches "can't move my LEFT arm".
        self.concept_matcher = Matcher(self.nlp.vocab)
        mods = [normalise(m, lang) for m in self.cues.get("phrase_modifiers", [])]
        term_langs = [lang] if lang == "en" else [lang, "en"]   # code-mixed text: also English terms
        for c in self.kb.concepts.values():
            patterns = []
            for tl in term_langs:
                for term in c.terms.get(tl, []):
                    pattern = []
                    for i, tok in enumerate(self.nlp.make_doc(normalise(term, lang))):
                        if i and mods:  # up to two optional modifiers ("कमर में बहुत तेज दर्द")
                            pattern.append({"LOWER": {"IN": mods}, "OP": "?"})
                            pattern.append({"LOWER": {"IN": mods}, "OP": "?"})
                        pattern.append(self._token_pattern(tok.text))
                    patterns.append(pattern)
            if patterns:
                self.concept_matcher.add(c.id, patterns)

        self.cue_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        neg = self.cues["negation"]
        self.scope_tokens = int(neg.get("scope_tokens", 6))
        self.post_scope = int(neg.get("post_scope_tokens", 3))
        groups = {"NEG_PRE": neg["pre"], "NEG_POST": neg["post"], "PSEUDO": neg["pseudo"],
                  "TERM": neg["terminate"], "HEDGE": self.cues["hedge"]}
        for attr in ("severity", "onset", "progression", "frequency"):
            for value, words in self.cues[attr].items():
                groups[f"{attr.upper()}:{value}"] = words
        for label, words in groups.items():
            self.cue_matcher.add(label, [self.nlp.make_doc(normalise(w, lang)) for w in words])

        # English spelling correction. It only touches Latin-script words, so it is also safe
        # for code-mixed Telugu/Hindi text.
        vocab = {w for c in self.kb.concepts.values() for t in c.terms.get("en", []) for w in t.lower().split()}
        vocab |= {w for words in groups.values() for p in words for w in p.lower().split()}
        self.speller = SpellingCorrector(all_cues.get("spelling_en", {}), vocab)

    @staticmethod
    def _merge_cues(all_cues: dict, lang: str) -> dict:
        """Telugu/Hindi cues + English cues, for code-mixed text such as "నాకు fever లేదు"."""
        own = all_cues[lang]
        if lang == "en":
            return own
        en = all_cues["en"]
        merged = dict(own)
        neg = dict(own["negation"])
        for key in _LIST_KEYS:
            neg[key] = list(own["negation"].get(key, [])) + list(en["negation"].get(key, []))
        merged["negation"] = neg
        merged["hedge"] = list(own.get("hedge", [])) + list(en.get("hedge", []))
        for attr in ("severity", "onset", "progression", "frequency"):
            merged[attr] = {v: list(own.get(attr, {}).get(v, [])) + list(en[attr].get(v, []))
                            for v in en[attr]}
        for key in ("scope_filler", "clause_words", "negators"):
            merged[key] = list(own.get(key, [])) + list(en.get(key, []))
        return merged

    def _token_pattern(self, word: str) -> dict:
        """Latin words: case-insensitive exact match. Telugu/Hindi words: also accept the
        known endings (జ్వరంతో, दिखने) and, for Telugu, the anusvara alternation
        (జ్వరం / జ్వరము / జ్వరమే)."""
        if self.lang not in ("te", "hi") or not _INDIC.search(word) or not self._suffix_re:
            return {"LOWER": word.lower()}
        if self.lang == "te" and word.endswith("\u0C02"):  # Telugu word ending in anusvara
            stem = re.escape(word[:-1]) + "(?:\u0C02|\u0C2E[\u0C41\u0C42\u0C47\u0C46]?)"
        else:
            stem = re.escape(word)
        return {"TEXT": {"REGEX": f"^{stem}(?:{self._suffix_re})?$"}}

    # ------------------------------------------------------------------------------------
    def extract(self, text: str) -> Extraction:
        normalised = normalise(clean(text), self.lang)
        corrections: list[tuple[str, str]] = []
        if self.speller:
            normalised, corrections = self.speller.correct(normalised)
        doc = self.nlp(normalised)
        sent_of = [0] * len(doc)
        for i, sent in enumerate(doc.sents):
            for tok in sent:
                sent_of[tok.i] = i
        clause_of = self._clauses(doc, sent_of)

        # 3. concept mentions - longest non-overlapping spans win ("swollen face" > "swollen")
        spans = [Span(doc, s, e, label=mid) for mid, s, e in self.concept_matcher(doc)]
        mentions = [Mention(concept_id=sp.label_, kind=self.kb.concepts[sp.label_].kind, text=sp.text,
                            start=sp.start, end=sp.end, sentence=sent_of[sp.start])
                    for sp in sorted(filter_spans(spans), key=lambda s: s.start)]
        covered = {i for m in mentions for i in range(m.start, m.end)}

        # 4. cue spans by label; a cue fully inside a mention belongs to that phrase
        cues: dict[str, list[tuple[int, int]]] = {}
        for mid, s, e in self.cue_matcher(doc):
            cues.setdefault(self.nlp.vocab.strings[mid], []).append((s, e))
        pseudo_tokens = {i for s, e in cues.get("PSEUDO", []) for i in range(s, e)}

        def usable(label: str, allow_inside_mention: bool = False) -> list[tuple[int, int]]:
            out = []
            for s, e in cues.get(label, []):
                toks = set(range(s, e))
                if label.startswith("NEG") and toks & pseudo_tokens:
                    continue
                if not allow_inside_mention and toks <= covered:
                    continue
                out.append((s, e))
            return out

        # 5. negation and hedging
        terminators = {s for s, _ in usable("TERM")}
        severity_end = {e for lbl, spans in cues.items() if lbl.startswith("SEVERITY:") for _, e in spans}
        # "నొప్పి ఎక్కువగా లేదు" / "दर्द ज्यादा नहीं" = the pain is NOT SEVERE (pain still present)
        post_neg = [(s, e) for s, e in usable("NEG_POST") if s not in severity_end]
        negated_severity = {s for s, e in usable("NEG_POST") if s in severity_end}
        for m in mentions:
            m.negated = self._negated(m, usable("NEG_PRE"), post_neg, terminators,
                                      sent_of, clause_of, covered, doc)
            m.hedged = any(e <= m.start and sent_of[s] == m.sentence and clause_of[s] == clause_of[m.start]
                           and m.start - e <= self.scope_tokens for s, e in usable("HEDGE"))

        # 6. attributes from cue words
        for value in self.cues["severity"]:
            for s, e in usable(f"SEVERITY:{value}", allow_inside_mention=True):
                if any(doc[i].lower_ in self.negators for i in range(max(s - 2, 0), s)) or e in negated_severity:
                    continue  # "not severe" / "ఎక్కువగా లేదు" is not severe
                target = self._nearest(mentions, s, e, sent_of, clause_of, max_gap=4)
                if target and SEVERITY_ORDER[value] > SEVERITY_ORDER.get(target.severity or "", 0):
                    target.severity = value
        for attr in ("onset", "progression", "frequency"):
            for value in self.cues[attr]:
                for s, e in usable(f"{attr.upper()}:{value}", allow_inside_mention=True):
                    for target in self._clause_targets(mentions, s, sent_of, clause_of):
                        if attr == "onset" and target.onset == "sudden":
                            continue  # sudden wins over gradual (safety)
                        if attr == "progression" and target.progression == "worsening":
                            continue
                        setattr(target, attr, value)

        # 7. regex attributes: duration, pain score; age and subject
        for start_char, end_char, days in attributes.find_durations(normalised, self.lang):
            span = doc.char_span(start_char, end_char, alignment_mode="expand")
            if span is None:
                continue
            for target in self._clause_targets(mentions, span.start, sent_of, clause_of):
                target.duration_days = max(days, target.duration_days or 0)
        for start_char, end_char, score in attributes.find_pain_scores(normalised):
            span = doc.char_span(start_char, end_char, alignment_mode="expand")
            target = span is not None and self._nearest(mentions, span.start, span.end, sent_of, clause_of, max_gap=6)
            if target:
                target.pain_score = score
                band = attributes.pain_band(score)
                if band and SEVERITY_ORDER[band] > SEVERITY_ORDER.get(target.severity or "", 0):
                    target.severity = band

        # signs that imply a model symptom ("worst headache of my life" -> headache)
        for m in list(mentions):
            for implied in self.kb.concepts[m.concept_id].implies:
                if not m.negated:
                    mentions.append(Mention(**{**m.__dict__, "concept_id": implied,
                                               "kind": self.kb.concepts[implied].kind, "implied_by": m.concept_id}))

        ext = Extraction(language=self.lang, original_text=text, normalised_text=normalised,
                         mentions=mentions, corrections=corrections,
                         age_years=attributes.find_age_years(normalised, self.lang),
                         subject=attributes.find_subject(normalised, self.lang))
        self._merge(ext)
        return ext

    # ------------------------------------------------------------------------------------
    def _clauses(self, doc, sent_of) -> list[int]:
        """Clause id per token: split at ';', 'but', 'however'..., and at ',' / 'and' that start
        a new statement ("..., and I feel dizzy")."""
        clause, out = 0, []
        for tok in doc:
            nxt = doc[tok.i + 1].lower_ if tok.i + 1 < len(doc) else ""
            if tok.i and sent_of[tok.i] != sent_of[tok.i - 1]:
                clause += 1
            elif tok.lower_ in self.clause_words or (tok.lower_ == "," and nxt in self.clause_starters) \
                    or (tok.lower_ == "and" and nxt in self.clause_starters - {"and", "but"}):
                clause += 1
            out.append(clause)
        return out

    def _negated(self, m, pre, post, terminators, sent_of, clause_of, covered, doc) -> bool:
        def content_gap(a: int, b: int) -> int:
            return sum(1 for i in range(a, b)
                       if not doc[i].is_punct and i not in covered and doc[i].lower_ not in self.scope_filler)

        for s, e in pre:
            if e <= m.start and sent_of[s] == m.sentence and not any(e <= t < m.start for t in terminators) \
                    and content_gap(e, m.start) <= self.scope_tokens:
                return True
        for s, e in post:
            if s >= m.end and sent_of[s] == m.sentence and not any(m.end <= t < s for t in terminators) \
                    and content_gap(m.end, s) <= self.post_scope:
                return True
        return False

    @staticmethod
    def _nearest(mentions, s, e, sent_of, clause_of, max_gap):
        """Mention closest to a cue in the same clause; ties go to the mention AFTER the cue
        ("severe headache"). Falls back to the previous sentence's mentions ("It is severe.")."""
        best, best_key = None, None
        for m in mentions:
            if m.kind == "context" or m.negated or sent_of[s] != m.sentence or clause_of[s] != clause_of[m.start]:
                continue
            gap = 0 if (m.start < e and s < m.end) else (m.start - e if m.start >= e else s - m.end)
            if gap <= max_gap:
                key = (gap, 0 if m.start >= s else 1)
                if best_key is None or key < best_key:
                    best, best_key = m, key
        if best is None and not any(m.sentence == sent_of[s] for m in mentions):
            prev = [m for m in mentions if m.sentence < sent_of[s] and m.kind != "context" and not m.negated]
            if prev:
                last = max(m.sentence for m in prev)
                cands = [m for m in prev if m.sentence == last]
                return cands[0] if len(cands) == 1 else None
        return best

    @staticmethod
    def _clause_targets(mentions, tok, sent_of, clause_of):
        """All mentions in the cue's clause; else the cue's sentence; else the previous sentence."""
        pool = [m for m in mentions if m.kind != "context"]
        same_clause = [m for m in pool if clause_of[m.start] == clause_of[tok]]
        if same_clause:
            return same_clause
        same_sent = [m for m in pool if m.sentence == sent_of[tok]]
        if same_sent:
            return same_sent
        # A sentence with no symptom of its own ("Since this morning.") describes the
        # symptoms mentioned before it.
        return [m for m in pool if m.sentence < sent_of[tok]]

    @staticmethod
    def _merge(ext: Extraction) -> None:
        by_concept: dict[str, list[Mention]] = {}
        for m in ext.mentions:
            by_concept.setdefault(m.concept_id, []).append(m)
        for cid, ms in by_concept.items():
            affirmed = [m for m in ms if not m.negated]
            if not affirmed:
                ext.negated.append(cid)
                continue
            f = Finding(concept_id=cid, kind=affirmed[0].kind)
            for m in affirmed:
                if m.severity and SEVERITY_ORDER[m.severity] > SEVERITY_ORDER.get(f.severity or "", 0):
                    f.severity = m.severity
                if m.pain_score is not None:
                    f.pain_score = max(m.pain_score, f.pain_score or 0)
                if m.duration_days is not None:
                    f.duration_days = max(m.duration_days, f.duration_days or 0)
                if m.onset and f.onset != "sudden":
                    f.onset = m.onset
                if m.progression and f.progression != "worsening":
                    f.progression = m.progression
                if m.frequency:
                    f.frequency = m.frequency
                f.evidence.append(m.text)
            f.hedged = all(m.hedged for m in affirmed)
            f.conflict = len(affirmed) < len(ms)
            ext.findings[cid] = f


@lru_cache(maxsize=None)
def get_extractor(lang: str = "en") -> SymptomExtractor:
    return SymptomExtractor(lang)


def extract(text: str, lang: str = "en") -> Extraction:
    return get_extractor(lang).extract(text)
