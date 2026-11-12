"""DEMO ONLY: fill the anonymous statistics table so the admin dashboard has something to show.

Every row is produced by running a SYNTHETIC test sentence (data/synthetic/*.yaml) through the
REAL assessment engine (when questions are asked: answers "none of these", age 30). Days are
spread over the last 14 days. No real users, no invented outcomes - but also NOT real usage,
so never present these numbers as usage statistics.

Usage: python scripts/seed_demo_stats.py            (uses the database configured in .env / env)
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from api.db import AssessmentStat, SessionLocal, init_db  # noqa: E402
from mediguide.recommend.engine import assess  # noqa: E402

FILES = ["safety_cases.yaml", "en_extraction_dev.yaml", "en_extraction_heldout.yaml", "te_extraction_dev.yaml",
         "te_extraction_heldout.yaml", "hi_extraction_dev.yaml", "hi_extraction_heldout.yaml"]


def texts():
    for name in FILES:
        for c in yaml.safe_load((ROOT / "data/synthetic" / name).read_text(encoding="utf-8"))["cases"]:
            lang = c.get("lang") or name[:2]
            yield c["text"], lang


def main() -> None:
    init_db()
    rng = random.Random(7)
    today = datetime.now(timezone.utc).date()
    rows = 0
    with SessionLocal() as db:
        for text, lang in texts():
            a = assess(text, lang)
            asked = a.status == "needs_followup"
            if asked:
                answers = {q.id: (["none"] if q.kind == "multi" else 30 if q.id == "age" else None) for q in a.questions}
                a = assess(text, lang, answers={k: v for k, v in answers.items() if v is not None})
            db.add(AssessmentStat(day=str(today - timedelta(days=rng.randint(0, 13))), input_language=a.input_language,
                                  level=a.level, rule_level=a.trace.get("rule_level"), ml_level=a.trace.get("ml_level"),
                                  asked_followup=asked,
                                  symptom_ids=",".join(s["id"] for s in a.symptoms if s["kind"] in ("symptom", "sign"))))
            rows += 1
        db.commit()
    print(f"Added {rows} DEMO statistics rows (synthetic sentences through the real engine).")


if __name__ == "__main__":
    main()
