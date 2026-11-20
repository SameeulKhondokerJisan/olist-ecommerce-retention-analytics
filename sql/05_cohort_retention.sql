-- 05_cohort_retention.sql
-- Monthly acquisition cohorts: share of each cohort that ordered again N months after the first order.
WITH activity AS (
    SELECT DISTINCT f.customer_unique_id, d.cohort_month, f.purchase_month,
           date_diff('month', d.cohort_month, f.purchase_month) AS months_since_first
    FROM fact_orders f JOIN dim_customer d USING (customer_unique_id)
), sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers FROM dim_customer GROUP BY 1
)
SELECT a.cohort_month, s.cohort_customers, a.months_since_first,
       COUNT(DISTINCT a.customer_unique_id) AS active_customers,
       COUNT(DISTINCT a.customer_unique_id) / s.cohort_customers::DOUBLE AS retention_rate
FROM activity a JOIN sizes s USING (cohort_month)
WHERE a.cohort_month >= DATE '2017-01-01'
GROUP BY a.cohort_month, s.cohort_customers, a.months_since_first
ORDER BY a.cohort_month, a.months_since_first;
