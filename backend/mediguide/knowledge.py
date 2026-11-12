"""Load and validate the knowledge files (symptom vocabulary + red-flag rules).

The YAML files in /knowledge are the single source of truth for:
  * which symptoms the NLP layer recognises, in English, Telugu and Hindi;
  * how each symptom links to NHAMCS reason-for-visit codes (model features);
  * which red-flag rules fire, and the public guidance each rule is based on.

`validate_knowledge()` returns a list of human-readable problems (empty list = valid).
It is run by the tests, so a typo in a YAML file fails the build instead of silently
switching off a safety rule.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "knowledge"
LANGS = ("en", "te", "hi")
KINDS = {"symptom", "sign", "context"}
LEVELS = {"EMERGENCY", "URGENT"}
CLAUSE_KEYS = {"all", "any", "severity", "onset", "onset_not", "min_duration_days", "context", "max_age_months"}
SEVERITIES = {"mild", "moderate", "severe"}
ONSETS = {"sudden", "gradual"}


def normalise_term(text: str) -> str:
    """Unicode-normalise (NFC), lowercase, collapse whitespace. Used for duplicate checks."""
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


@dataclass(frozen=True)
class Concept:
    id: str
    kind: str
    label: dict[str, str]
    terms: dict[str, list[str]]
    rfv: tuple[int, ...] = ()
    implies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rule:
    id: str
    level: str
    title: str
    match: list[dict]
    sources: list[str]
    quote: str
    note: str = ""


@dataclass
class Knowledge:
    concepts: dict[str, Concept]
    rules: list[Rule]
    sources: dict[str, dict]
    emergency_contacts: list[dict] = field(default_factory=list)

    def symptom_ids(self) -> list[str]:
        return [c.id for c in self.concepts.values() if c.kind == "symptom"]

    def rfv_to_symptom(self) -> dict[int, str]:
        return {code: c.id for c in self.concepts.values() for code in c.rfv}


class _UniqueKeyLoader(yaml.SafeLoader):
    """PyYAML silently keeps the LAST value of a duplicated key. In a safety file that could
    delete a rule without any error, so duplicated keys are rejected."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
            seen.add(key)
        return super().construct_mapping(node, deep)


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader subclass


@lru_cache(maxsize=1)
def load_knowledge(directory: Path = KNOWLEDGE_DIR) -> Knowledge:
    sym = load_yaml(directory / "symptoms.yaml")
    red = load_yaml(directory / "red_flags.yaml")
    concepts = {}
    for c in sym["concepts"]:
        concepts[c["id"]] = Concept(id=c["id"], kind=c["kind"], label=c.get("label", {}),
                                    terms={k: [str(t) for t in v] for k, v in c.get("terms", {}).items()},
                                    rfv=tuple(c.get("rfv", [])), implies=tuple(c.get("implies", [])))
    rules = [Rule(id=r["id"], level=r["level"], title=r["title"], match=r["match"],
                  sources=r["sources"], quote=r.get("quote", ""), note=r.get("note", ""))
             for r in red["rules"]]
    return Knowledge(concepts, rules, red["sources"], red.get("emergency_contacts", []))


def validate_knowledge(kb: Knowledge, known_rfv_codes: set[int] | None = None) -> list[str]:
    problems: list[str] = []

    # --- concepts ---------------------------------------------------------------------
    term_owner: dict[tuple[str, str], str] = {}
    rfv_owner: dict[int, str] = {}
    for c in kb.concepts.values():
        if c.kind not in KINDS:
            problems.append(f"{c.id}: unknown kind '{c.kind}'")
        # Unquoted commas inside YAML {...} silently split a label into extra keys
        # (found in the browser test: "Pain spreading to arm" lost ", jaw, neck or back").
        if set(c.label) != set(LANGS):
            problems.append(f"{c.id}: label keys {sorted(c.label)} - quote labels that contain commas")
        if not set(c.terms) <= set(LANGS):
            problems.append(f"{c.id}: unexpected term languages {sorted(set(c.terms) - set(LANGS))}")
        for lang in LANGS:
            if not c.label.get(lang):
                problems.append(f"{c.id}: missing {lang} label")
            if not c.terms.get(lang):
                problems.append(f"{c.id}: no {lang} terms")
            for t in c.terms.get(lang, []):
                key = (lang, normalise_term(t))
                if key in term_owner and term_owner[key] != c.id:
                    problems.append(f"term '{t}' ({lang}) is used by both {term_owner[key]} and {c.id}")
                term_owner.setdefault(key, c.id)
        if c.kind == "symptom" and not c.rfv:
            problems.append(f"{c.id}: symptom has no rfv codes (cannot become a model feature)")
        if c.kind != "symptom" and c.rfv:
            problems.append(f"{c.id}: only symptoms may carry rfv codes")
        for imp in c.implies:
            if imp not in kb.concepts or kb.concepts[imp].kind != "symptom":
                problems.append(f"{c.id}: implies '{imp}' which is not a known symptom")
        for code in c.rfv:
            if code in rfv_owner:
                problems.append(f"rfv {code} mapped to both {rfv_owner[code]} and {c.id}")
            rfv_owner[code] = c.id
            if known_rfv_codes is not None and code not in known_rfv_codes:
                problems.append(f"{c.id}: rfv {code} not found in NHAMCS code list")

    # --- rules ----------------------------------------------------------------------------
    seen = set()
    for r in kb.rules:
        if r.id in seen:
            problems.append(f"duplicate rule id {r.id}")
        seen.add(r.id)
        if r.level not in LEVELS:
            problems.append(f"{r.id}: invalid level {r.level}")
        if not r.sources:
            problems.append(f"{r.id}: no sources")
        for s in r.sources:
            if s not in kb.sources:
                problems.append(f"{r.id}: unknown source '{s}'")
        if not r.quote:
            problems.append(f"{r.id}: missing quote of the guidance it encodes")
        if not r.match:
            problems.append(f"{r.id}: no match clauses")
        for i, clause in enumerate(r.match):
            where = f"{r.id} clause {i + 1}"
            extra = set(clause) - CLAUSE_KEYS
            if extra:
                problems.append(f"{where}: unknown keys {sorted(extra)}")
            if not set(clause) & {"all", "any", "severity", "max_age_months"}:
                problems.append(f"{where}: clause would match every input")
            for key in ("all", "any", "context"):
                for cid in clause.get(key, []):
                    if cid not in kb.concepts:
                        problems.append(f"{where}: unknown concept '{cid}'")
                    elif key == "context" and kb.concepts[cid].kind != "context":
                        problems.append(f"{where}: '{cid}' used as context but kind is {kb.concepts[cid].kind}")
            if "severity" in clause and clause["severity"] not in SEVERITIES:
                problems.append(f"{where}: invalid severity {clause['severity']}")
            for key in ("onset", "onset_not"):
                if key in clause and clause[key] not in ONSETS:
                    problems.append(f"{where}: invalid {key} {clause[key]}")

    for key, src in kb.sources.items():
        if key != "project_policy" and not str(src.get("url", "")).startswith("https://"):
            problems.append(f"source {key}: missing https url")
    return problems
