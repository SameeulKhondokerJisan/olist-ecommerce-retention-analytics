-- 04_star_schema.sql
-- Star schema for analysis and Power BI. Grain of each table is stated in the comment.
-- Orders up to {cutoff} are used; the last weeks of the source data are incomplete.

-- fact_orders: one row per order (non-canceled, purchased on or before the cutoff)
CREATE OR REPLACE TABLE fact_orders AS
WITH items AS (
    SELECT i.order_id,
           COUNT(*)                         AS items,
           COUNT(DISTINCT i.seller_id)      AS sellers,
           SUM(i.price)                     AS item_value,
           SUM(i.freight)                   AS freight_value,
           arg_max(p.category, i.price)     AS main_category,
           arg_max(i.seller_id, i.price)    AS main_seller_id
    FROM stg_items i JOIN stg_products p USING (product_id)
    GROUP BY 1
), pay AS (
    SELECT order_id, SUM(payment_value) AS payment_value,
           arg_max(payment_type, payment_value) AS payment_type,
           MAX(payment_installments) AS installments
    FROM stg_payments GROUP BY 1
)
SELECT
    o.order_id,
    c.customer_unique_id,
    o.order_status,
    o.purchase_ts,
    CAST(o.purchase_ts AS DATE)                                  AS purchase_date,
    date_trunc('month', o.purchase_ts)::DATE                     AS purchase_month,
    i.items, i.sellers, i.item_value, i.freight_value,
    i.freight_value / NULLIF(i.item_value, 0)                    AS freight_ratio,
    COALESCE(p.payment_value, i.item_value + i.freight_value)    AS order_value,
    p.payment_type, p.installments,
    i.main_category, i.main_seller_id,
    c.state                                                      AS customer_state,
    s.state                                                      AS seller_state,
    o.delivered_ts IS NOT NULL AND o.order_status = 'delivered'  AS is_delivered,
    date_diff('day', o.purchase_ts, o.delivered_ts)              AS delivery_days,
    date_diff('day', o.purchase_ts, o.estimated_ts)              AS promised_days,
    date_diff('day', CAST(o.estimated_ts AS DATE), CAST(o.delivered_ts AS DATE)) AS delay_days,
    CASE WHEN o.delivered_ts IS NULL THEN NULL
         ELSE CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE) END AS is_late,
    r.review_score,
    r.has_comment,
    -- great-circle distance between customer and main seller zip centroids (km)
    2 * 6371 * asin(sqrt(
        pow(sin(radians(gs.lat - gc.lat) / 2), 2)
        + cos(radians(gc.lat)) * cos(radians(gs.lat)) * pow(sin(radians(gs.lng - gc.lng) / 2), 2)
    ))                                                           AS distance_km
FROM stg_orders o
JOIN stg_customers c USING (customer_id)
JOIN items i USING (order_id)
LEFT JOIN pay p USING (order_id)
LEFT JOIN stg_sellers s ON s.seller_id = i.main_seller_id
LEFT JOIN stg_reviews r USING (order_id)
LEFT JOIN geo_zip gc ON gc.zip_prefix = c.zip_prefix
LEFT JOIN geo_zip gs ON gs.zip_prefix = s.zip_prefix
WHERE o.order_status NOT IN ('canceled', 'unavailable')
  AND CAST(o.purchase_ts AS DATE) <= DATE '{cutoff}';

-- fact_order_items: one row per order line
CREATE OR REPLACE TABLE fact_order_items AS
SELECT i.order_id, i.order_item_id, i.product_id, i.seller_id, p.category, i.price, i.freight,
       f.purchase_date, f.customer_unique_id
FROM stg_items i
JOIN fact_orders f USING (order_id)
JOIN stg_products p USING (product_id);

-- dim_customer: one row per person (customer_unique_id)
CREATE OR REPLACE TABLE dim_customer AS
WITH firsts AS (
    SELECT customer_unique_id, MIN(purchase_ts) AS first_purchase_ts, MAX(purchase_ts) AS last_purchase_ts,
           COUNT(*) AS orders, SUM(order_value) AS lifetime_value,
           arg_min(customer_state, purchase_ts) AS state
    FROM fact_orders GROUP BY 1
)
SELECT customer_unique_id, state, first_purchase_ts, last_purchase_ts,
       date_trunc('month', first_purchase_ts)::DATE AS cohort_month, orders, lifetime_value,
       orders > 1 AS is_repeat
FROM firsts;

-- dim_seller and dim_product
CREATE OR REPLACE TABLE dim_seller AS
SELECT s.seller_id, s.state, s.city, g.lat, g.lng
FROM stg_sellers s LEFT JOIN geo_zip g USING (zip_prefix);

CREATE OR REPLACE TABLE dim_product AS SELECT product_id, category, photos, weight_g, volume_cm3 FROM stg_products;

-- dim_date: one row per calendar day covered by the orders
CREATE OR REPLACE TABLE dim_date AS
SELECT CAST(d AS DATE) AS date, year(d) AS year, month(d) AS month, strftime(d, '%Y-%m') AS year_month,
       quarter(d) AS quarter, dayofweek(d) AS day_of_week, strftime(d, '%a') AS day_name
FROM range((SELECT MIN(purchase_date) FROM fact_orders), (SELECT MAX(purchase_date) FROM fact_orders) + 1,
           INTERVAL 1 DAY) t(d);
