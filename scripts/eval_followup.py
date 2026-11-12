"""Experiment 5: follow-up questions and end-to-end assessments.

Usage: python scripts/eval_followup.py [--show-errors]
"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.recommend.engine import assess  # noqa: E402


def check_question_case(c: dict) -> list[str]:
    a = assess(c["text"], c["lang"])
    asked = {q.id for q in a.questions}
    offered = {o.value for q in a.questions if q.id == "checklist" for o in q.options}
    errs = []
    if "status" in c and a.status != c["status"]:
        errs.append(f"status: want {c['status']}, got {a.status}")
    if "level" in c and a.level != c["level"]:
        errs.append(f"level: want {c['level']}, got {a.level}")
    if c.get("no_questions") and asked:
        errs.append(f"asked questions although none expected: {sorted(asked)}")
    if set(c.get("must_ask", [])) - asked:
        errs.append(f"did not ask {sorted(set(c['must_ask']) - asked)} (asked {sorted(asked)})")
    if set(c.get("must_not_ask", [])) & asked:
        errs.append(f"unnecessarily asked {sorted(set(c['must_not_ask']) & asked)}")
    if set(c.get("must_offer", [])) - offered:
        errs.append(f"checklist missing {sorted(set(c['must_offer']) - offered)}")
    for q in a.questions:   # every question must exist in the display language
        if not q.text.get(a.display_language):
            errs.append(f"question {q.id} has no {a.display_language} text")
    return errs


def check_e2e_case(c: dict) -> list[str]:
    a = assess(c["text"], c["lang"], answers=c.get("answers") or {})
    errs = []
    if a.status != "complete":
        errs.append(f"status {a.status}")
    if a.level != c["level"]:
        errs.append(f"level: want {c['level']}, got {a.level} (trace {a.trace})")
    if c.get("note") == "age_missing" and not a.notes:
        errs.append("expected an 'age missing' note")
    if a.level in ("URGENT", "ROUTINE") and not a.safety_net.get("items"):
        errs.append("no safety-netting on a non-emergency result")
    return errs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load((ROOT / "data/synthetic/followup_cases.yaml").read_text(encoding="utf-8"))
    for part, cases, fn in (("A. question generation", data["questions"], check_question_case),
                            ("B. end-to-end with answers", data["end_to_end"], check_e2e_case)):
        errors = [(c["id"], c["text"], e) for c in cases if (e := fn(c))]
        print(f"{part}: {len(cases) - len(errors)}/{len(cases)} correct")
        if args.show_errors:
            for cid, text, errs in errors:
                print(f"  {cid} {text!r}\n      " + "\n      ".join(errs))


if __name__ == "__main__":
    main()
