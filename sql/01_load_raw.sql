-- 01_load_raw.sql
-- Load the nine Olist CSVs as-is. Zip prefixes are read as text so leading zeros survive.
-- {raw} is replaced with the absolute path of data/raw by src/data.py.
CREATE OR REPLACE TABLE raw_orders    AS SELECT * FROM read_csv_auto('{raw}/olist_orders_dataset.csv', header = true);
CREATE OR REPLACE TABLE raw_customers AS SELECT * FROM read_csv_auto('{raw}/olist_customers_dataset.csv', header = true,
    types = {'customer_zip_code_prefix': 'VARCHAR'});
CREATE OR REPLACE TABLE raw_items     AS SELECT * FROM read_csv_auto('{raw}/olist_order_items_dataset.csv', header = true);
CREATE OR REPLACE TABLE raw_payments  AS SELECT * FROM read_csv_auto('{raw}/olist_order_payments_dataset.csv', header = true);
CREATE OR REPLACE TABLE raw_reviews   AS SELECT * FROM read_csv_auto('{raw}/olist_order_reviews_dataset.csv', header = true);
CREATE OR REPLACE TABLE raw_products  AS SELECT * FROM read_csv_auto('{raw}/olist_products_dataset.csv', header = true);
CREATE OR REPLACE TABLE raw_sellers   AS SELECT * FROM read_csv_auto('{raw}/olist_sellers_dataset.csv', header = true,
    types = {'seller_zip_code_prefix': 'VARCHAR'});
CREATE OR REPLACE TABLE raw_geolocation AS SELECT * FROM read_csv_auto('{raw}/olist_geolocation_dataset.csv', header = true,
    types = {'geolocation_zip_code_prefix': 'VARCHAR'});
CREATE OR REPLACE TABLE raw_category_translation AS
    SELECT * FROM read_csv_auto('{raw}/product_category_name_translation.csv', header = true);
