"""
app/tasks/scheduler.py
-----------------------
APScheduler wiring for the quarterly self-update (Chapter III, Rule 1).

Started and stopped by the FastAPI lifespan in app/main.py. One cron job runs
the pipeline (app/tasks/quarterly_pipeline.py) in a child process, so the
multi-gigabyte XLM-RoBERTa model and the Optuna search never live inside the
API's memory and a crash in either cannot take the API down. When the child
finishes, this process publishes the result:

  * clears every cached forecast, explanation and the loaded model, so the
    next request is served by whatever model is now on disk, and
  * stages the newest quarter's province forecasts for DA review (STAGED rows
    in review_records), exactly as opening the review queue would.

An administrator can also start a run on demand (POST /api/v1/admin/pipeline/run).
The same file lock the child takes means a manual run, a scheduled run and a
CLI run can never overlap, even across uvicorn workers.

Limitation: the job store is in memory. If the server is down at the scheduled
moment, that quarter's run waits until an administrator starts it (or until
the next quarter); it is not replayed automatically on restart.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.tasks import quarterly_pipeline as qp

logger = logging.getLogger(__name__)

JOB_ID = "quarterly_pipeline"

_scheduler: BackgroundScheduler | None = None
_thread_lock = threading.Lock()


def build_trigger() -> CronTrigger:
    return CronTrigger.from_crontab(settings.PIPELINE_CRON, timezone=settings.PIPELINE_TIMEZONE)


def start() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("scheduler: disabled (SCHEDULER_ENABLED=false)")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    sched = BackgroundScheduler(timezone=settings.PIPELINE_TIMEZONE)
    sched.add_job(
        run_now, trigger=build_trigger(), id=JOB_ID, kwargs={"trigger": "scheduled"},
        max_instances=1, coalesce=True, misfire_grace_time=6 * 3600, replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    logger.info("scheduler: quarterly pipeline '%s' (%s), next run %s",
                settings.PIPELINE_CRON, settings.PIPELINE_TIMEZONE, next_run_time())
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def next_run_time() -> datetime | None:
    if _scheduler is None:
        return None
    job = _scheduler.get_job(JOB_ID)
    return job.next_run_time if job else None


def is_running() -> bool:
    return _thread_lock.locked() or qp.is_running()


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def run_now(trigger: str = "manual") -> str:
    """Run the pipeline synchronously (the scheduler calls this on its own thread)."""
    if not _thread_lock.acquire(blocking=False):
        raise qp.PipelineBusy("A quarterly pipeline run is already in progress.")
    run_id = qp.new_run_id()
    try:
        logger.info("pipeline %s: starting (%s)", run_id, trigger)
        env = {**os.environ, "PYTHONPATH": str(qp.ROOT)}
        cmd = [sys.executable, "-m", "app.tasks.quarterly_pipeline",
               "--trigger", trigger, "--run-id", run_id]
        try:
            proc = subprocess.run(cmd, cwd=qp.ROOT, env=env,
                                  timeout=settings.PIPELINE_TIMEOUT_SECONDS)
            logger.info("pipeline %s: child exited %s", run_id, proc.returncode)
        except subprocess.TimeoutExpired:
            logger.error("pipeline %s: timed out after %ss", run_id, settings.PIPELINE_TIMEOUT_SECONDS)
        publish(run_id)
    finally:
        _thread_lock.release()
    return run_id


def start_in_background(trigger: str = "manual") -> None:
    """For the admin endpoint: refuse at once if busy, otherwise run on a thread."""
    if is_running():
        raise qp.PipelineBusy("A quarterly pipeline run is already in progress.")
    threading.Thread(target=_safe_run, args=(trigger,), name="pipeline-manual",
                     daemon=True).start()


def _safe_run(trigger: str) -> None:
    try:
        run_now(trigger)
    except qp.PipelineBusy:
        logger.warning("pipeline: manual start lost a race with another run")
    except Exception:
        logger.exception("pipeline: run raised")


# ---------------------------------------------------------------------------
# Publishing into the running API
# ---------------------------------------------------------------------------

def reset_serving_caches() -> None:
    """Drop every cached model, forecast and explanation so disk is re-read."""
    from app.ml.inference.thesis_predictor import ThesisPredictor
    from app.services import dashboard as svc

    ThesisPredictor._instance = None
    for value in vars(svc).values():
        if isinstance(value, functools._lru_cache_wrapper):
            value.cache_clear()


async def _stage_latest_quarter() -> str:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.services import dashboard as svc
    from app.services import review as rv

    # A fresh engine: this runs on its own event loop, and pooled aiosqlite
    # connections cannot cross loops.
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        quarter = svc.latest_quarter()
        async with session() as db:
            await rv.ensure_rows(db, quarter)
        return quarter
    finally:
        await engine.dispose()


def publish(run_id: str) -> None:
    record = qp.load_latest_run() or {}
    if record.get("run_id") != run_id:
        logger.error("pipeline %s: no run record written; nothing published", run_id)
        return
    detail, status = "", "ok"
    try:
        reset_serving_caches()
        quarter = asyncio.run(_stage_latest_quarter())
        detail = (f"serving caches reloaded; {quarter} province forecasts staged "
                  "for DA review" + ("; new model in service" if record.get("model_promoted") else ""))
    except Exception as exc:
        logger.exception("pipeline %s: publish failed", run_id)
        detail, status = f"publish failed: {exc}"[:500], "warning"

    record.setdefault("stages", []).append(
        {"name": "publish", "status": status, "detail": detail, "seconds": 0.0})
    if status == "warning" and record.get("status") == "succeeded":
        record["status"] = "completed_with_warnings"
    record["published_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_record(record)


def _write_record(record: dict) -> None:
    import json
    payload = json.dumps(record, indent=2, default=str)
    qp.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (qp.RUNS_DIR / f"{record['run_id']}.json").write_text(payload, encoding="utf-8")
    (qp.RUNS_DIR / "latest.json").write_text(payload, encoding="utf-8")


def status() -> dict:
    nrt = next_run_time()
    return {
        "enabled": settings.SCHEDULER_ENABLED and _scheduler is not None,
        "schedule": settings.PIPELINE_CRON,
        "timezone": settings.PIPELINE_TIMEZONE,
        "nextRun": nrt.isoformat() if nrt else None,
        "running": is_running(),
        "lastRun": qp.load_latest_run(),
    }
