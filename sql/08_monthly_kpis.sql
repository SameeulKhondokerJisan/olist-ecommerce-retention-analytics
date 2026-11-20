-- 08_monthly_kpis.sql
-- Monthly business KPIs with month-over-month growth (window functions).
WITH m AS (
    SELECT purchase_month, COUNT(*) AS orders, COUNT(DISTINCT customer_unique_id) AS customers,
           SUM(order_value) AS gmv, AVG(order_value) AS avg_order_value,
           AVG(CASE WHEN is_late THEN 1.0 WHEN is_late = false THEN 0.0 END) AS late_rate,
           AVG(review_score) AS avg_review
    FROM fact_orders GROUP BY 1
)
SELECT *, gmv / LAG(gmv) OVER (ORDER BY purchase_month) - 1 AS gmv_mom_growth,
       SUM(gmv) OVER (ORDER BY purchase_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS gmv_rolling_3m
FROM m ORDER BY purchase_month;
