# Data dictionary (warehouse tables)

All tables live in `data/processed/olist.duckdb`, built by `sql/04_star_schema.sql`. Money is in R$.

## fact_orders (one row per non-canceled order purchased on or before the cutoff)
| Column | Description |
|---|---|
| order_id | Order key |
| customer_unique_id | Person key (a person gets a new customer_id with every order) |
| order_status | Status as published |
| purchase_ts, purchase_date, purchase_month | Purchase time |
| items, sellers | Order lines and distinct sellers |
| item_value, freight_value, freight_ratio | Item revenue, freight, freight / item revenue |
| order_value | Total paid (payments; falls back to items + freight) |
| payment_type, installments | Main payment method and maximum installments |
| main_category, main_seller_id | Category and seller of the highest-priced line |
| customer_state, seller_state | Brazilian states |
| is_delivered | Delivered with a delivery date |
| delivery_days, promised_days | Purchase to delivery; purchase to promised date |
| delay_days, is_late | Delivery date minus promised date (days); late = delivered after the promised date |
| review_score, has_comment | Latest review for the order |
| distance_km | Great-circle distance between customer and main seller zip-prefix centroids |

## dim_customer (one row per customer_unique_id)
state, first_purchase_ts, last_purchase_ts, cohort_month, orders, lifetime_value, is_repeat.

## Other tables
`fact_order_items` (order line), `dim_seller`, `dim_product`, `dim_date`, `geo_zip` (zip prefix centroid),
staging tables `stg_*`, raw tables `raw_*`.

## Power BI extracts (`dashboards/powerbi/data/`)
`fact_orders.csv`, `dim_customer.csv` (adds RFM segment, K-means cluster, CLV), `dim_date.csv`,
`cohort_retention.csv`, `seller_scorecard.csv`, `delivery_by_state.csv`.
