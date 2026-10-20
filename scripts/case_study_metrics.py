"""Compute the figures cited in docs/CASE_STUDY.md and draw its charts.

Reads data/model/*.csv, writes docs/case_study_tables/*.csv and assets/case_study_*.png,
and prints the headline values. Population and wage figures are real; programme results,
partners and TPM visits are synthetic (illustrative only).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL, TABLES, ASSETS = ROOT / "data" / "model", ROOT / "docs" / "case_study_tables", ROOT / "assets"
CUT = pd.Timestamp("2026-01-01")
BLUE, ORANGE, VERM, GREY, INK = "#0072B2", "#E69F00", "#D55E00", "#9E9E9E", "#333333"


def rd(name: str) -> pd.DataFrame:
    return pd.read_csv(MODEL / f"{name}.csv", keep_default_na=False, na_values=[""])


def save(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df


def achievement(f: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Indicator ratio (sum/sum or mean/mean), then equal-weight mean across indicators."""
    g = f.dropna(subset=["achieved"]).groupby(by + ["indicator_id", "aggregation"])
    r = g.agg(t=("target", "sum"), a=("achieved", "sum"), tm=("target", "mean"), am=("achieved", "mean")).reset_index()
    r["pct"] = (r["a"] / r["t"]).where(r["aggregation"] == "sum", r["am"] / r["tm"]) * 100
    return r.groupby(by, as_index=False)["pct"].mean()


def style(ax, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GREY)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="x" if ax.get_xlabel() == "" else "y", color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    f, v = rd("fact_results"), rd("fact_tpm_visits")
    camp, ind, sec, par = rd("dim_camp"), rd("dim_indicator"), rd("dim_sector"), rd("dim_partner")
    pop, demo, wage, dq = rd("ref_population_2026"), rd("ref_demographics_2026"), rd("ref_wages_coxsbazar"), rd("dq_log")
    f["date"] = pd.to_datetime(f["date"])
    f = f.merge(ind, on="indicator_id").merge(sec, on="sector_id")
    f["is_late"] = f["is_late"].astype(str).str.upper()
    f["period"] = (f["date"] >= CUT).map({False: "2025", True: "2026 H1"})
    out: dict[str, str] = {}

    # 1. Context (real)
    tot, fam = pop["individuals"].sum(), pop["families"].sum()
    u18 = demo[demo.age_group.isin(["Below 1", "1-4", "5-11", "12-17"])]["individuals"].sum()
    fem = demo[demo.sex == "Female"]["individuals"].sum()
    ctx = pd.DataFrame({"metric": ["individuals", "families", "under_18", "under_18_share_pct", "female_share_pct",
                                   "camps_in_model", "population_in_model"],
                        "value": [tot, fam, u18, round(u18 / tot * 100, 1), round(fem / tot * 100, 1),
                                  len(camp), camp["population"].sum()]})
    save(ctx, "context_population")
    save(pop.sort_values("individuals", ascending=False).head(5), "context_largest_camps")

    # 2. Sector achievement before / after the January 2026 cut
    s = achievement(f, ["sector_name", "period"]).pivot(index="sector_name", columns="period", values="pct")
    s["change_pp"] = s["2026 H1"] - s["2025"]
    tg = f.groupby(["sector_name", "period"])["target"].sum().unstack()
    s["target_change_pct"] = (tg["2026 H1"] / 6) / (tg["2025"] / 12) * 100 - 100
    s = save(s.round(1).reset_index().sort_values("2026 H1"), "sector_achievement")
    overall = achievement(f, ["period"]).set_index("period")["pct"]
    ind_p = achievement(f, ["indicator_name", "period"])
    off = ind_p[(ind_p.period == "2026 H1") & (ind_p.pct < 70)]
    risk = ind_p[(ind_p.period == "2026 H1") & (ind_p.pct.between(70, 90, inclusive="left"))]
    save(ind_p.pivot(index="indicator_name", columns="period", values="pct").round(1).reset_index(), "indicator_achievement")

    # 3. Camp reach per 1,000 children (children-unit count indicators)
    ch = f[(f.unit == "children") & (f.aggregation == "sum")]
    months = ch["date"].nunique()
    cr = ch.groupby("camp_id")["achieved"].sum().div(months).rename("monthly_reached").reset_index().merge(camp, on="camp_id")
    cr["children_population"] = (cr["population"] * cr["children_share"]).round()
    cr["reach_per_1000"] = cr["monthly_reached"] / cr["children_population"] * 1000
    cr["achievement_pct"] = cr["camp_id"].map(achievement(f, ["camp_id"]).set_index("camp_id")["pct"])
    cr = save(cr[["camp_name", "upazila", "population", "children_population", "monthly_reached", "reach_per_1000",
                  "achievement_pct"]].round(1).sort_values("reach_per_1000", ascending=False), "camp_reach")

    # 4. Timeliness and DQ by partner
    f["lag"] = (pd.to_datetime(f["reported_date"]) - f["date"]).dt.days  # as DAX [Avg Reporting Lag (days)]
    p = f.groupby("partner_id").agg(rows=("is_late", "size"), late=("is_late", lambda x: (x == "TRUE").sum()),
                                    lag=("lag", "mean"), dq_issues=("dq_flag", lambda x: (x != "OK").sum())).reset_index()
    p["timeliness_pct"] = 100 - p["late"] / p["rows"] * 100
    p["dq_score_pct"] = 100 - p["dq_issues"] / p["rows"] * 100
    p = save(p.merge(par, on="partner_id")[["partner_name", "partner_type", "rows", "late", "timeliness_pct", "lag",
                                             "dq_issues", "dq_score_pct"]].round(1).sort_values("timeliness_pct"),
             "partner_timeliness_dq")
    dqt = save(f["dq_flag"].value_counts().rename_axis("dq_flag").reset_index(name="rows"), "dq_by_type")
    save(dq, "dq_cleaning_log")

    # 5. TPM follow-up
    iss = v[v.issues_flagged > 0].copy()
    t = iss.groupby("issue_category").agg(visits=("visit_id", "size"), issues=("issues_flagged", "sum"),
                                          closed=("followup_status", lambda x: (x == "Closed").sum()),
                                          avg_days=("days_to_close", "mean"), median_days=("days_to_close", "median")).reset_index()
    t["closure_pct"] = t["closed"] / t["visits"] * 100
    latest = pd.to_datetime(v["visit_date"]).max()
    iss["overdue"] = (iss.followup_status == "Open") & ((latest - pd.to_datetime(iss.visit_date)).dt.days > 30)
    t["open_over_30d"] = t["issue_category"].map(iss.groupby("issue_category")["overdue"].sum())
    t = save(t.round(1).sort_values("closure_pct"), "tpm_by_category")

    # 6. Female share
    cnt = f[f.aggregation == "sum"].dropna(subset=["achieved"])
    fs = cnt.groupby(["sector_name", "sex"])["achieved"].sum().unstack()
    fs["female_share_pct"] = fs["Female"] / fs.sum(axis=1) * 100
    fs = save(fs.round(1).reset_index(), "female_share_by_sector")
    fc = cnt.groupby(["camp_id", "sex"])["achieved"].sum().unstack()
    fc = (fc["Female"] / fc.sum(axis=1) * 100).rename("female_share_pct").reset_index().merge(camp[["camp_id", "camp_name"]])
    save(fc[["camp_name", "female_share_pct"]].round(1).sort_values("female_share_pct"), "female_share_by_camp")
    fem_all = cnt.loc[cnt.sex == "Female", "achieved"].sum() / cnt["achieved"].sum() * 100

    # 7. Host wages (real)
    w = wage[wage.meals == "No meals"].copy()
    w["year"] = w["date"].str[:4].astype(int)
    wy = w.groupby(["district", "sex", "year"])["daily_wage_bdt"].median().unstack("district").reset_index()
    wy["gap_pct"] = wy["Cox's Bazar"] / wy["Bangladesh (national median)"] * 100 - 100
    wy = save(wy.round(1), "wage_annual_no_meals")

    # Charts
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150})
    fig, ax = plt.subplots(figsize=(7, 3.4))
    y = range(len(s))
    ax.barh([i + 0.2 for i in y], s["2025"], height=0.38, color=GREY, label="2025")
    ax.barh([i - 0.2 for i in y], s["2026 H1"], height=0.38, color=BLUE, label="2026 H1 (after cut)")
    ax.set_yticks(list(y), s["sector_name"]); ax.axvline(90, color=INK, lw=0.8, ls="--")
    ax.text(90.5, len(s) - 0.4, "90% on track", fontsize=8, color=INK)
    ax.set_xlim(0, 110); ax.set_xlabel("Achievement % (equal-weight indicators)", fontsize=9)
    style(ax, "Achievement by sector, before and after the January 2026 funding cut")
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, fontsize=8, loc="lower right", ncol=2)
    fig.text(0.01, 0.01, "Illustrative: synthetic programme data.", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(ASSETS / "case_study_sectors.png"); plt.close(fig)

    c = cr.sort_values("reach_per_1000")
    fig, ax = plt.subplots(figsize=(7, 5.6))
    cols = [VERM if i < 5 else (BLUE if i >= len(c) - 5 else GREY) for i in range(len(c))]
    ax.barh(c["camp_name"], c["reach_per_1000"], color=cols, height=0.7)
    med = c["reach_per_1000"].median(); ax.axvline(med, color=INK, lw=0.8, ls="--")
    ax.text(med + 3, 0, f"median {med:,.0f}", fontsize=8, color=INK)
    ax.set_xlabel("Children reached per month per 1,000 children (real population denominator)", fontsize=9)
    style(ax, "Reach per 1,000 children by camp (bottom 5 vermilion, top 5 blue)")
    ax.tick_params(axis="y", labelsize=8)
    fig.text(0.01, 0.01, "Illustrative: synthetic results; real 2026 camp population.", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(ASSETS / "case_study_camp_reach.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.barh(t["issue_category"], t["closure_pct"], color=[VERM if x == "Safeguarding" else BLUE for x in t["issue_category"]], height=0.6)
    for i, (cp, d) in enumerate(zip(t["closure_pct"], t["avg_days"])):
        ax.text(cp + 1, i, f"{cp:.0f}% closed, {d:.0f} days avg", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 115); ax.set_xlabel("Closure rate % (visits with issues)", fontsize=9)
    style(ax, "TPM follow-up closure by issue category")
    fig.text(0.01, 0.01, "Illustrative: synthetic TPM visits.", fontsize=7, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(ASSETS / "case_study_tpm.png"); plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(8, 3.2), gridspec_kw={"width_ratios": [2.3, 1]})
    m = w[w.sex == "Male"]
    for d, col in [("Cox's Bazar", BLUE), ("Bangladesh (national median)", GREY)]:
        sr = m[m.district == d].assign(date=lambda x: pd.to_datetime(x.date)).set_index("date")["daily_wage_bdt"]
        sr = sr.reindex(pd.date_range("2017-01-01", "2025-12-01", freq="MS"))
        axs[0].plot(sr.index, sr.values, color=col, lw=2)
        last = sr.dropna()
        axs[0].text(last.index[-1], last.iloc[-1], " Cox's Bazar" if d.startswith("Cox") else " National", fontsize=8,
                    color=INK, va="center")
    axs[0].set_ylabel("BDT per day (nominal)", fontsize=9); axs[0].set_xlabel("")
    style(axs[0], "Male agricultural wage, no meals")
    axs[0].grid(axis="y", color="#e5e5e5", linewidth=0.6); axs[0].set_xlim(right=pd.Timestamp("2027-06-01"))
    axs[1].bar(["Oct 2021", "Jun 2026"], [901_703, tot], color=BLUE, width=0.55)
    for i, val in enumerate([901_703, tot]):
        axs[1].text(i, val, f"{val / 1e6:.2f}m", ha="center", va="bottom", fontsize=8, color=INK)
    axs[1].set_ylim(0, 1_350_000); axs[1].set_yticks([]); style(axs[1], "Registered camp population"); axs[1].grid(False)
    axs[1].spines["left"].set_visible(False)
    fig.text(0.01, 0.01, "Sources: BBS Agricultural Wage Statistics (derived by author); RRRC-UNHCR (2021), "
             "GoB-UNHCR Joint Registration (30 Jun 2026). Descriptive only.", fontsize=6.5, color="#666")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(ASSETS / "case_study_host_wages.png"); plt.close(fig)

    # Print headline values
    print(f"Population: {tot:,} individuals, {fam:,} families; under-18 {u18:,} ({u18 / tot * 100:.1f}%); "
          f"female {fem / tot * 100:.1f}%; model camps {len(camp)} = {camp.population.sum():,}")
    print(f"Overall achievement: 2025 {overall['2025']:.1f}% -> 2026 H1 {overall['2026 H1']:.1f}%")
    print("Sector achievement:\n" + s.to_string(index=False))
    print(f"Indicators off track in 2026 H1: {len(off)} ({', '.join(off.indicator_name)}); at risk: {len(risk)}")
    print(f"Camp reach per 1,000 children: median {med:.0f}; top 5:\n{cr.head(5).to_string(index=False)}\n"
          f"bottom 5:\n{cr.tail(5).to_string(index=False)}")
    print(f"Timeliness overall {(f.is_late == 'FALSE').mean() * 100:.1f}%; DQ score {(f.dq_flag == 'OK').mean() * 100:.1f}%")
    print("Timeliness by period: " + str((f.groupby("period")["is_late"].apply(lambda x: (x == "FALSE").mean() * 100)).round(1).to_dict()))
    print("Partners:\n" + p.to_string(index=False))
    print("DQ by type:\n" + dqt.to_string(index=False))
    print(f"TPM: {len(v)} visits, {len(iss)} with issues, closure {(iss.followup_status == 'Closed').mean() * 100:.1f}%, "
          f"avg days {iss.days_to_close.mean():.1f}, open >30d {int(iss.overdue.sum())}, avg rating {v.rating.mean():.2f}")
    print(t.to_string(index=False))
    print(f"Female share overall {fem_all:.1f}%\n" + fs.to_string(index=False))
    print(f"Camps with female share < 45%: {(fc.female_share_pct < 45).sum()}; range "
          f"{fc.female_share_pct.min():.1f}-{fc.female_share_pct.max():.1f}%")
    print("Wages (no meals, annual median):\n" + wy.to_string(index=False))
    print(f"Wrote {len(list(TABLES.glob('*.csv')))} tables to docs/case_study_tables/ and 4 charts to assets/.")


if __name__ == "__main__":
    main()
