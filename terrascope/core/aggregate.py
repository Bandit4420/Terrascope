# Monthly -> seasonal series. Missing months make the whole season NaN (never zero).
# Code generated with AI assistance (Claude, Anthropic).
import calendar
import warnings

import numpy as np


def season_series(monthly, months, agg, start, end):
    """monthly: {(year, month): value}. Returns (years array, values array).
    agg='sum_days'  : sum(rate * days_in_month)   e.g. mm/day -> mm/season
    agg='mean_days' : day-weighted mean           e.g. temperature"""
    years = np.arange(start, end + 1)
    vals = np.full(len(years), np.nan)
    for i, y in enumerate(years):
        parts = [monthly.get((int(y), m), np.nan) for m in months]
        if any(np.isnan(p) for p in parts):
            continue
        days = [calendar.monthrange(int(y), m)[1] for m in months]
        if agg == "sum_days":
            vals[i] = sum(p * d for p, d in zip(parts, days))
        else:
            vals[i] = sum(p * d for p, d in zip(parts, days)) / sum(days)
    return years, vals


def zone_mean(series_list, min_frac=0.5):
    """Average several point series (same years). A year needs >= min_frac of points valid."""
    arr = np.vstack(series_list)
    valid = np.isfinite(arr).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # all-NaN columns are expected
        m = np.nanmean(arr, axis=0)
    m[valid < max(1, min_frac * arr.shape[0])] = np.nan
    return m
