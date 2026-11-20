# Power BI report

`OlistRetention.pbip` is a Power BI project (PBIP) written by `src/powerbi.py`:

* `OlistRetention.SemanticModel/`: TMDL model with 5 tables loaded from `data/*.csv`, 2 relationships
  (fact_orders to dim_customer and dim_date, a marked date table) and 14 DAX measures.
* `OlistRetention.Report/`: PBIR report with two pages: *Overview* (KPI cards, GMV trend, late rate by
  state, review by delay, GMV by category) and *Customers and retention* (cohort matrix, RFM segments,
  seller scorecard).

## Open it (Windows, Power BI Desktop)
1. Open `OlistRetention.pbip`.
2. Transform data > Edit parameters > set **DataFolder** to the full path of this folder's `data\` subfolder,
   ending with a backslash, for example `C:\Users\you\olist-ecommerce-retention-analytics\dashboards\powerbi\data\`.
3. Close & Apply (or Refresh).

## Checks done here
The report's JSON files validate against Microsoft's PBIR schemas (`visualContainer/2.4.0`, `page/2.0.0`,
`report/3.0.0`). Power BI Desktop is not available on macOS, so the report has not been opened in Desktop;
`report_preview.png` is a Python rendering of the Overview page from the same CSVs.

## If you prefer to build it by hand
Load the CSVs in `data/`, relate `fact_orders[customer_unique_id]` to `dim_customer` and
`fact_orders[purchase_date]` to `dim_date[date]`, mark `dim_date` as a date table, and copy the measures from
`OlistRetention.SemanticModel/definition/tables/*.tmdl`.
