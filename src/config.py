"""Paths, analysis settings and business assumptions."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "processed" / "olist.duckdb"
SQL_DIR = ROOT / "sql"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
RESULTS_JSON = REPORTS / "results.json"
POWERBI_DIR = ROOT / "dashboards" / "powerbi"
POWERBI_DATA = POWERBI_DIR / "data"
EXCEL_PATH = ROOT / "excel" / "retention_economics_model.xlsx"

CUTOFF = "2018-08-31"            # last complete month in the source data
CALIBRATION_END = "2018-02-28"   # CLV model: fit on orders up to here ...
HOLDOUT_WEEKS = 26               # ... and test on the next 26 weeks
REPEAT_WINDOW_DAYS = 180         # "repeat customer" = second order within 180 days
SEED = 42
CURRENCY = "R$"                  # Olist values are Brazilian reais

# Business assumptions (not in the data; editable in the Excel Inputs sheet)
CONTRIBUTION_MARGIN = 0.15       # Olist's contribution per R$ of GMV
TARGET_REVIEW = 4.20             # target average review score for the delivery scenario
VOUCHER_COST = 10.0              # R$ cost per customer of a second-order voucher
