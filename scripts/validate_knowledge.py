"""Phase 2: validate knowledge/symptoms.yaml + knowledge/red_flags.yaml and report how much
of the NHAMCS dev data our symptom vocabulary covers.

Usage: python scripts/validate_knowledge.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.knowledge import LANGS, load_knowledge, validate_knowledge  # noqa: E402

kb = load_knowledge()
rfv_file = ROOT / "data" / "processed" / "rfv_codes.csv"
known = set(pd.read_csv(rfv_file)["code"]) if rfv_file.exists() else None
problems = validate_knowledge(kb, known)

kinds = pd.Series([c.kind for c in kb.concepts.values()]).value_counts()
print(f"Concepts: {len(kb.concepts)}  ({', '.join(f'{k}={v}' for k, v in kinds.items())})")
for lang in LANGS:
    print(f"  {lang} terms: {sum(len(c.terms.get(lang, [])) for c in kb.concepts.values())}")
levels = pd.Series([r.level for r in kb.rules]).value_counts()
print(f"Rules: {len(kb.rules)}  ({', '.join(f'{k}={v}' for k, v in levels.items())})")
print(f"Sources: {len(kb.sources)}")

data = ROOT / "data" / "processed" / "nhamcs_ed.csv.gz"
if data.exists():
    df = pd.read_csv(data)
    dev = df[df["SPLIT"] == "dev"]
    codes = dev[[f"RFV{i}" for i in range(1, 6)]].stack().dropna().astype(int)
    mapped = set(kb.rfv_to_symptom())
    symptom_codes = codes[(codes >= 10000) & (codes < 20000)]
    any_mapped = dev[[f"RFV{i}" for i in range(1, 6)]].isin(mapped).any(axis=1)
    print("\nCoverage on NHAMCS dev split:")
    print(f"  all coded reasons covered       : {codes.isin(mapped).mean():.1%}")
    print(f"  symptom-module reasons covered  : {symptom_codes.isin(mapped).mean():.1%}")
    print(f"  visits with >=1 mapped reason   : {any_mapped.mean():.1%}")

print("\nVALIDATION:", "PASSED" if not problems else f"{len(problems)} PROBLEM(S)")
for p in problems:
    print("  -", p)
sys.exit(1 if problems else 0)
