"""Administrator statistics (Module 10). Reads ONLY the anonymous assessment_stats table and
the model's saved evaluation metrics - never user accounts, text or individual results."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import ROOT
from api.db import AssessmentStat, User, get_db
from api.deps import admin_user
from mediguide.knowledge import load_knowledge

router = APIRouter(prefix="/api/admin", tags=["admin"])
MIN_GROUP = 5  # small-count suppression: groups smaller than this are reported as "<5"


def _suppress(counter: Counter) -> dict:
    return {k: (v if v >= MIN_GROUP else "<5") for k, v in counter.most_common()}


@router.get("/stats")
def stats(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(AssessmentStat)).all()
    kb = load_knowledge()
    symptoms = Counter(s for r in rows for s in r.symptom_ids.split(",") if s)
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    days = Counter(r.day for r in rows if r.day >= since)
    ml_vs_rule = Counter(f"rule={r.rule_level or 'none'} / model={r.ml_level or 'not run'}" for r in rows)

    model_meta = json.loads((ROOT / "models" / "dt_app_v1.json").read_text(encoding="utf-8"))
    results_file = ROOT / "reports" / "phase6_results.json"
    test = json.loads(results_file.read_text(encoding="utf-8"))["test"] if results_file.exists() else {}
    return {
        "total_assessments": len(rows),
        "levels": _suppress(Counter(r.level for r in rows)),
        "languages": _suppress(Counter(r.input_language for r in rows)),
        "followup_rate": round(sum(r.asked_followup for r in rows) / len(rows), 3) if rows else None,
        "top_symptoms": [{"id": s, "label": kb.concepts[s].label["en"] if s in kb.concepts else s,
                          "count": n if n >= MIN_GROUP else "<5"} for s, n in symptoms.most_common(15)],
        "daily_last_30_days": dict(sorted(days.items())),
        "rule_vs_model": _suppress(ml_vs_rule),
        "model": {"version": model_meta["version"], "trained": model_meta["trained"],
                  "thresholds": model_meta["thresholds"], "status": model_meta["status"],
                  "test_2022_app_policy": test.get("APP: Rules + depth-6 DT (ML capped at URGENT)"),
                  "test_2022_random_forest": test.get("Random Forest (argmax)")},
        "privacy_note": f"Aggregated anonymous data only; groups smaller than {MIN_GROUP} are suppressed.",
    }
