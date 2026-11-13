"""
The automatic forecasting cycle of the served model. Safe to run as often as you like (daily by the scheduler): it does nothing
unless something is due.

    1  period     the Philippine quarter now and the issue that should be served (app.final.period)
    2  lock       one run at a time (lock file; a lock older than 6 hours is treated as abandoned)
    3  sources    fetch the official sources that are due (app.final.sources); failures keep the previous data
    4  issue      only when the current issue is not yet in the history:
                    a. data stage: news collection and scoring, panel rebuild and FINAL's extra inputs, all as of the issue's
                       information cut-off (the issue day, exclusive)
                    b. forecast: frozen FINAL model, Leads 1..max_lead (app.final.issue)  -> data/final/issues/<issue>/
                    c. history: one record per province x target quarter (app.final.history), never overwritten
       A new survey round (training rows changed) stops the issue with status "retraining required"; the last valid issue stays.
    5  log        data/final/runs.jsonl (every run, its stages, status and error)

    python -m app.final.cycle run [--now 2027-02-01T08:00] [--skip-data] [--skip-sources]
    python -m app.final.cycle status
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.final import history as HI
from app.final import period as PD
from app.paths import BACKEND_DIR

ROOT = BACKEND_DIR / "data" / "final"
RUNS = ROOT / "runs.jsonl"
LOCK = ROOT / ".cycle.lock"
LOCK_MAX_AGE_S = 6 * 3600


class Locked(RuntimeError):
    pass


def _acquire(lock: Path = LOCK) -> int:
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < LOCK_MAX_AGE_S:
            raise Locked("another forecasting run is in progress")
        lock.unlink(missing_ok=True)                              # abandoned by a crashed run
        return os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)


def _release(fd: int, lock: Path = LOCK) -> None:
    os.close(fd)
    lock.unlink(missing_ok=True)


def _log(rec: dict, runs: Path = RUNS) -> None:
    runs.parent.mkdir(parents=True, exist_ok=True)
    with open(runs, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


def _sub(code: str, as_of: str, timeout: int = 7200) -> str:
    """Run a data-stage step in a fresh interpreter with the issue's as-of date (the panels read it at import)."""
    env = {**os.environ, "AIPHEED_LIVE_ASOF": as_of, "PYTHONPATH": str(BACKEND_DIR)}
    p = subprocess.run([sys.executable, "-c", code], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"data step failed: {(p.stderr or p.stdout)[-1500:]}")
    return p.stdout


def data_stage(as_of: str, published: str) -> dict:
    """News collection and scoring, panel rebuild and FINAL's extra inputs as of the issue cut-off (existing E168 refresh steps)."""
    out = {}
    out["news"] = _sub(f"import json; from app.e168 import live_refresh as R; print(json.dumps(R.news_pipeline('{as_of}', '{published}'), default=str))", as_of)[-2000:]
    out["panels"] = _sub("import json; from app.e168 import live_refresh as R; print(json.dumps(R.rebuild_panels(), default=str))", as_of)[-2000:]
    out["final_inputs"] = _sub("import runpy; runpy.run_module('app.hcw.inputs', run_name='__main__')", as_of)[-500:]
    return out


def run(now=None, skip_sources: bool = False, skip_data: bool = False, *, build_issue=None, update_sources=None, refresh_data=None,
        ledger: Path | None = None, runs: Path = RUNS, lock: Path = LOCK) -> dict:
    """One cycle. The keyword-only hooks exist for tests (a controllable clock and stand-in stages); production uses the defaults."""
    per = PD.period(now)
    model = per["model_id"]
    rec = {"run_id": uuid.uuid4().hex[:12], "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "now_ph": per["now_ph"], "current_quarter": per["current_quarter"], "issue_quarter": per["issue_quarter"], "stages": {}}
    try:
        fd = _acquire(lock)
    except Locked as e:
        rec.update(status="skipped", reason=str(e))
        _log(rec, runs)
        return rec
    try:
        if not skip_sources:
            from app.final import sources as SR
            rec["stages"]["sources"] = (update_sources or SR.update)(now)
        issue = per["issue_quarter"]
        if HI.has_issue(model, issue, ledger):
            rec["status"] = "up to date"
            rec["reason"] = f"issue {issue} is already recorded; next issue {per['next_issue_quarter']} on {per['next_issue_date']}"
        else:
            as_of = PD.issue_datetime(issue).date().isoformat()
            published = PD.now_ph(now).date().isoformat()
            os.environ["AIPHEED_LIVE_ASOF"] = as_of
            os.environ.pop("AIPHEED_LIVE_PUBLISHED", None)     # strict: only figures online before the cut-off (issue.check_information_rule)
            if not skip_data:
                rec["stages"]["data"] = (refresh_data or data_stage)(as_of, published)
            if build_issue is not None:
                issue_dir = build_issue(issue)
            else:
                from app.final import issue as IS
                d = IS.ISSUES / issue
                issue_dir = d if d.exists() else IS.build(issue)      # a built but unrecorded issue (crash after build) is recorded, not rebuilt
            from app.final import issue as IS
            rec["stages"]["history"] = HI.record_issue(IS.ledger_rows(Path(issue_dir)), ledger)
            rec["issue_dir"] = str(issue_dir)
            rec["status"] = "issued"
    except Exception as e:                                       # noqa: BLE001 - recorded; the last valid issue stays served
        from app.final.issue import RetrainingRequired
        rec["status"] = "retraining required" if isinstance(e, RetrainingRequired) else "failed"
        rec["error"] = f"{type(e).__name__}: {e}"[:2000]
        rec["trace"] = traceback.format_exc()[-1500:]
    finally:
        _release(fd, lock)
        rec["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _log(rec, runs)
    return rec


def runs_log(runs: Path = RUNS) -> list[dict]:
    if not runs.exists():
        return []
    return [json.loads(x) for x in runs.read_text(encoding="utf-8").splitlines() if x.strip()]


def status(now=None, ledger: Path | None = None, runs: Path = RUNS) -> dict:
    """What is served and how fresh it is. Stale = the issue that should be served now is not in the history yet."""
    per = PD.period(now)
    model = per["model_id"]
    served = HI.latest_issue(model, ledger)
    log = runs_log(runs)
    last = log[-1] if log else None
    last_ok = next((r for r in reversed(log) if r.get("status") in ("issued", "up to date")), None)
    last_issued = next((r for r in reversed(log) if r.get("status") == "issued"), None)
    gen = None
    if served:
        g = [r["generated_utc"] for r in HI.forecasts(ledger) if r["model_id"] == model and r["issue_quarter"] == served]
        gen = max(g) if g else None
    stale = served != per["issue_quarter"]
    return {**per, "served_issue_quarter": served, "served_generated_utc": gen, "stale": stale,
            "stale_reason": (f"the {per['issue_quarter']} issue has not been generated yet; the {served} issue (generated {gen}) is shown"
                             if stale and served else ("no forecast has been issued yet" if stale else None)),
            "last_run": {k: last.get(k) for k in ("run_id", "started_utc", "status", "error", "issue_quarter")} if last else None,
            "last_successful_run_utc": last_ok["finished_utc"] if last_ok else None,
            "last_issue_run_utc": last_issued["finished_utc"] if last_issued else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status"])
    ap.add_argument("--now")
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--skip-sources", action="store_true")
    a = ap.parse_args()
    out = run(a.now, a.skip_sources, a.skip_data) if a.cmd == "run" else status(a.now)
    print(json.dumps(out, indent=1, default=str))
