# NASA POWER monthly point client with retry + local cache.
# Code generated with AI assistance (Claude, Anthropic).
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import numpy as np
import requests

import config

HEADERS = {"User-Agent": "TerraScope/1.0 (NASA Space Apps project)"}


def _cache_path(param, lat, lon, community):
    key = f"{param}_{community}_{lat:.4f}_{lon:.4f}"
    return os.path.join(config.CACHE_DIR, key + ".json")


def _atomic_write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def build_url(param, lat, lon, start, end, community=config.COMMUNITY):
    return (f"{config.POWER_URL}?parameters={param}&community={community}"
            f"&longitude={lon:.4f}&latitude={lat:.4f}&start={start}&end={end}&format=JSON")


def parse_power_json(js, param):
    """NASA POWER JSON -> ({(year, month): value or NaN}, units, longname).
    Keys look like '198101'; month 13 is the annual mean and is skipped. -999 = missing."""
    series = js["properties"]["parameter"][param]
    monthly = {}
    for k, v in series.items():
        k = str(k)
        if len(k) != 6:
            continue
        y, m = int(k[:4]), int(k[4:])
        if not 1 <= m <= 12:
            continue
        monthly[(y, m)] = np.nan if (v is None or float(v) <= -998) else float(v)
    meta = (js.get("parameters") or {}).get(param, {})
    return monthly, meta.get("units"), meta.get("longname")


def _http_get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        except requests.RequestException as e:
            last = str(e)[:120]
        time.sleep(1.5 * (2 ** i))
    raise RuntimeError(f"NASA POWER request failed: {last}")


def fetch_monthly(param, lat, lon, community=config.COMMUNITY):
    """Return dict: monthly {(y,m): v}, units, longname, url, retrieved, from_cache, synthetic."""
    if config.SYNTHETIC:
        from core.synthetic import make_monthly
        monthly = make_monthly(param, lat, lon, config.FIRST_YEAR, config.LAST_YEAR)
        return {"monthly": monthly, "units": "SYNTHETIC", "longname": "SYNTHETIC TEST DATA (not NASA)",
                "url": "synthetic://test-data", "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "from_cache": False, "synthetic": True}

    lat, lon = round(float(lat), 4), round(float(lon), 4)
    path = _cache_path(param, lat, lon, community)
    if os.path.exists(path):
        with open(path) as f:
            c = json.load(f)
        monthly = {(int(k[:4]), int(k[4:])): (np.nan if v is None else v) for k, v in c["monthly"].items()}
        c.update(monthly=monthly, from_cache=True, synthetic=False)
        return c

    url = build_url(param, lat, lon, config.FIRST_YEAR, config.LAST_YEAR, community)
    js = _http_get(url)
    monthly, units, longname = parse_power_json(js, param)
    if not monthly:
        raise RuntimeError("NASA POWER returned no monthly values")
    out = {"monthly": monthly, "units": units, "longname": longname, "url": url,
           "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    _atomic_write(path, {**out, "monthly": {f"{y}{m:02d}": (None if np.isnan(v) else v) for (y, m), v in monthly.items()}})
    out.update(from_cache=False, synthetic=False)
    return out
