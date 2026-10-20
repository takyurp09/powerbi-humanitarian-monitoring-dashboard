"""Generate README images: assets/banner.png and assets/dashboard_mockup.png (design mock-up, not a Power BI screenshot)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL, ASSETS = ROOT / "data" / "model", ROOT / "assets"
INK, MUTED, BG, CARD, ACCENT = "#1f2933", "#616e7c", "#f5f7fa", "#ffffff", "#2f6f8f"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.hashsalt": "x", "figure.dpi": 100})


def banner() -> None:
    fig = plt.figure(figsize=(12, 3), facecolor=BG)
    fig.add_artist(plt.Rectangle((0, 0), 0.012, 1, color=ACCENT, transform=fig.transFigure))
    fig.text(0.05, 0.60, "Humanitarian Programme Monitoring Dashboard", fontsize=26, weight="bold", color=INK)
    fig.text(0.05, 0.36, "Power BI  ·  Cox's Bazar", fontsize=17, color=ACCENT)
    fig.text(0.05, 0.16, "Python data pipeline  ·  star schema  ·  DAX measure library  ·  real public population data",
             fontsize=11, color=MUTED)
    fig.savefig(ASSETS / "banner.png", dpi=150, facecolor=BG); plt.close(fig)


def mockup() -> None:
    r = pd.read_csv(MODEL / "fact_results.csv")
    ind = pd.read_csv(MODEL / "dim_indicator.csv")
    sec, tpm = pd.read_csv(MODEL / "dim_sector.csv"), pd.read_csv(MODEL / "fact_tpm_visits.csv")
    r = r.merge(ind, on="indicator_id").merge(sec, on="sector_id")

    def ach(g: pd.DataFrame) -> float:  # mixed aggregation, equal weight across indicators
        per = [(x.achieved.sum() / x.target.sum()) if x.aggregation.iloc[0] == "sum"
               else (x.achieved.mean() / x.target.mean()) for _, x in g.groupby("indicator_id")]
        return 100 * sum(per) / len(per)

    flagged = tpm[tpm.issues_flagged > 0]
    kpis = [("Achievement", ach(r)), ("Reporting timeliness", 100 * (1 - r.is_late.astype(str).str.upper().eq("TRUE").mean())),
            ("Data quality score", 100 * r.dq_flag.eq("OK").mean()),
            ("TPM closure rate", 100 * flagged.followup_status.eq("Closed").mean())]
    by_sec = r.groupby("sector_name").apply(ach, include_groups=False).sort_values()
    # Reach per 1,000 children uses the same definition as the case study (scripts/case_study_metrics.py).
    reach = pd.read_csv(ROOT / "docs" / "case_study_tables" / "camp_reach.csv").set_index("camp_name").reach_per_1000
    reach = reach.sort_values().tail(10)
    fig = plt.figure(figsize=(12, 7), facecolor=BG)
    fig.text(0.03, 0.94, "Executive overview", fontsize=18, weight="bold", color=INK)
    fig.text(0.03, 0.905, "Jan 2025 – Jun 2026  ·  all sectors, camps and partners  ·  synthetic programme data",
             fontsize=10, color=MUTED)
    for i, (name, v) in enumerate(kpis):
        ax = fig.add_axes((0.03 + i * 0.24, 0.70, 0.22, 0.16)); ax.set_facecolor(CARD)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_color("#d9e2ec")
        ax.text(0.07, 0.68, name, fontsize=11, color=MUTED, transform=ax.transAxes)
        ax.text(0.07, 0.22, f"{v:.1f}%", fontsize=24, weight="bold", color=INK, transform=ax.transAxes)
    for box, data, title, fmt in [((0.12, 0.08, 0.33, 0.52), by_sec, "Achievement % by sector", "{:.1f}%"),
                                  ((0.60, 0.08, 0.36, 0.52), reach, "Reach per 1,000 children (top 10 camps)", "{:.0f}")]:
        ax = fig.add_axes(box); ax.set_facecolor(BG)
        ax.barh(data.index, data.values, color=ACCENT, height=0.6)
        ax.set_title(title, loc="left", fontsize=12, color=INK, pad=10)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=9)
        for y, v in enumerate(data.values):
            ax.text(v, y, " " + fmt.format(v), va="center", fontsize=8, color=INK)
        ax.set_xlim(0, data.max() * 1.15)
    fig.savefig(ASSETS / "dashboard_mockup.png", dpi=120, facecolor=BG); plt.close(fig)


if __name__ == "__main__":
    banner(); mockup(); print("README assets written: banner.png, dashboard_mockup.png")
