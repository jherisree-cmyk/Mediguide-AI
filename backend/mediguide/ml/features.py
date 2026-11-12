"""Feature construction shared by TRAINING (NHAMCS rows) and PREDICTION (app users).

Using one module for both prevents "train/serve skew", where the model is trained on
features built one way and used on features built another way.

Features (all things a patient can tell the app at home; NO vital signs, NO hospital data):
  sym_<id>      1 if the symptom is present (62 symptoms from knowledge/symptoms.yaml)
  age_years     patient age
  pain_known    1 if a 0-10 pain score is available
  pain_score    0-10 (0 when unknown; pain_known tells the model it is unknown)
  n_symptoms    number of distinct symptoms reported

Sex is deliberately NOT used: the app cannot always know it, and a model feature that is
often missing at prediction time would behave differently from training.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mediguide.knowledge import Knowledge, load_knowledge

RFV_COLS = [f"RFV{i}" for i in range(1, 6)]
# Severity words -> approximate pain score, used ONLY when the user gave no number.
# This is an assumption of this project (documented in the model card), not a validated scale.
SEVERITY_TO_PAIN = {"mild": 2, "moderate": 5, "severe": 8}


def feature_names(kb: Knowledge | None = None) -> list[str]:
    kb = kb or load_knowledge()
    return [f"sym_{s}" for s in sorted(kb.symptom_ids())] + ["age_years", "pain_known", "pain_score", "n_symptoms"]


def from_nhamcs(df: pd.DataFrame, kb: Knowledge | None = None) -> pd.DataFrame:
    """One feature row per NHAMCS visit."""
    kb = kb or load_knowledge()
    rfv_map = kb.rfv_to_symptom()
    out = pd.DataFrame(index=df.index)
    codes = df[RFV_COLS]
    for sid in sorted(kb.symptom_ids()):
        own = [c for c, s in rfv_map.items() if s == sid]
        out[f"sym_{sid}"] = codes.isin(own).any(axis=1).astype(np.int8)
    out["age_years"] = df["AGE"].astype(float)
    out["pain_known"] = df["PAINSCALE"].notna().astype(np.int8)
    out["pain_score"] = df["PAINSCALE"].fillna(0).astype(float)
    out["n_symptoms"] = out[[c for c in out if c.startswith("sym_")]].sum(axis=1).astype(np.int16)
    return out


def from_findings(symptoms: set[str], age_years: float, pain_score: float | None = None,
                  severities: list[str] | None = None, kb: Knowledge | None = None) -> pd.DataFrame:
    """One feature row for an app user. `symptoms` = present symptom concept ids."""
    kb = kb or load_knowledge()
    row = {f"sym_{s}": int(s in symptoms) for s in sorted(kb.symptom_ids())}
    if pain_score is None and severities:
        known = [SEVERITY_TO_PAIN[s] for s in severities if s in SEVERITY_TO_PAIN]
        pain_score = max(known) if known else None
    row["age_years"] = float(age_years)
    row["pain_known"] = int(pain_score is not None)
    row["pain_score"] = float(pain_score or 0)
    row["n_symptoms"] = sum(v for k, v in row.items() if k.startswith("sym_"))
    return pd.DataFrame([row], columns=feature_names(kb))
