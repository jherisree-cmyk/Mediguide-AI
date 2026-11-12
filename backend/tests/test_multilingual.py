"""Phase 4 tests: language detection, normalisation, Telugu/Hindi extraction."""
from pathlib import Path

import pytest
import yaml

from mediguide.multilingual.langdetect import detect_language
from mediguide.multilingual.normalise import normalise
from mediguide.multilingual.pipeline import analyse
from mediguide.nlp.extractor import extract

ROOT = Path(__file__).resolve().parents[2]


def _cases(lang):
    data = yaml.safe_load((ROOT / f"data/synthetic/{lang}_extraction_dev.yaml").read_text(encoding="utf-8"))
    return [(lang, c) for c in data["cases"]]


@pytest.mark.parametrize("lang,case", _cases("te") + _cases("hi"), ids=lambda x: x["id"] if isinstance(x, dict) else x)
def test_dev_case(lang, case):
    ext = extract(case["text"], lang)
    assert set(ext.findings) == set(case.get("present", [])), (case["text"], ext.findings.keys())
    assert set(case.get("negated", [])) <= set(ext.negated)
    for cid, attrs in (case.get("attrs") or {}).items():
        for key, want in attrs.items():
            got = getattr(ext.findings[cid], key)
            assert got == pytest.approx(want) if isinstance(want, float) else got == want, (cid, key, got)
    if "subject" in case:
        assert ext.subject == case["subject"]


@pytest.mark.parametrize("text,lang", [("నాకు జ్వరం ఉంది", "te"), ("मुझे बुखार है", "hi"), ("I have a fever", "en"),
                                       ("నాకు fever ఉంది", "te"), ("मुझे fever है", "hi")])
def test_language_detection(text, lang):
    assert detect_language(text).lang == lang


def test_code_mixed_flag():
    assert detect_language("నాకు fever ఉంది").mixed is True
    assert detect_language("నాకు జ్వరం ఉంది").mixed is False


def test_digits_only_is_not_confident():
    assert detect_language("123").confident is False


def test_hindi_normalisation():
    assert normalise("बुख़ार", "hi") == normalise("बुखार", "hi")      # nukta
    assert normalise("उल्टियाँ", "hi") == normalise("उल्टियां", "hi")  # chandrabindu
    assert normalise("३ दिन", "hi") == "3 दिन"                         # digits
    assert normalise("౩ రోజులు", "te").startswith("3")


def test_same_concept_id_in_all_three_languages():
    """The language-neutral concept id is the shared internal representation."""
    texts = {"en": "I have a headache and fever", "te": "నాకు తలనొప్పి మరియు జ్వరం ఉంది", "hi": "मुझे सिरदर्द और बुखार है"}
    results = {lang: set(analyse(t)[1].findings) for lang, t in texts.items()}
    assert results["en"] == results["te"] == results["hi"] == {"headache", "fever"}


@pytest.mark.parametrize("text,lang", [("చలికాలంలో నాకు ఏ సమస్యా లేదు", "te"),   # winter is not chills
                                       ("कल मैं बाजार गया था, कोई परेशानी नहीं है", "hi")])
def test_no_false_positives(text, lang):
    assert extract(text, lang).findings == {}


def test_telugu_negated_severity_keeps_symptom():
    ext = extract("తలనొప్పి ఎక్కువగా లేదు", "te")   # "the headache is not severe"
    assert "headache" in ext.findings and ext.findings["headache"].severity is None


def test_telugu_phrase_with_negation_word_is_a_warning_sign():
    ext = extract("ఊపిరి అందడం లేదు", "te")          # "I can't breathe"
    assert "severe_breathing_distress" in ext.findings


def test_user_choice_overrides_detection():
    det, ext = analyse("I have fever", lang="hi")    # Hindi extractor still matches English terms
    assert det.lang == "en" and ext.language == "hi" and "fever" in ext.findings


# Phase 12 (found by live detection): "ఊపిరి ఆడటం లేదు" means "I can't breathe", not "unconscious".
@pytest.mark.parametrize("text,expected,not_expected", [
    ("నాకు ఊపిరి ఆడటం లేదు", "severe_breathing_distress", "unconsciousness"),
    ("ఊపిరి ఆడట్లేదు", "severe_breathing_distress", "unconsciousness"),
    ("బాబు ఊపిరి తీసుకోవడం లేదు", "unconsciousness", None),
    ("నాకు ఊపిరి ఆడటం కష్టంగా ఉంది", "shortness_of_breath", "severe_breathing_distress"),
])
def test_telugu_breathing_phrases(text, expected, not_expected):
    found = analyse(text, "te")[1].present()
    assert expected in found
    assert not_expected is None or not_expected not in found
