# Data

Source: Olist, *Brazilian E-Commerce Public Dataset by Olist*, from Olist's repository
https://github.com/olist/work-at-olist-data (same files as kaggle.com/datasets/olistbr/brazilian-ecommerce).
Licence: CC BY-NC-SA 4.0 (non-commercial use with attribution).

`make data` downloads the nine CSVs (about 125 MB) into `raw/` and writes `raw/MANIFEST.json` with sizes and
SHA-256 checksums. `make pipeline` builds `processed/olist.duckdb`. Both folders are git-ignored.

| File | Rows | Grain |
|---|---:|---|
| olist_orders_dataset.csv | 99,441 | order |
| olist_customers_dataset.csv | 99,441 | customer_id (one per order) |
| olist_order_items_dataset.csv | 112,650 | order line |
| olist_order_payments_dataset.csv | 103,886 | payment |
| olist_order_reviews_dataset.csv | 99,224 | review |
| olist_products_dataset.csv | 32,951 | product |
| olist_sellers_dataset.csv | 3,095 | seller |
| olist_geolocation_dataset.csv | 1,000,163 | zip prefix point |
| product_category_name_translation.csv | 71 | category |
