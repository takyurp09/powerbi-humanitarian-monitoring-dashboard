"""Aggregate data/model CSVs into compact JSON for the static web dashboard (site/data/).

Usage: python scripts/build_site_data.py
Outputs site/data/{metadata,dims,results,tpm,population,wages}.json.
Results are pre-aggregated to month x camp x indicator x partner (summed over sex) so the
browser can apply date / sector / upazila filters itself. Compact arrays keep the payload small.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data" / "model"
OUT = ROOT / "site" / "data"
MAX_BYTES = 1_500_000


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(MODEL / f"{name}.csv")


def dump(name: str, obj) -> int:
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return path.stat().st_size


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().eq("TRUE")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dates = read("dim_date")
    camps = read("dim_camp")
    sectors = read("dim_sector")
    inds = read("dim_indicator")
    partners = read("dim_partner")
    res = read("fact_results")
    tpm = read("fact_tpm_visits")
    pop = read("ref_population_2026")
    demo = read("ref_demographics_2026")
    wages = read("ref_wages_coxsbazar")
    dq_log = read("dq_log")

    months = [d[:7] for d in dates["date"].astype(str)]
    m_idx = {m: i for i, m in enumerate(months)}
    c_idx = {c: i for i, c in enumerate(camps["camp_id"])}
    i_idx = {c: i for i, c in enumerate(inds["indicator_id"])}
    p_idx = {c: i for i, c in enumerate(partners["partner_id"])}
    s_idx = {c: i for i, c in enumerate(sectors["sector_id"])}

    # ---- dims
    dims = {
        "months": months,
        "sectors": sectors["sector_name"].tolist(),
        "indicators": [
            {"name": r.indicator_name, "sector": s_idx[r.sector_id], "unit": r.unit,
             "agg": r.aggregation, "children": bool(r.unit == "children" and r.aggregation == "sum")}
            for r in inds.itertuples()
        ],
        "partners": [{"name": r.partner_name, "type": r.partner_type} for r in partners.itertuples()],
        "camps": [
            {"name": r.camp_name, "upazila": r.upazila, "union": r.union,
             "lat": round(float(r.latitude), 5), "lon": round(float(r.longitude), 5),
             "pop": int(r.population), "families": int(r.families),
             "childShare": float(r.children_share)}
            for r in camps.itertuples()
        ],
        "upazilas": sorted(camps["upazila"].unique().tolist()),
    }

    # ---- results: [m, c, i, p, target(valid), achieved, achievedFemale, rows, late, lagDaysSum, missing, outlier, inconsistent]
    res = res.copy()
    res["m"] = res["date"].astype(str).str[:7].map(m_idx)
    res["valid"] = res["achieved"].notna()
    res["tgt_v"] = res["target"].where(res["valid"], 0)
    res["ach"] = res["achieved"].fillna(0)
    res["ach_f"] = res["ach"].where(res["sex"].eq("Female"), 0)
    res["late"] = as_bool(res["is_late"]).astype(int)
    period_end = pd.to_datetime(res["date"]) + pd.offsets.MonthEnd(0)
    res["lag"] = (pd.to_datetime(res["reported_date"]) - period_end).dt.days.clip(lower=0).fillna(0)
    for flag in ("Missing", "Outlier", "Inconsistent"):
        res[flag] = res["dq_flag"].eq(flag).astype(int)
    g = res.groupby(["m", "camp_id", "indicator_id", "partner_id"], sort=True).agg(
        tgt=("tgt_v", "sum"), ach=("ach", "sum"), achf=("ach_f", "sum"), n=("date", "size"),
        late=("late", "sum"), lag=("lag", "sum"), mi=("Missing", "sum"), ou=("Outlier", "sum"),
        inc=("Inconsistent", "sum")).reset_index()

    def num(x):
        x = float(x)
        return int(x) if x.is_integer() else round(x, 2)

    rows = [
        [int(r.m), c_idx[r.camp_id], i_idx[r.indicator_id], p_idx[r.partner_id], num(r.tgt), num(r.ach),
         num(r.achf), int(r.n), int(r.late), int(r.lag), int(r.mi), int(r.ou), int(r.inc)]
        for r in g.itertuples()
    ]
    results = {"fields": ["month", "camp", "indicator", "partner", "target", "achieved", "achievedFemale",
                          "rows", "late", "lagDays", "missing", "outlier", "inconsistent"], "rows": rows}

    # ---- TPM visits: [month, camp, partner, sector, rating, issues, category, open(0/1), daysToClose|null, day]
    cats = sorted(tpm["issue_category"].dropna().unique().tolist())
    tpm_rows = []
    for r in tpm.itertuples():
        d = str(r.visit_date)
        tpm_rows.append([
            m_idx.get(d[:7], -1), c_idx[r.camp_id], p_idx[r.partner_id], s_idx[r.sector_id], int(r.rating),
            int(r.issues_flagged), cats.index(r.issue_category) if isinstance(r.issue_category, str) else -1,
            int(r.followup_status == "Open"), None if pd.isna(r.days_to_close) else int(r.days_to_close),
            r.visit_id, d])
    tpm_out = {"categories": cats,
               "fields": ["month", "camp", "partner", "sector", "rating", "issues", "category", "open",
                          "daysToClose", "id", "date"], "rows": tpm_rows}

    # ---- population (real)
    population = {
        "asOf": str(pop["as_of"].iloc[0]),
        "total": int(pop["individuals"].sum()),
        "families": int(pop["families"].sum()),
        "camps": [{"name": r.camp_name, "families": int(r.families), "individuals": int(r.individuals)}
                  for r in pop.sort_values("individuals", ascending=False).itertuples()],
        "ageGroups": demo["age_group"].drop_duplicates().tolist(),
        "ageSex": {sex: demo[demo["sex"] == sex].set_index("age_group").loc[
            demo["age_group"].drop_duplicates(), "individuals"].astype(int).tolist() for sex in ("Female", "Male")},
    }

    # ---- wages (real BBS)
    w = wages.copy()
    w["month"] = w["date"].astype(str).str[:7]
    series = {}
    for (dist, sex, meals), grp in w.groupby(["district", "sex", "meals"]):
        series.setdefault(meals, {})[f"{dist}|{sex}"] = dict(zip(grp["month"], grp["daily_wage_bdt"].astype(int)))
    wage_months = sorted(w["month"].unique().tolist())
    wages_out = {"months": wage_months, "meals": ["No meals", "1 meal", "2 meals", "3 meals"],
                 "series": {meals: {k: [v.get(m) for m in wage_months] for k, v in d.items()}
                            for meals, d in series.items()}}

    metadata = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "programmePeriod": [months[0], months[-1]],
        "fundingCut": "2026-01",
        "asOf": {"population": population["asOf"], "camps": str(camps["population_as_of"].iloc[0]),
                 "wages": wage_months[-1], "programme": months[-1]},
        "flags": {"population": "real", "campCoordinates": "real", "demographics": "real", "wages": "real",
                  "programmeResults": "synthetic", "partners": "synthetic", "tpmVisits": "synthetic"},
        "sources": [
            {"name": "Rohingya Refugees Population by Location (site coordinates)", "publisher": "ISCG on HDX",
             "licence": "CC0 (public domain)",
             "url": "https://data.humdata.org/dataset/site-location-of-rohingya-refugees-in-cox-s-bazar"},
            {"name": "Rohingya refugee population dashboard, 30 Jun 2026",
             "publisher": "Government of Bangladesh - UNHCR Joint Registration",
             "licence": "Public document; figures reused with attribution",
             "attribution": "Source: Government of Bangladesh – UNHCR Joint Registration, 30 Jun 2026",
             "url": "https://data.unhcr.org/en/documents/download/123174"},
            {"name": "Agricultural Wage Statistics", "publisher": "Bangladesh Bureau of Statistics (BBS)",
             "licence": "Public government statistics; reused with attribution",
             "attribution": "Source: BBS Agricultural Wage Statistics; derived by the author",
             "url": "http://www.bbs.gov.bd/"},
        ],
        "thresholds": {"onTrack": 0.9, "atRisk": 0.7},
        "dqLog": dq_log.to_dict(orient="records"),
        "repo": "https://github.com/takyurp09/powerbi-humanitarian-monitoring-dashboard",
    }

    sizes = {name: dump(name, obj) for name, obj in [
        ("metadata", metadata), ("dims", dims), ("results", results), ("tpm", tpm_out),
        ("population", population), ("wages", wages_out)]}
    total = sum(sizes.values())
    for k, v in sizes.items():
        print(f"site/data/{k}.json  {v / 1024:7.1f} KB")
    print(f"total               {total / 1024:7.1f} KB")
    if total > MAX_BYTES:
        raise SystemExit(f"JSON payload {total} bytes exceeds {MAX_BYTES}")


if __name__ == "__main__":
    main()
