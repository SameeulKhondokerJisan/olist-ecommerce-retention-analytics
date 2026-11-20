"""BG/NBD and Gamma-Gamma recover known parameters from simulated data."""
import numpy as np
import pandas as pd
import pytest

from src import clv


def _simulate(n=4000, r=0.8, alpha=6.0, a=1.2, b=3.0, T=52.0, seed=7):
    rng = np.random.default_rng(seed)
    lam = rng.gamma(r, 1 / alpha, n)
    p = rng.beta(a, b, n)
    rows = []
    for i in range(n):
        t, x, last = 0.0, 0, 0.0
        while True:
            t += rng.exponential(1 / lam[i])
            if t > T:
                break
            x, last = x + 1, t
            if rng.uniform() < p[i]:
                break
        rows.append((x, last, T))
    return pd.DataFrame(rows, columns=["x", "t_x", "T"])


def test_bgnbd_recovers_parameters():
    data = _simulate()
    model = clv.BGNBD().fit(data)
    assert model.r == pytest.approx(0.8, rel=0.25)
    assert model.alpha == pytest.approx(6.0, rel=0.35)
    expected = model.expected_purchases(26, data.x, data.t_x, data["T"])
    assert np.all(expected >= 0) and np.isfinite(expected).all()


def test_prob_alive_is_one_without_repeats_and_bounded():
    model = clv.BGNBD(r=0.5, alpha=5, a=1.5, b=2.5)
    assert model.prob_alive([0], [0], [10])[0] == pytest.approx(1.0)
    pa = model.prob_alive([3, 3], [2, 9], [10, 10])
    assert 0 < pa[0] < pa[1] <= 1   # more recent last purchase -> more likely alive


def test_gamma_gamma_mean_close_to_simulation():
    rng = np.random.default_rng(3)
    p, q, v = 4.0, 3.0, 60.0
    nu = rng.gamma(q, 1 / v, 3000)
    x = rng.integers(2, 6, 3000)
    m = np.array([rng.gamma(p, 1 / n_, k).mean() for n_, k in zip(nu, x)])
    gg = clv.GammaGamma().fit(x, m)
    assert gg.p * gg.v / (gg.q - 1) == pytest.approx(p * v / (q - 1), rel=0.15)
