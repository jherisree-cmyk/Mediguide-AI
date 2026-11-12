"""Phase 3 tests: English symptom extraction.

1. Regression: every case in the dev set must stay correct.
2. Focused unit tests for the safety-relevant behaviours (negation, phrases containing
   negation words, severity, duration, implied symptoms).
The held-out set is NOT a test: it is scored by scripts/eval_extraction.py and reported.
"""
from pathlib import Path

import pytest
import yaml

from mediguide.knowledge import load_yaml
from mediguide.nlp.attributes import find_age_years, find_durations
from mediguide.nlp.extractor import extract

ROOT = Path(__file__).resolve().parents[2]
DEV = yaml.safe_load((ROOT / "data/synthetic/en_extraction_dev.yaml").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", DEV, ids=[c["id"] for c in DEV])
def test_dev_case(case):
    ext = extract(case["text"])
    assert set(ext.findings) == set(case.get("present", [])), ext.findings.keys()
    assert set(case.get("negated", [])) <= set(ext.negated)
    for cid, attrs in (case.get("attrs") or {}).items():
        for key, want in attrs.items():
            got = getattr(ext.findings[cid], key)
            assert got == pytest.approx(want) if isinstance(want, float) else got == want, (cid, key, got)


def test_negation_does_not_remove_phrase_with_negation_inside():
    # "can't breathe" is a warning sign, NOT a negated symptom
    assert "severe_breathing_distress" in extract("I can't breathe").findings


def test_negated_and_affirmed_mentions_keep_symptom_present():
    ext = extract("No fever yesterday but today I have a fever")
    assert "fever" in ext.findings and ext.findings["fever"].conflict


def test_negation_scope_stops_at_but():
    ext = extract("no cough but chest pain")
    assert "chest_pain" in ext.findings and "cough" in ext.negated


def test_sudden_onset_wins_over_gradual():
    ext = extract("The headache came on gradually, then suddenly got much worse")
    assert ext.findings["headache"].onset == "sudden"


def test_implied_symptom_from_sign():
    ext = extract("worst headache of my life")
    assert {"thunderclap_headache", "headache"} <= set(ext.findings)


def test_spelling_corrections_are_reported():
    ext = extract("terrible feaver")
    assert ("feaver", "fever") in ext.corrections


def test_no_false_spelling_correction_of_ordinary_words():
    ext = extract("I had fewer problems swearing at my brother")
    assert ext.findings == {} and ext.corrections == []


@pytest.mark.parametrize("text,days", [("for 3 days", 3), ("2 weeks ago", 14), ("since yesterday", 1),
                                       ("for the past week", 7), ("it has been 5 days", 5), ("for half an hour", 1 / 48)])
def test_durations(text, days):
    found = find_durations(text)
    assert found and found[0][2] == pytest.approx(days, abs=1e-3)


@pytest.mark.parametrize("text,years", [("I am 45 years old", 45), ("my 6 month old", 0.5), ("a 3-week-old baby", 3 * 7 / 365)])
def test_age(text, years):
    assert find_age_years(text) == pytest.approx(years, abs=1e-3)


def test_duplicate_yaml_keys_are_rejected(tmp_path):
    f = tmp_path / "dup.yaml"
    f.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate key"):
        load_yaml(f)
