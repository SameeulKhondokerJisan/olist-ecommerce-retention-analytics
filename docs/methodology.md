# Methodology

## Scope and cleaning
Orders purchased up to 2018-08-31 that are not canceled or unavailable. Customers are identified by
`customer_unique_id` because Olist issues a new `customer_id` for every order. Reviews: the latest answered
review per order. Geolocation: points outside Brazil's bounding box are dropped and the rest averaged per
zip prefix. Every rule and its row count is in `data_quality_log.md`.

## Delivery and reviews
* Late = delivered after the promised (estimated) date, compared by calendar day.
* Mann-Whitney U test of review scores (ordinal, non-normal), rank-biserial effect size, and a 1,000-draw
  bootstrap CI for the difference in mean score.
* Ordered logit (statsmodels `OrderedModel`) of review score on lateness with controls: log distance,
  log order value, freight share, multi-item and multi-seller flags, top-12 category dummies. Reported:
  the lateness coefficient and the average predicted probability of a 1-2 star review with every order
  set to late versus on time.

## Repeat purchases
First order per customer, restricted to customers observable for 180 days. Outcome: a second order within
180 days. Two-proportion z-test, then a logistic regression with the same controls plus state and month
of first order (the 264 first orders from 2016 form one level, because single-customer months stop the
fit from converging; the pipeline stops with an error if the fit does not converge). This is observational, and an estimate whose confidence interval includes zero is reported as inconclusive.

## Segmentation
RFM: recency quintiles, frequency bands (1, 2, 3+ orders), monetary quintiles, mapped to named segments.
K-means on standardized log(recency, frequency, monetary); k from 3-6 chosen by silhouette on a 10k sample.

## Customer lifetime value
BG/NBD (purchase and dropout process) and Gamma-Gamma (spend per purchase) implemented by maximum
likelihood (Fader, Hardie & Lee 2005). Time unit: weeks; a purchase is a distinct purchase day.
Validation: fit on orders up to 2018-02-28, predict the following 26 weeks, compare with actual purchases.
Final model fitted on all data predicts 52-week purchases and value per customer.

## Business case
Excel formulas over measured figures: on-time share needed for a target review score, value of repeat
lifts, and the break-even lift for a second-order voucher (paid on every repeat order by holders:
lift = base rate x voucher / (AOV x margin - voucher)).
