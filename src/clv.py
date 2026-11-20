"""Customer lifetime value: BG/NBD purchase model + Gamma-Gamma spend model.

Implemented from Fader, Hardie & Lee (2005), "Counting Your Customers the Easy Way"
and "RFM and CLV: Using Iso-Value Curves", with maximum likelihood via scipy.
Time unit: weeks. A "purchase" is a distinct purchase day, so several orders placed
on the same day count once (the standard convention for these models).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln, hyp2f1


def rfm_summary(orders: pd.DataFrame, end: pd.Timestamp) -> pd.DataFrame:
    """Per customer: x (repeat purchase days), t_x and T in weeks, mean order value."""
    df = orders[orders.purchase_ts <= end].copy()
    df["day"] = df.purchase_ts.dt.normalize()
    daily = df.groupby(["customer_unique_id", "day"], as_index=False).order_value.sum()
    g = daily.groupby("customer_unique_id")
    first, last = g.day.min(), g.day.max()
    out = pd.DataFrame({
        "x": g.day.nunique() - 1,
        "t_x": (last - first).dt.days / 7.0,
        "T": (end.normalize() - first).dt.days / 7.0,
        "monetary": g.order_value.mean(),
    })
    return out[out["T"] > 0]


@dataclass
class BGNBD:
    r: float = np.nan
    alpha: float = np.nan
    a: float = np.nan
    b: float = np.nan

    @staticmethod
    def _nll(log_params, x, t_x, T):
        r, alpha, a, b = np.exp(log_params)
        with np.errstate(divide="ignore", invalid="ignore"):
            a1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
            a2 = gammaln(a + b) + gammaln(b + x) - gammaln(b) - gammaln(a + b + x)
            a3 = -(r + x) * np.log(alpha + T)
            a4 = np.where(x > 0, np.log(a) - np.log(b + x - 1) - (r + x) * np.log(alpha + t_x), -np.inf)
        return -np.sum(a1 + a2 + np.logaddexp(a3, a4))

    def fit(self, summary: pd.DataFrame) -> "BGNBD":
        x, t_x, T = (summary[c].to_numpy(float) for c in ("x", "t_x", "T"))
        best = None
        for start in ([0.0, 1.0, 0.0, 0.0], [-1.0, 2.0, -0.5, 1.0], [0.5, 3.0, 0.5, 2.0]):
            res = minimize(self._nll, np.array(start), args=(x, t_x, T), method="Nelder-Mead",
                           options={"maxiter": 20000, "xatol": 1e-7, "fatol": 1e-7})
            if best is None or res.fun < best.fun:
                best = res
        self.r, self.alpha, self.a, self.b = np.exp(best.x)
        self.loglik = -best.fun
        return self

    def expected_purchases(self, t: float, x, t_x, T) -> np.ndarray:
        """E[purchases in (T, T + t]] for customers with history (x, t_x, T)."""
        r, alpha, a, b = self.r, self.alpha, self.a, self.b
        x, t_x, T = (np.asarray(v, float) for v in (x, t_x, T))
        hyp = hyp2f1(r + x, b + x, a + b + x - 1, t / (alpha + T + t))
        term = (a + b + x - 1) / (a - 1) * (1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp)
        with np.errstate(divide="ignore", invalid="ignore"):
            odds = np.where(x > 0, (a / (b + x - 1)) * ((alpha + T) / (alpha + t_x)) ** (r + x), 0.0)
        return term / (1 + odds)

    def prob_alive(self, x, t_x, T) -> np.ndarray:
        x, t_x, T = (np.asarray(v, float) for v in (x, t_x, T))
        with np.errstate(divide="ignore", invalid="ignore"):
            odds = np.where(x > 0, (self.a / (self.b + x - 1)) * ((self.alpha + T) / (self.alpha + t_x))
                            ** (self.r + x), 0.0)
        return 1 / (1 + odds)


@dataclass
class GammaGamma:
    p: float = np.nan
    q: float = np.nan
    v: float = np.nan

    @staticmethod
    def _nll(log_params, x, m):
        p, q, v = np.exp(log_params)
        ll = (gammaln(p * x + q) - gammaln(p * x) - gammaln(q) + q * np.log(v)
              + (p * x - 1) * np.log(m) + (p * x) * np.log(x) - (p * x + q) * np.log(v + m * x))
        return -np.sum(ll)

    def fit(self, x: np.ndarray, m: np.ndarray) -> "GammaGamma":
        """x = number of purchases behind the average m (customers with repeat purchases only)."""
        res = minimize(self._nll, np.log([2.0, 3.0, 50.0]), args=(np.asarray(x, float), np.asarray(m, float)),
                       method="Nelder-Mead", options={"maxiter": 20000})
        self.p, self.q, self.v = np.exp(res.x)
        return self

    def expected_avg_value(self, x, m) -> np.ndarray:
        """Expected value per future purchase; customers without repeat history get the population mean."""
        x, m = np.asarray(x, float), np.asarray(m, float)
        pop = self.p * self.v / (self.q - 1)
        cond = (self.v + m * x) * self.p / (self.p * x + self.q - 1)
        return np.where(x > 0, cond, pop)


def holdout_check(orders: pd.DataFrame, cal_end: pd.Timestamp, weeks: int) -> dict:
    """Fit on the calibration period and compare predicted vs actual purchase days in the holdout."""
    cal = rfm_summary(orders, cal_end)
    model = BGNBD().fit(cal)
    hold_end = cal_end + pd.Timedelta(weeks=weeks)
    hold = orders[(orders.purchase_ts > cal_end) & (orders.purchase_ts <= hold_end)].copy()
    hold["day"] = hold.purchase_ts.dt.normalize()
    actual = hold.groupby("customer_unique_id").day.nunique().reindex(cal.index, fill_value=0)
    predicted = model.expected_purchases(weeks, cal.x, cal.t_x, cal["T"])
    by_freq = (pd.DataFrame({"x": cal.x.clip(upper=3), "actual": actual.to_numpy(), "predicted": predicted})
               .groupby("x").agg(customers=("actual", "size"), actual=("actual", "mean"),
                                 predicted=("predicted", "mean")).reset_index())
    return {"calibration_customers": int(len(cal)), "holdout_weeks": weeks,
            "actual_purchases": float(actual.sum()), "predicted_purchases": float(predicted.sum()),
            "error_pct": float(predicted.sum() / max(actual.sum(), 1) - 1),
            "by_frequency": by_freq, "params": model.__dict__.copy()}
