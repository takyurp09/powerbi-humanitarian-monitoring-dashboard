"""Build data/model/ref_wages_coxsbazar.csv from the author's cleaned BBS wage panel.

Source: Bangladesh Bureau of Statistics (BBS) Agricultural Wage Statistics, a public
download from the BBS website (district x month x sex x meal provision). The cleaned
monthly district files come from the author's own research pipeline, which rebuilds
them from the public BBS files. Only nominal daily wages are used here.

Output: Cox's Bazar district rows plus a national median across all 64 districts for the
same month, sex and meal provision, 2017-01 to 2025-12.

If WAGE_SOURCE is missing (e.g. on a fresh clone) the script exits 0 and keeps the
committed CSV.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Folder holding the cleaned monthly district wage panel from the author's research pipeline.
# Override with the WAGE_SOURCE environment variable.
WAGE_SOURCE = Path(os.environ.get("WAGE_SOURCE", ROOT.parent / "wage_model" / "data" / "Regression_data"))
FILES = ["wage_by_month.csv", "wage_new_2024_2025.csv"]  # 2014-2023 and 2024-2025 nominal wages
OUT = ROOT / "data" / "model" / "ref_wages_coxsbazar.csv"
SOURCE_LABEL = "BBS Agricultural Wage Statistics (public); derived by author"
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                                      "Oct", "Nov", "Dec"], start=1)}
MEALS = {"None": "No meals", "One": "1 meal", "Two": "2 meals", "Three": "3 meals"}


def load() -> pd.DataFrame:
    frames = [pd.read_csv(WAGE_SOURCE / f, usecols=["District", "Month", "wage_type", "meal_type",
                                                    "gender", "wage", "year"]) for f in FILES]
    d = pd.concat(frames, ignore_index=True)
    d = d[d["year"].between(2017, 2025)].copy()
    # "Without" food = no meals; "With" carries the number of meals. Drop unlabelled meal rows.
    d["meals"] = d["meal_type"].where(d["wage_type"] == "With", "None").map(MEALS)
    d["wage"] = pd.to_numeric(d["wage"], errors="coerce")
    d = d.dropna(subset=["meals", "wage"])
    d = d[d["wage"] > 0]
    d["date"] = pd.to_datetime(dict(year=d["year"], month=d["Month"].str[:3].map(MONTHS), day=1))
    d["district_key"] = d["District"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    return d.rename(columns={"gender": "sex"})


def main() -> int:
    missing = [f for f in FILES if not (WAGE_SOURCE / f).exists()]
    if missing:
        print(f"ingest_wages: WAGE_SOURCE not found ({WAGE_SOURCE}); keeping committed {OUT.name}.")
        return 0
    d = load()
    keys = ["date", "sex", "meals"]
    cox = (d[d["district_key"] == "coxsbazar"].groupby(keys, as_index=False)["wage"].median()
           .assign(district="Cox's Bazar"))
    nat = (d.groupby(keys + ["district_key"], as_index=False)["wage"].median()
           .groupby(keys, as_index=False)["wage"].median().assign(district="Bangladesh (national median)"))
    out = pd.concat([cox, nat], ignore_index=True).rename(columns={"wage": "daily_wage_bdt"})
    out["daily_wage_bdt"] = out["daily_wage_bdt"].round(0).astype(int)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out["source"] = SOURCE_LABEL
    out = out[["date", "district", "sex", "meals", "daily_wage_bdt", "source"]].sort_values(
        ["district", "date", "sex", "meals"], key=lambda s: s.map(lambda v: list(MEALS.values()).index(v))
        if s.name == "meals" else s)
    out.to_csv(OUT, index=False)
    c = out[out.district == "Cox's Bazar"]
    print(f"ingest_wages: {len(out):,} rows ({len(c):,} Cox's Bazar, {len(out) - len(c):,} national) "
          f"{out.date.min()} to {out.date.max()} -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
