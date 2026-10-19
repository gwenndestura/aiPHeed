"""E62 r7: API load-time measurement of the dashboard's request set, before/after, E58 mode and the E38 default.

For each (mode, variant): start a fresh server (r7_serve_variant.py) on a free port, wait until /api/v1/config answers,
then
  * cold, parallel: the dashboard's first-screen requests issued at once (as the browser does), wall time per request
    and until the forecast (provinces + region forecast) is in, and until all are in;
  * warm: 5 repeats of the same parallel batch, median per request;
  * news alone (region + province) timed separately;
  * payload bytes per request.
The server is stopped by its own PID afterwards. No deployment is measured (none is reachable from here).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E62_Final_System_Audit/runner/r7_measure.py
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

E62 = Path(__file__).resolve().parents[1]
BACKEND = E62.parents[2] / "backend"
PY = str(BACKEND / "venv" / "Scripts" / "python.exe")
SERVE = str(E62 / "runner" / "r7_serve_variant.py")
Q = "2027-Q1"
FIRST = [("config", "/api/v1/config"), ("quarters", "/api/v1/quarters?horizon=nowcast"),
         ("provinces", f"/api/v1/provinces?quarter={Q}&horizon=nowcast"),
         ("forecast_region", f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}&horizon=nowcast"),
         ("timeseries_region", "/api/v1/forecast/timeseries?scope=region&id=calabarzon&horizon=nowcast"),
         ("explain_region", f"/api/v1/explainability?scope=region&id=calabarzon&quarter={Q}"),
         ("news_region", f"/api/v1/news?scope=region&id=calabarzon&quarter={Q}&page=1&pageSize=10"),
         ("forecast_laguna", f"/api/v1/forecast?scope=province&id=laguna&quarter={Q}&horizon=nowcast"),
         ("timeseries_laguna", "/api/v1/forecast/timeseries?scope=province&id=laguna&horizon=nowcast"),
         ("explain_laguna", f"/api/v1/explainability?scope=province&id=laguna&quarter={Q}"),
         ("news_laguna", f"/api/v1/news?scope=province&id=laguna&quarter={Q}&page=1&pageSize=10"),
         ("municipalities_laguna", f"/api/v1/provinces/laguna/municipalities?quarter={Q}")]
FORECAST_KEYS = {"provinces", "forecast_region"}


def fetch(base, item):
    name, path = item
    t0 = time.perf_counter()
    with urllib.request.urlopen(base + path, timeout=120) as r:
        body = r.read()
        status = r.status
    return name, round((time.perf_counter() - t0) * 1000, 1), status, len(body), t0


def batch(base):
    t0 = time.perf_counter()
    with ThreadPoolExecutor(len(FIRST)) as ex:
        res = list(ex.map(lambda it: fetch(base, it), FIRST))
    done = {n: round((s + ms / 1000 - t0) * 1000, 1) for n, ms, _, _, s in res}
    return ({n: ms for n, ms, *_ in res}, {n: b for n, _, _, b, _ in res}, {n: st for n, _, st, _, _ in res},
            max(done[k] for k in FORECAST_KEYS), max(done.values()))


def run(mode, variant, port):
    env = dict(os.environ)
    env.pop("AIPHEED_NOW", None)
    if mode == "e38":
        env.pop("AIPHEED_LEAD2_MODEL", None)
    else:
        env["AIPHEED_LEAD2_MODEL"] = mode
    t_start = time.perf_counter()
    proc = subprocess.Popen([PY, "-B", SERVE, variant, str(port)], cwd=BACKEND, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        while True:
            try:
                urllib.request.urlopen(base + "/api/v1/health", timeout=2).read()
                break
            except Exception:
                if time.perf_counter() - t_start > 180:
                    raise
                time.sleep(0.25)
        startup = round((time.perf_counter() - t_start) * 1000)
        cold, size, status, cold_fc, cold_all = batch(base)
        warm = [batch(base) for _ in range(5)]
        news = []
        for _ in range(5):
            news.append({n: fetch(base, it)[1] for n, it in [("news_region", FIRST[6]), ("news_laguna", FIRST[10])]})
        return {"mode": mode, "variant": variant, "server_start_ms": startup, "cold_ms": cold, "cold_until_forecast_ms": cold_fc,
                "cold_until_all_ms": cold_all, "warm_median_ms": {k: statistics.median(w[0][k] for w in warm) for k in cold},
                "warm_until_forecast_median_ms": statistics.median(w[3] for w in warm),
                "warm_until_all_median_ms": statistics.median(w[4] for w in warm),
                "news_alone_median_ms": {k: statistics.median(n[k] for n in news) for k in news[0]},
                "bytes": size, "status": status}
    finally:
        proc.terminate()
        try:
            proc.wait(15)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    out = []
    for i, (mode, variant) in enumerate([("e58", "before"), ("e58", "after"), ("e38", "before"), ("e38", "after")]):
        r = run(mode, variant, 8162 + i)
        out.append(r)
        print(mode, variant, "start", r["server_start_ms"], "cold forecast", r["cold_until_forecast_ms"], "cold all",
              r["cold_until_all_ms"], "warm all", r["warm_until_all_median_ms"], flush=True)
    (E62 / "out" / "r7_performance.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
