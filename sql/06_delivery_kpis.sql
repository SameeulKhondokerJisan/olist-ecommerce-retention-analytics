-- 06_delivery_kpis.sql
-- Delivery performance by customer state (delivered orders only).
SELECT customer_state,
       COUNT(*)                                 AS delivered_orders,
       AVG(CASE WHEN is_late THEN 1 ELSE 0 END) AS late_rate,
       AVG(delivery_days)                       AS avg_delivery_days,
       AVG(promised_days)                       AS avg_promised_days,
       AVG(review_score)                        AS avg_review,
       AVG(distance_km)                         AS avg_distance_km,
       AVG(freight_ratio)                       AS avg_freight_ratio
FROM fact_orders
WHERE is_delivered
GROUP BY 1
ORDER BY delivered_orders DESC;
