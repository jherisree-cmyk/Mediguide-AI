"""Phase 7 tests: follow-up questions, recommendation, templates."""
import re
import sys
from pathlib import Path

import pytest
import yaml

from mediguide.followup.questions import apply_answers, load_templates
from mediguide.knowledge import load_knowledge
from mediguide.nlp.extractor import extract
from mediguide.recommend.engine import assess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from eval_followup import check_e2e_case, check_question_case  # noqa: E402

DATA = yaml.safe_load((ROOT / "data/synthetic/followup_cases.yaml").read_text(encoding="utf-8"))
SCRIPT = {"te": re.compile(r"[ఀ-౿]"), "hi": re.compile(r"[ऀ-ॿ]")}


@pytest.mark.parametrize("case", DATA["questions"], ids=[c["id"] for c in DATA["questions"]])
def test_question_generation(case):
    assert check_question_case(case) == []


@pytest.mark.parametrize("case", DATA["end_to_end"], ids=[c["id"] for c in DATA["end_to_end"]])
def test_end_to_end(case):
    assert check_e2e_case(case) == []


# ---- safety architecture --------------------------------------------------------------------
def test_ml_cannot_lower_rule_level():
    """Chest pain (rule floor URGENT) in a young person with mild pain: ML says ROUTINE, final stays URGENT."""
    a = assess("chest pain that comes and goes, 2/10", answers={"checklist": ["none"], "age": 19,
                                                                "onset:chest_pain": "gradual"})
    assert a.trace["rule_level"] == "URGENT"
    assert a.level == "URGENT"


def test_emergency_never_waits_for_questions_or_ml():
    a = assess("I can't breathe")
    assert a.level == "EMERGENCY" and a.questions == [] and a.trace["ml_level"] is None
    assert {"112", "108"} <= {c["number"] for c in a.emergency_contacts}


def test_unclear_input_is_never_reassuring():
    a = assess("blah blah", answers={"emergency_checklist": ["none"], "age": 30})
    assert a.level == "URGENT" and a.notes


def test_routine_result_has_safety_net_and_self_care():
    a = assess("runny nose and sneezing, I am 25 years old")
    assert a.level == "ROUTINE" and a.safety_net["items"] and a.self_care_info
    assert a.emergency_contacts == []


def test_emergency_result_has_no_self_care_advice():
    a = assess("I can't breathe")
    assert a.self_care_info == "" and a.safety_net == {}


def test_mental_health_support_shown():
    assert "14416" in assess("I want to end my life").support


def test_display_language_override():
    a = assess("I can't breathe", display_lang="te")
    assert SCRIPT["te"].search(a.level_text) and SCRIPT["te"].search(a.next_step)
    assert SCRIPT["te"].search(a.warnings[0]["title"])


def test_disclaimer_always_present():
    for text in ("I can't breathe", "runny nose, I am 25 years old", "blah"):
        assert "diagnose" in assess(text).disclaimer


def test_apply_answers_does_not_modify_original():
    ext = extract("I have chest pain")
    new, age = apply_answers(ext, {"checklist": ["sweating"], "age": 50, "pain": 8})
    assert "sweating" not in ext.findings and "sweating" in new.findings and age == 50
    assert ext.findings["chest_pain"].pain_score is None


# ---- templates --------------------------------------------------------------------------------
def _leaves(node, path=""):
    if isinstance(node, dict):
        if set(node) >= {"en", "te", "hi"}:
            yield path, node
        else:
            for k, v in node.items():
                yield from _leaves(v, f"{path}.{k}")


def test_every_template_has_all_languages_in_the_right_script():
    tpl = load_templates()
    for path, texts in _leaves({k: v for k, v in tpl.items() if k != "rule_titles"}):
        for lang in ("te", "hi"):
            items = texts[lang] if isinstance(texts[lang], list) else [texts[lang]]
            for item in items:
                assert SCRIPT[lang].search(item), f"{path}.{lang} not in {lang} script: {item}"


def test_every_rule_has_translated_title():
    titles = load_templates()["rule_titles"]
    for rule in load_knowledge().rules:
        assert rule.id in titles and titles[rule.id].get("te") and titles[rule.id].get("hi"), rule.id


def test_template_entries_have_exactly_three_languages():
    """Unquoted commas in YAML {...} silently create extra keys; every text entry must have
    exactly en/te/hi (rule titles: te/hi)."""
    def walk(node, path):
        if isinstance(node, dict):
            langs = {"en", "te", "hi"} & set(node)
            if langs:
                expected = {"te", "hi"} if path.startswith(".rule_titles") else {"en", "te", "hi"}
                assert set(node) == expected, f"{path}: keys {sorted(node)}"
            else:
                for k, v in node.items():
                    walk(v, f"{path}.{k}")
    walk(load_templates(), "")
