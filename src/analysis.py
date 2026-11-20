"""Customer segmentation, delivery-experience statistics and repeat-purchase analysis."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.miscmodels.ordinal_model import OrderedModel

from src import config

DELAY_BUCKETS = [(-10_000, 0, "On time"), (1, 3, "1-3 days late"), (4, 7, "4-7 days late"),
                 (8, 14, "8-14 days late"), (15, 10_000, "15+ days late")]


# --- RFM segmentation -------------------------------------------------------------------------
def rfm_table(orders: pd.DataFrame) -> pd.DataFrame:
    snapshot = pd.Timestamp(config.CUTOFF) + pd.Timedelta(days=1)
    g = orders.groupby("customer_unique_id")
    rfm = pd.DataFrame({"recency_days": (snapshot - g.purchase_ts.max()).dt.days,
                        "frequency": g.order_id.nunique(), "monetary": g.order_value.sum()})
    rfm["R"] = pd.qcut(rfm.recency_days.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["M"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["F"] = np.select([rfm.frequency >= 3, rfm.frequency == 2], [5, 3], 1)
    conditions = [
        (rfm.F >= 3) & (rfm.R >= 4),
        (rfm.F >= 3),
        (rfm.R >= 4) & (rfm.M >= 4),
        (rfm.R >= 4),
        (rfm.R <= 2) & (rfm.M >= 4),
        (rfm.R <= 2),
    ]
    labels = ["Champions (recent repeat)", "Loyal repeaters", "New high-value", "New low-value",
              "At-risk high-value", "Hibernating low-value"]
    rfm["segment"] = np.select(conditions, labels, "Needs attention")
    return rfm


def kmeans_segments(rfm: pd.DataFrame, k_range=range(3, 7)) -> tuple[pd.Series, pd.DataFrame]:
    """K-means on log RFM; k chosen by silhouette on a 10k sample."""
    X = StandardScaler().fit_transform(np.log1p(rfm[["recency_days", "frequency", "monetary"]]))
    rng = np.random.default_rng(config.SEED)
    sample = rng.choice(len(X), size=min(10_000, len(X)), replace=False)
    scores = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=config.SEED).fit(X)
        scores.append({"k": k, "silhouette": float(silhouette_score(X[sample], km.labels_[sample])),
                       "inertia": float(km.inertia_)})
    scores = pd.DataFrame(scores)
    best_k = int(scores.sort_values("silhouette").k.iloc[-1])
    labels = KMeans(n_clusters=best_k, n_init=10, random_state=config.SEED).fit_predict(X)
    return pd.Series(labels, index=rfm.index, name="cluster"), scores


# --- Delivery and reviews ----------------------------------------------------------------------
def delivered_reviewed(orders: pd.DataFrame) -> pd.DataFrame:
    d = orders[orders.is_delivered & orders.review_score.notna() & orders.is_late.notna()].copy()
    d["is_late"] = d.is_late.astype(bool)
    d["negative_review"] = (d.review_score <= 2).astype(int)
    d["delay_bucket"] = pd.cut(d.delay_days, bins=[b[0] - 0.5 for b in DELAY_BUCKETS] + [10_000.5],
                               labels=[b[2] for b in DELAY_BUCKETS])
    return d


def review_by_lateness(d: pd.DataFrame, n_boot: int = 1000) -> dict:
    late, ontime = d[d.is_late].review_score, d[~d.is_late].review_score
    u, p = stats.mannwhitneyu(late, ontime, alternative="two-sided")
    rank_biserial = 1 - 2 * u / (len(late) * len(ontime))   # P(on-time > late) - P(late > on-time)
    rng = np.random.default_rng(config.SEED)
    lv, ov = late.to_numpy(), ontime.to_numpy()
    boots = [rng.choice(lv, len(lv)).mean() - rng.choice(ov, len(ov)).mean() for _ in range(n_boot)]
    return {"late_orders": int(len(late)), "ontime_orders": int(len(ontime)),
            "late_share": float(len(late) / len(d)),
            "mean_review_late": float(late.mean()), "mean_review_ontime": float(ontime.mean()),
            "negative_rate_late": float((late <= 2).mean()), "negative_rate_ontime": float((ontime <= 2).mean()),
            "mean_diff": float(late.mean() - ontime.mean()),
            "mean_diff_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "mann_whitney_u": float(u), "p_value": float(p), "rank_biserial": float(rank_biserial)}


def review_by_delay_bucket(d: pd.DataFrame) -> pd.DataFrame:
    return (d.groupby("delay_bucket", observed=True)
             .agg(orders=("order_id", "size"), avg_review=("review_score", "mean"),
                  negative_rate=("negative_review", "mean"))
             .reset_index())


def _design(d: pd.DataFrame, top_categories: int = 12) -> pd.DataFrame:
    cats = d.main_category.value_counts().index[:top_categories]
    X = pd.DataFrame({
        "is_late": d.is_late.astype(float),
        "log_distance_km": np.log1p(d.distance_km.fillna(d.distance_km.median())),
        "log_order_value": np.log(d.order_value.clip(lower=1)),
        "freight_ratio": d.freight_ratio.clip(upper=2).fillna(0),
        "multi_item": (d["items"] > 1).astype(float),
        "multi_seller": (d.sellers > 1).astype(float),
    }, index=d.index)
    dummies = pd.get_dummies(d.main_category.where(d.main_category.isin(cats), "other"), prefix="cat",
                             drop_first=False, dtype=float).drop(columns="cat_other", errors="ignore")
    return pd.concat([X, dummies], axis=1)


def ordinal_model(d: pd.DataFrame) -> dict:
    """Ordered logit of review score on lateness and controls; also P(1-2 stars) late vs on-time."""
    X = _design(d)
    model = OrderedModel(d.review_score.astype(int), X, distr="logit").fit(method="bfgs", maxiter=500, disp=False)
    coef, se = model.params["is_late"], model.bse["is_late"]
    probs_late = np.asarray(model.predict(X.assign(is_late=1.0)))
    probs_on = np.asarray(model.predict(X.assign(is_late=0.0)))
    # OrderedModel: higher latent value = higher score, so a negative coefficient lowers ratings
    return {"n": int(len(d)), "coef_is_late": float(coef), "se_is_late": float(se),
            "odds_ratio_higher_score": float(np.exp(coef)),
            "or_ci": [float(np.exp(coef - 1.96 * se)), float(np.exp(coef + 1.96 * se))],
            "p_value": float(model.pvalues["is_late"]),
            "p_negative_if_late": float(probs_late[:, :2].sum(axis=1).mean()),
            "p_negative_if_ontime": float(probs_on[:, :2].sum(axis=1).mean()),
            "controls": [c for c in X.columns if c != "is_late"]}


# --- Repeat purchase -----------------------------------------------------------------------------
def first_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """First order per customer with a 180-day repeat flag (customers observable for 180 days only)."""
    o = orders.sort_values(["customer_unique_id", "purchase_ts"]).copy()
    o["nth"] = o.groupby("customer_unique_id").cumcount()
    first = o[o.nth == 0].set_index("customer_unique_id")
    second = o[o.nth == 1].set_index("customer_unique_id").purchase_ts.rename("second_ts")
    first = first.join(second)
    horizon = pd.Timestamp(config.CUTOFF) - pd.Timedelta(days=config.REPEAT_WINDOW_DAYS)
    first = first[first.purchase_ts <= horizon].copy()
    gap = (first.second_ts - first.purchase_ts).dt.days
    first["repeat_180d"] = (gap <= config.REPEAT_WINDOW_DAYS).fillna(False).astype(int)
    return first


def repeat_by_first_delivery(first: pd.DataFrame) -> dict:
    f = first[first.is_delivered & first.is_late.notna()].copy()
    f["is_late"] = f.is_late.astype(bool)
    late, ontime = f[f.is_late].repeat_180d, f[~f.is_late].repeat_180d
    p_l, p_o = late.mean(), ontime.mean()
    se = np.sqrt(p_l * (1 - p_l) / len(late) + p_o * (1 - p_o) / len(ontime))
    pooled = f.repeat_180d.mean()
    z = (p_l - p_o) / np.sqrt(pooled * (1 - pooled) * (1 / len(late) + 1 / len(ontime)))
    # logistic regression with controls (state, category, value, month of first order)
    X = _design(f)
    top_states = f.customer_state.value_counts().index[:8]
    # 2016 has only 264 first orders spread over three months (one month has a single customer), which
    # separates the data and stops the fit from converging, so 2016 is one level. The busiest month is the base.
    month = f.purchase_month.dt.strftime("%Y-%m").where(f.purchase_month.dt.year > 2016, "2016")
    months = pd.get_dummies(month, prefix="m", dtype=float).drop(columns=f"m_{month.value_counts().idxmax()}")
    X = pd.concat([X, pd.get_dummies(f.customer_state.where(f.customer_state.isin(top_states), "other"),
                                     prefix="state", dtype=float).drop(columns="state_other", errors="ignore"),
                   months], axis=1)
    logit = sm.Logit(f.repeat_180d, sm.add_constant(X)).fit(disp=False, maxiter=100)
    if not logit.mle_retvals.get("converged", False):
        raise RuntimeError("repeat-purchase logit did not converge")
    b, s = logit.params["is_late"], logit.bse["is_late"]
    return {"customers": int(len(f)), "repeat_rate_overall": float(f.repeat_180d.mean()),
            "repeat_rate_late": float(p_l), "repeat_rate_ontime": float(p_o), "diff": float(p_l - p_o),
            "diff_ci": [float(p_l - p_o - 1.96 * se), float(p_l - p_o + 1.96 * se)],
            "z_p_value": float(2 * stats.norm.sf(abs(z))),
            "logit_odds_ratio": float(np.exp(b)), "logit_or_ci": [float(np.exp(b - 1.96 * s)), float(np.exp(b + 1.96 * s))],
            "logit_p_value": float(logit.pvalues["is_late"])}
