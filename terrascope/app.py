# TerraScope - Earth System Trend Discovery (Flask app).
# Run:  python app.py     then open http://127.0.0.1:5000
# Code generated with AI assistance (Claude, Anthropic).
import threading
import uuid
from collections import OrderedDict

from flask import Flask, jsonify, render_template, request

import config
from core.catalog import SEASONS, VARIABLES
from core.engine import InputError, run_analysis, validate
from core.regions import ZONES

app = Flask(__name__)
JOBS = OrderedDict()          # job_id -> state (in memory; fine for a single-user demo)
LOCK = threading.Lock()


@app.get("/")
def index():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


@app.get("/api/catalog")
def catalog():
    return jsonify({
        "variables": VARIABLES,
        "seasons": [{"id": k, **v} for k, v in SEASONS.items()],
        "zones": [{"name": n, "desc": z["desc"], "points": [{"lat": a, "lon": b, "label": c} for a, b, c in z["points"]]}
                  for n, z in ZONES.items()],
        "first_year": config.FIRST_YEAR, "last_year": config.LAST_YEAR,
        "alpha": config.ALPHA, "synthetic": config.SYNTHETIC,
    })


def _worker(job_id, params):
    def progress(done, total):
        with LOCK:
            JOBS[job_id].update(done=done, total=total)
    try:
        res = run_analysis(params, progress)
        with LOCK:
            JOBS[job_id].update(status="done", result=res)
    except Exception as e:  # report any failure to the UI instead of dying silently
        with LOCK:
            JOBS[job_id].update(status="error", error=str(e))


@app.post("/api/analyze")
def analyze():
    params = request.get_json(silent=True) or {}
    try:
        validate(params)
    except (InputError, ValueError) as e:
        return jsonify(error=str(e)), 400
    job_id = uuid.uuid4().hex[:12]
    with LOCK:
        JOBS[job_id] = {"status": "running", "done": 0, "total": 0}
        while len(JOBS) > 20:
            JOBS.popitem(last=False)
    threading.Thread(target=_worker, args=(job_id, params), daemon=True).start()
    return jsonify(job=job_id)


@app.get("/api/job/<job_id>")
def job(job_id):
    with LOCK:
        j = JOBS.get(job_id)
        if not j:
            return jsonify(error="Unknown job"), 404
        return jsonify(j)


if __name__ == "__main__":
    if config.SYNTHETIC:
        print("\n*** SYNTHETIC TEST MODE: data is FAKE and not from NASA ***\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
