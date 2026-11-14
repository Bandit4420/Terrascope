# TerraScope — Earth System Trend Detective

Pixel-art space-themed web app for the NASA Space Apps Challenge 2026
("Be an Earth System Trend Detective"). It pulls real **NASA POWER (MERRA-2)** data, shows what is
changing, where, by how much, and whether the change is statistically significant.
Flagship case study: **Monsoon Mirror** (Indian monsoon rainfall trends since 1981).

> **AI disclosure:** the code in this project was generated with AI assistance (Claude, Anthropic)
> and then run and tested. Pixel art is drawn in code. No NASA logos or branding are used.
> TerraScope is an independent project, not affiliated with or endorsed by NASA.

## Run it (5 minutes)

You need Python 3.10+ and an internet connection.

```bash
cd terrascope

# 1. (recommended) make a virtual environment
python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# 2. install
pip install -r requirements.txt

# 3. PROVE real NASA data works on your machine (do this first!)
python check_nasa.py

# 4. start the app
python app.py
```

Open **http://127.0.0.1:5000** in your browser, click **MONSOON MIRROR → LAUNCH**.
The first run downloads 30 locations (about 30–90 seconds); after that it uses the `cache/` folder.
(Delete `cache/*.json` to force a fresh download.)

## What it does

| Question | Where in the app |
|---|---|
| What is changing? | Data Explorer (searchable variable catalog) |
| Where? | Map of locations coloured by significant increase / decrease / no significant trend |
| How much? | Sen's slope with 95% confidence interval, % per decade |
| Is it significant? | Mann-Kendall (autocorrelation-aware) + Benjamini-Hochberg FDR correction |
| Do regions differ? | Opposing-trends detector + compare up to 3 regions on one chart |
| Evidence? | Provenance panel, CSV export, Markdown report, print view |

Variables: precipitation, 2 m temperature, relative humidity, wind speed.
Scopes: 5 India zones (30 sample points), a single clicked point, or a custom box (up to 4×4 points).

## Tests

```bash
python -m pytest tests -q
```

Software tests use **synthetic** data with known answers (e.g. recover a known −5 mm/yr slope,
false-positive rate near 5%, correct rainfall unit conversion, missing months never become zero).

## Offline test mode (FAKE data)

`TERRASCOPE_SYNTHETIC=1 python app.py` runs the whole app on generated fake data so you can try the
interface without internet. A red banner is shown and every export is labelled SYNTHETIC.
**Never use this mode for your submission.**

## Project layout

```
app.py              Flask routes (+ background job for progress bar)
config.py           years, alpha, limits
check_nasa.py       step-0 test: can this computer download NASA data?
core/nasa.py        NASA POWER client (retry + cache)
core/aggregate.py   monthly -> seasonal (rate x days, day-weighted means)
core/stats.py       regression, Sen's slope + CI, Mann-Kendall, Hamed-Rao, FDR
core/engine.py      one investigation: fetch -> stats -> FDR -> result
core/regions.py     India zones + point/box sampling
core/catalog.py     variables and seasons
core/synthetic.py   TEST-ONLY fake data
templates/ static/  pixel-art front end (Leaflet map, Plotly charts)
tests/              pytest suite
```

## Honest limitations (put these in your submission too)

- MERRA-2 is a reanalysis (model + observations), not a rain-gauge record.
- Each India zone is a set of sample points, not a full grid; zone values are plain averages.
- "No statistically significant trend detected" does not mean "no change".
- A trend shows what changed, not why.
- Results depend on the chosen period and season.

## Data and credits

NASA POWER project / MERRA-2 (NASA GMAO) · Flask · NumPy · SciPy · pymannkendall · Leaflet ·
Plotly · CARTO / OpenStreetMap tiles · fonts Press Start 2P and VT323.
