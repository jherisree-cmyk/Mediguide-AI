"""Phase 6 tests: the app's Decision Tree predictor."""
import itertools
import random

import pytest

from mediguide.knowledge import load_knowledge
from mediguide.ml.predictor import get_predictor, predict
from mediguide.nlp.extractor import extract
from mediguide.nlp.schema import Extraction, Finding


def test_model_metadata_matches_policy():
    meta = get_predictor().meta
    assert meta["params"]["max_depth"] == 6
    assert "capped at URGENT" in meta["app_policy"]
    assert meta["thresholds"]["t_urgent_or_higher"] == pytest.approx(0.45)


def test_ml_never_outputs_emergency():
    """Random symptom combinations, ages and pain scores: the ML level is URGENT or ROUTINE only."""
    rng = random.Random(0)
    symptoms = load_knowledge().symptom_ids()
    for _ in range(300):
        ext = Extraction(language="en", original_text="", normalised_text="")
        for s in rng.sample(symptoms, rng.randint(1, 5)):
            ext.findings[s] = Finding(concept_id=s, kind="symptom")
        res = predict(ext, age_years=rng.uniform(0, 95), pain_score=rng.choice([None, 0, 3, 7, 10]))
        assert res.level in {"URGENT", "ROUTINE"}


def test_explanation_path_is_short_and_multilingual():
    res = predict(extract("chest pain and shortness of breath"), age_years=60)
    assert 1 <= len(res.path) <= 6
    for cond in res.path:
        assert set(cond.text) == {"en", "te", "hi"} and all(cond.text.values())


def test_prediction_is_deterministic():
    ext = extract("stomach pain and vomiting")
    a, b = predict(ext, 30), predict(ext, 30)
    assert a.level == b.level and a.probabilities == b.probabilities


def test_unknown_pain_is_explained_as_not_given():
    res = predict(extract("मुझे पेट दर्द और उल्टी है", "hi"), 30)
    texts = [c.text["en"] for c in res.path]
    assert not any(t.startswith("pain score ≤") for t in texts)


def test_probabilities_sum_to_one():
    res = predict(extract("cough"), 25)
    assert sum(res.probabilities.values()) == pytest.approx(1.0)
