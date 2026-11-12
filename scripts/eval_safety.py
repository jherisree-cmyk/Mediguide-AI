"""Experiment 4: evaluate the full text -> NLP -> safety-rule path on synthetic cases.

Usage: python scripts/eval_safety.py [data/synthetic/safety_cases.yaml] [--show-errors]

Reports a 3x3 confusion matrix (EMERGENCY / URGENT / NONE), emergency recall and precision,
and the number of UNDER-triaged cases (predicted level lower than expected), which is the
safety-critical error. These are software-test results, not clinical validation.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.nlp.extractor import extract  # noqa: E402
from mediguide.safety.engine import evaluate  # noqa: E402

LEVELS = ["EMERGENCY", "URGENT", "NONE"]
RANK = {"NONE": 0, "URGENT": 1, "EMERGENCY": 2}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="?", default=str(ROOT / "data/synthetic/safety_cases.yaml"))
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args()
    cases = yaml.safe_load(Path(args.cases).read_text(encoding="utf-8"))["cases"]

    conf = Counter()
    errors, by_lang = [], Counter()
    under = over = 0
    for c in cases:
        ext = extract(c["text"], c["lang"])
        res = evaluate(ext)
        pred = res.level or "NONE"
        conf[(c["level"], pred)] += 1
        problems = []
        if pred != c["level"]:
            problems.append(f"level: want {c['level']}, got {pred}")
            if RANK[pred] < RANK[c["level"]]:
                under += 1
            else:
                over += 1
        fired = {f.id for f in res.fired}
        missing_rules = set(c.get("rules", [])) - fired
        if missing_rules:
            problems.append(f"rules missing: {sorted(missing_rules)} (fired: {sorted(fired)})")
        if "understood" in c and res.understood != c["understood"]:
            problems.append(f"understood: want {c['understood']}, got {res.understood}")
        by_lang[(c["lang"], not problems)] += 1
        if problems:
            errors.append((c["id"], c["text"], sorted(ext.findings), problems))

    print(f"Cases: {len(cases)}")
    print("\nConfusion matrix (rows = expected, columns = rule engine)")
    print(f"{'':12}" + "".join(f"{lv:>11}" for lv in LEVELS))
    for exp in LEVELS:
        print(f"{exp:12}" + "".join(f"{conf[(exp, p)]:>11}" for p in LEVELS))
    tp = conf[("EMERGENCY", "EMERGENCY")]
    fn = sum(conf[("EMERGENCY", p)] for p in LEVELS if p != "EMERGENCY")
    fp = sum(conf[(e, "EMERGENCY")] for e in LEVELS if e != "EMERGENCY")
    print(f"\nEmergency recall    {tp}/{tp + fn} = {tp / max(tp + fn, 1):.3f}   <- primary safety metric")
    print(f"Emergency precision {tp}/{tp + fp} = {tp / max(tp + fp, 1):.3f}")
    print(f"Under-triaged cases {under}   Over-triaged cases {over}")
    print("Fully correct by language: " + ", ".join(
        f"{lang} {by_lang[(lang, True)]}/{by_lang[(lang, True)] + by_lang[(lang, False)]}" for lang in ("en", "te", "hi")))
    if args.show_errors and errors:
        print("\nErrors:")
        for cid, text, found, probs in errors:
            print(f"  {cid}  {text!r}\n        found: {found}\n        " + "\n        ".join(probs))


if __name__ == "__main__":
    main()
