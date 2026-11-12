"""Decision Tree prediction for the app (Module 6), with a plain-language explanation.

APP POLICY: the model can only return URGENT or ROUTINE. EMERGENCY comes only from the
independent red-flag rules (mediguide.safety). A high predicted emergency probability is
reported as a flag so the recommendation can say "get seen today".

The explanation is the path the case takes through the depth-6 tree, e.g.
    chest pain: yes  ->  age > 52.5  ->  pain score unknown
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import joblib

from mediguide.knowledge import load_knowledge
from mediguide.ml.features import from_findings
from mediguide.nlp.schema import Extraction

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models"


@dataclass
class Condition:
    feature: str
    text: dict[str, str]       # human-readable condition per language (en/te/hi)


@dataclass
class MLResult:
    level: str                               # "URGENT" | "ROUTINE"  (never EMERGENCY)
    probabilities: dict[str, float]
    high_emergency_probability: bool
    path: list[Condition] = field(default_factory=list)
    model_version: str = ""


class UrgencyPredictor:
    def __init__(self, name: str = "dt_app_v1"):
        self.model = joblib.load(MODEL_DIR / f"{name}.joblib")
        self.meta = json.loads((MODEL_DIR / f"{name}.json").read_text(encoding="utf-8"))
        self.features = self.meta["features"]
        self.classes = self.meta["classes"]
        self.t_e = self.meta["thresholds"]["t_emergency"]
        self.t_u = self.meta["thresholds"]["t_urgent_or_higher"]
        self.kb = load_knowledge()

    def predict(self, ext: Extraction, age_years: float, pain_score: float | None = None) -> MLResult:
        symptoms = set(ext.present("symptom"))
        severities = [f.severity for f in ext.findings.values() if f.severity]
        if pain_score is None:
            scores = [f.pain_score for f in ext.findings.values() if f.pain_score is not None]
            pain_score = max(scores) if scores else None
        X = from_findings(symptoms, age_years, pain_score, severities, self.kb)[self.features]
        proba = self.model.predict_proba(X)[0]
        p = {c: float(proba[i]) for i, c in enumerate(self.classes)}
        urgent_plus = p["EMERGENCY"] + p["URGENT"]
        return MLResult(level="URGENT" if urgent_plus >= self.t_u else "ROUTINE",
                        probabilities=p,
                        high_emergency_probability=p["EMERGENCY"] >= self.t_e,
                        path=self._path(X),
                        model_version=self.meta["version"])

    # ------------------------------------------------------------------------------------
    def _path(self, X) -> list[Condition]:
        tree = self.model.tree_
        nodes = self.model.decision_path(X).indices
        x = X.to_numpy()[0]
        out = []
        for node in nodes:
            if tree.children_left[node] == tree.children_right[node]:
                continue  # leaf
            f = self.features[tree.feature[node]]
            thr = float(tree.threshold[node])
            pain_known = bool(x[self.features.index("pain_known")])
            out.append(Condition(feature=f, text=self._describe(f, x[tree.feature[node]] <= thr, thr, pain_known)))
        return out

    def _describe(self, feature: str, left: bool, thr: float, pain_known: bool = True) -> dict[str, str]:
        if feature.startswith("sym_"):
            label = self.kb.concepts[feature[4:]].label
            yes = not left
            return {"en": f"{label['en']}: {'yes' if yes else 'no'}",
                    "te": f"{label['te']}: {'ఉంది' if yes else 'లేదు'}",
                    "hi": f"{label['hi']}: {'हाँ' if yes else 'नहीं'}"}
        if feature == "age_years":
            a = f"{thr:.0f}" if thr >= 1 else f"{thr * 12:.0f} months"
            return {"en": f"age {'≤' if left else '>'} {a}", "te": f"వయస్సు {'≤' if left else '>'} {a}",
                    "hi": f"उम्र {'≤' if left else '>'} {a}"}
        if feature == "pain_known" or (feature == "pain_score" and not pain_known):
            left = not pain_known if feature == "pain_score" else left
            known = not left
            return {"en": "pain score given" if known else "pain score not given",
                    "te": "నొప్పి స్థాయి చెప్పారు" if known else "నొప్పి స్థాయి చెప్పలేదు",
                    "hi": "दर्द का स्तर बताया" if known else "दर्द का स्तर नहीं बताया"}
        if feature == "pain_score":
            return {"en": f"pain score {'≤' if left else '>'} {thr:.1f}/10",
                    "te": f"నొప్పి స్థాయి {'≤' if left else '>'} {thr:.1f}/10",
                    "hi": f"दर्द स्तर {'≤' if left else '>'} {thr:.1f}/10"}
        if feature == "n_symptoms":
            return {"en": f"number of symptoms {'≤' if left else '>'} {thr:.0f}",
                    "te": f"లక్షణాల సంఖ్య {'≤' if left else '>'} {thr:.0f}",
                    "hi": f"लक्षणों की संख्या {'≤' if left else '>'} {thr:.0f}"}
        return {lang: f"{feature} {'≤' if left else '>'} {thr:.2f}" for lang in ("en", "te", "hi")}


@lru_cache(maxsize=1)
def get_predictor() -> UrgencyPredictor:
    return UrgencyPredictor()


def predict(ext: Extraction, age_years: float, pain_score: float | None = None) -> MLResult:
    return get_predictor().predict(ext, age_years, pain_score)

