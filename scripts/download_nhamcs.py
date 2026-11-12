"""Download NHAMCS Emergency Department public-use files (Stata format) from CDC.

Source  : CDC / National Center for Health Statistics (public domain, US Government work)
Landing : https://www.cdc.gov/nchs/ahcd/datasets_documentation_related.htm
Files   : https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/stata/

Usage   : python scripts/download_nhamcs.py            (default years 2016-2022)
          python scripts/download_nhamcs.py 2019 2021  (specific years)
"""
import sys
import zipfile
import urllib.request
from pathlib import Path

BASE = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS"
# CDC file names are inconsistent in capitalisation, so list them exactly.
STATA_ZIPS = {
    2016: "stata/ED2016-stata.zip",
    2017: "stata/ed2017-stata.zip",
    2018: "stata/ED2018-stata.zip",
    2019: "stata/ED2019-stata.zip",
    2020: "stata/ed2020-stata.zip",
    2021: "stata/ed2021-stata.zip",
    2022: "stata/ed2022-stata.zip",
}
# Public-use file documentation (codebooks: variable definitions, RFV code list)
DOCS = {
    2016: "doc16_ed.pdf",
    2017: "doc17_ed-508.pdf",
    2018: "doc18-ed-508.pdf",
    2019: "doc19-ed-508.pdf",
    2020: "doc20-ed-508.pdf",
    2021: "doc21-ed-508.pdf",
    2022: "doc22-ed-508.pdf",
}

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nhamcs"


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  already have {dest.name}")
        return
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "mediguide-student-project"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    print(f"  saved {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main(years: list[int]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "docs").mkdir(exist_ok=True)
    for year in years:
        print(f"== {year}")
        zpath = RAW / Path(STATA_ZIPS[year]).name
        fetch(f"{BASE}/{STATA_ZIPS[year]}", zpath)
        fetch(f"{BASE}/{DOCS[year]}", RAW / "docs" / DOCS[year])
        with zipfile.ZipFile(zpath) as zf:
            for member in zf.namelist():
                # Only extract .dta files, and only by their base name (no path traversal).
                if member.lower().endswith(".dta"):
                    target = RAW / f"ed{year}.dta"
                    if not target.exists():
                        target.write_bytes(zf.read(member))
                    print(f"  extracted {member} -> {target.name}")


if __name__ == "__main__":
    yrs = [int(a) for a in sys.argv[1:]] or sorted(STATA_ZIPS)
    main(yrs)
