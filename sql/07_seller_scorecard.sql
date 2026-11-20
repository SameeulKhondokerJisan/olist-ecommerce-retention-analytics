-- 07_seller_scorecard.sql
-- Seller scorecard: volume, revenue, lateness and reviews for sellers with 30+ delivered orders.
SELECT main_seller_id AS seller_id, ANY_VALUE(seller_state) AS seller_state,
       COUNT(*) AS delivered_orders, SUM(item_value) AS item_revenue,
       AVG(CASE WHEN is_late THEN 1 ELSE 0 END) AS late_rate,
       AVG(review_score) AS avg_review,
       AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) AS negative_review_rate
FROM fact_orders
WHERE is_delivered
GROUP BY 1
HAVING COUNT(*) >= 30
ORDER BY late_rate DESC, delivered_orders DESC;
