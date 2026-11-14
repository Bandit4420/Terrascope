# Orchestrates one investigation: fetch -> aggregate -> statistics -> FDR -> result dict.
# Code generated with AI assistance (Claude, Anthropic).
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pymannkendall
import scipy

import config
from core import regions
from core.aggregate import season_series, zone_mean
from core.catalog import SEASONS, get_variable
from core.nasa import fetch_monthly
from core.stats import analyze_series, bh_fdr, classify


class InputError(ValueError):
    pass


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, np.ndarray):
        return [_clean(v) for v in o.tolist()]
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _num(params, key, lo, hi):
    try:
        v = float(params[key])
    except (KeyError, TypeError, ValueError):
        raise InputError(f"Missing or invalid '{key}'")
    if not lo <= v <= hi:
        raise InputError(f"'{key}' must be between {lo} and {hi}")
    return v


def validate(params):
    var = get_variable(params.get("variable"))
    if not var or not var["enabled"]:
        raise InputError("Unknown or unavailable variable")
    season = SEASONS.get(params.get("season"))
    if not season:
        raise InputError("Unknown season")
    start, end = int(params.get("start", config.FIRST_YEAR)), int(params.get("end", config.LAST_YEAR))
    if start < config.FIRST_YEAR or end > config.LAST_YEAR or end <= start:
        raise InputError(f"Years must be within {config.FIRST_YEAR}-{config.LAST_YEAR} with end > start")
    if end - start + 1 < config.MIN_VALID_YEARS:
        raise InputError(f"Need at least {config.MIN_VALID_YEARS} years of data for trend tests")
    scope = params.get("scope", "india")
    if scope == "india":
        pts = regions.india_points()
    elif scope == "point":
        pts = regions.point_scope(_num(params, "lat", -90, 90), _num(params, "lon", -180, 180))
    elif scope == "box":
        la0, la1 = _num(params, "lat_min", -90, 90), _num(params, "lat_max", -90, 90)
        lo0, lo1 = _num(params, "lon_min", -180, 180), _num(params, "lon_max", -180, 180)
        la0, la1, lo0, lo1 = min(la0, la1), max(la0, la1), min(lo0, lo1), max(lo0, lo1)
        if la1 - la0 < 0.5 or lo1 - lo0 < 0.5:
            raise InputError("Box is too small (minimum 0.5 degrees each way)")
        if la1 - la0 > 40 or lo1 - lo0 > 60:
            raise InputError("Box is too large (max 40 x 60 degrees)")
        pts = regions.box_scope(la0, la1, lo0, lo1)
    else:
        raise InputError("Unknown scope")
    return var, season, start, end, scope, pts


def run_analysis(params, progress=lambda done, total: None):
    var, season, start, end, scope, pts = validate(params)
    alpha, min_valid = config.ALPHA, config.MIN_VALID_YEARS
    total, done = len(pts), 0

    # 1) fetch (parallel, polite)
    fetched, errors = {}, {}
    with ThreadPoolExecutor(max_workers=config.WORKERS) as ex:
        futs = {ex.submit(fetch_monthly, var["id"], p["lat"], p["lon"]): i for i, p in enumerate(pts)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                fetched[i] = fut.result()
            except Exception as e:
                errors[i] = str(e)
            done += 1
            progress(done, total)
    if not fetched:
        first = next(iter(errors.values()), "unknown error")
        raise RuntimeError(f"No data could be retrieved. {first}. Check your internet connection.")

    # 2) aggregate + per-point statistics
    years = np.arange(start, end + 1)
    point_rows, series_by_zone = [], {}
    for i, p in enumerate(pts):
        row = {"id": i, **p, "values": None, "stats": None, "error": errors.get(i)}
        if i in fetched:
            _, vals = season_series(fetched[i]["monthly"], season["months"], var["agg"], start, end)
            row["values"] = vals
            row["stats"] = analyze_series(years, vals, alpha, min_valid, var["relative"])
            series_by_zone.setdefault(p["zone"], []).append(vals)
        point_rows.append(row)

    # 3) FDR across all grid points (multiple-testing control)
    pvals = [r["stats"]["mk_p"] if r["stats"] and r["stats"]["status"] == "ok" else np.nan for r in point_rows]
    qvals = bh_fdr(pvals)
    for r, q in zip(point_rows, qvals):
        ok = r["stats"] and r["stats"]["status"] == "ok"
        r["q"] = q
        r["cls"] = classify(q, r["stats"]["sen_slope"], alpha) if ok else "insufficient"

    # 4) zone-level series + statistics (+ FDR across zones)
    zone_rows = []
    for zname, lst in series_by_zone.items():
        vals = zone_mean(lst)
        st = analyze_series(years, vals, alpha, min_valid, var["relative"])
        desc = regions.ZONES.get(zname, {}).get("desc", "")
        zone_rows.append({"name": zname, "desc": desc, "n_points": len(lst), "values": vals, "stats": st})
    zq = bh_fdr([z["stats"]["mk_p"] if z["stats"]["status"] == "ok" else np.nan for z in zone_rows])
    for z, q in zip(zone_rows, zq):
        ok = z["stats"]["status"] == "ok"
        z["q"] = q
        z["cls"] = classify(q, z["stats"]["sen_slope"], alpha) if ok else "insufficient"

    up = [z["name"] for z in zone_rows if z["cls"] == "increase"]
    down = [z["name"] for z in zone_rows if z["cls"] == "decrease"]
    counts = {c: sum(1 for r in point_rows if r["cls"] == c) for c in ("increase", "decrease", "none", "insufficient")}

    api_units = next((f["units"] for f in fetched.values() if f.get("units")), None)
    synthetic = any(f.get("synthetic") for f in fetched.values())
    retrieved = sorted(f["retrieved"] for f in fetched.values())
    warnings = []
    if end - start + 1 < config.WARN_YEARS:
        warnings.append(f"Short record ({end - start + 1} years): treat trends with caution.")
    if errors:
        warnings.append(f"{len(errors)} of {total} points could not be retrieved and were skipped.")
    if synthetic:
        warnings.append("SYNTHETIC TEST DATA - not NASA measurements.")

    meta = {
        "synthetic": synthetic,
        "variable": {k: var[k] for k in ("id", "name", "api_unit", "out_unit", "agg", "source", "description")},
        "api_units_reported": api_units,
        "season": {"id": params.get("season"), **season},
        "start": start, "end": end, "scope": scope, "n_points": total, "n_failed": len(errors),
        "n_cached": sum(1 for f in fetched.values() if f.get("from_cache")),
        "community": config.COMMUNITY, "alpha": alpha, "min_valid_years": min_valid,
        "dataset": "NASA POWER monthly point API (MERRA-2 based)",
        "example_request": next(iter(fetched.values()))["url"],
        "retrieved_first": retrieved[0], "retrieved_last": retrieved[-1],
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {"numpy": np.__version__, "scipy": scipy.__version__, "pymannkendall": pymannkendall.__version__},
        "warnings": warnings,
    }
    result = {
        "meta": meta, "years": years, "points": point_rows, "zones": zone_rows,
        "summary": {"counts": counts, "increase_zones": up, "decrease_zones": down,
                    "opposing": bool(up and down)},
    }
    return _clean(result)
