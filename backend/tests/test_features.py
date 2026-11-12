"""Phase 6 tests: features are built identically for training and for the live app."""
import numpy as np
import pandas as pd

from mediguide.knowledge import load_knowledge
from mediguide.ml.features import feature_names, from_findings, from_nhamcs


def test_training_and_app_features_are_identical():
    kb = load_knowledge()
    # NHAMCS visit: chest pain (10501) + shortness of breath (14150), age 58, pain 7
    row = pd.DataFrame([{"RFV1": 10501, "RFV2": 14150, "RFV3": np.nan, "RFV4": np.nan, "RFV5": np.nan,
                         "AGE": 58, "PAINSCALE": 7}])
    train = from_nhamcs(row, kb)
    app = from_findings({"chest_pain", "shortness_of_breath"}, age_years=58, pain_score=7, kb=kb)
    assert list(train.columns) == list(app.columns) == feature_names(kb)
    np.testing.assert_array_equal(train.to_numpy(dtype=float), app.to_numpy(dtype=float))


def test_unknown_pain_is_encoded_explicitly():
    x = from_findings({"cough"}, age_years=30)
    assert x["pain_known"].iloc[0] == 0 and x["pain_score"].iloc[0] == 0


def test_severity_word_used_only_when_no_number():
    assert from_findings({"headache"}, 30, severities=["severe"])["pain_score"].iloc[0] == 8
    assert from_findings({"headache"}, 30, pain_score=3, severities=["severe"])["pain_score"].iloc[0] == 3


def test_signs_and_context_are_not_model_features():
    names = feature_names()
    assert "sym_radiating_pain" not in names and "sym_pregnant" not in names
