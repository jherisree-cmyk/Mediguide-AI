"""Data structures returned by the NLP extractor.

Mention   one occurrence of a concept in the text ("severe headache" at characters 7-22)
Finding   all mentions of one concept merged ("headache": severe, 2 days, worsening)
Extraction the full result for one user message
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

SEVERITY_ORDER = {"mild": 1, "moderate": 2, "severe": 3}


@dataclass
class Mention:
    concept_id: str
    kind: str                       # symptom | sign | context
    text: str                       # the matched words, as written (after spelling fixes)
    start: int                      # token index (inclusive)
    end: int                        # token index (exclusive)
    sentence: int
    negated: bool = False
    hedged: bool = False            # "maybe", "I think" -> ask the user to confirm
    implied_by: str | None = None   # set when added because a warning sign implies it
    severity: str | None = None     # mild | moderate | severe
    pain_score: int | None = None   # 0-10, from "7/10" or "7 out of 10"
    duration_days: float | None = None
    onset: str | None = None        # sudden | gradual
    progression: str | None = None  # worsening | improving
    frequency: str | None = None    # intermittent | constant


@dataclass
class Finding:
    concept_id: str
    kind: str
    severity: str | None = None
    pain_score: int | None = None
    duration_days: float | None = None
    onset: str | None = None
    progression: str | None = None
    frequency: str | None = None
    hedged: bool = False
    conflict: bool = False          # mentioned both as present and as absent -> kept as present
    evidence: list[str] = field(default_factory=list)


@dataclass
class Extraction:
    language: str
    original_text: str
    normalised_text: str
    findings: dict[str, Finding] = field(default_factory=dict)   # present (not negated) concepts
    negated: list[str] = field(default_factory=list)             # concepts explicitly denied
    mentions: list[Mention] = field(default_factory=list)
    corrections: list[tuple[str, str]] = field(default_factory=list)  # (as typed, corrected)
    age_years: float | None = None
    subject: str = "self"           # self | other ("my baby has...")

    def present(self, kind: str | None = None) -> list[str]:
        return [cid for cid, f in self.findings.items() if kind is None or f.kind == kind]

    def to_dict(self) -> dict:
        return asdict(self)
