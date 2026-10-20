"""E63: objective ISO/IEC 25010 measurements of the API (performance efficiency, reliability). Report only.

    python -B backend/experiments/e63/runner/loadtest.py      (from the repo root; about 5 minutes)

Starts its OWN uvicorn (127.0.0.1:8011, one worker) with AIPHEED_RECORD=e49, AIPHEED_MAX_LEAD=1, a throwaway SQLite
database in the OS temp directory (never aipheed.db) and the rate limiter off (it would otherwise throttle the load
generator, a single client). Load: N concurrent users (10, 50, 100), each looping over the seven endpoints for 60 s,
after a 5 s warm-up. Reliability: 50 users for 60 s; the server is killed at 20 s and restarted at once; recovery time =
kill -> first successful response. Results -> backend/experiments/e63/E63_load.json.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

E63 = Path(__file__).resolve().parents[1]
BACKEND = E63.parents[1]
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
ENDPOINTS = {
    "provinces": "/api/v1/provinces?quarter=2026-Q4",
    "forecast_region": "/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4",
    "forecast_province": "/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q4",
    "ranking": "/api/v1/ranking?quarter=2026-Q4",
    "explainability": "/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q4",
    "municipalities": "/api/v1/provinces/quezon/municipalities?quarter=2026-Q4",
    "report_data": "/api/v1/report/data?type=trend&scope=region&from=2023-Q1",
}
LEVELS, DURATION, WARMUP = (10, 50, 100), 60.0, 5.0


def make_db() -> str:
    from sqlalchemy import create_engine

    sys.path.insert(0, str(BACKEND))
    from app.db.database import Base
    import app.db.models  # noqa: F401  (register the tables)

    f = Path(tempfile.gettempdir()) / "aipheed_e63_loadtest.db"
    if f.exists():
        f.unlink()
    eng = create_engine(f"sqlite:///{f}")
    Base.metadata.create_all(eng)
    eng.dispose()
    return f"sqlite+aiosqlite:///{f.as_posix()}"


def start_server(db_url: str) -> subprocess.Popen:
    env = dict(os.environ, AIPHEED_RECORD="e49", AIPHEED_MAX_LEAD="1", DATABASE_URL=db_url,
               RATE_LIMIT_ENABLED="false", ENABLE_API_DOCS="false", AIPHEED_ENABLE_SCHEDULER="0")
    return subprocess.Popen([str(BACKEND / "venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
                             "--host", "127.0.0.1", "--port", str(PORT), "--workers", "1", "--log-level", "warning"],
                            cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ready(timeout=120.0) -> float:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        try:
            if httpx.get(BASE + "/api/v1/health", timeout=2).status_code == 200:
                return time.perf_counter() - t0
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise SystemExit("server did not start")


async def run_load(users: int, duration: float, warmup: float, on_tick=None) -> list[dict]:
    """Each user loops over the endpoints (offset by its index). Returns per-request records after the warm-up."""
    recs: list[dict] = []
    names = list(ENDPOINTS)
    start = time.perf_counter()
    end = start + warmup + duration
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)

    async with httpx.AsyncClient(base_url=BASE, timeout=30.0, limits=limits) as client:
        async def user(i: int):
            k = i
            while time.perf_counter() < end:
                name = names[k % len(names)]
                k += 1
                t0 = time.perf_counter()
                try:
                    r = await client.get(ENDPOINTS[name])
                    ok, code = r.status_code == 200, r.status_code
                except httpx.HTTPError as ex:
                    ok, code = False, type(ex).__name__
                t1 = time.perf_counter()
                if t0 - start >= warmup:
                    recs.append({"ep": name, "t": t0 - start - warmup, "ms": (t1 - t0) * 1000, "ok": ok, "code": code})
                if not ok:
                    await asyncio.sleep(0.05)

        tasks = [asyncio.create_task(user(i)) for i in range(users)]
        if on_tick:
            await on_tick(start + warmup)
        await asyncio.gather(*tasks)
    return recs


def pct(v, q):
    v = sorted(v)
    if not v:
        return None
    i = (len(v) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def summarise(recs, duration):
    out = {}
    for name in list(ENDPOINTS) + ["ALL"]:
        rs = recs if name == "ALL" else [r for r in recs if r["ep"] == name]
        ok = [r["ms"] for r in rs if r["ok"]]
        out[name] = {"requests": len(rs), "ok": len(ok), "error_rate": (1 - len(ok) / len(rs)) if rs else None,
                     "throughput_rps": len(ok) / duration,
                     "p50_ms": pct(ok, .50), "p95_ms": pct(ok, .95), "p99_ms": pct(ok, .99),
                     "mean_ms": statistics.fmean(ok) if ok else None,
                     "errors": sorted({str(r["code"]) for r in rs if not r["ok"]})}
    return out


def main():
    db = make_db()
    res = {"server": "uvicorn 1 worker, 127.0.0.1, AIPHEED_RECORD=e49, AIPHEED_MAX_LEAD=1, throwaway SQLite, "
                     "rate limiter off", "duration_s": DURATION, "warmup_s": WARMUP, "endpoints": ENDPOINTS,
           "levels": {}}
    srv = start_server(db)
    try:
        res["startup_s"] = wait_ready()
        for n in LEVELS:
            print("load", n, "users", flush=True)
            recs = asyncio.run(run_load(n, DURATION, WARMUP))
            res["levels"][str(n)] = summarise(recs, DURATION)
            a = res["levels"][str(n)]["ALL"]
            print(f"  {a['throughput_rps']:.1f} rps p50 {a['p50_ms']:.0f} p95 {a['p95_ms']:.0f} p99 {a['p99_ms']:.0f} "
                  f"err {a['error_rate']:.4f}", flush=True)

        # ---- reliability: kill at 20 s, restart at once
        print("reliability run", flush=True)
        state = {}

        async def chaos(t_start):
            nonlocal srv
            await asyncio.sleep(max(0.0, t_start + 20.0 - time.perf_counter()))
            state["kill_t"] = time.perf_counter() - t_start
            srv.kill()
            srv.wait()
            state["killed_at"] = time.perf_counter()
            srv = start_server(db)
            state["restart_issued_t"] = time.perf_counter() - t_start

        recs = asyncio.run(run_load(50, DURATION, WARMUP, on_tick=chaos))
        kill_t = state["kill_t"]
        after = sorted((r for r in recs if r["t"] > kill_t), key=lambda r: r["t"] + r["ms"] / 1000)
        first_ok = next((r for r in after if r["ok"]), None)
        recovery = (first_ok["t"] + first_ok["ms"] / 1000 - kill_t) if first_ok else None
        down = [r for r in recs if r["t"] > kill_t and (recovery is None or r["t"] < kill_t + recovery)]
        res["reliability"] = {"users": 50, "kill_at_s": kill_t, "recovery_s": recovery,
                              "requests_failed_during_outage": sum(not r["ok"] for r in down),
                              "summary": summarise(recs, DURATION),
                              "errors_before_kill": sum(not r["ok"] for r in recs if r["t"] < kill_t),
                              "errors_after_recovery": sum(not r["ok"] for r in recs
                                                           if recovery is not None and r["t"] > kill_t + recovery)}
        print("  recovery", recovery, flush=True)
    finally:
        srv.kill()
    (E63 / "E63_load.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("written", E63 / "E63_load.json")


if __name__ == "__main__":
    main()
