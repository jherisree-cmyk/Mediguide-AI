"""Urgency recommendation and explanation (Modules 7 + 8): the full assessment flow.

    text --(language detection + NLP)--> Extraction
         --(follow-up answers, if any)--> updated Extraction
         --(red-flag rules)----------------> EMERGENCY?  -> stop: emergency result, no questions
         --(follow-up questions needed?)--> return questions
         --(depth-6 Decision Tree, capped at URGENT)
         --> FINAL LEVEL = most urgent of (rules, model)
         --> result text from knowledge/templates.yaml in the user's language

Conservative fallbacks (never falsely reassuring):
  * nothing understood (even after the emergency checklist) -> URGENT + "we could not understand"
  * age unknown -> the model cannot run -> at least URGENT
  * every URGENT/ROUTINE result carries safety-netting; ROUTINE also carries self-care info
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from mediguide.followup.questions import Question, apply_answers, generate, load_templates
from mediguide.knowledge import load_knowledge
from mediguide.ml.predictor import predict
from mediguide.multilingual.pipeline import SUPPORTED, analyse
from mediguide.safety.engine import evaluate

ORDER = {"ROUTINE": 0, "URGENT": 1, "EMERGENCY": 2}
MENTAL_HEALTH = {"suicidal_thoughts", "hallucinations", "low_mood"}


@dataclass
class Assessment:
    status: str                                   # "needs_followup" | "complete"
    input_language: str
    display_language: str
    questions: list[Question] = field(default_factory=list)
    level: str | None = None                      # EMERGENCY | URGENT | ROUTINE (complete only)
    preliminary_level: str | None = None          # level from rules so far (needs_followup)
    level_text: str = ""
    next_step: str = ""
    notes: list[str] = field(default_factory=list)
    symptoms: list[dict] = field(default_factory=list)       # [{id, label, severity, duration_days, ...}]
    denied: list[str] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)       # fired rules with sources and quotes
    model_path: list[str] = field(default_factory=list)
    safety_net: dict = field(default_factory=dict)
    self_care_info: str = ""
    support: str = ""
    emergency_contacts: list[dict] = field(default_factory=list)
    disclaimer: str = ""
    prototype_notice: str = ""
    corrections: list[list[str]] = field(default_factory=list)
    trace: dict = field(default_factory=dict)                # rule level, ML level, probabilities

    def to_dict(self) -> dict:
        return asdict(self)


def assess(text: str, lang: str | None = None, display_lang: str | None = None,
           answers: dict | None = None, age_years: float | None = None, sex: str | None = None) -> Assessment:
    kb = load_knowledge()
    tpl = load_templates()
    detection, ext = analyse(text, lang)
    in_lang = ext.language
    out = display_lang if display_lang in SUPPORTED else in_lang
    age = age_years if age_years is not None else ext.age_years
    if answers:
        ext, age = apply_answers(ext, answers, age, kb)

    safety = evaluate(ext, age)
    a = Assessment(status="complete", input_language=in_lang, display_language=out,
                   disclaimer=tpl["disclaimer"][out], prototype_notice=tpl["prototype_notice"][out],
                   corrections=[list(c) for c in ext.corrections])
    _describe_findings(a, ext, kb, tpl, out, safety)

    if safety.is_emergency:                      # no questions, no ML: emergency guidance now
        return _finish(a, "EMERGENCY", tpl, out, safety, ext, ml=None)

    if answers is None:
        qs = generate(ext, safety, age, sex, kb)
        if qs:
            a.status = "needs_followup"
            a.questions = qs
            a.preliminary_level = safety.level
            return a

    if not ext.findings:                         # still nothing understood
        a.notes.append(tpl["unclear_input"][out])
        return _finish(a, "URGENT", tpl, out, safety, ext, ml=None)

    rule_level = safety.level or "ROUTINE"
    if age is None:
        a.notes.append(tpl["age_missing"][out])
        return _finish(a, max(rule_level, "URGENT", key=ORDER.get), tpl, out, safety, ext, ml=None)

    ml = predict(ext, age) if ext.present("symptom") else None
    ml_level = ml.level if ml else "ROUTINE"
    final = max(rule_level, ml_level, key=ORDER.get)
    if ml:
        a.model_path = [c.text[out] for c in ml.path]
        if ml.high_emergency_probability and final != "EMERGENCY":
            a.notes.append(tpl["high_emergency_probability"][out])
    return _finish(a, final, tpl, out, safety, ext, ml)


# ------------------------------------------------------------------------------------------
def _describe_findings(a: Assessment, ext, kb, tpl, out: str, safety) -> None:
    for cid, f in ext.findings.items():
        a.symptoms.append({"id": cid, "kind": f.kind, "label": kb.concepts[cid].label[out],
                           "severity": f.severity, "pain_score": f.pain_score, "duration_days": f.duration_days,
                           "onset": f.onset, "progression": f.progression, "uncertain": f.hedged,
                           "evidence": f.evidence})
    a.denied = [kb.concepts[c].label[out] for c in ext.negated]
    titles = tpl["rule_titles"]
    for r in safety.fired:
        a.warnings.append({"rule": r.id, "level": r.level,
                           "title": r.title if out == "en" else titles.get(r.id, {}).get(out, r.title),
                           "because_of": [kb.concepts[c].label[out] for c in r.matched_concepts if c in kb.concepts],
                           "guidance_quote_en": r.quote,
                           "sources": [{"title": s["title"], "publisher": s["publisher"], "url": s["url"]}
                                       for s in r.sources if s.get("url")]})


def _finish(a: Assessment, level: str, tpl, out: str, safety, ext, ml) -> Assessment:
    a.level = level
    a.level_text = tpl["levels"][level][out]
    a.next_step = tpl["next_step"][level][out]
    if level == "EMERGENCY":
        a.emergency_contacts = safety.emergency_contacts or load_knowledge().emergency_contacts
    else:
        a.safety_net = {"title": tpl["safety_net"]["title"][out], "items": tpl["safety_net"]["items"][out]}
    if level == "ROUTINE":
        a.self_care_info = tpl["self_care_info"][out]
    if MENTAL_HEALTH & set(ext.findings):
        a.support = tpl["mental_health_support"][out]
    a.trace = {"rule_level": safety.level, "ml_level": ml.level if ml else None,
               "ml_probabilities": ml.probabilities if ml else None,
               "ml_high_emergency_probability": ml.high_emergency_probability if ml else None,
               "model_version": ml.model_version if ml else None}
    return a


# ------------------------------------------------------------------------------------------
def preview(text: str, lang: str | None = None, display_lang: str | None = None,
            age_years: float | None = None) -> dict:
    """Live "what we understood so far" while the user types (stateless: nothing stored).

    Shows the extracted concepts and whether an EMERGENCY warning sign is already present, so the
    user can be told to check now. It never shows ROUTINE/URGENT: that needs the full assessment.
    """
    kb = load_knowledge()
    detection, ext = analyse(text, lang)
    out = display_lang if display_lang in SUPPORTED else ext.language
    safety = evaluate(ext, age_years if age_years is not None else ext.age_years)
    return {
        "input_language": ext.language,
        "detected_language": detection.lang,
        "symptoms": [{"id": cid, "kind": f.kind, "label": kb.concepts[cid].label[out], "uncertain": f.hedged}
                     for cid, f in ext.findings.items()],
        "denied": [{"id": c, "label": kb.concepts[c].label[out]} for c in ext.negated],
        "emergency_sign": safety.is_emergency,
    }
