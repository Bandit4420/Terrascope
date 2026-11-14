# Trend statistics: linear regression, Sen's slope (+CI), Mann-Kendall (original or Hamed-Rao
# modified when lag-1 autocorrelation is detected), and Benjamini-Hochberg FDR.
# Code generated with AI assistance (Claude, Anthropic).
import numpy as np
import pymannkendall as mk
from scipy import stats as sps


def sen_slopes(t, x):
    i, j = np.triu_indices(len(t), 1)
    return (x[j] - x[i]) / (t[j] - t[i])


def sen_ci(x, slopes, alpha=0.05):
    """Sen slope confidence interval (Gilbert 1987), with tie correction in Var(S)."""
    n = len(x)
    _, counts = np.unique(x, return_counts=True)
    ties = sum(c * (c - 1) * (2 * c + 5) for c in counts if c > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0
    c = sps.norm.ppf(1 - alpha / 2) * np.sqrt(var_s)
    s = np.sort(slopes)
    big_n = len(s)
    lo = s[max(int(np.floor((big_n - c) / 2)) - 1, 0)]
    hi = s[min(int(np.ceil((big_n + c) / 2)), big_n - 1)]
    return float(lo), float(hi)


def _f(v):
    return None if v is None or not np.isfinite(v) else float(v)


def analyze_series(years, values, alpha=0.05, min_valid=10, relative=False):
    """Full trend analysis of one yearly series. NaN years are ignored (and counted as gaps)."""
    years = np.asarray(years, float)
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    n = int(ok.sum())
    if n < min_valid:
        return {"status": "insufficient", "n": n}
    t, x = years[ok], v[ok]
    gaps = int(t.max() - t.min() + 1 - n)

    # --- linear regression (for visual communication) ---
    lr = sps.linregress(t, x)
    tcrit = sps.t.ppf(1 - alpha / 2, n - 2)
    lin_lo, lin_hi = lr.slope - tcrit * lr.stderr, lr.slope + tcrit * lr.stderr

    # --- Sen's slope (uses real year spacing, so gaps are handled) ---
    sl = sen_slopes(t, x)
    b = float(np.median(sl))
    a = float(np.median(x - b * t))
    s_lo, s_hi = sen_ci(x, sl, alpha)

    # --- serial correlation of Sen-detrended residuals ---
    resid = x - (a + b * t)
    r1 = float(np.corrcoef(resid[:-1], resid[1:])[0, 1]) if n > 3 and np.ptp(resid) > 0 else 0.0
    r1_sig = bool(abs(r1) > 1.96 / np.sqrt(n))

    # --- Mann-Kendall ---
    note = None
    # Positive serial correlation inflates false positives, so only then is the Hamed-Rao
    # correction applied. With NEGATIVE lag-1 correlation the correction can shrink the variance
    # (even below zero) and make the test wildly over-confident, so the original test is kept.
    use_modified = r1_sig and r1 > 0
    if np.ptp(x) == 0:
        p, z, tau, method = 1.0, 0.0, 0.0, "Mann-Kendall (constant series)"
    else:
        res, method = None, "Mann-Kendall (original)"
        if use_modified:
            try:
                cand = mk.hamed_rao_modification_test(x, alpha=alpha)
                if np.isfinite(cand.p) and np.isfinite(cand.z):
                    res, method = cand, "Hamed-Rao modified Mann-Kendall (positive autocorrelation detected)"
                else:
                    note = "modified test gave a non-finite result; original test used"
            except Exception as e:
                note = f"modified test failed ({type(e).__name__}); original test used"
        if res is None:
            res = mk.original_test(x, alpha=alpha)
        p, z, tau = float(res.p), float(res.z), float(res.Tau)

    mean = float(np.mean(x))
    pct_dec = float(b * 10 / mean * 100) if relative and mean != 0 else None
    return {
        "status": "ok", "n": n, "gaps": gaps, "year_start": int(t.min()), "year_end": int(t.max()),
        "mean": mean,
        "sen_slope": b, "sen_lo": s_lo, "sen_hi": s_hi, "sen_intercept": a, "pct_per_decade": _f(pct_dec),
        "lin_slope": float(lr.slope), "lin_lo": float(lin_lo), "lin_hi": float(lin_hi),
        "lin_intercept": float(lr.intercept), "lin_p": float(lr.pvalue), "r2": float(lr.rvalue ** 2),
        "mk_p": p, "mk_z": z, "mk_tau": tau, "method": method, "note": note,
        "lag1": r1, "lag1_significant": r1_sig,
        "direction": "increasing" if b > 0 else "decreasing" if b < 0 else "flat",
    }


def bh_fdr(pvals):
    """Benjamini-Hochberg adjusted p-values (q-values). NaN stays NaN."""
    p = np.asarray(pvals, float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0, 1)
    q[ok] = out
    return q


def classify(q, slope, alpha=0.05):
    """increase / decrease = significant after correction; none = no statistically significant trend."""
    if q is None or not np.isfinite(q) or slope is None:
        return "insufficient"
    if q < alpha and slope > 0:
        return "increase"
    if q < alpha and slope < 0:
        return "decrease"
    return "none"
