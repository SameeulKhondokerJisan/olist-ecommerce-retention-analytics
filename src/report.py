"""Render README.md and reports/memo.md from reports/results.json (numbers never typed by hand)."""
from __future__ import annotations

from src import config


def _p(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def _brl(x: float, d: int = 0) -> str:
    return f"R${x:,.{d}f}"


def render(results: dict) -> None:
    b, rv, om, rp, cl = (results[k] for k in ("business", "review_vs_lateness", "ordinal_model",
                                               "repeat_vs_first_delivery", "clv"))
    a = results["assumptions"]
    seg = {s["segment"]: s for s in results["rfm_segments"]}
    worst = results["worst_states_late_rate"][:3]
    worst_txt = ", ".join(f"{w['customer_state']} ({_p(w['late_rate'])}, {w['delivered_orders']:,} orders)" for w in worst)
    hold = cl["holdout"]
    rep_sig = rp["z_p_value"] < 0.05 and rp["logit_p_value"] < 0.05
    need = (a["target_review"] - rv["mean_review_late"]) / (rv["mean_review_ontime"] - rv["mean_review_late"])
    need_txt = (f"Reaching an average review of {a['target_review']:.2f} needs {_p(need)} of deliveries on time, "
                f"against {_p(1 - rv['late_share'])} today" if a["target_review"] < rv["mean_review_ontime"]
                else f"A {a['target_review']:.2f} average is above what even on-time orders score")
    base, aov, m, v = rp["repeat_rate_overall"], b["avg_order_value_last_12m"], a["contribution_margin"], a["voucher_cost"]
    breakeven = base * v / (aov * m - v) if aov * m > v else None

    findings = [
        f"**Retention is the gap.** {_p(b['share_customers_one_order'])} of {b['customers']:,} customers ordered only once; on "
        f"average {_p(b['month1_retention_avg'], 2)} of a monthly cohort orders again the next month.",
        f"**Late deliveries drive bad reviews.** Late orders average {rv['mean_review_late']:.2f} stars against "
        f"{rv['mean_review_ontime']:.2f} on time (difference {rv['mean_diff']:.2f}, 95% CI {rv['mean_diff_ci'][0]:.2f} to "
        f"{rv['mean_diff_ci'][1]:.2f}; Mann-Whitney p < 0.001). Holding distance, order value, freight share, basket "
        f"size and category fixed, an ordered logit puts the chance of a 1-2 star review at {_p(om['p_negative_if_late'])} "
        f"for late orders versus {_p(om['p_negative_if_ontime'])} on time.",
        f"**Lateness is concentrated.** {_p(b['late_rate_delivered'])} of deliveries are late overall; the worst large "
        f"states are {worst_txt}.",
        (f"**Late first orders cut repeat purchases.** " if rep_sig else "**No clear retention penalty yet.** ")
        + f"Customers whose first order arrived late re-ordered within 180 days at {_p(rp['repeat_rate_late'], 2)} versus "
        f"{_p(rp['repeat_rate_ontime'], 2)} (difference {rp['diff'] * 100:+.2f} pts, 95% CI {rp['diff_ci'][0] * 100:+.2f} to "
        f"{rp['diff_ci'][1] * 100:+.2f}; logistic regression odds ratio {rp['logit_odds_ratio']:.2f}, p = "
        f"{rp['logit_p_value']:.2f})." + ("" if rep_sig else " The direction is negative but the interval includes zero."),
        f"**The CLV model is well calibrated.** Fitted on orders to {results['settings']['calibration_end']}, BG/NBD "
        f"predicted {hold['predicted_purchases']:,.0f} repeat purchase days in the next {hold['holdout_weeks']} weeks "
        f"against {hold['actual_purchases']:,.0f} actual ({hold['error_pct'] * 100:+.1f}%). Refitted on all data, it expects "
        f"{cl['expected_repeat_purchases_52w']:,.0f} repeat purchases worth {_brl(cl['expected_repeat_gmv_52w'])} in the "
        f"next 12 months, {_p(cl['expected_repeat_gmv_52w'] / b['gmv_last_12m'])} of last year's GMV.",
        f"**Where the value sits.** 'New high-value' customers ({seg['New high-value']['customers']:,}) hold "
        f"{_p(seg['New high-value']['gmv_share'])} of GMV; 'At-risk high-value' customers "
        f"({seg['At-risk high-value']['customers']:,}, last order about "
        f"{seg['At-risk high-value']['avg_recency_days'] / 30:.0f} months ago) hold {_p(seg['At-risk high-value']['gmv_share'])}.",
    ]
    recs = [
        f"Fix delivery promises first in {', '.join(w['customer_state'] for w in worst)}: renegotiate carriers or pad the "
        f"estimated date there. {need_txt}.",
        "Score sellers on late rate and 1-2 star share every month (seller scorecard in Power BI) and cap promises for "
        "the worst offenders.",
        f"Test a second-order voucher on 'New high-value' customers with a holdout group. At {_brl(v, 0)} per voucher and a "
        f"{_p(m, 0)} contribution margin it must lift the 180-day repeat rate by "
        + (f"{breakeven * 100:.1f} pts (from {_p(base, 1)}) to break even." if breakeven else "more than is achievable."),
        "Do not count on retention gains from delivery fixes in the business case until a test confirms them; the "
        "measured review effect alone justifies the delivery work.",
    ]

    readme = f"""# Olist Marketplace: Retention, Customer Lifetime Value and Delivery Experience

**Why do Olist customers not come back, and what should the business fix first?** This project builds a
SQL warehouse from Olist's public marketplace data ({b['orders']:,} orders, {b['first_month']} to {b['last_month']}),
measures how delivery performance shapes reviews and repeat purchases, segments customers, forecasts
lifetime value, and turns the results into an Excel business case and a Power BI report.

**Tools:** SQL (DuckDB star schema, window functions) · Python (pandas, statsmodels, scikit-learn, SciPy) ·
Statistics (Mann-Whitney, ordered logit, logistic regression, bootstrap) · CLV (BG/NBD + Gamma-Gamma) ·
Excel (scenario model) · Power BI (TMDL semantic model, DAX, PBIR report)

![Monthly GMV and late deliveries](reports/figures/01_monthly_gmv_late_rate.png)

## Results

""" + "\n".join(f"{i}. {t}" for i, t in enumerate(findings, 1)) + """

![Review by delay](reports/figures/03_review_by_delay.png)

## Recommendations

""" + "\n".join(f"{i}. {t}" for i, t in enumerate(recs, 1)) + f"""

## Deliverables

| Deliverable | Where |
|---|---|
| Power BI project: TMDL semantic model, 14 DAX measures, 2 report pages | `dashboards/powerbi/OlistRetention.pbip` |
| Star-schema extracts used by Power BI | `dashboards/powerbi/data/` |
| Excel business case (delivery, retention, voucher break-even, sensitivity) | `excel/retention_economics_model.xlsx` |
| Analysis notebook with outputs | `notebooks/olist_analysis.ipynb` |
| One-page memo | `reports/memo.md` |
| SQL warehouse: load, staging, 20 quality rules, star schema, cohorts, KPIs | `sql/` |
| Result tables and figures | `reports/tables/`, `reports/figures/` |

![Power BI overview page preview](dashboards/powerbi/report_preview.png)

The Power BI project was generated from code and its report files validate against Microsoft's
published PBIR JSON schemas. Power BI Desktop runs on Windows only, so the preview above is a Python
rendering of the Overview page from the same data. To open the real report on Windows: open
`OlistRetention.pbip` in Power BI Desktop, set the `DataFolder` parameter (Transform data > Edit parameters)
to the full path of `dashboards/powerbi/data/`, and click Refresh. See `dashboards/powerbi/README.md`.

## How it works

1. **Warehouse** (`sql/01-04`): DuckDB loads the nine CSVs, stages and cleans them, runs 20 data-quality
   rules ([`docs/data_quality_log.md`](docs/data_quality_log.md)), and builds `fact_orders`, `fact_order_items`,
   `dim_customer` (one row per person via `customer_unique_id`), `dim_seller`, `dim_product` and `dim_date`.
2. **Business views** (`sql/05-08`): cohort retention, delivery KPIs by state, seller scorecard and monthly KPIs
   with month-over-month growth and rolling sums.
3. **Statistics** (`src/analysis.py`): Mann-Whitney test and bootstrap CI for reviews, an ordered logit with
   controls, and a logistic regression of 180-day repeat purchase on first-delivery lateness.
4. **Segmentation**: rule-based RFM segments plus K-means on log RFM (k chosen by silhouette).
5. **CLV** (`src/clv.py`): BG/NBD and Gamma-Gamma implemented by maximum likelihood, validated on a 26-week holdout.
6. **Business case**: Excel formulas over the measured figures; Power BI model and report generated by `src/powerbi.py`.

Details: [`docs/methodology.md`](docs/methodology.md) · data dictionary: [`docs/data_dictionary.md`](docs/data_dictionary.md)

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make all        # download data, build warehouse, run analysis, execute notebook, run tests
```

## Project structure

```
├── data/                 raw/ and processed/ (git-ignored); README with source and licence
├── sql/                  DuckDB SQL: load, staging, quality rules, star schema, cohorts, KPIs
├── src/                  pipeline: data, analysis, CLV, figures, Excel, Power BI, report
├── notebooks/            executed analysis notebook
├── excel/                retention economics model
├── dashboards/powerbi/   .pbip project (SemanticModel + Report), CSV extracts, preview
├── reports/              results.json, memo, figures, tables
├── docs/                 methodology, data dictionary, data quality log
└── tests/                pytest suite
```

## Data

Olist, *Brazilian E-Commerce Public Dataset by Olist*, downloaded from Olist's repository
[github.com/olist/work-at-olist-data](https://github.com/olist/work-at-olist-data) (also on Kaggle as
`olistbr/brazilian-ecommerce`). Licence CC BY-NC-SA 4.0. Raw files are not stored in this repository.

## Assumptions and limits

* Contribution margin ({_p(a['contribution_margin'], 0)}) and voucher value ({_brl(a['voucher_cost'], 0)}) are assumptions.
* Orders after {results['settings']['cutoff']} are excluded because the last weeks of the source are incomplete.
* Observational data: lateness effects are associations with controls, not randomized estimates.
* Review scores exist only for reviewed orders; customers who never review are not represented in review statistics.
"""
    (config.ROOT / "README.md").write_text(readme)
    memo = ("# Memo: why Olist customers do not return\n\n**To:** Head of Customer Experience · **Data:** "
            f"{b['orders']:,} Olist orders, {b['first_month']} to {b['last_month']}\n\n**What we found**\n\n"
            + "\n".join(f"- {t}" for t in findings) + "\n\n**What to do**\n\n"
            + "\n".join(f"{i}. {t}" for i, t in enumerate(recs, 1))
            + f"\n\n**Caveats:** observational data; margin and voucher value are assumptions; orders after "
              f"{results['settings']['cutoff']} excluded.\n")
    (config.REPORTS / "memo.md").write_text(memo)
