"""Phase 1: clean NHAMCS ED 2016-2022 into one analysis table.

Input : data/raw/nhamcs/ed{year}.dta  (from scripts/download_nhamcs.py)
Output: data/processed/nhamcs_ed.csv.gz   one row per ED visit that HAS a triage label
        data/processed/rfv_codes.csv      official reason-for-visit code dictionary
        data/processed/label_audit.csv    how many visits each IMMEDR code had, per year

Split  : 2016-2021 = "dev" (training + validation in Phase 6)
         2022      = "test" (temporal hold-out, never looked at until final evaluation)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from mediguide.ml.labels import IMMEDR_NAMES, map_immedr  # noqa: E402

RAW = ROOT / "data" / "raw" / "nhamcs"
OUT = ROOT / "data" / "processed"
YEARS = range(2016, 2023)
TEST_YEAR = 2022
RFV_COLS = [f"RFV{i}" for i in range(1, 6)]
KEEP = ["AGE", "SEX", "PAINSCALE", "IMMEDR", "PATWT", *RFV_COLS]


def load_year(year: int) -> tuple[pd.DataFrame, dict[int, str]]:
    reader = pd.read_stata(RAW / f"ed{year}.dta", iterator=True, convert_categoricals=False)
    labels = reader.value_labels()
    lbl_names = dict(zip(reader.variable_labels(), reader._lbllist))
    df = reader.read(columns=KEEP)
    df.insert(0, "YEAR", year)
    rfv_dict = {int(k): v for k, v in labels.get(lbl_names["RFV1"], {}).items() if k > 0}
    return df, rfv_dict


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames, rfv_rows, audit = [], {}, []
    for year in YEARS:
        df, rfv = load_year(year)
        frames.append(df)
        for code, text in rfv.items():
            rfv_rows.setdefault(code, {"code": code, "label": text, "first_year": year})
            rfv_rows[code]["last_year"] = year
        for code, n in df["IMMEDR"].value_counts().items():
            audit.append({"year": year, "immedr": int(code), "meaning": IMMEDR_NAMES.get(int(code), "?"), "n": int(n)})
        print(f"{year}: {len(df):>6} visits")

    data = pd.concat(frames, ignore_index=True)
    total = len(data)

    # Negative codes (-7/-8/-9) mean blank / unknown / not applicable -> missing.
    for col in ["AGE", "PAINSCALE", *RFV_COLS]:
        data[col] = data[col].where(data[col] >= 0)
    data["SEX"] = data["SEX"].map({1: "F", 2: "M"})

    # NB: Urgency.ROUTINE == 0 is falsy, so test "is None" explicitly (never `u and u.name`).
    def to_label(code: int) -> str | None:
        u = map_immedr(code)
        return None if u is None else u.name

    data["URGENCY"] = data["IMMEDR"].map(to_label)
    labeled = data[data["URGENCY"].notna()].copy()
    labeled["SPLIT"] = (labeled["YEAR"] == TEST_YEAR).map({True: "test", False: "dev"})
    labeled["VISIT_ID"] = [f"{y}-{i:06d}" for y, i in zip(labeled["YEAR"], range(len(labeled)))]

    labeled.to_csv(OUT / "nhamcs_ed.csv.gz", index=False)
    pd.DataFrame(sorted(rfv_rows.values(), key=lambda r: r["code"])).to_csv(OUT / "rfv_codes.csv", index=False)
    pd.DataFrame(audit).sort_values(["year", "immedr"]).to_csv(OUT / "label_audit.csv", index=False)

    print(f"\nTotal visits 2016-2022 : {total}")
    print(f"With a triage label    : {len(labeled)}  ({len(labeled) / total:.1%})")
    print(f"Excluded (no label)    : {total - len(labeled)}")
    print("\nRows per split:")
    print(labeled["SPLIT"].value_counts().to_string())
    print("\nUrgency distribution per split (%):")
    print((pd.crosstab(labeled["SPLIT"], labeled["URGENCY"], normalize="index") * 100).round(1).to_string())
    print(f"\nRFV dictionary entries: {len(rfv_rows)}")
    print(f"Saved -> {OUT}")


if __name__ == "__main__":
    main()
