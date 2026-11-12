"""Experiment 1/2: evaluate symptom extraction against hand-labelled sentences.

Usage: python scripts/eval_extraction.py data/synthetic/en_extraction_dev.yaml [--lang en] [--show-errors]

Metrics
  present P/R/F1   concept-level, micro-averaged over all cases
  negation acc.    share of expected-negated concepts that were detected as negated
  attribute acc.   share of checked attributes with the exact expected value
  case exact match all of present/negated/attrs/age/subject correct for that case
These measure SOFTWARE behaviour on synthetic sentences, not clinical accuracy.
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.nlp.extractor import SymptomExtractor  # noqa: E402


def score_case(case: dict, ext) -> dict:
    found = set(ext.findings)
    exp = set(case.get("present", []))
    exp_neg = set(case.get("negated", []))
    r = {"tp": len(found & exp), "fp": len(found - exp), "fn": len(exp - found),
         "neg_ok": len(exp_neg & set(ext.negated)), "neg_total": len(exp_neg),
         "attr_ok": 0, "attr_total": 0, "errors": []}
    if found - exp:
        r["errors"].append(f"extra: {sorted(found - exp)}")
    if exp - found:
        r["errors"].append(f"missed: {sorted(exp - found)}")
    if exp_neg - set(ext.negated):
        r["errors"].append(f"negation missed: {sorted(exp_neg - set(ext.negated))}")
    for cid, attrs in (case.get("attrs") or {}).items():
        for key, want in attrs.items():
            r["attr_total"] += 1
            got = getattr(ext.findings[cid], key, None) if cid in ext.findings else "<absent>"
            ok = (abs(got - want) < 0.01) if isinstance(want, (int, float)) and isinstance(got, (int, float)) \
                and not isinstance(want, bool) else got == want
            r["attr_ok"] += ok
            if not ok:
                r["errors"].append(f"{cid}.{key}: want {want}, got {got}")
    if "age_years" in case:
        got = ext.age_years
        if got is None or abs(got - case["age_years"]) > 0.01:
            r["errors"].append(f"age: want {case['age_years']}, got {got}")
    if "subject" in case and ext.subject != case["subject"]:
        r["errors"].append(f"subject: want {case['subject']}, got {ext.subject}")
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args()
    cases = yaml.safe_load(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    ex = SymptomExtractor(args.lang)

    tot = defaultdict(int)
    by_cat = defaultdict(lambda: [0, 0])
    failures = []
    for case in cases:
        r = score_case(case, ex.extract(case["text"]))
        for k in ("tp", "fp", "fn", "neg_ok", "neg_total", "attr_ok", "attr_total"):
            tot[k] += r[k]
        by_cat[case["cat"]][1] += 1
        if not r["errors"]:
            by_cat[case["cat"]][0] += 1
        else:
            failures.append((case["id"], case["text"], r["errors"]))

    p = tot["tp"] / max(tot["tp"] + tot["fp"], 1)
    rc = tot["tp"] / max(tot["tp"] + tot["fn"], 1)
    f1 = 2 * p * rc / max(p + rc, 1e-9)
    exact = sum(v[0] for v in by_cat.values())
    print(f"Cases: {len(cases)}   file: {args.cases}")
    print(f"Present concepts  precision {p:.3f}  recall {rc:.3f}  F1 {f1:.3f}   (tp={tot['tp']} fp={tot['fp']} fn={tot['fn']})")
    print(f"Negation          {tot['neg_ok']}/{tot['neg_total']} detected")
    print(f"Attributes        {tot['attr_ok']}/{tot['attr_total']} correct")
    print(f"Case exact match  {exact}/{len(cases)} ({exact / len(cases):.1%})")
    print("By category (exact / total):", ", ".join(f"{c} {a}/{b}" for c, (a, b) in by_cat.items()))
    if args.show_errors and failures:
        print("\nErrors:")
        for cid, text, errs in failures:
            print(f"  {cid}  {text!r}\n        " + "\n        ".join(errs))


if __name__ == "__main__":
    main()
