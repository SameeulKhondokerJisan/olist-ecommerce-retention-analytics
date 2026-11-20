"""Warehouse and results checks on the real data (skipped until `make data pipeline` has run)."""
import json

import pytest

from src import config, data

pytestmark = pytest.mark.skipif(not config.DB_PATH.exists(), reason="run `make pipeline` first")


def test_source_row_counts_match_published_dataset():
    counts = data.row_counts()
    assert counts["raw_orders"] == 99441
    assert counts["raw_items"] == 112650
    assert counts["raw_customers"] == 99441


def test_fact_orders_grain_and_keys():
    df = data.query("SELECT COUNT(*) n, COUNT(DISTINCT order_id) d, COUNT(*) FILTER (WHERE customer_unique_id IS NULL) "
                    "nulls FROM fact_orders")
    assert df.n[0] == df.d[0] and df.nulls[0] == 0


def test_item_revenue_reconciles_between_tables():
    df = data.query("SELECT (SELECT SUM(item_value) FROM fact_orders) a, (SELECT SUM(price) FROM fact_order_items) b")
    assert df.a[0] == pytest.approx(df.b[0], rel=1e-9)


def test_cohort_retention_month_zero_is_complete():
    coh = data.query("05_cohort_retention.sql")
    assert (coh[coh.months_since_first == 0].retention_rate.round(9) == 1.0).all()


def test_results_are_consistent():
    r = json.loads(config.RESULTS_JSON.read_text())
    rv = r["review_vs_lateness"]
    assert rv["mean_diff"] == pytest.approx(rv["mean_review_late"] - rv["mean_review_ontime"])
    assert rv["mean_diff_ci"][0] <= rv["mean_diff"] <= rv["mean_diff_ci"][1]
    assert 0 < r["business"]["late_rate_delivered"] < 1
