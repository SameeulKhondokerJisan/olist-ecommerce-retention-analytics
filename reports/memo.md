# Memo: why Olist customers do not return

**To:** Head of Customer Experience · **Data:** 98,198 Olist orders, 2016-09 to 2018-08

**What we found**

- **Retention is the gap.** 97.0% of 94,983 customers ordered only once; on average 0.48% of a monthly cohort orders again the next month.
- **Late deliveries drive bad reviews.** Late orders average 2.27 stars against 4.29 on time (difference -2.02, 95% CI -2.06 to -1.98; Mann-Whitney p < 0.001). Holding distance, order value, freight share, basket size and category fixed, an ordered logit puts the chance of a 1-2 star review at 59.9% for late orders versus 9.8% on time.
- **Lateness is concentrated.** 6.8% of deliveries are late overall; the worst large states are CE (13.8%, 1,279 orders), BA (12.2%, 3,256 orders), RJ (12.1%, 12,350 orders).
- **No clear retention penalty yet.** Customers whose first order arrived late re-ordered within 180 days at 2.79% versus 3.20% (difference -0.41 pts, 95% CI -0.95 to +0.13; logistic regression odds ratio 0.88, p = 0.22). The direction is negative but the interval includes zero.
- **The CLV model is well calibrated.** Fitted on orders to 2018-02-28, BG/NBD predicted 736 repeat purchase days in the next 26 weeks against 712 actual (+3.3%). Refitted on all data, it expects 1,559 repeat purchases worth R$237,233 in the next 12 months, 2.0% of last year's GMV.
- **Where the value sits.** 'New high-value' customers (14,647) hold 28.2% of GMV; 'At-risk high-value' customers (13,985, last order about 13 months ago) hold 27.5%.

**What to do**

1. Fix delivery promises first in CE, BA, RJ: renegotiate carriers or pad the estimated date there. Reaching an average review of 4.20 needs 95.5% of deliveries on time, against 93.3% today.
2. Score sellers on late rate and 1-2 star share every month (seller scorecard in Power BI) and cap promises for the worst offenders.
3. Test a second-order voucher on 'New high-value' customers with a holdout group. At R$10 per voucher and a 15% contribution margin it must lift the 180-day repeat rate by 2.2 pts (from 3.2%) to break even.
4. Do not count on retention gains from delivery fixes in the business case until a test confirms them; the measured review effect alone justifies the delivery work.

**Caveats:** observational data; margin and voucher value are assumptions; orders after 2018-08-31 excluded.
