"""Generate deterministic synthetic data for the humanitarian monitoring dashboard.

dim_camp is built from REAL public population data (run scripts/ingest_population.py first):
camp names, upazila, union and coordinates from the HDX 2021 site list, population/families from
the GoB-UNHCR 30 Jun 2026 dashboard, children share = national under-18 share (2026).
Programme results and TPM visits are synthetic (seed 2026), with targets scaled to real
camp (children) population. Writes:
  data/raw/ref_*.csv                       clean reference dimensions
  data/raw/raw_results_partner_reports.csv messy partner reports
  data/raw/raw_tpm_visits.csv              messy TPM visit log
Run scripts/clean_data.py afterwards to build data/model/.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MODEL = ROOT / "data" / "model"
N_CAMPS = 24
MONTHS = pd.date_range("2025-01-01", "2026-06-01", freq="MS")
FUNDING_CUT = pd.Timestamp("2026-01-01")


SECTORS = ["Education", "Child Protection", "WASH", "Health", "Nutrition"]

# (sector_idx, name, unit, aggregation, base monthly target per 10k population or % target).
# "children" indicators are scaled by children population (base per 5,200 children = 10k people
# at the national 52% under-18 share); other count indicators by total population.
INDICATORS = [
    (0, "Children enrolled in learning centres", "children", "sum", 900),
    (0, "Learning facilities meeting standards", "facilities", "sum", 6),
    (0, "Learning centre attendance rate", "%", "avg", 85),
    (1, "Children receiving case management", "children", "sum", 40),
    (1, "Children reached with psychosocial support", "children", "sum", 350),
    (1, "Child protection cases closed", "%", "avg", 70),
    (2, "People with access to safe water", "people", "sum", 4500),
    (2, "Latrines rehabilitated", "facilities", "sum", 12),
    (2, "Hygiene kits distributed on time", "%", "avg", 90),
    (3, "Outpatient consultations", "people", "sum", 1200),
    (3, "Children vaccinated against measles", "children", "sum", 120),
    (3, "Health facilities with no stock-out", "%", "avg", 95),
    (4, "Children screened for malnutrition", "children", "sum", 1400),
    (4, "SAM admissions treated", "children", "sum", 25),
    (4, "SAM cure rate", "%", "avg", 75),
]
PARTNERS = [("Partner A", "International NGO"), ("Partner B", "International NGO"),
            ("Partner C", "National NGO"), ("Partner D", "National NGO"),
            ("Partner E", "Government"), ("Partner F", "International NGO"),
            ("Partner G", "National NGO"), ("Partner H", "National NGO"),
            ("Partner I", "International NGO"), ("Partner J", "Government")]
# Partners active per sector (index into PARTNERS)
SECTOR_PARTNERS = {0: [0, 2, 6], 1: [1, 3, 7], 2: [5, 2, 8], 3: [4, 9, 0], 4: [8, 3, 6]}
ISSUE_CATS = ["Quality", "Access", "Safeguarding", "Supplies", "Reporting"]


def camp_sort_key(name: str) -> tuple[int, str]:
    """Natural camp order: Camp 1E, 1W, 2E, ..., 4, 4 Extension, ..., then named sites."""
    m = re.match(r"Camp (\d+)(.*)", name)
    return (int(m.group(1)), m.group(2)) if m else (999, name)


def build_dim_camp() -> pd.DataFrame:
    """Real camp list: the N_CAMPS most populous camps in the 2026 GoB-UNHCR table that also
    appear in the HDX 2021 site list (excludes Bhasan Char and 'Other', which have no site row).
    population = 2026 figure if available, else HDX 2021 figure."""
    h = pd.read_csv(MODEL / "dim_camp_population_2021.csv")
    p = pd.read_csv(MODEL / "ref_population_2026.csv")
    demo = pd.read_csv(MODEL / "ref_demographics_2026.csv")
    u18 = demo.loc[~demo.age_group.isin(["18-59", "60+"]), "individuals"].sum() / demo.individuals.sum()
    m = h.merge(p[["camp_name", "families", "individuals", "as_of"]], on="camp_name", how="left",
                suffixes=("_2021", "_2026"))
    has26 = m["individuals_2026"].notna()
    m["population"] = m["individuals_2026"].where(has26, m["individuals_2021"]).astype(int)
    m["families"] = m["families"].where(has26, m["households"]).astype(int)
    m["population_source"] = np.where(has26, "GoB-UNHCR Joint Registration (dashboard)",
                                      "RRRC-UNHCR family counting (HDX)")
    m["population_as_of"] = m["as_of_2026"].where(has26, m["as_of_2021"])
    top = m.sort_values("population", ascending=False).head(N_CAMPS)
    top = top.iloc[sorted(range(len(top)), key=lambda i: camp_sort_key(top.iloc[i]["camp_name"]))]
    return pd.DataFrame({
        "camp_id": [f"C{i + 1:02d}" for i in range(len(top))],
        "camp_name": top["camp_name"].values,
        "upazila": top["upazila"].values,
        "union": top["union"].values,
        "latitude": top["latitude"].round(5).values,
        "longitude": top["longitude"].round(5).values,
        "population": top["population"].values,
        "families": top["families"].values,
        "children_share": round(float(u18), 3),
        "population_source": top["population_source"].values,
        "population_as_of": top["population_as_of"].values,
    })


def build_dims(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    """Build clean reference dimension tables."""
    d = pd.DataFrame({"date": MONTHS})
    dim_date = pd.DataFrame({
        "date": d["date"].dt.strftime("%Y-%m-%d"),
        "year": d["date"].dt.year,
        "quarter": "Q" + d["date"].dt.quarter.astype(str),
        "month_num": d["date"].dt.month,
        "month_name": d["date"].dt.strftime("%b"),
        "fiscal_label": d["date"].dt.strftime("%Y-%m"),
    })
    dim_camp = build_dim_camp()
    dim_sector = pd.DataFrame({"sector_id": [f"S{i + 1}" for i in range(5)], "sector_name": SECTORS})
    dim_indicator = pd.DataFrame({
        "indicator_id": [f"I{i + 1:02d}" for i in range(len(INDICATORS))],
        "sector_id": [f"S{s + 1}" for s, *_ in INDICATORS],
        "indicator_name": [x[1] for x in INDICATORS],
        "unit": [x[2] for x in INDICATORS],
        "aggregation": [x[3] for x in INDICATORS],
        "higher_is_better": "TRUE",
    })
    dim_partner = pd.DataFrame({
        "partner_id": [f"P{i + 1:02d}" for i in range(len(PARTNERS))],
        "partner_name": [p[0] for p in PARTNERS],
        "partner_type": [p[1] for p in PARTNERS],
    })
    return {"dim_date": dim_date, "dim_camp": dim_camp, "dim_sector": dim_sector,
            "dim_indicator": dim_indicator, "dim_partner": dim_partner}


def messy_camp(name: str, rng: np.random.Generator) -> str:
    """Return an inconsistent spelling of a camp name ~30% of the time."""
    r = rng.random()
    code = name.replace("Camp ", "")
    if r < 0.08:
        return "camp-" + code.lower().replace(" ", "")
    if r < 0.16 and code[-1] in "EW" and code[:-1].isdigit():
        return f"Camp {code[:-1]} {code[-1]}"
    if r < 0.24:
        return name.upper()
    if r < 0.30:
        return f"  {name} "
    return name


def messy_date(ts: pd.Timestamp, rng: np.random.Generator) -> str:
    """Format a date in one of several formats."""
    fmt = rng.choice(["%Y-%m-%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y"])
    return ts.strftime(str(fmt))


def build_results(dims: dict[str, pd.DataFrame], rng: np.random.Generator) -> pd.DataFrame:
    """Build messy partner reports (month x camp x indicator x partner x sex)."""
    camps = dims["dim_camp"]
    partner_eff = rng.normal(1.0, 0.06, len(PARTNERS))
    rows = []
    for ci, camp in camps.iterrows():
        pop_factor = camp["population"] / 10000
        child_factor = camp["population"] * camp["children_share"] / 5200
        for ii, (s, _name, unit, agg, base) in enumerate(INDICATORS):
            plist = SECTOR_PARTNERS[s]
            k = 1 if rng.random() < 0.55 else 2
            chosen = list(rng.choice(plist, size=k, replace=False))
            shares = [1.0] if k == 1 else [0.6, 0.4]
            for p, share in zip(chosen, shares):
                for m in MONTHS:
                    monsoon = m.month in (6, 7, 8, 9)
                    cut = m >= FUNDING_CUT
                    for sex in ("Female", "Male"):
                        sex_share = 0.52 if sex == "Female" else 0.48
                        if agg == "avg":
                            target = float(base)
                            ach = base * partner_eff[p] * rng.normal(0.97, 0.05)
                            ach -= 6 if monsoon else 0
                            ach -= 4 if cut else 0
                            ach = float(np.clip(ach, 20, 100))
                            target_v, ach_v = round(target, 1), round(ach, 1)
                        else:
                            f = child_factor if unit == "children" else pop_factor
                            t = base * f * share * sex_share * (0.8 if cut else 1.0)
                            t *= rng.normal(1.0, 0.05)
                            perf = partner_eff[p] * rng.normal(0.94, 0.08)
                            perf *= 0.82 if monsoon else 1.0
                            perf *= 0.95 if cut else 1.0
                            target_v = max(1, int(round(t)))
                            ach_v = max(0, int(round(target_v * perf)))
                        # reporting lag: days after month end
                        lag = int(rng.integers(1, 10)) if rng.random() > 0.06 else int(rng.integers(11, 35))
                        rep = m + pd.offsets.MonthEnd(0) + pd.Timedelta(days=lag)
                        rows.append({
                            "report_month": messy_date(m, rng),
                            "camp": messy_camp(camp["camp_name"], rng),
                            "indicator_code": f"I{ii + 1:02d}",
                            "partner_code": f"P{p + 1:02d}",
                            "sex": sex if rng.random() > 0.05 else sex[0],
                            "target": target_v,
                            "achieved": ach_v,
                            "submitted_on": messy_date(rep, rng),
                        })
    df = pd.DataFrame(rows)
    n = len(df)
    # ~1.5% blank achieved, ~1.5% outliers (x6), ~1% inconsistent (avg>100 or achieved<0)
    idx = rng.permutation(n)
    a, b, c = int(n * 0.015), int(n * 0.03), int(n * 0.04)
    df["achieved"] = df["achieved"].astype(float)
    df.loc[idx[:a], "achieved"] = np.nan
    df.loc[idx[a:b], "achieved"] = df.loc[idx[a:b], "achieved"] * 6
    df.loc[idx[b:c], "achieved"] = -df.loc[idx[b:c], "achieved"].abs() - 1
    # duplicates (~1%)
    dups = df.sample(frac=0.01, random_state=SEED)
    return pd.concat([df, dups], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)


def build_tpm(dims: dict[str, pd.DataFrame], rng: np.random.Generator, n: int = 900) -> pd.DataFrame:
    """Build messy TPM visit log."""
    camps = dims["dim_camp"]
    start, end = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-06-30")
    days = (end - start).days
    rows = []
    for v in range(n):
        s = int(rng.integers(0, 5))
        p = int(rng.choice(SECTOR_PARTNERS[s]))
        dt = start + pd.Timedelta(days=int(rng.integers(0, days + 1)))
        rating = int(rng.choice([1, 2, 3, 4], p=[0.08, 0.22, 0.42, 0.28]))
        issues = int(rng.poisson({1: 4, 2: 2.5, 3: 1, 4: 0.3}[rating]))
        cat = str(rng.choice(ISSUE_CATS, p=[0.35, 0.2, 0.1, 0.2, 0.15]))
        age = (end - dt).days
        closed = issues == 0 or rng.random() < min(0.9, 0.35 + age / 400)
        dtc = int(np.clip(rng.gamma(2.2, 9 + 4 * (rating < 3)), 1, max(age, 1))) if (closed and issues > 0) else None
        if issues == 0:
            dtc = 0
        rows.append({
            "visit_ref": f"V{v + 1:05d}",
            "date_of_visit": messy_date(dt, rng),
            "camp": messy_camp(camps.loc[int(rng.integers(0, len(camps))), "camp_name"], rng),
            "partner": f"P{p + 1:02d}",
            "sector": f"S{s + 1}",
            "rating": rating,
            "issues_flagged": issues,
            "issue_category": cat if rng.random() > 0.02 else cat.lower(),
            "followup_status": "Closed" if closed else "Open",
            "days_to_close": dtc,
        })
    df = pd.DataFrame(rows)
    dups = df.sample(n=12, random_state=SEED)
    return pd.concat([df, dups], ignore_index=True)


def main() -> None:
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    dims = build_dims(rng)
    for name, df in dims.items():
        df.to_csv(RAW / f"ref_{name}.csv", index=False)
    build_results(dims, rng).to_csv(RAW / "raw_results_partner_reports.csv", index=False)
    build_tpm(dims, rng).to_csv(RAW / "raw_tpm_visits.csv", index=False)
    print(f"Raw files written to {RAW}")


if __name__ == "__main__":
    main()
