"""
app/services/pipeline_runs.py
------------------------------
The Admin's "trigger the quarterly pipeline" use case (Figure 3.6.1).

The Use Case Diagram gives the administrator a Run Quarterly Pipeline case with
an «include» relationship to Collect Data, "since no forecast can be produced
without first gathering that quarter's news and government data". The Automatic
Scheduler runs the same cycle on its own schedule (Rule 1); this is the manual
path for the same work, not a second pipeline.

A cycle takes far longer than a request, so the endpoint starts it on a worker
thread and returns immediately. Progress is whatever the run writes to
`data/processed/pipeline_run.json`, which is the same file the scheduled path
writes, so a reader cannot tell the two apart and does not need to.

Nothing here publishes. The cycle stages its forecasts and alerts for review,
exactly as the scheduled path does.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SUMMARY_PATH = Path("data/processed/pipeline_run.json")

_lock = threading.Lock()
_thread: threading.Thread | None = None
_state: dict = {"status": "idle", "started_at": None, "started_by": None,
                "finished_at": None, "error": None}


def status() -> dict:
    """Current run state, plus the last completed run's summary if there is one."""
    with _lock:
        out = dict(_state)
    out["running"] = out["status"] == "running"
    if SUMMARY_PATH.exists():
        try:
            out["last_run"] = json.loads(SUMMARY_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            out["last_run"] = None
    else:
        out["last_run"] = None
    return out


def _run(skip_collect: bool, skip_train: bool, quarter: str | None) -> None:
    from scripts.run_quarterly_pipeline import run_pipeline

    try:
        run_pipeline(skip_collect=skip_collect, skip_train=skip_train, quarter=quarter)
        with _lock:
            _state["status"] = "finished"
            _state["error"] = None
    except Exception as exc:                      # noqa: BLE001 - reported, not raised
        logger.exception("quarterly pipeline failed")
        with _lock:
            _state["status"] = "failed"
            _state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _lock:
            _state["finished_at"] = datetime.now(timezone.utc).isoformat()


def start(actor_email: str, skip_collect: bool = False,
          skip_train: bool = False, quarter: str | None = None) -> dict:
    """
    Start a cycle on a worker thread.

    Raises RuntimeError when one is already running: two concurrent cycles would
    write the same parquets and the same review queue.
    """
    global _thread
    with _lock:
        if _state["status"] == "running":
            raise RuntimeError(
                "A quarterly pipeline run is already in progress "
                f"(started {_state['started_at']} by {_state['started_by']})."
            )
        _state.update(status="running", error=None, finished_at=None,
                      started_at=datetime.now(timezone.utc).isoformat(),
                      started_by=actor_email)

    _thread = threading.Thread(
        target=_run, args=(skip_collect, skip_train, quarter),
        name="aipheed-quarterly-pipeline", daemon=True,
    )
    _thread.start()
    logger.info("quarterly pipeline started by %s", actor_email)
    return status()
