"""Step 0: prove that real NASA POWER data can be downloaded on THIS computer.

Run:  python check_nasa.py
It fetches monthly rainfall for one point (Kochi area), prints the units NASA reports,
a few values, and the June-September total for the latest complete year.
Code generated with AI assistance (Claude, Anthropic).
"""
import os
import sys

os.environ["TERRASCOPE_SYNTHETIC"] = "0"   # always real data here

import config  # noqa: E402
from core.aggregate import season_series  # noqa: E402
from core.nasa import build_url, fetch_monthly  # noqa: E402

LAT, LON = 9.93, 76.27

print("Requesting:", build_url("PRECTOTCORR", LAT, LON, config.FIRST_YEAR, config.LAST_YEAR))
try:
    d = fetch_monthly("PRECTOTCORR", LAT, LON)
except Exception as e:
    print("\nFAILED:", e)
    print("Check your internet connection / firewall, then try again. If it keeps failing, send this message to whoever is helping you.")
    sys.exit(1)

m = d["monthly"]
print(f"\nOK  ({'from cache' if d['from_cache'] else 'downloaded'})")
print("Units reported by NASA:", d["units"], "|", d["longname"])
print("Months received:", len(m), "| missing:", sum(1 for v in m.values() if v != v))
for ym in [(1981, 6), (1981, 7), (config.LAST_YEAR, 6), (config.LAST_YEAR, 7)]:
    print(f"  {ym[0]}-{ym[1]:02d}: {m.get(ym)} mm/day")
y, v = season_series(m, [6, 7, 8, 9], "sum_days", config.LAST_YEAR, config.LAST_YEAR)
print(f"\nMonsoon (Jun-Sep) total for {y[0]}: {v[0]:.0f} mm   <- sanity check: should be in the high hundreds to few thousand mm for Kerala")
