"""Follow-up question generation (Module 4).

Questions are DERIVED FROM THE SAFETY RULES rather than hand-written per symptom:
for every rule that is more urgent than the current level and that the case already
partly matches (one of its concepts is present), we ask about exactly the information
the rule still needs:
    missing concepts      -> one "do you also have any of these?" checklist
    onset: sudden         -> "did the <symptom> start suddenly or gradually?"
    severity: severe      -> 0-10 pain/discomfort score
    min_duration_days     -> "how long have you had the <symptom>?"
    context: pregnant     -> "is the person pregnant?"
    max_age_months / ML   -> age (if unknown)
Plus a pain score for pain-type symptoms (a model feature).

Guarantees (tested):
  * NO questions when an emergency is already identified (do not delay emergency care);
  * unrecognised text -> an explicit emergency-sign checklist instead of guessing;
  * no question about something the user has already answered or explicitly denied.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from mediguide.knowledge import KNOWLEDGE_DIR, Knowledge, load_knowledge, load_yaml
from mediguide.nlp.attributes import pain_band
from mediguide.nlp.schema import Extraction, Finding
from mediguide.safety.engine import LEVEL_ORDER, SafetyResult

PAIN_CONCEPTS = {"chest_pain", "chest_tightness", "abdominal_pain", "headache", "back_pain", "neck_pain",
                 "limb_joint_pain", "body_ache", "flank_pain", "ear_pain", "sore_throat", "toothache",
                 "eye_pain", "pelvic_pain", "painful_urination"}
EMERGENCY_CHECKLIST = ["severe_breathing_distress", "chest_pain", "face_droop", "focal_weakness",
                       "speech_difficulty", "unconsciousness", "seizure", "heavy_bleeding",
                       "face_throat_swelling", "confusion", "suicidal_thoughts"]
DURATION_DAYS = {"lt1": 0.5, "d1_4": 2.5, "d5p": 5.0}
MAX_CHECKLIST = 10


@dataclass
class Option:
    value: str
    text: dict[str, str]


@dataclass
class Question:
    id: str                       # "age", "pain", "onset:<concept>", "duration:<concept>", "checklist", ...
    kind: str                     # number | choice | multi | yesno
    text: dict[str, str]
    options: list[Option] = field(default_factory=list)
    min: float | None = None
    max: float | None = None
    reason: str = ""              # which rule(s) made this question necessary (for the report/tests)


@lru_cache(maxsize=1)
def load_templates(directory: Path = KNOWLEDGE_DIR) -> dict:
    return load_yaml(directory / "templates.yaml")


def _fill(texts: dict[str, str], **kw) -> dict[str, str]:
    return {lang: t.format(**{k: v[lang] for k, v in kw.items()}) for lang, t in texts.items()}


def _contradicted(clause: dict, targets: list[Finding]) -> bool:
    """True if already-known attributes make the clause impossible, so asking is pointless
    (e.g. pain 3/10 already given -> a 'severity: severe' clause cannot match)."""
    if not targets:
        return False
    if "severity" in clause and all((f.severity or f.pain_score is not None) for f in targets)             and not any(f.severity == "severe" for f in targets):
        return True
    if clause.get("onset") == "sudden" and all(f.onset for f in targets) and not any(f.onset == "sudden" for f in targets):
        return True
    if "min_duration_days" in clause and all(f.duration_days is not None for f in targets)             and not any(f.duration_days >= clause["min_duration_days"] for f in targets):
        return True
    return False


def _label(concept, lower_en: bool = True) -> dict[str, str]:
    """Concept label for use INSIDE a sentence (English lower-cased)."""
    return {k: (v[0].lower() + v[1:] if k == "en" and lower_en else v) for k, v in concept.label.items()}


def generate(ext: Extraction, safety: SafetyResult, age_years: float | None = None,
             sex: str | None = None, kb: Knowledge | None = None) -> list[Question]:
    kb = kb or load_knowledge()
    t = load_templates()["questions"]
    if safety.is_emergency:
        return []

    questions: list[Question] = []
    age = age_years if age_years is not None else ext.age_years
    if not safety.understood:
        questions.append(Question(
            id="emergency_checklist", kind="multi", text=t["emergency_checklist"],
            options=[Option(c, kb.concepts[c].label) for c in EMERGENCY_CHECKLIST] +
                    [Option("none", t["none_of_these"])], reason="text not understood"))
        if age is None:
            questions.append(Question(id="age", kind="number", text=t["age"], min=0, max=120, reason="model input"))
        return questions

    present = ext.findings
    denied = set(ext.negated)
    current = LEVEL_ORDER.get(safety.level or "", 0)
    checklist: dict[str, list[str]] = {}
    onset_for: dict[str, list[str]] = {}
    duration_for: dict[str, list[str]] = {}
    need_pain, need_pregnant = [], []

    for rule in kb.rules:
        if LEVEL_ORDER[rule.level] <= current:
            continue  # cannot change the outcome
        for clause in rule.match:
            ids = list(clause.get("all", [])) + list(clause.get("any", []))
            if not any(c in present for c in ids + list(clause.get("context", []))):
                continue  # clause does not touch this case
            targets_known = [present[c] for c in ids if c in present]
            if _contradicted(clause, targets_known):
                continue  # what the user already told us rules this clause out
            missing = [c for c in clause.get("all", []) if c not in present]
            any_ids = clause.get("any", [])
            if any_ids and not any(c in present for c in any_ids):
                missing += any_ids
            missing = [c for c in missing if c not in denied]
            for c in missing:
                checklist.setdefault(c, []).append(rule.id)
            targets = [c for c in ids if c in present]
            if clause.get("onset") == "sudden":
                for c in targets:
                    if present[c].onset is None:
                        onset_for.setdefault(c, []).append(rule.id)
            if "severity" in clause and not any(present[c].severity or present[c].pain_score is not None
                                                for c in targets):
                need_pain.append(rule.id)
            if "min_duration_days" in clause:
                for c in targets:
                    if present[c].duration_days is None:
                        duration_for.setdefault(c, []).append(rule.id)
            for c in clause.get("context", []):
                if c not in present and c not in denied:
                    need_pregnant.append(rule.id)

    # 1. checklist of missing warning features (safety first)
    options = [Option(c, kb.concepts[c].label) for c in checklist if kb.concepts[c].kind != "context"][:MAX_CHECKLIST]
    if options:
        questions.append(Question(id="checklist", kind="multi", text=t["checklist"],
                                  options=options + [Option("none", t["none_of_these"])],
                                  reason=",".join(sorted({r for c in checklist for r in checklist[c]}))))
    # 2. age (model input + infant rules)
    if age is None:
        questions.append(Question(id="age", kind="number", text=t["age"], min=0, max=120, reason="model input"))
    # 3. onset for rules that need "sudden"
    for c, rules in onset_for.items():
        questions.append(Question(id=f"onset:{c}", kind="choice", text=_fill(t["onset"], symptom=_label(kb.concepts[c])),
                                  options=[Option(k, v) for k, v in t["onset_options"].items()],
                                  reason=",".join(sorted(set(rules)))))
    # 4. pain score (rules needing severity, or a pain-type symptom for the model)
    has_pain_info = any(f.pain_score is not None or f.severity for f in present.values())
    if not has_pain_info and (need_pain or PAIN_CONCEPTS & set(present)):
        questions.append(Question(id="pain", kind="number", text=t["pain"], min=0, max=10,
                                  reason=",".join(sorted(set(need_pain))) or "model input"))
    # 5. duration where a rule needs it
    for c, rules in duration_for.items():
        questions.append(Question(id=f"duration:{c}", kind="choice",
                                  text=_fill(t["duration"], symptom=_label(kb.concepts[c])),
                                  options=[Option(k, v) for k, v in t["duration_options"].items()],
                                  reason=",".join(sorted(set(rules)))))
    # 6. pregnancy, only when plausible
    plausible = sex != "M" and (age is None or 10 <= age <= 55)
    if need_pregnant and plausible:
        questions.append(Question(id="pregnant", kind="yesno", text=t["pregnant"],
                                  options=[Option(k, v) for k, v in t["yes_no"].items()],
                                  reason=",".join(sorted(set(need_pregnant)))))
    return questions


def apply_answers(ext: Extraction, answers: dict, age_years: float | None = None,
                  kb: Knowledge | None = None) -> tuple[Extraction, float | None]:
    """Return an UPDATED COPY of the extraction plus the (possibly new) age."""
    kb = kb or load_knowledge()
    new = copy.deepcopy(ext)
    age = age_years if age_years is not None else ext.age_years

    def add(cid: str) -> None:
        if cid not in kb.concepts or cid in new.findings:
            return
        c = kb.concepts[cid]
        new.findings[cid] = Finding(concept_id=cid, kind=c.kind, evidence=["follow-up answer"])
        if cid in new.negated:
            new.negated.remove(cid)
        for imp in c.implies:
            add(imp)

    for key in ("checklist", "emergency_checklist"):
        for cid in answers.get(key, []) or []:
            if cid != "none":
                add(cid)
    if answers.get("age") is not None:
        age = float(answers["age"])
    if answers.get("pain") is not None:
        score = int(answers["pain"])
        band = pain_band(score)
        for f in new.findings.values():
            if f.kind == "symptom":
                f.pain_score = score
                if band:
                    f.severity = band
    for key, value in answers.items():
        if key.startswith("onset:") and key[6:] in new.findings and value in ("sudden", "gradual"):
            new.findings[key[6:]].onset = value
        if key.startswith("duration:") and key[9:] in new.findings and value in DURATION_DAYS:
            new.findings[key[9:]].duration_days = DURATION_DAYS[value]
    if answers.get("pregnant") == "yes":
        add("pregnant")
    elif answers.get("pregnant") == "no" and "pregnant" not in new.negated:
        new.negated.append("pregnant")
    return new, age
