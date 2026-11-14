# Tests the NASA POWER client against a MOCK response in POWER's documented JSON shape
# (the sandbox this was built in could not reach the live API, so live calls are untested there).
# Code generated with AI assistance (Claude, Anthropic).
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import nasa  # noqa: E402

MOCK = {
    "type": "Feature",
    "properties": {"parameter": {"PRECTOTCORR": {
        "198106": 8.5, "198107": 12.25, "198108": -999.0, "198109": 6.0, "198113": 7.1, "198201": 0.4}}},
    "parameters": {"PRECTOTCORR": {"units": "mm/day", "longname": "Precipitation Corrected"}},
}


def test_parse_skips_annual_key_and_maps_missing_to_nan():
    monthly, units, longname = nasa.parse_power_json(MOCK, "PRECTOTCORR")
    assert (1981, 13) not in monthly and len(monthly) == 5
    assert monthly[(1981, 6)] == 8.5 and np.isnan(monthly[(1981, 8)])
    assert units == "mm/day" and "Precip" in longname


def test_url_matches_documented_format():
    u = nasa.build_url("T2M", 10.0, 76.0, 1981, 2025)
    assert u.startswith("https://power.larc.nasa.gov/api/temporal/monthly/point?")
    for part in ("parameters=T2M", "community=AG", "longitude=76.0000", "latitude=10.0000",
                 "start=1981", "end=2025", "format=JSON"):
        assert part in u


def test_fetch_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "SYNTHETIC", False)
    calls = []
    monkeypatch.setattr(nasa, "_http_get", lambda url, tries=4: calls.append(url) or MOCK)
    a = nasa.fetch_monthly("PRECTOTCORR", 10.0, 76.0)
    b = nasa.fetch_monthly("PRECTOTCORR", 10.0, 76.0)
    assert len(calls) == 1 and a["from_cache"] is False and b["from_cache"] is True
    assert np.isnan(b["monthly"][(1981, 8)]) and b["monthly"][(1981, 7)] == 12.25
    assert b["units"] == "mm/day"
