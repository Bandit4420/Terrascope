# SYNTHETIC TEST DATA GENERATOR. NOT NASA DATA. Only used when TERRASCOPE_SYNTHETIC=1.
# Lets the app be exercised offline; the UI shows a red banner whenever this is active.
# Code generated with AI assistance (Claude, Anthropic).
import zlib

import numpy as np


def make_monthly(param, lat, lon, y0, y1):
    rng = np.random.default_rng(zlib.crc32(f"{param}{lat:.3f}{lon:.3f}".encode()))
    years = np.arange(y0, y1 + 1)
    trend = np.sin(lat * 0.35) * np.cos(lon * 0.22)          # varies in sign across space
    ar = np.zeros(len(years))
    for i in range(1, len(years)):
        ar[i] = 0.3 * ar[i - 1] + rng.normal(0, 1)
    out = {}
    for yi, y in enumerate(years):
        for m in range(1, 13):
            season = np.cos(2 * np.pi * (m - 7.5) / 12)
            if param == "PRECTOTCORR":
                base = max(0.2, 4.0 + 5.0 * season + 1.5 * np.sin(lat / 5))
                v = base * (1 + 0.006 * trend * (y - y0) * 5) + 0.35 * ar[yi] * base / 4 + rng.normal(0, 0.25)
                v = max(v, 0.0)
            elif param == "T2M":
                v = 26 - 6 * np.cos(2 * np.pi * (m - 1) / 12) + 0.025 * (1 + trend) * (y - y0) + 0.3 * ar[yi] + rng.normal(0, 0.3)
            elif param == "RH2M":
                v = 60 + 20 * season - 0.05 * trend * (y - y0) * 4 + ar[yi] + rng.normal(0, 1.5)
            else:  # WS10M and anything else
                v = 3 + 0.8 * season + 0.004 * trend * (y - y0) + 0.1 * ar[yi] + rng.normal(0, 0.15)
            out[(int(y), m)] = float(v)
    return out
