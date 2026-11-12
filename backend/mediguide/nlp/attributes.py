"""Regex-based attribute extraction: duration, pain score, age and who the patient is.

All functions take the cleaned text and return character offsets, so the extractor can
attach each value to the right symptom.

Duration words without a number ("for days", "for weeks") use deliberately rough values;
they are only used to decide whether a follow-up question about duration is needed and
for the >= 5-day fever rule.
"""
from __future__ import annotations

import re

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "couple of": 2, "a couple of": 2, "few": 3, "a few": 3, "several": 4, "half an": 0.5, "half a": 0.5,
}
UNIT_DAYS = {"minute": 1 / 1440, "min": 1 / 1440, "hour": 1 / 24, "hr": 1 / 24, "day": 1, "night": 1,
             "week": 7, "wk": 7, "month": 30, "year": 365, "yr": 365}
RELATIVE_DAYS = {
    "yesterday": 1, "last night": 0.5, "this morning": 0.25, "morning": 0.25, "today": 0.25,
    "this afternoon": 0.2, "this evening": 0.1, "tonight": 0.05, "last week": 7, "last month": 30,
    "the day before yesterday": 2, "day before yesterday": 2,
}
VAGUE_DAYS = {"minutes": 0.02, "hours": 0.25, "days": 3, "weeks": 14, "months": 60, "years": 365}

_NUM = r"(\d+(?:\.\d+)?|a couple of|couple of|a few|few|several|half an|half a|an|a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)"
_UNIT = r"(minute|min|hour|hr|day|night|week|wk|month|year|yr)s?"
_REL = "|".join(sorted(map(re.escape, RELATIVE_DAYS), key=len, reverse=True))

# (kind, pattern): "num" = number + unit, "rel" = relative day word, "one" = a single unit
# ("for the last week"), "vague" = no number ("for days").
DURATION_PATTERNS = [
    ("num", re.compile(rf"\b(?:for|since|past|last|over the past|over the last|in the last|in the past)\s+(?:the\s+)?{_NUM}\s+{_UNIT}\b", re.I)),
    ("num", re.compile(rf"\b(?:it(?:'s| is| has)?\s+been|been)\s+{_NUM}\s+{_UNIT}\b", re.I)),
    ("num", re.compile(rf"\b{_NUM}\s+{_UNIT}\s+(?:ago|back|now)\b", re.I)),
    ("rel", re.compile(rf"\b(?:since|from|started|began|start|starting)\s+({_REL})\b", re.I)),
    ("one", re.compile(rf"\b(?:for|over|in|during|since)\s+the\s+(?:past|last)\s+{_UNIT}\b", re.I)),
    ("vague", re.compile(r"\bfor\s+(minutes|hours|days|weeks|months|years)\b", re.I)),
]


def _number(text: str) -> float:
    text = text.lower()
    return float(text) if re.fullmatch(r"\d+(?:\.\d+)?", text) else float(NUMBER_WORDS[text])


def find_durations(text: str) -> list[tuple[int, int, float]]:
    """Return (start_char, end_char, days) for every duration expression."""
    found: list[tuple[int, int, float]] = []
    taken: list[tuple[int, int]] = []
    for kind, pat in DURATION_PATTERNS:
        for m in pat.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            if kind == "num":
                days = _number(m.group(1)) * UNIT_DAYS[m.group(2).lower()]
            elif kind == "rel":
                days = RELATIVE_DAYS[m.group(1).lower()]
            elif kind == "one":
                days = UNIT_DAYS[m.group(1).lower()]
            else:
                days = VAGUE_DAYS[m.group(1).lower()]
            found.append((m.start(), m.end(), round(days, 4)))
            taken.append((m.start(), m.end()))
    return sorted(found)


_PAIN = re.compile(r"\b(\d{1,2})\s*(?:/|out of)\s*10\b", re.I)


def find_pain_scores(text: str) -> list[tuple[int, int, int]]:
    return [(m.start(), m.end(), int(m.group(1))) for m in _PAIN.finditer(text) if int(m.group(1)) <= 10]


def pain_band(score: int) -> str | None:
    """Same bands used for the NHAMCS pain-score analysis in Phase 1."""
    if score >= 7:
        return "severe"
    if score >= 4:
        return "moderate"
    if score >= 1:
        return "mild"
    return None


_AGE_PATTERNS = [
    (re.compile(r"\b(\d{1,3})[\s-]*(?:years?|yrs?)[\s-]*old\b", re.I), 1.0),
    (re.compile(r"\b(\d{1,3})\s*(?:yo|y/o)\b", re.I), 1.0),
    (re.compile(r"\baged?\s+(\d{1,3})\b", re.I), 1.0),
    (re.compile(r"\b(\d{1,2})[\s-]*months?[\s-]*old\b", re.I), 1 / 12),
    (re.compile(r"\b(\d{1,2})[\s-]*weeks?[\s-]*old\b", re.I), 7 / 365),
    (re.compile(r"\b(\d{1,2})[\s-]*days?[\s-]*old\b", re.I), 1 / 365),
]
_NEWBORN = re.compile(r"\b(newborn|new-born|new born)\b", re.I)


def find_age_years(text: str) -> float | None:
    for pat, factor in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            age = int(m.group(1)) * factor
            if 0 <= age <= 120:
                return round(age, 4)
    if _NEWBORN.search(text):
        return 0.02
    return None


_OTHER = re.compile(r"\bmy\s+(?:[\w-]+\s+){0,4}?(baby|son|daughter|child|kid|infant|father|dad|mother|mom|mum|wife|husband|"
                    r"brother|sister|grandfather|grandmother|grandma|grandpa|friend|partner|newborn)\b", re.I)


def find_subject(text: str) -> str:
    """'other' when describing someone else ("my baby has a fever"); otherwise 'self'."""
    return "other" if _OTHER.search(text) else "self"


# ======================================================================================
# Telugu and Hindi (DRAFT - pending native-speaker review)
# A number + time unit is only a DURATION when a "since/for/ago" marker follows; otherwise
# "45 సంవత్సరాలు" / "45 साल" is more likely an AGE.
# ======================================================================================
TE_NUM = {"ఒక": 1, "ఒక్క": 1, "ఒకటి": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4, "ఐదు": 5, "అయిదు": 5,
          "ఆరు": 6, "ఏడు": 7, "ఎనిమిది": 8, "తొమ్మిది": 9, "పది": 10, "కొన్ని": 3}
TE_UNIT = {"రోజు": 1, "రోజుల": 1, "దినాల": 1, "వారం": 7, "వారా": 7, "నెల": 30, "గంట": 1 / 24,
           "నిమిష": 1 / 1440, "సంవత్సర": 365, "ఏడాది": 365, "ఏళ్ల": 365}
TE_REL = {"నిన్న రాత్రి": 0.5, "నిన్నటి": 1, "నిన్న": 1, "మొన్నటి": 2, "మొన్న": 2, "ఈ రోజు ఉదయం": 0.25,
          "ఈరోజు ఉదయం": 0.25, "పొద్దున్న": 0.25, "పొద్దున": 0.25, "ఉదయం": 0.25, "ఈ రోజు": 0.25,
          "ఈరోజు": 0.25, "రాత్రి": 0.5, "గత వారం": 7}
HI_NUM = {"एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9,
          "दस": 10, "कुछ": 3, "डेढ": 1.5}
HI_UNIT = {"दिन": 1, "दिनों": 1, "हफ्ते": 7, "हफ्ता": 7, "हफ्तों": 7, "सप्ताह": 7, "महीने": 30, "महीना": 30,
           "महीनों": 30, "घंटे": 1 / 24, "घंटा": 1 / 24, "घंटों": 1 / 24, "मिनट": 1 / 1440, "साल": 365, "वर्ष": 365}
HI_REL = {"कल रात": 0.5, "कल": 1, "परसों": 2, "आज सुबह": 0.25, "सुबह": 0.25, "आज": 0.25, "रात": 0.5,
          "पिछले हफ्ते": 7, "पिछले महीने": 30}


def _alt(words) -> str:
    return "|".join(sorted(map(re.escape, words), key=len, reverse=True))


_TE_DUR = re.compile(rf"(\d+(?:\.\d+)?|{_alt(TE_NUM)})\s*({_alt(TE_UNIT)})([ఀ-౿]*)"
                     rf"(\s+(?:నుండి|నుంచి|నుండీ|నుంచీ|క్రితం|అయింది|అయ్యింది|అవుతోంది|అవుతుంది))?")
_TE_REL = re.compile(rf"({_alt(TE_REL)})(?:టి)?\s*(?:నుండి|నుంచి|నుండీ|నుంచీ|నుండే|నుంచే|మొదలై|మొదలైంది|మొదలయ్యింది)")
_HI_DUR = re.compile(rf"(?:पिछले\s+)?(\d+(?:\.\d+)?|{_alt(HI_NUM)})\s*({_alt(HI_UNIT)})\s+"
                     rf"(से|पहले|हो\s+गए|हो\s+गया|हो\s+गई|हो\s+गये)")
_HI_REL = re.compile(rf"({_alt(HI_REL)})\s+(?:से|शुरू)")


def _durations_indic(text: str, lang: str) -> list[tuple[int, int, float]]:
    out = []
    if lang == "te":
        for m in _TE_DUR.finditer(text):
            rest, after = m.group(3) or "", m.group(4)
            if not (after or rest.endswith("గా") or "నుండి" in rest or "నుంచి" in rest):
                continue  # no "for/since/ago" marker -> probably an age, not a duration
            n = float(m.group(1)) if m.group(1)[0].isdigit() else TE_NUM[m.group(1)]
            out.append((m.start(), m.end(), round(n * TE_UNIT[m.group(2)], 4)))
        for m in _TE_REL.finditer(text):
            out.append((m.start(), m.end(), TE_REL[m.group(1)]))
    elif lang == "hi":
        for m in _HI_DUR.finditer(text):
            n = float(m.group(1)) if m.group(1)[0].isdigit() else HI_NUM[m.group(1)]
            out.append((m.start(), m.end(), round(n * HI_UNIT[m.group(2)], 4)))
        for m in _HI_REL.finditer(text):
            out.append((m.start(), m.end(), HI_REL[m.group(1)]))
    out.sort(key=lambda x: (x[0], -(x[1] - x[0])))   # drop overlaps, keep the longest
    kept: list[tuple[int, int, float]] = []
    for item in out:
        if not any(item[0] < e and s < item[1] for s, e, _ in kept):
            kept.append(item)
    return kept


_TE_AGE = [
    (re.compile(r"(?:వయస్సు|వయసు)\s*(\d{1,3})"), 1.0),
    (re.compile(r"(\d{1,3})\s*(?:సంవత్సరాల|ఏళ్ల|ఏళ్ళ)"), 1.0),
    (re.compile(r"(\d{1,2})\s*నెలల\s*(?:బాబు|పాప|బిడ్డ|పిల్ల|పసిబిడ్డ)"), 1 / 12),
    (re.compile(r"(\d{1,2})\s*వారాల\s*(?:బాబు|పాప|బిడ్డ|పిల్ల|పసిబిడ్డ)"), 7 / 365),
    (re.compile(r"(\d{1,2})\s*రోజుల\s*(?:బాబు|పాప|బిడ్డ|పిల్ల|పసిబిడ్డ)"), 1 / 365),
]
_HI_AGE = [
    (re.compile(r"(?:उम्र|उमर|आयु)\s*(\d{1,3})"), 1.0),
    (re.compile(r"(\d{1,3})\s*(?:साल|वर्ष)\s*(?:का|की|के)"), 1.0),
    (re.compile(r"(\d{1,2})\s*(?:महीने|महीना)\s*(?:का|की|के)"), 1 / 12),
    (re.compile(r"(\d{1,2})\s*(?:हफ्ते|सप्ताह)\s*(?:का|की|के)"), 7 / 365),
    (re.compile(r"(\d{1,2})\s*दिन\s*(?:का|की|के)"), 1 / 365),
]
_TE_OTHER = re.compile(r"(?:మా|నా)\s+(?:\S+\s+){0,2}?(?:బాబు|పాప|అబ్బాయి|అమ్మాయి|అమ్మ|నాన్న|తాత|అమ్మమ్మ|నానమ్మ|బిడ్డ|"
                       r"పిల్లాడు|పిల్ల|కొడుకు|కూతురు|భార్య|భర్త|ఆయన|ఆవిడ|తమ్ముడు|అన్న|చెల్లి|అక్క|పసిబిడ్డ)")
_HI_OTHER = re.compile(r"(?:मेरे|मेरी|मेरा|हमारे|हमारी|हमारा)\s+(?:\S+\s+){0,3}?(?:बच्चा|बच्चे|बच्ची|बेटा|बेटे|बेटी|"
                       r"मां|मम्मी|माता|पिता|पिताजी|पापा|पत्नी|पति|भाई|बहन|दादा|दादी|नाना|नानी)")


# ---- language dispatch (English patterns always run too: code-mixed text) ------------------
_find_durations_en, _find_age_en, _find_subject_en = find_durations, find_age_years, find_subject


def find_durations(text: str, lang: str = "en") -> list[tuple[int, int, float]]:  # noqa: F811
    found = _find_durations_en(text)
    if lang in ("te", "hi"):
        found += [d for d in _durations_indic(text, lang)
                  if not any(d[0] < e and s < d[1] for s, e, _ in found)]
    return sorted(found)


def find_age_years(text: str, lang: str = "en") -> float | None:  # noqa: F811
    for pat, factor in {"te": _TE_AGE, "hi": _HI_AGE}.get(lang, []):
        m = pat.search(text)
        if m and 0 <= int(m.group(1)) * factor <= 120:
            return round(int(m.group(1)) * factor, 4)
    return _find_age_en(text)


def find_subject(text: str, lang: str = "en") -> str:  # noqa: F811
    pat = {"te": _TE_OTHER, "hi": _HI_OTHER}.get(lang)
    if pat is not None and pat.search(text):
        return "other"
    age = find_age_years(text, lang)
    if age is not None and age < 1:
        return "other"  # a baby cannot be the person typing the message
    return _find_subject_en(text)
