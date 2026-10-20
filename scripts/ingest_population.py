"""Ingest real public population data into data/model/ reference tables.

Inputs (downloaded public files, read as data only):
  data/external/hdx/20211122_location_fce_rrrc_unhcr_population-registration_public.xlsx
      HDX / ISCG, RRRC-UNHCR family counting, CC0, population as of 31 Oct 2021.
  data/external/unhcr/unhcr_rohingya_population_dashboard_2026-06-30.pdf
      GoB-UNHCR Joint Registration, 30 Jun 2026 (text extracted with `pdftotext -layout`).
Outputs:
  data/model/dim_camp_population_2021.csv  camp-level HH / individuals, upazila, union, coordinates
  data/model/ref_population_2026.csv       camp-level families / individuals (page 2 table)
  data/model/ref_demographics_2026.csv     age group x sex individuals (page 1 pyramid)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
MODEL = ROOT / "data" / "model"
# Override with the HDX_SOURCE / UNHCR_PDF environment variables.
HDX = Path(os.environ.get("HDX_SOURCE", EXT / "hdx" / "20211122_location_fce_rrrc_unhcr_population-registration_public.xlsx"))
PDF = Path(os.environ.get("UNHCR_PDF", EXT / "unhcr" / "unhcr_rohingya_population_dashboard_2026-06-30.pdf"))
AS_OF_2021, AS_OF_2026 = "2021-10-31", "2026-06-30"
NATIONAL_TOTAL_2026, NATIONAL_FAMILIES_2026 = 1_200_171, 249_823
AGE_GROUPS = ["Below 1", "1-4", "5-11", "12-17", "18-59", "60+"]


def num(s: str) -> int:
    return int(s.replace(",", ""))


def ingest_hdx() -> pd.DataFrame:
    """Camp list with households, individuals, upazila, union and coordinates (2021)."""
    df = pd.read_excel(HDX, sheet_name=0).dropna(subset=["New_Camp_Name"])
    out = pd.DataFrame({
        "camp_ssid": df["New_Camp_SSID"].str.strip(),
        "camp_name": df["New_Camp_Name"].str.strip(),
        "site_alias": df["Site_Name_Alias"].fillna("").astype(str).str.strip(),
        "upazila": df["Upazila"].str.strip(),
        "union": df["Union"].str.strip(),
        "households": df["Total_HH"].astype(int),
        "individuals": df["Total_Pop"].astype(int),
        "latitude": df["Latitude"].astype(float).round(6),
        "longitude": df["Longitude"].astype(float).round(6),
        "as_of": AS_OF_2021,
    })
    return out.reset_index(drop=True)


def pdf_text(page: int) -> str:
    return subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(PDF), "-"],
                          check=True, capture_output=True, text=True).stdout


def ingest_camps_2026() -> pd.DataFrame:
    """Parse the two-column 'Camp / Families / Individuals' table on page 2."""
    text = pdf_text(2)
    start = text.index("Families Individuals")
    pat = re.compile(r"((?:Camp \d+[EW]?(?: Extension)?)|Bhasan Char|Kutupalong RC|Nayapara RC|Other)"
                     r"\s+([\d,]+)\s+([\d,]+)")
    rows = [(m.group(1), num(m.group(2)), num(m.group(3))) for m in pat.finditer(text[start:])]
    df = pd.DataFrame(rows, columns=["camp_name", "families", "individuals"]).drop_duplicates("camp_name")
    df["as_of"] = AS_OF_2026
    if df["individuals"].sum() != NATIONAL_TOTAL_2026 or df["families"].sum() != NATIONAL_FAMILIES_2026:
        raise ValueError(f"2026 camp table does not reconcile: {df.individuals.sum():,} / {df.families.sum():,}")
    return df


def ingest_demographics_2026() -> pd.DataFrame:
    """Parse the age/sex pyramid on page 1: 6 rows of 'female (x%) ... male (y%)'."""
    text = pdf_text(1)
    i0 = text.index("Below 1")
    block = text[i0:text.index("60+", i0) + 200]
    vals = [num(v) for v in re.findall(r"([\d,]+) \(\d+%\)", block)]
    if len(vals) != 12:
        raise ValueError(f"expected 12 pyramid values, found {len(vals)}")
    rows = []
    for i, g in enumerate(AGE_GROUPS):
        rows += [(g, "Female", vals[2 * i]), (g, "Male", vals[2 * i + 1])]
    df = pd.DataFrame(rows, columns=["age_group", "sex", "individuals"])
    df["as_of"] = AS_OF_2026
    if df["individuals"].sum() != NATIONAL_TOTAL_2026:
        raise ValueError(f"pyramid total {df.individuals.sum():,} != {NATIONAL_TOTAL_2026:,}")
    return df


def main() -> int:
    missing = [str(f) for f in (HDX, PDF) if not f.exists()]
    if missing or shutil.which("pdftotext") is None:
        why = f"input(s) not found: {', '.join(missing)}" if missing else "pdftotext not installed"
        print(f"ingest_population: {why}; keeping committed reference tables in {MODEL.name}/.")
        return 0
    MODEL.mkdir(parents=True, exist_ok=True)
    h, p, d = ingest_hdx(), ingest_camps_2026(), ingest_demographics_2026()
    h.to_csv(MODEL / "dim_camp_population_2021.csv", index=False)
    p.to_csv(MODEL / "ref_population_2026.csv", index=False)
    d.to_csv(MODEL / "ref_demographics_2026.csv", index=False)
    print(f"HDX 2021: {len(h)} sites, {h.individuals.sum():,} individuals, {h.households.sum():,} households")
    print(f"UNHCR 2026: {len(p)} camp rows, {p.individuals.sum():,} individuals, {p.families.sum():,} families")
    u18 = d[~d.age_group.isin(["18-59", "60+"])].individuals.sum()
    print(f"UNHCR 2026 demographics: under-18 share {u18 / d.individuals.sum():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
