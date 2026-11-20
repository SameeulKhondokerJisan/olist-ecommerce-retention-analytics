-- 03_quality_checks.sql
-- One row per rule: failures = rows breaking it. 'hard' rules stop the pipeline.
SELECT 'orders: order_id is unique' AS rule, 'hard' AS severity, COUNT(*) - COUNT(DISTINCT order_id) AS failures FROM stg_orders
UNION ALL SELECT 'customers: customer_id is unique', 'hard', COUNT(*) - COUNT(DISTINCT customer_id) FROM stg_customers
UNION ALL SELECT 'items: (order_id, order_item_id) is unique', 'hard',
       COUNT(*) - COUNT(DISTINCT order_id || '#' || CAST(order_item_id AS VARCHAR)) FROM stg_items
UNION ALL SELECT 'orders: every order has a customer', 'hard', COUNT(*)
       FROM stg_orders o LEFT JOIN stg_customers c USING (customer_id) WHERE c.customer_id IS NULL
UNION ALL SELECT 'items: every item belongs to a known order', 'hard', COUNT(*)
       FROM stg_items i LEFT JOIN stg_orders o USING (order_id) WHERE o.order_id IS NULL
UNION ALL SELECT 'items: every item has a known product and seller', 'hard', COUNT(*)
       FROM stg_items i LEFT JOIN stg_products p USING (product_id) LEFT JOIN stg_sellers s USING (seller_id)
       WHERE p.product_id IS NULL OR s.seller_id IS NULL
UNION ALL SELECT 'items: price > 0 and freight >= 0', 'hard', COUNT(*) FROM stg_items WHERE price <= 0 OR freight < 0
UNION ALL SELECT 'reviews: score between 1 and 5', 'hard', COUNT(*) FROM stg_reviews WHERE review_score NOT BETWEEN 1 AND 5
UNION ALL SELECT 'orders: delivered status without delivery date', 'soft', COUNT(*)
       FROM stg_orders WHERE order_status = 'delivered' AND delivered_ts IS NULL
UNION ALL SELECT 'orders: delivered before purchase', 'soft', COUNT(*) FROM stg_orders WHERE delivered_ts < purchase_ts
UNION ALL SELECT 'orders: handed to carrier before approval', 'soft', COUNT(*) FROM stg_orders WHERE carrier_ts < approved_ts
UNION ALL SELECT 'orders: no items (mostly canceled/unavailable)', 'soft', COUNT(*)
       FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_items i WHERE i.order_id = o.order_id)
UNION ALL SELECT 'orders: no payment record', 'soft', COUNT(*)
       FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_payments p WHERE p.order_id = o.order_id)
UNION ALL SELECT 'payments: total differs from items + freight by > $1', 'soft', COUNT(*)
       FROM (SELECT order_id, SUM(price + freight) AS item_total FROM stg_items GROUP BY 1) i
       JOIN (SELECT order_id, SUM(payment_value) AS paid FROM stg_payments GROUP BY 1) p USING (order_id)
       WHERE abs(i.item_total - p.paid) > 1
UNION ALL SELECT 'reviews: orders with more than one review (latest kept)', 'soft', COUNT(*)
       FROM (SELECT order_id FROM raw_reviews GROUP BY 1 HAVING COUNT(*) > 1)
UNION ALL SELECT 'reviews: review_id reused across orders', 'soft', COUNT(*)
       FROM (SELECT review_id FROM raw_reviews GROUP BY 1 HAVING COUNT(DISTINCT order_id) > 1)
UNION ALL SELECT 'products: missing category (set to unknown)', 'soft', COUNT(*)
       FROM raw_products WHERE product_category_name IS NULL
UNION ALL SELECT 'geolocation: points outside Brazil (dropped)', 'soft', COUNT(*)
       FROM raw_geolocation WHERE NOT (geolocation_lat BETWEEN -34.0 AND 5.5 AND geolocation_lng BETWEEN -74.0 AND -34.0)
UNION ALL SELECT 'customers: zip prefix with no geolocation', 'soft', COUNT(*)
       FROM stg_customers c LEFT JOIN geo_zip g USING (zip_prefix) WHERE g.zip_prefix IS NULL
UNION ALL SELECT 'customers: people with more than one customer_id', 'soft', COUNT(*)
       FROM (SELECT customer_unique_id FROM stg_customers GROUP BY 1 HAVING COUNT(*) > 1);
