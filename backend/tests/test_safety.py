"""Phase 5 tests: red-flag rule engine."""
import ast
from pathlib import Path

import pytest
import yaml

from mediguide.nlp.extractor import extract
from mediguide.nlp.schema import Extraction, Finding
from mediguide.safety.engine import SafetyEngine, evaluate

ROOT = Path(__file__).resolve().parents[2]
CASES = yaml.safe_load((ROOT / "data/synthetic/safety_cases.yaml").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_safety_case(case):
    res = evaluate(extract(case["text"], case["lang"]))
    assert (res.level or "NONE") == case["level"]
    assert set(case.get("rules", [])) <= {f.id for f in res.fired}
    if "understood" in case:
        assert res.understood == case["understood"]


# ---- architecture: safety logic is independent of machine learning -----------------------
def test_safety_package_never_imports_ml():
    for py in (ROOT / "backend/mediguide/safety").rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert not n.startswith("mediguide.ml") and "sklearn" not in n, f"{py.name} imports {n}"


# ---- clause logic on hand-built findings (no NLP involved) -------------------------------
def _ext(*findings, age=None):
    e = Extraction(language="en", original_text="", normalised_text="", age_years=age)
    for f in findings:
        e.findings[f.concept_id] = f
    return e


def F(cid, kind="symptom", **kw):
    return Finding(concept_id=cid, kind=kind, **kw)


def test_unknown_age_never_satisfies_age_rule():
    assert "EM_INFANT_FEVER" not in {f.id for f in evaluate(_ext(F("fever"))).fired}


def test_profile_age_overrides_text_age():
    res = SafetyEngine().evaluate(_ext(F("fever"), age=30), age_years=0.1)
    assert res.is_emergency and "EM_INFANT_FEVER" in {f.id for f in res.fired}


def test_hedged_finding_still_counts():
    assert evaluate(_ext(F("chest_pain", hedged=True))).level == "URGENT"


def test_confusion_with_unknown_onset_is_emergency_but_gradual_is_urgent():
    assert evaluate(_ext(F("confusion"))).level == "EMERGENCY"
    assert evaluate(_ext(F("confusion", onset="gradual"))).level == "URGENT"


def test_severity_condition_uses_rule_targets_only():
    # severe back pain + (non-severe) chest pain: EM_CHEST_PAIN's severity clause must NOT fire
    res = evaluate(_ext(F("chest_pain"), F("back_pain", severity="severe")))
    assert res.level == "URGENT" and "EM_CHEST_PAIN" not in {f.id for f in res.fired}


def test_negated_symptom_does_not_fire():
    res = evaluate(extract("I have no chest pain and no shortness of breath"))
    assert res.level is None


def test_emergency_result_carries_contacts_and_sources():
    res = evaluate(extract("I can't breathe"))
    assert res.is_emergency
    assert {"112", "108"} <= {c["number"] for c in res.emergency_contacts}
    assert all(s["url"].startswith("https://") for s in res.fired[0].sources if s["key"] != "project_policy")
    assert res.fired[0].quote


def test_most_urgent_rule_listed_first():
    res = evaluate(extract("chest pain spreading to my left arm"))
    assert res.fired[0].level == "EMERGENCY" and any(f.level == "URGENT" for f in res.fired)


def test_unrecognised_text_is_flagged():
    res = evaluate(extract("blah blah nothing medical here"))
    assert res.level is None and res.understood is False
