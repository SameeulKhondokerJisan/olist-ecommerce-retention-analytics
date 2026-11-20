-- 02_staging.sql
-- Typed, cleaned staging tables. Every cleaning decision here is listed in docs/data_quality_log.md.

-- Orders: timestamps typed; status kept as published.
CREATE OR REPLACE TABLE stg_orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    CAST(order_purchase_timestamp AS TIMESTAMP)       AS purchase_ts,
    CAST(order_approved_at AS TIMESTAMP)              AS approved_ts,
    CAST(order_delivered_carrier_date AS TIMESTAMP)   AS carrier_ts,
    CAST(order_delivered_customer_date AS TIMESTAMP)  AS delivered_ts,
    CAST(order_estimated_delivery_date AS TIMESTAMP)  AS estimated_ts
FROM raw_orders;

-- Customers: customer_id is one per order; customer_unique_id identifies the person.
CREATE OR REPLACE TABLE stg_customers AS
SELECT customer_id, customer_unique_id,
       lpad(customer_zip_code_prefix, 5, '0') AS zip_prefix,
       customer_city AS city, customer_state AS state
FROM raw_customers;

CREATE OR REPLACE TABLE stg_items AS
SELECT order_id, order_item_id, product_id, seller_id,
       CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_ts,
       CAST(price AS DOUBLE) AS price, CAST(freight_value AS DOUBLE) AS freight
FROM raw_items;

CREATE OR REPLACE TABLE stg_payments AS
SELECT order_id, payment_sequential, payment_type, payment_installments,
       CAST(payment_value AS DOUBLE) AS payment_value
FROM raw_payments;

-- Reviews: a few orders have several reviews; keep the most recently answered one.
CREATE OR REPLACE TABLE stg_reviews AS
SELECT order_id, review_id, CAST(review_score AS INTEGER) AS review_score,
       CAST(review_creation_date AS TIMESTAMP) AS review_created_ts,
       review_comment_message IS NOT NULL AND length(trim(review_comment_message)) > 0 AS has_comment
FROM raw_reviews
QUALIFY row_number() OVER (PARTITION BY order_id
                           ORDER BY CAST(review_answer_timestamp AS TIMESTAMP) DESC, review_id) = 1;

-- Products: English category names; missing categories become 'unknown'.
CREATE OR REPLACE TABLE stg_products AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       p.product_photos_qty AS photos,
       CAST(p.product_weight_g AS DOUBLE) AS weight_g,
       CAST(p.product_length_cm AS DOUBLE) * CAST(p.product_height_cm AS DOUBLE)
           * CAST(p.product_width_cm AS DOUBLE) AS volume_cm3
FROM raw_products p
LEFT JOIN raw_category_translation t USING (product_category_name);

CREATE OR REPLACE TABLE stg_sellers AS
SELECT seller_id, lpad(seller_zip_code_prefix, 5, '0') AS zip_prefix,
       seller_city AS city, seller_state AS state
FROM raw_sellers;

-- Geolocation has ~1M rows for ~19k zip prefixes and some points outside Brazil.
-- Keep points inside Brazil's bounding box and average them to one centroid per prefix.
CREATE OR REPLACE TABLE geo_zip AS
SELECT lpad(geolocation_zip_code_prefix, 5, '0') AS zip_prefix,
       AVG(geolocation_lat) AS lat, AVG(geolocation_lng) AS lng, COUNT(*) AS points
FROM raw_geolocation
WHERE geolocation_lat BETWEEN -34.0 AND 5.5 AND geolocation_lng BETWEEN -74.0 AND -34.0
GROUP BY 1;
