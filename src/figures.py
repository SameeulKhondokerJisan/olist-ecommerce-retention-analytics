"""Static charts (matplotlib) for the README, memo and notebook."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import config  # noqa: E402

BLUE, ORANGE, GREY, RED = "#2b6cb0", "#c05621", "#a0aec0", "#c53030"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})


def _save(fig, name: str) -> str:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(config.FIGURES / name, bbox_inches="tight")
    plt.close(fig)
    return f"reports/figures/{name}"


def monthly_kpis(m: pd.DataFrame) -> str:
    m = m[m.purchase_month >= pd.Timestamp("2017-01-01")]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.bar(m.purchase_month, m.gmv / 1e6, width=20, color=BLUE, label="GMV (R$ millions)")
    ax.set_ylabel("GMV (R$ millions)")
    ax2 = ax.twinx()
    ax2.plot(m.purchase_month, m.late_rate * 100, color=RED, marker="o", label="Late deliveries (%)")
    ax2.set_ylabel("Late deliveries (%)")
    ax2.spines["top"].set_visible(False)
    ax.set_title("Monthly GMV and late-delivery rate", fontweight="bold")
    fig.legend(loc="upper left", bbox_to_anchor=(0.07, 0.9), fontsize=8)
    return _save(fig, "01_monthly_gmv_late_rate.png")


def cohort_heatmap(cohorts: pd.DataFrame, max_month: int = 12) -> str:
    c = cohorts[(cohorts.months_since_first >= 1) & (cohorts.months_since_first <= max_month)]
    pivot = c.pivot_table(index="cohort_month", columns="months_since_first", values="retention_rate") * 100
    pivot.index = pd.to_datetime(pivot.index).strftime("%Y-%m")
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(pivot.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(range(pivot.shape[1]), pivot.columns)
    ax.set_yticks(range(pivot.shape[0]), pivot.index, fontsize=8)
    for (i, j), v in np.ndenumerate(pivot.to_numpy()):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6.5)
    ax.set_xlabel("Months since first order")
    fig.colorbar(im, ax=ax, label="Customers ordering again (%)")
    ax.set_title("Monthly cohort retention", fontweight="bold")
    return _save(fig, "02_cohort_retention.png")


def review_by_delay(buckets: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(buckets.delay_bucket.astype(str), buckets.avg_review, color=[BLUE] + [ORANGE] * (len(buckets) - 1))
    for i, row in buckets.reset_index(drop=True).iterrows():
        ax.text(i, row.avg_review + 0.05, f"{row.avg_review:.2f}\n({row.negative_rate * 100:.0f}% 1-2 stars)",
                ha="center", fontsize=8)
    ax.set_ylim(0, 5.6)
    ax.set_ylabel("Average review score")
    ax.set_title("Review score by delivery delay versus the promised date", fontweight="bold")
    return _save(fig, "03_review_by_delay.png")


def late_rate_by_state(states: pd.DataFrame, top: int = 15) -> str:
    s = states.head(top).sort_values("late_rate")
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.barh(s.customer_state, s.late_rate * 100, color=BLUE)
    for i, row in enumerate(s.itertuples()):
        ax.text(row.late_rate * 100 + 0.3, i, f"{row.late_rate * 100:.1f}%  (n={row.delivered_orders:,})",
                va="center", fontsize=8)
    ax.set_xlabel("Late deliveries (%)")
    ax.set_title(f"Late-delivery rate, {top} largest customer states", fontweight="bold")
    return _save(fig, "04_late_rate_by_state.png")


def segment_sizes(seg: pd.DataFrame) -> str:
    seg = seg.sort_values("customers")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    axes[0].barh(seg.segment, seg.customers, color=BLUE)
    axes[0].set_title("Customers")
    axes[1].barh(seg.segment, seg.gmv_share * 100, color=ORANGE)
    axes[1].set_title("Share of GMV (%)")
    fig.suptitle("RFM segments", fontweight="bold")
    return _save(fig, "05_rfm_segments.png")


def clv_holdout(by_freq: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7, 3.4))
    x = np.arange(len(by_freq))
    ax.bar(x - 0.2, by_freq.actual, 0.4, color=BLUE, label="Actual")
    ax.bar(x + 0.2, by_freq.predicted, 0.4, color=ORANGE, label="BG/NBD predicted")
    ax.set_xticks(x, [f"{int(v)}{'+' if v == 3 else ''} repeat days\n(n={n:,})" for v, n in
                      zip(by_freq.x, by_freq.customers)])
    ax.set_ylabel("Purchases per customer in holdout")
    ax.legend()
    ax.set_title("CLV model check: 26-week holdout, by calibration frequency", fontweight="bold")
    return _save(fig, "06_clv_holdout.png")
