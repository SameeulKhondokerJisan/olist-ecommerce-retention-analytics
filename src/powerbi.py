"""Power BI deliverable: star-schema CSV extracts + a generated Power BI project (.pbip).

Writes dashboards/powerbi/data/*.csv, dashboards/powerbi/OlistRetention.pbip (TMDL semantic
model + PBIR report) and a Python-rendered preview of the overview page.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src import config, data  # noqa: E402
from src.pbip import Measure, Page, Relationship, Table, Visual, validate, write_project  # noqa: E402

SCHEMA_ROOT = config.ROOT.parent / "_tools" / "json-schemas" / "fabric"


def _delay_bucket(days: pd.Series) -> pd.Series:
    return pd.cut(days, bins=[-10_000, 0, 3, 7, 14, 10_000],
                  labels=["1 On time", "2 1-3 days late", "3 4-7 days late", "4 8-14 days late", "5 15+ days late"])


def export(orders: pd.DataFrame, rfm: pd.DataFrame, clv_scores: pd.DataFrame, cohorts: pd.DataFrame,
           states: pd.DataFrame) -> dict:
    d = config.POWERBI_DATA
    d.mkdir(parents=True, exist_ok=True)
    fact = orders[["order_id", "customer_unique_id", "purchase_date", "purchase_month", "order_status",
                   "customer_state", "seller_state", "main_category", "payment_type", "items", "order_value",
                   "freight_value", "delivery_days", "delay_days", "review_score", "distance_km"]].copy()
    fact["purchase_date"] = pd.to_datetime(fact.purchase_date).dt.strftime("%Y-%m-%d")
    fact["purchase_month"] = pd.to_datetime(fact.purchase_month).dt.strftime("%Y-%m-%d")
    fact["is_delivered"] = orders.is_delivered.astype(int)
    fact["is_late"] = orders.is_late.map({True: 1, False: 0})
    fact["delay_bucket"] = _delay_bucket(orders.delay_days).astype(str).replace("nan", "")
    fact.to_csv(d / "fact_orders.csv", index=False)

    cust = data.table("dim_customer")
    cust = cust.merge(rfm[["recency_days", "segment", "cluster"]], left_on="customer_unique_id", right_index=True,
                      how="left")
    cust = cust.merge(clv_scores[["customer_unique_id", "exp_purchases_52w", "prob_alive", "clv_12m_gmv"]],
                      on="customer_unique_id", how="left")
    cust["first_purchase_date"] = pd.to_datetime(cust.first_purchase_ts).dt.strftime("%Y-%m-%d")
    cust["cohort_month"] = pd.to_datetime(cust.cohort_month).dt.strftime("%Y-%m-%d")
    cust["is_repeat"] = cust.is_repeat.astype(int)
    cust = cust.drop(columns=["first_purchase_ts", "last_purchase_ts"])
    cust.to_csv(d / "dim_customer.csv", index=False)

    dates = data.table("dim_date")
    dates["date"] = pd.to_datetime(dates.date).dt.strftime("%Y-%m-%d")
    dates.to_csv(d / "dim_date.csv", index=False)
    coh = cohorts.copy()
    coh["cohort_month"] = pd.to_datetime(coh.cohort_month).dt.strftime("%Y-%m-%d")
    coh.to_csv(d / "cohort_retention.csv", index=False)
    data.query("07_seller_scorecard.sql").to_csv(d / "seller_scorecard.csv", index=False)
    states.to_csv(d / "delivery_by_state.csv", index=False)
    return build_project()


def build_project() -> dict:
    d = config.POWERBI_DATA
    F, C = "fact_orders", "dim_customer"
    measures = [
        Measure("GMV (R$)", f"SUM({F}[order_value])", "#,0", "Sales"),
        Measure("Orders", f"COUNTROWS({F})", "#,0", "Sales"),
        Measure("Customers", f"DISTINCTCOUNT({F}[customer_unique_id])", "#,0", "Sales"),
        Measure("Avg order value (R$)", "DIVIDE([GMV (R$)], [Orders])", "#,0.00", "Sales"),
        Measure("GMV MoM %", "VAR cur = [GMV (R$)] VAR prev = CALCULATE([GMV (R$)], DATEADD(dim_date[date], -1, MONTH)) "
                             "RETURN DIVIDE(cur - prev, prev)", "0.0%", "Sales"),
        Measure("Late delivery rate", f"DIVIDE(SUM({F}[is_late]), COUNT({F}[is_late]))", "0.0%", "Delivery"),
        Measure("Avg delivery days", f"AVERAGE({F}[delivery_days])", "0.0", "Delivery"),
        Measure("Avg review", f"AVERAGE({F}[review_score])", "0.00", "Experience"),
        Measure("Negative review rate", f"DIVIDE(CALCULATE(COUNT({F}[review_score]), {F}[review_score] <= 2), "
                                        f"COUNT({F}[review_score]))", "0.0%", "Experience"),
    ]
    cust_measures = [
        Measure("Customers in segment", f"COUNTROWS({C})", "#,0", "Customers"),
        Measure("Repeat customer rate", f"DIVIDE(CALCULATE(COUNTROWS({C}), {C}[is_repeat] = 1), COUNTROWS({C}))",
                "0.0%", "Customers"),
        Measure("Expected repeat GMV next 12m (R$)", f"SUM({C}[clv_12m_gmv])", "#,0", "Customers"),
        Measure("At-risk high-value customers", f'CALCULATE(COUNTROWS({C}), {C}[segment] = "At-risk high-value")',
                "#,0", "Customers"),
    ]
    tables = [
        Table(F, d / "fact_orders.csv", measures, hidden=("customer_unique_id",),
              formats={"order_value": "#,0.00", "freight_value": "#,0.00", "distance_km": "#,0"}),
        Table(C, d / "dim_customer.csv", cust_measures, formats={"clv_12m_gmv": "#,0.00", "lifetime_value": "#,0.00"}),
        Table("dim_date", d / "dim_date.csv", key="date", is_date_table=True),
        Table("cohort_retention", d / "cohort_retention.csv",
              [Measure("Cohort retention", "AVERAGE(cohort_retention[retention_rate])", "0.0%", "Customers")]),
        Table("seller_scorecard", d / "seller_scorecard.csv", formats={"late_rate": "0.0%", "avg_review": "0.00"}),
    ]
    rels = [Relationship(F, "customer_unique_id", C, "customer_unique_id"),
            Relationship(F, "purchase_date", "dim_date", "date")]
    m = lambda name: ("measure", F, name)  # noqa: E731
    cm = lambda name: ("measure", C, name)  # noqa: E731
    cards = ["GMV (R$)", "Orders", "Customers", "Avg order value (R$)", "Late delivery rate", "Avg review"]
    overview = Page("Overview", [Visual("card", 10 + i * 211, 10, 200, 90, {"Values": [m(c)]}) for i, c in enumerate(cards)] + [
        Visual("lineChart", 10, 110, 620, 290, {"Category": [("column", "dim_date", "year_month")], "Y": [m("GMV (R$)")]},
               "GMV by month (R$)"),
        Visual("clusteredBarChart", 650, 110, 620, 290,
               {"Category": [("column", F, "customer_state")], "Y": [m("Late delivery rate")]}, "Late-delivery rate by customer state"),
        Visual("clusteredColumnChart", 10, 410, 620, 300,
               {"Category": [("column", F, "delay_bucket")], "Y": [m("Avg review")]}, "Average review by delivery delay"),
        Visual("clusteredBarChart", 650, 410, 620, 300,
               {"Category": [("column", F, "main_category")], "Y": [m("GMV (R$)")]}, "GMV by product category (R$)"),
    ])
    retention = Page("Customers and retention", [
        Visual("card", 10, 10, 300, 90, {"Values": [cm("Repeat customer rate")]}),
        Visual("card", 325, 10, 300, 90, {"Values": [cm("Expected repeat GMV next 12m (R$)")]}),
        Visual("card", 640, 10, 300, 90, {"Values": [cm("At-risk high-value customers")]}),
        Visual("card", 955, 10, 315, 90, {"Values": [cm("Customers in segment")]}),
        Visual("pivotTable", 10, 110, 760, 600, {"Rows": [("column", "cohort_retention", "cohort_month")],
                                                  "Columns": [("column", "cohort_retention", "months_since_first")],
                                                  "Values": [("measure", "cohort_retention", "Cohort retention")]},
               "Monthly cohort retention (share ordering again)"),
        Visual("clusteredBarChart", 790, 110, 480, 290, {"Category": [("column", C, "segment")],
                                                          "Y": [cm("Customers in segment")]}, "Customers by RFM segment"),
        Visual("tableEx", 790, 410, 480, 300, {"Values": [("column", "seller_scorecard", c) for c in
                                                         ("seller_id", "seller_state", "delivered_orders", "late_rate",
                                                          "avg_review")]}, "Seller scorecard (30+ delivered orders)"),
    ])
    pbip = write_project(config.POWERBI_DIR, "OlistRetention", tables, rels, [overview, retention],
                         data_folder_hint="C:\\path\\to\\olist-ecommerce-retention-analytics\\dashboards\\powerbi\\data\\")
    problems = validate(config.POWERBI_DIR, SCHEMA_ROOT) if SCHEMA_ROOT.exists() else ["schemas not available"]
    render_preview()
    return {"pbip": str(pbip.relative_to(config.ROOT)), "schema_problems": problems}


def render_preview() -> None:
    """Python rendering of the Overview page layout, for the README (not a Power BI screenshot)."""
    d = config.POWERBI_DATA
    f = pd.read_csv(d / "fact_orders.csv", parse_dates=["purchase_month"])
    kpis = {"GMV (R$)": f"{f.order_value.sum() / 1e6:,.2f}M", "Orders": f"{len(f):,}",
            "Customers": f"{f.customer_unique_id.nunique():,}", "Avg order value (R$)": f"{f.order_value.mean():,.2f}",
            "Late delivery rate": f"{f.is_late.mean() * 100:.1f}%", "Avg review": f"{f.review_score.mean():.2f}"}
    fig = plt.figure(figsize=(16, 9), facecolor="#f3f2f1")
    for i, (label, value) in enumerate(kpis.items()):
        ax = fig.add_axes([0.01 + i * 0.165, 0.86, 0.155, 0.12])
        ax.set_facecolor("white"); ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.5, 0.58, value, ha="center", va="center", fontsize=20, fontweight="bold", color="#252423")
        ax.text(0.5, 0.2, label, ha="center", va="center", fontsize=10, color="#605e5c")
    monthly = f[f.purchase_month >= "2017-01-01"].groupby("purchase_month").order_value.sum() / 1e6
    ax = fig.add_axes([0.04, 0.47, 0.44, 0.33]); ax.plot(monthly.index, monthly.values, color="#118DFF", lw=2)
    ax.set_title("GMV by month (R$ millions)", loc="left", fontsize=11)
    state = f.groupby("customer_state").is_late.mean().sort_values().tail(12) * 100
    ax = fig.add_axes([0.55, 0.47, 0.43, 0.33]); ax.barh(state.index, state.values, color="#118DFF")
    ax.set_title("Late-delivery rate by customer state (%)", loc="left", fontsize=11)
    bucket = f.groupby("delay_bucket").review_score.mean()
    ax = fig.add_axes([0.04, 0.05, 0.44, 0.34]); ax.bar([b[2:] for b in bucket.index], bucket.values, color="#118DFF")
    ax.set_title("Average review by delivery delay", loc="left", fontsize=11); ax.tick_params(axis="x", labelsize=8)
    cat = f.groupby("main_category").order_value.sum().sort_values().tail(10) / 1e6
    ax = fig.add_axes([0.62, 0.05, 0.36, 0.34]); ax.barh(cat.index, cat.values, color="#118DFF")
    ax.set_title("GMV by product category (R$ millions)", loc="left", fontsize=11); ax.tick_params(axis="y", labelsize=8)
    for a in fig.axes[6:]:
        a.spines[["top", "right"]].set_visible(False)
    fig.text(0.99, 0.005, "Python preview of the Power BI 'Overview' page layout (same data and measures)",
             ha="right", fontsize=8, color="#605e5c")
    fig.savefig(config.POWERBI_DIR / "report_preview.png", dpi=110)
    plt.close(fig)
