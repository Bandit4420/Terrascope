# TerraScope config.
# NOTE: Code in this project was generated with AI assistance (Claude, Anthropic).
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")

POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
COMMUNITY = "AG"

FIRST_YEAR = 1981                    # start of the NASA POWER / MERRA-2 monthly record
LAST_YEAR = date.today().year - 1    # last *complete* calendar year
ALPHA = 0.05                         # significance threshold
MIN_VALID_YEARS = 10                 # hard minimum to run any trend test
WARN_YEARS = 20                      # below this, show a short-record warning

WORKERS = 3                          # parallel NASA requests (be polite to the API)

# TEST MODE ONLY: fake data so the app can be tried offline.
# Set TERRASCOPE_SYNTHETIC=1 to enable. Results are NOT NASA data and are bannered as such.
SYNTHETIC = os.environ.get("TERRASCOPE_SYNTHETIC", "0") == "1"
