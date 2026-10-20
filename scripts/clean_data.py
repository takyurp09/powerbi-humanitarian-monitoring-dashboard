"""Clean raw files into the star-schema model tables in data/model/ (idempotent)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MODEL = ROOT / "data" / "model"
DIMS = ["dim_date", "dim_camp", "dim_sector", "dim_indicator", "dim_partner"]
RESULT_COLS = ["date", "camp_id", "indicator_id", "partner_id", "sex", "target", "achieved",
               "reported_date", "is_late", "dq_flag"]
TPM_COLS = ["visit_id", "visit_date", "camp_id", "partner_id", "sector_id", "rating",
            "issues_flagged", "issue_category", "followup_status", "days_to_close"]


def camp_key(s: str) -> str:
    """Normalise a camp spelling to a comparison key, e.g. ' camp-1e ' -> '1E'."""
    s = re.sub(r"(?i)^\s*camp", "", str(s))
    s = re.sub(r"[\s\-_]+", "", s).upper()
    return s.replace("EXT", " EXT")


def parse_dates(s: pd.Series) -> pd.Series:
    """Parse ISO, dd/mm/yyyy and dd-Mon-yyyy strings."""
    out = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    for fmt in ("%d/%m/%Y", "%d-%b-%Y"):
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out


def main() -> None:
    MODEL.mkdir(parents=True, exist_ok=True)
    log: list[tuple[str, int]] = []
    dims = {d: pd.read_csv(RAW / f"ref_{d}.csv") for d in DIMS}
    for d, df in dims.items():
        df.to_csv(MODEL / f"{d}.csv", index=False)
    camp_map = {camp_key(n): cid for n, cid in zip(dims["dim_camp"].camp_name, dims["dim_camp"].camp_id)}
    agg = dims["dim_indicator"].set_index("indicator_id")["aggregation"]

    # ---- results ----
    r = pd.read_csv(RAW / "raw_results_partner_reports.csv")
    n0 = len(r)
    r = r.drop_duplicates()
    log.append(("results: exact duplicate rows removed", n0 - len(r)))
    keys = r["camp"].map(camp_key)
    log.append(("results: camp names standardised", int((~r["camp"].isin(dims["dim_camp"].camp_name)).sum())))
    r["camp_id"] = keys.map(camp_map)
    if r["camp_id"].isna().any():
        raise ValueError(f"Unmapped camps: {r.loc[r.camp_id.isna(), 'camp'].unique()}")
    d = parse_dates(r["report_month"])
    log.append(("results: non-ISO report dates parsed", int((~r["report_month"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum())))
    r["date"] = d.dt.to_period("M").dt.to_timestamp()
    rep = parse_dates(r["submitted_on"])
    sex_fix = r["sex"].isin(["F", "M"])
    log.append(("results: sex codes expanded (F/M)", int(sex_fix.sum())))
    r["sex"] = r["sex"].replace({"F": "Female", "M": "Male"})
    r = r.rename(columns={"indicator_code": "indicator_id", "partner_code": "partner_id"})
    r["reported_date"] = rep
    deadline = r["date"] + pd.DateOffset(months=1) + pd.Timedelta(days=9)
    r["is_late"] = r["reported_date"] > deadline
    log.append(("results: late reports flagged", int(r["is_late"].sum())))
    key = ["date", "camp_id", "indicator_id", "partner_id", "sex"]
    n1 = len(r)
    r = r.sort_values("reported_date").drop_duplicates(key, keep="last")
    log.append(("results: key duplicates removed (kept latest)", n1 - len(r)))

    is_avg = r["indicator_id"].map(agg).eq("avg")
    flag = pd.Series("OK", index=r.index)
    missing = r["achieved"].isna()
    inconsistent = ~missing & ((r["achieved"] < 0) | (is_avg & (r["achieved"] > 100)))
    ratio = r["achieved"] / r["target"]
    outlier = ~missing & ~inconsistent & ~is_avg & (ratio > 2.5)
    flag[missing], flag[inconsistent], flag[outlier] = "Missing", "Inconsistent", "Outlier"
    r["dq_flag"] = flag
    log += [("results: missing achieved flagged", int(missing.sum())),
            ("results: inconsistent values flagged (negative / >100%) and blanked", int(inconsistent.sum())),
            ("results: outliers flagged (achieved > 2.5x target)", int(outlier.sum()))]
    r.loc[inconsistent, "achieved"] = np.nan
    r["date"] = r["date"].dt.strftime("%Y-%m-%d")
    r["reported_date"] = r["reported_date"].dt.strftime("%Y-%m-%d")
    r["is_late"] = r["is_late"].map({True: "TRUE", False: "FALSE"})
    for col in ("target", "achieved"):  # integers for count indicators, 1 dp for %
        r[col] = [("" if pd.isna(x) else (f"{x:.1f}" if a else str(int(round(x)))))
                  for x, a in zip(r[col], is_avg)]
    r = r.sort_values(key)[RESULT_COLS]
    r.to_csv(MODEL / "fact_results.csv", index=False)

    # ---- TPM ----
    t = pd.read_csv(RAW / "raw_tpm_visits.csv")
    n0 = len(t)
    t = t.drop_duplicates("visit_ref")
    log.append(("tpm: duplicate visits removed", n0 - len(t)))
    t["camp_id"] = t["camp"].map(camp_key).map(camp_map)
    log.append(("tpm: camp names standardised", int((~t["camp"].isin(dims["dim_camp"].camp_name)).sum())))
    t["visit_date"] = parse_dates(t["date_of_visit"]).dt.strftime("%Y-%m-%d")
    log.append(("tpm: issue_category case fixed", int((t["issue_category"] != t["issue_category"].str.title()).sum())))
    t["issue_category"] = t["issue_category"].str.title()
    t = t.rename(columns={"visit_ref": "visit_id", "partner": "partner_id", "sector": "sector_id"})
    t["days_to_close"] = t["days_to_close"].where(t["followup_status"] == "Closed").astype("Int64")
    t = t.sort_values("visit_id")[TPM_COLS]
    t.to_csv(MODEL / "fact_tpm_visits.csv", index=False)

    pd.DataFrame(log, columns=["rule", "rows_affected"]).to_csv(MODEL / "dq_log.csv", index=False)
    print(f"Model tables written to {MODEL}")


if __name__ == "__main__":
    main()
