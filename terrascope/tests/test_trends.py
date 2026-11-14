# Software tests using SYNTHETIC data with known properties (never NASA measurements).
# Code generated with AI assistance (Claude, Anthropic).
import os
import sys

import numpy as np
import pymannkendall as mk
import pytest
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.aggregate import season_series, zone_mean  # noqa: E402
from core.stats import analyze_series, bh_fdr, classify, sen_slopes  # noqa: E402

YEARS = np.arange(1981, 2021)  # 40 years


def synth(slope, sd=30.0, base=1500.0, seed=0, phi=0.0):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, sd, len(YEARS))
    for i in range(1, len(e)):
        e[i] += phi * e[i - 1]
    return base + slope * (YEARS - YEARS[0]) + e


def test_recovers_known_decreasing_slope():
    r = analyze_series(YEARS, synth(-5.0))
    assert abs(r["sen_slope"] - (-5.0)) < 1.5
    assert r["sen_lo"] <= -5.0 <= r["sen_hi"]
    assert r["mk_p"] < 0.05 and r["direction"] == "decreasing"


def test_recovers_known_increasing_slope():
    r = analyze_series(YEARS, synth(+4.0, seed=3))
    assert abs(r["sen_slope"] - 4.0) < 1.5 and r["mk_p"] < 0.05


def test_no_trend_false_positive_rate_is_near_alpha():
    hits = sum(analyze_series(YEARS, synth(0.0, seed=s))["mk_p"] < 0.05 for s in range(300))
    assert hits / 300 < 0.10          # nominal 5%; allow sampling noise


def test_sen_matches_pymannkendall_and_linregress_matches_scipy():
    x = synth(-2.0, seed=7)
    r = analyze_series(YEARS, x)
    ref = mk.original_test(x)
    assert r["sen_slope"] == pytest.approx(ref.slope, rel=1e-9)
    assert r["mk_p"] == pytest.approx(ref.p, rel=1e-9)
    lr = sps.linregress(YEARS, x)
    assert r["lin_slope"] == pytest.approx(lr.slope) and r["r2"] == pytest.approx(lr.rvalue ** 2)


def test_autocorrelated_series_uses_modified_test():
    found = [analyze_series(YEARS, synth(0.0, seed=s, phi=0.8))["lag1_significant"] for s in range(40)]
    assert sum(found) >= 10
    r = next(analyze_series(YEARS, synth(0.0, seed=s, phi=0.8)) for s in range(40)
             if analyze_series(YEARS, synth(0.0, seed=s, phi=0.8))["lag1_significant"])
    assert "Hamed" in r["method"]


def test_negative_autocorrelation_never_gives_nan_or_absurd_p():
    # Regression test: Hamed-Rao used on negative lag-1 correlation once produced NaN p
    # and p ~ 1e-7 on pure noise. It must stay finite and sane.
    for s in range(500):
        r = analyze_series(YEARS, synth(0.0, seed=s))
        assert np.isfinite(r["mk_p"]) and np.isfinite(r["mk_z"])
        if r["lag1"] < 0:
            assert "Hamed" not in r["method"]
            assert r["mk_p"] > 1e-4


def test_modified_test_reduces_false_positives_under_autocorrelation():
    orig = mod = 0
    for s in range(200):
        x = synth(0.0, seed=s, phi=0.8)
        orig += mk.original_test(x).p < 0.05
        mod += analyze_series(YEARS, x)["mk_p"] < 0.05
    assert mod < orig


def test_insufficient_data_and_gaps():
    x = synth(-3.0)
    few = x.copy(); few[8:] = np.nan
    assert analyze_series(YEARS, few)["status"] == "insufficient"
    gap = x.copy(); gap[10:13] = np.nan
    r = analyze_series(YEARS, gap)
    assert r["status"] == "ok" and r["gaps"] == 3 and r["n"] == 37


def test_constant_series_is_not_significant():
    r = analyze_series(YEARS, np.full(len(YEARS), 5.0))
    assert r["mk_p"] == 1.0 and r["sen_slope"] == 0


def test_bh_fdr_known_values():
    q = bh_fdr([0.01, 0.02, 0.03, 0.04, 0.05])
    assert np.allclose(q, 0.05)
    q = bh_fdr([0.001, 0.8, np.nan, 0.01])
    assert np.isnan(q[2]) and q[0] == pytest.approx(0.003) and q[3] == pytest.approx(0.015)


def test_fdr_stops_chance_hits_on_a_map():
    ps = [analyze_series(YEARS, synth(0.0, seed=s))["mk_p"] for s in range(500)]
    raw = sum(p < 0.05 for p in ps)
    adj = int(np.sum(bh_fdr(ps) < 0.05))
    assert raw > 5 and adj <= 2


def test_classify():
    assert classify(0.01, 1.0) == "increase" and classify(0.01, -1.0) == "decrease"
    assert classify(0.2, 1.0) == "none" and classify(np.nan, 1.0) == "insufficient"


def test_rainfall_aggregation_converts_rate_to_total():
    monthly = {(2001, m): 5.0 for m in range(1, 13)}
    _, v = season_series(monthly, [6, 7, 8, 9], "sum_days", 2001, 2001)
    assert v[0] == pytest.approx(5.0 * (30 + 31 + 31 + 30))
    _, a = season_series(monthly, list(range(1, 13)), "sum_days", 2001, 2001)
    assert a[0] == pytest.approx(5.0 * 365)
    monthly[(2004, 1)] = 1.0
    monthly.update({(2004, m): 1.0 for m in range(1, 13)})
    _, a = season_series(monthly, list(range(1, 13)), "sum_days", 2004, 2004)
    assert a[0] == pytest.approx(366.0)  # leap year


def test_missing_month_is_nan_never_zero():
    monthly = {(2001, m): 5.0 for m in range(1, 13)}
    monthly[(2001, 7)] = np.nan
    _, v = season_series(monthly, [6, 7, 8, 9], "sum_days", 2001, 2001)
    assert np.isnan(v[0])
    _, v2 = season_series({}, [6, 7, 8, 9], "mean_days", 2001, 2002)
    assert np.isnan(v2).all()


def test_temperature_uses_day_weighted_mean_not_sum():
    monthly = {(2001, m): 20.0 for m in range(1, 13)}
    _, v = season_series(monthly, [6, 7, 8, 9], "mean_days", 2001, 2001)
    assert v[0] == pytest.approx(20.0)


def test_zone_mean_needs_enough_points():
    a = np.array([1.0, np.nan, 3.0]); b = np.array([3.0, np.nan, np.nan]); c = np.array([5.0, np.nan, np.nan])
    m = zone_mean([a, b, c])
    assert m[0] == pytest.approx(3.0) and np.isnan(m[1]) and np.isnan(m[2])


def test_sen_slopes_pair_count():
    assert len(sen_slopes(np.arange(10.0), np.arange(10.0))) == 45
