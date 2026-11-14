# Variable catalog + season definitions.
# Code generated with AI assistance (Claude, Anthropic).

# agg: how monthly API values (daily-average rates/means) become one value per season-year
#   sum_days  -> value * days_in_month, summed   (rainfall totals)
#   mean_days -> day-weighted mean               (temperature, humidity, wind)
VARIABLES = [
    {
        "id": "PRECTOTCORR", "name": "Corrected precipitation", "category": "Precipitation",
        "api_unit": "mm/day", "out_unit": "mm/season", "agg": "sum_days", "relative": True, "enabled": True,
        "source": "NASA POWER (MERRA-2, observationally corrected precipitation)",
        "description": "Rainfall rate corrected towards gauge observations over land. Converted here to season totals (rate x days in month).",
        "coverage": "1981 - near real-time", "resolution": "~0.5 deg lat x 0.625 deg lon, monthly",
        "keywords": ["rain", "rainfall", "monsoon", "precipitation", "wet", "dry", "drought", "flood"],
        "method": "Season total -> Sen's slope + Mann-Kendall",
    },
    {
        "id": "T2M", "name": "Air temperature at 2 m", "category": "Temperature", "api_unit": "C",
        "out_unit": "deg C", "agg": "mean_days", "relative": False, "enabled": True,
        "source": "NASA POWER (MERRA-2)",
        "description": "Near-surface air temperature. Seasonal value is the day-weighted mean of monthly means.",
        "coverage": "1981 - near real-time", "resolution": "~0.5 deg lat x 0.625 deg lon, monthly",
        "keywords": ["temperature", "heat", "warming", "hot", "cold", "climate"],
        "method": "Day-weighted season mean -> Sen's slope + Mann-Kendall",
    },
    {
        "id": "RH2M", "name": "Relative humidity at 2 m", "category": "Humidity", "api_unit": "%",
        "out_unit": "%", "agg": "mean_days", "relative": False, "enabled": True,
        "source": "NASA POWER (MERRA-2)",
        "description": "Near-surface relative humidity; day-weighted season mean.",
        "coverage": "1981 - near real-time", "resolution": "~0.5 deg lat x 0.625 deg lon, monthly",
        "keywords": ["humidity", "moisture", "muggy", "air"],
        "method": "Day-weighted season mean -> Sen's slope + Mann-Kendall",
    },
    {
        "id": "WS10M", "name": "Wind speed at 10 m", "category": "Wind", "api_unit": "m/s",
        "out_unit": "m/s", "agg": "mean_days", "relative": True, "enabled": True,
        "source": "NASA POWER (MERRA-2)",
        "description": "Near-surface wind speed; day-weighted season mean.",
        "coverage": "1981 - near real-time", "resolution": "~0.5 deg lat x 0.625 deg lon, monthly",
        "keywords": ["wind", "storm", "breeze", "gust"],
        "method": "Day-weighted season mean -> Sen's slope + Mann-Kendall",
    },
    {
        "id": "MODIS_NDVI", "name": "Vegetation greenness (NDVI)", "category": "Vegetation", "api_unit": "-",
        "out_unit": "index", "agg": "mean_days", "relative": False, "enabled": False,
        "source": "NASA MODIS MOD13Q1 (planned)",
        "description": "Future expansion: vegetation greenness trends from MODIS.",
        "coverage": "2000 - present", "resolution": "250 m, 16-day",
        "keywords": ["vegetation", "green", "forest", "crop", "ndvi"],
        "method": "Planned",
    },
]

SEASONS = {
    "ANNUAL": {"name": "Annual (Jan-Dec)", "months": list(range(1, 13))},
    "JJAS": {"name": "Monsoon (Jun-Sep)", "months": [6, 7, 8, 9]},
    "MAM": {"name": "Pre-monsoon (Mar-May)", "months": [3, 4, 5]},
    "OND": {"name": "Post-monsoon (Oct-Dec)", "months": [10, 11, 12]},
    "JF": {"name": "Winter (Jan-Feb)", "months": [1, 2]},
}


def get_variable(vid):
    for v in VARIABLES:
        if v["id"] == vid:
            return v
    return None
