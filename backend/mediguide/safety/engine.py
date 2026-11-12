"""Red-flag safety rule engine (Module 5).

Input : an Extraction (symptoms found by the NLP layer) + optional age from the user profile.
Output: SafetyResult - the highest rule level that fired, every fired rule with its source
        and quoted guidance, and whether the message was understood at all.

Design guarantees (each one is tested):
  * INDEPENDENT of machine learning: this package never imports mediguide.ml.
  * EMERGENCY is decided here, BEFORE any ML prediction exists, so ML cannot override it.
  * Conservative interpretation: uncertain ("maybe a fever") findings count as present;
    unknown onset counts as "not gradual" where the rule says so.
  * Every decision is explainable: the rule id, the matched concepts, the guideline quote.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mediguide.knowledge import Knowledge, Rule, load_knowledge
from mediguide.nlp.schema import SEVERITY_ORDER, Extraction, Finding

LEVEL_ORDER = {"URGENT": 1, "EMERGENCY": 2}


@dataclass
class FiredRule:
    id: str
    level: str
    title: str
    matched_concepts: list[str]
    sources: list[dict]
    quote: str
    note: str = ""


@dataclass
class SafetyResult:
    level: str | None                     # "EMERGENCY", "URGENT" or None (no rule fired)
    fired: list[FiredRule] = field(default_factory=list)
    understood: bool = True               # False -> no symptom recognised at all
    emergency_contacts: list[dict] = field(default_factory=list)

    @property
    def is_emergency(self) -> bool:
        return self.level == "EMERGENCY"


class SafetyEngine:
    def __init__(self, kb: Knowledge | None = None):
        self.kb = kb or load_knowledge()

    # ------------------------------------------------------------------------------------
    def evaluate(self, ext: Extraction, age_years: float | None = None) -> SafetyResult:
        """`age_years` from the user profile wins over an age mentioned in the text."""
        age = age_years if age_years is not None else ext.age_years
        present = ext.findings
        fired: list[FiredRule] = []
        for rule in self.kb.rules:
            matched = self._match_rule(rule, present, age)
            if matched is not None:
                fired.append(FiredRule(
                    id=rule.id, level=rule.level, title=rule.title, matched_concepts=matched,
                    sources=[{"key": s, **self.kb.sources[s]} for s in rule.sources],
                    quote=rule.quote, note=rule.note))
        fired.sort(key=lambda f: -LEVEL_ORDER[f.level])
        level = fired[0].level if fired else None
        understood = bool(ext.findings or ext.negated)
        return SafetyResult(level=level, fired=fired, understood=understood,
                            emergency_contacts=self.kb.emergency_contacts if level == "EMERGENCY" else [])

    # ------------------------------------------------------------------------------------
    def _match_rule(self, rule: Rule, present: dict[str, Finding], age: float | None) -> list[str] | None:
        for clause in rule.match:
            matched = self._match_clause(clause, present, age)
            if matched is not None:
                return matched
        return None

    @staticmethod
    def _match_clause(clause: dict, present: dict[str, Finding], age: float | None) -> list[str] | None:
        """Return the concepts that satisfied the clause, or None if it does not match."""
        all_ids = clause.get("all", [])
        any_ids = clause.get("any", [])
        if any(cid not in present for cid in all_ids):
            return None
        any_hits = [cid for cid in any_ids if cid in present]
        if any_ids and not any_hits:
            return None
        if any(cid not in present for cid in clause.get("context", [])):
            return None
        if "max_age_months" in clause:
            if age is None or age * 12 > clause["max_age_months"]:
                return None  # unknown age never satisfies an age condition

        # Which findings the severity/onset/duration conditions apply to (see red_flags.yaml).
        if all_ids:
            targets = list(all_ids)
        elif any_ids:
            targets = any_hits
        else:
            targets = [cid for cid, f in present.items() if f.kind != "context"]
        tf = [present[cid] for cid in targets if cid in present]

        if "severity" in clause:
            need = SEVERITY_ORDER[clause["severity"]]
            tf = [f for f in tf if SEVERITY_ORDER.get(f.severity or "", 0) >= need]
            if not tf:
                return None
        if "onset" in clause:
            tf = [f for f in tf if f.onset == clause["onset"]]
            if not tf:
                return None
        if "onset_not" in clause:
            tf = [f for f in tf if f.onset != clause["onset_not"]]
            if not tf:
                return None
        if "min_duration_days" in clause:
            tf = [f for f in tf if (f.duration_days or 0) >= clause["min_duration_days"]]
            if not tf:
                return None
        if not targets and "max_age_months" not in clause:
            return None
        matched = {f.concept_id for f in tf} | set(any_hits) | set(all_ids) | set(clause.get("context", []))
        return sorted(matched)


_ENGINE: SafetyEngine | None = None


def evaluate(ext: Extraction, age_years: float | None = None) -> SafetyResult:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SafetyEngine()
    return _ENGINE.evaluate(ext, age_years)
