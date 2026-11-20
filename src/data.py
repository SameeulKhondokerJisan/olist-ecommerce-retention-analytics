"""Build the DuckDB warehouse from the raw CSVs and expose query helpers."""
from __future__ import annotations

import re

import duckdb
import pandas as pd

from src import config


class DataQualityError(RuntimeError):
    """Raised when a hard data-quality rule fails."""


def split_statements(sql: str) -> list[str]:
    no_comments = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(config.DB_PATH), read_only=read_only)


def run_sql(con, filename: str) -> pd.DataFrame | None:
    sql = (config.SQL_DIR / filename).read_text()
    sql = sql.replace("{raw}", config.RAW_DIR.as_posix()).replace("{cutoff}", config.CUTOFF)
    result = None
    for statement in split_statements(sql):
        result = con.execute(statement)
    try:
        return result.df() if result is not None else None
    except duckdb.Error:
        return None


def build_warehouse() -> pd.DataFrame:
    """Load, stage, check and model the data. Returns the quality-check report."""
    missing = [p for p in ("olist_orders_dataset.csv", "olist_customers_dataset.csv")
               if not (config.RAW_DIR / p).exists()]
    if missing:
        raise FileNotFoundError(f"Missing {missing}. Run `python -m src.download_data` first.")
    with connect() as con:
        run_sql(con, "01_load_raw.sql")
        run_sql(con, "02_staging.sql")
        checks = run_sql(con, "03_quality_checks.sql")
        failed = checks[(checks.severity == "hard") & (checks.failures > 0)]
        if not failed.empty:
            raise DataQualityError("Hard data-quality rules failed:\n" + failed.to_string(index=False))
        run_sql(con, "04_star_schema.sql")
    return checks


def query(filename_or_sql: str) -> pd.DataFrame:
    with connect(read_only=True) as con:
        if filename_or_sql.endswith(".sql"):
            return run_sql(con, filename_or_sql)
        return con.execute(filename_or_sql).df()


def table(name: str) -> pd.DataFrame:
    return query(f"SELECT * FROM {name}")


def row_counts() -> dict[str, int]:
    names = ["raw_orders", "raw_customers", "raw_items", "raw_payments", "raw_reviews", "raw_products",
             "raw_sellers", "raw_geolocation", "fact_orders", "fact_order_items", "dim_customer"]
    with connect(read_only=True) as con:
        return {n: int(con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]) for n in names}
