"""Validate data/model/ tables against docs/SCHEMA.md; exit non-zero on failure."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODEL = Path(__file__).resolve().parents[1] / "data" / "model"
SCHEMA: dict[str, list[str]] = {
    "dim_date": ["date", "year", "quarter", "month_num", "month_name", "fiscal_label"],
    "dim_camp": ["camp_id", "camp_name", "upazila", "union", "latitude", "longitude", "population", "families",
                 "children_share", "population_source", "population_as_of"],
    "dim_camp_population_2021": ["camp_ssid", "camp_name", "site_alias", "upazila", "union", "households",
                                 "individuals", "latitude", "longitude", "as_of"],
    "ref_population_2026": ["camp_name", "families", "individuals", "as_of"],
    "ref_demographics_2026": ["age_group", "sex", "individuals", "as_of"],
    "dim_sector": ["sector_id", "sector_name"],
    "dim_indicator": ["indicator_id", "sector_id", "indicator_name", "unit", "aggregation", "higher_is_better"],
    "dim_partner": ["partner_id", "partner_name", "partner_type"],
    "fact_results": ["date", "camp_id", "indicator_id", "partner_id", "sex", "target", "achieved",
                     "reported_date", "is_late", "dq_flag"],
    "fact_tpm_visits": ["visit_id", "visit_date", "camp_id", "partner_id", "sector_id", "rating",
                        "issues_flagged", "issue_category", "followup_status", "days_to_close"],
    "dq_log": ["rule", "rows_affected"],
    "ref_wages_coxsbazar": ["date", "district", "sex", "meals", "daily_wage_bdt", "source"],
}
KEYS = {"dim_date": ["date"], "dim_camp": ["camp_id"], "dim_sector": ["sector_id"],
        "dim_indicator": ["indicator_id"], "dim_partner": ["partner_id"],
        "fact_results": ["date", "camp_id", "indicator_id", "partner_id", "sex"],
        "fact_tpm_visits": ["visit_id"], "dim_camp_population_2021": ["camp_name"],
        "ref_population_2026": ["camp_name"], "ref_demographics_2026": ["age_group", "sex"],
        "ref_wages_coxsbazar": ["date", "district", "sex", "meals"]}
errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    """Record a failed check."""
    if not cond:
        errors.append(msg)


def main() -> int:
    t = {n: pd.read_csv(MODEL / f"{n}.csv", dtype=str, keep_default_na=False) for n in SCHEMA}
    for n, cols in SCHEMA.items():
        check(list(t[n].columns) == cols, f"{n}: columns {list(t[n].columns)} != {cols}")
    for n, k in KEYS.items():
        check(not t[n].duplicated(k).any(), f"{n}: duplicate keys on {k}")
    f, v = t["fact_results"], t["fact_tpm_visits"]
    for fact in (f, v):
        for col, dim in [("camp_id", "dim_camp"), ("partner_id", "dim_partner")]:
            check(fact[col].isin(t[dim][col]).all(), f"orphan {col}")
    check(f["date"].isin(t["dim_date"]["date"]).all(), "fact_results: date outside dim_date")
    check(f["indicator_id"].isin(t["dim_indicator"]["indicator_id"]).all(), "orphan indicator_id")
    check(v["sector_id"].isin(t["dim_sector"]["sector_id"]).all(), "orphan sector_id")
    check(t["dim_indicator"]["sector_id"].isin(t["dim_sector"]["sector_id"]).all(), "dim_indicator orphan sector")
    check(len(t["dim_date"]) == 18 and t["dim_date"]["date"].min() == "2025-01-01"
          and t["dim_date"]["date"].max() == "2026-06-01", "dim_date range")
    check(len(t["dim_camp"]) == 24 and len(t["dim_indicator"]) == 15 and len(t["dim_partner"]) == 10
          and len(t["dim_sector"]) == 5, "dimension cardinality")
    vd = pd.to_datetime(v["visit_date"], format="%Y-%m-%d", errors="coerce")
    check(vd.notna().all() and vd.min() >= pd.Timestamp("2025-01-01") and vd.max() <= pd.Timestamp("2026-06-30"),
          "visit_date range/format")
    check(pd.to_datetime(f["reported_date"], format="%Y-%m-%d", errors="coerce").notna().all(), "reported_date format")
    c = t["dim_camp"]
    check(c["upazila"].isin(["Ukhia", "Teknaf"]).all(), "upazila values")
    check(pd.to_numeric(c["latitude"]).between(20.9, 21.3).all() and pd.to_numeric(c["longitude"]).between(92.1, 92.3).all(), "lat/lon")
    check((pd.to_numeric(c["population"]) > 0).all() and (pd.to_numeric(c["families"]) > 0).all(), "population")
    check(c["population_as_of"].isin(["2026-06-30", "2021-10-31"]).all(), "population_as_of values")
    h, p26, demo = t["dim_camp_population_2021"], t["ref_population_2026"], t["ref_demographics_2026"]
    check(c["camp_name"].isin(h["camp_name"]).all(), "dim_camp names must come from the HDX site list")
    real = c.merge(p26, on="camp_name", how="left")
    check((real["individuals"].isna() | (real["individuals"] == real["population"])).all(),
          "dim_camp population must equal the 2026 camp figure where available")
    check(pd.to_numeric(p26["individuals"]).sum() == 1_200_171 and pd.to_numeric(p26["families"]).sum() == 249_823,
          "ref_population_2026 must reconcile to 1,200,171 individuals / 249,823 families")
    check(pd.to_numeric(demo["individuals"]).sum() == 1_200_171 and len(demo) == 12, "ref_demographics_2026 total")
    check(pd.to_numeric(c["children_share"]).between(0, 1).all(), "children_share")
    check(f["sex"].isin(["Female", "Male"]).all(), "sex values")
    check(f["is_late"].isin(["TRUE", "FALSE"]).all(), "is_late values")
    check(f["dq_flag"].isin(["OK", "Missing", "Outlier", "Inconsistent"]).all(), "dq_flag values")
    tgt = pd.to_numeric(f["target"]); ach = pd.to_numeric(f["achieved"].replace("", None))
    check((tgt > 0).all(), "target must be > 0")
    check((ach.dropna() >= 0).all(), "achieved must be >= 0")
    check(ach[f["dq_flag"] == "OK"].notna().all(), "OK rows must have achieved")
    check(v["rating"].isin(list("1234")).all(), "rating 1-4")
    check(v["issue_category"].isin(["Quality", "Access", "Safeguarding", "Supplies", "Reporting"]).all(), "issue_category")
    check(v["followup_status"].isin(["Closed", "Open"]).all(), "followup_status")
    check((v.loc[v.followup_status == "Open", "days_to_close"] == "").all(), "Open visits must have blank days_to_close")
    check(v.loc[v.followup_status == "Closed", "days_to_close"].str.isdigit().all(), "Closed visits need int days_to_close")

    w = t["ref_wages_coxsbazar"]
    wd = pd.to_datetime(w["date"], format="%Y-%m-%d", errors="coerce")
    check(wd.notna().all() and (wd.dt.day == 1).all(), "ref_wages: date must be first of month")
    check(wd.min() >= pd.Timestamp("2017-01-01") and wd.max() <= pd.Timestamp("2025-12-01"), "ref_wages: date range")
    check(w["district"].isin(["Cox's Bazar", "Bangladesh (national median)"]).all(), "ref_wages: district values")
    check((w["district"] == "Cox's Bazar").sum() > 0, "ref_wages: no Cox's Bazar rows")
    check(w["sex"].isin(["Female", "Male"]).all(), "ref_wages: sex values")
    check(w["meals"].isin(["No meals", "1 meal", "2 meals", "3 meals"]).all(), "ref_wages: meals values")
    check(pd.to_numeric(w["daily_wage_bdt"], errors="coerce").between(50, 3000).all(), "ref_wages: wage 50-3000 BDT")
    check(w["source"].str.startswith("BBS Agricultural Wage Statistics").all(), "ref_wages: source label")

    # summary
    ind = t["dim_indicator"].set_index("indicator_id")["aggregation"]
    is_sum = f["indicator_id"].map(ind).eq("sum")
    ok = ach.notna()
    ach_pct = ach[is_sum & ok].sum() / tgt[is_sum & ok].sum() * 100
    avg_pct = (ach[~is_sum & ok] / tgt[~is_sum & ok]).mean() * 100
    issues = v[pd.to_numeric(v["issues_flagged"]) > 0]
    print("Row counts:")
    for n in SCHEMA:
        print(f"  {n:16s} {len(t[n]):>7,}")
    print(f"Overall achievement % (sum indicators): {ach_pct:.1f}%")
    print(f"Average achievement % (avg indicators): {avg_pct:.1f}%")
    print(f"Reporting timeliness %:                 {(f['is_late'] == 'FALSE').mean() * 100:.1f}%")
    print(f"Data quality score %:                   {(f['dq_flag'] == 'OK').mean() * 100:.1f}%")
    print(f"TPM follow-up closure rate:             {(issues['followup_status'] == 'Closed').mean() * 100:.1f}%")
    closed = pd.to_numeric(issues.loc[issues.followup_status == "Closed", "days_to_close"])
    print(f"Average days to close (closed, issues>0): {closed.mean():.1f}")
    print(f"Real population in dim_camp:            {pd.to_numeric(c['population']).sum():,} "
          f"({(c['population_as_of'] == '2026-06-30').sum()} camps as of 2026-06-30)")
    cw = w[(w["district"] == "Cox's Bazar") & (w["meals"] == "No meals") & (w["sex"] == "Male")]
    print(f"Cox's Bazar male wage, no meals (BBS):  {cw['daily_wage_bdt'].astype(int).median():,.0f} BDT/day median, "
          f"{len(w):,} wage rows {w['date'].min()} to {w['date'].max()}")
    if errors:
        print("\nVALIDATION FAILED:"); [print("  -", e) for e in errors]
        return 1
    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
