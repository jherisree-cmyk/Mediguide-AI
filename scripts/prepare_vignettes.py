"""Phase 1: extract the clinician gold-standard triage level for each of the 45
Semigran et al. (2015) case vignettes from the Zenodo workbook (Schmieding et al. 2022,
doi:10.5281/zenodo.6054093, CC BY 4.0).

Output: data/processed/vignette_gold.csv  (vignette_id, gold_level, gold_urgency)
Gold levels: Em = emergency care, NE = non-emergency care, Sc = self-care.
Vignette TEXT must be added manually from the BMJ appendix (see data/DATASETS.md).
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "vignettes" / "Triage_Accuracy_Symptom_Checker_Apps_2020.xlsx"
OUT = ROOT / "data" / "processed" / "vignette_gold.csv"
# Our 3-class system has no self-care class: Sc and NE both map to ROUTINE for scoring.
TO_URGENCY = {"Em": "EMERGENCY", "NE": "ROUTINE", "Sc": "ROUTINE"}

df = pd.read_excel(SRC)
gold = df.groupby("Vignette_id")["Goldstandard_solution_triage_level"].agg(set)
assert gold.map(len).eq(1).all(), "a vignette has conflicting gold labels"
out = pd.DataFrame({"vignette_id": gold.index, "gold_level": gold.map(lambda s: next(iter(s))).values})
out["gold_urgency"] = out["gold_level"].map(TO_URGENCY)
out.to_csv(OUT, index=False)
print(out["gold_level"].value_counts().to_string())
print(f"Saved {len(out)} vignettes -> {OUT}")
