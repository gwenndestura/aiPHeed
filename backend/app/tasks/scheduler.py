"""
app/tasks/scheduler.py
-----------------------
Rule 1 — Quarter Self-Update.

"The pipeline will automatically retrain LightGBM each quarter and will
generate forecasts at the empirically validated lead time established during
model evaluation, staging all outputs for mandatory review before publication."

APScheduler triggers the quarterly cycle (Section 3.1, Deploy phase; Section
3.5; the Automatic Scheduler actor in Figure 3.6.1). The scheduler runs the
data collection step automatically on a pre-scheduled date and requires no
human initialization.

What the job does NOT do is publish. Every forecast and every alert it produces
enters the review queue as STAGED. An administrator at DA Region IV-A
confirms or rejects each one before it reaches the dashboard — the two-step
review of Figure 3.6.3, which guarantees no forecast or warning appears
publicly without human decision-making.

Usage:
    from app.tasks.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()      # called from the FastAPI lifespan
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_scheduler = None

# The pipeline runs shortly after each quarter closes, once the source agencies
# have published that quarter's releases: the 15th of January, April, July and
# October. The paper (p.59) says 02:00 Philippine time; the code default stays
# 03:00 and a deployment sets AIPHEED_QUARTERLY_CRON_HOUR=2
# (deploy/scheduler.env.example).
CRON_MONTHS = os.getenv("AIPHEED_QUARTERLY_CRON_MONTHS", "1,4,7,10").strip()
CRON_DAY = os.getenv("AIPHEED_QUARTERLY_CRON_DAY", "15").strip()
CRON_HOUR = os.getenv("AIPHEED_QUARTERLY_CRON_HOUR", "3").strip()

JOB_ID = "aipheed_quarterly_cycle"

# Off by default so importing the app in a test or a script does not start a
# background thread. Set AIPHEED_ENABLE_SCHEDULER=1 in the deployed environment.
ENABLED = os.getenv("AIPHEED_ENABLE_SCHEDULER", "0").strip() == "1"

# Copied into the temporary root of a dry run: everything run_cycle reads or writes under its root.
DRY_RUN_COPY = ("config", "data/inbox", "data/outcomes", "data/ledger", "data/quarterly_runs",
                "data/quarterly_store", "data/evidence_status_derived.json", "data/cycle_log.jsonl")


def dry_run_default() -> bool:
    return os.getenv("AIPHEED_SCHEDULER_DRY_RUN", "0").strip() == "1"


def run_cycle_dry(root: Path | str = ".", now=None) -> dict:
    """
    One quarterly cycle in a temporary copy of `root`'s config and pipeline data (DRY_RUN_COPY): the same code path
    as the scheduled job (app.quarterly.cycle.run_cycle with the forecaster and news loader of
    scripts.quarterly_update), so a deployment can check the cycle without changing its files. Nothing under
    `root` is written; the served record (data/<AIPHEED_RECORD>/) is neither read nor written by the cycle.
    Returns the cycle report plus "dry_run": True and the temporary root (deleted afterwards).
    """
    import shutil
    import tempfile

    import pandas as pd

    from app.quarterly.cycle import run_cycle
    from app.quarterly.forecaster_v2 import make_pcf_forecaster
    from scripts.quarterly_update import news_loader

    root = Path(root)
    with tempfile.TemporaryDirectory(prefix="aipheed_cycle_dry_") as tmp:
        tmp_root = Path(tmp)
        for rel in DRY_RUN_COPY:
            src, dst = root / rel, tmp_root / rel
            if src.is_dir():
                shutil.copytree(src, dst)
            elif src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        report = run_cycle(tmp_root, now=pd.Timestamp(now) if now is not None else None,
                           forecaster=lambda ev: make_pcf_forecaster(ev), news_loader=news_loader)
        report = {**report, "dry_run": True, "root": str(tmp_root)}
    logger.info("Quarterly cycle dry run: update status %s; nothing written under %s.",
                (report.get("update") or {}).get("status"), root.resolve())
    return report


def run_quarterly_cycle(dry_run: bool | None = None) -> dict:
    """
    One quarterly cycle, in the order Figure 3.6.2 lays out.

    Both data tracks are collected, the NLP track is scored and aggregated, the
    two are fused, the model is retrained, forecasts are produced at the
    Maximum Reliable Lead Time, SHAP attributions are computed, province
    probabilities are disaggregated to the 142 LGUs, and any province breaching
    its rolling alert threshold is staged for review.

    Returns the run summary produced by the pipeline runner. With dry_run (or
    AIPHEED_SCHEDULER_DRY_RUN=1) the cycle runs in a temporary copy instead
    (run_cycle_dry) and nothing is written.
    """
    if dry_run if dry_run is not None else dry_run_default():
        return run_cycle_dry()
    # E28 fix: this imported scripts.run_quarterly_pipeline, which does not exist in the repository, so every
    # scheduled run would have raised ImportError. The automatic cycle is scripts.quarterly_update `cycle` (E27).
    from scripts.quarterly_update import main as quarterly_main

    logger.info("Quarterly cycle starting (Rule 1, Quarter Self-Update).")
    code = quarterly_main(["cycle"])
    summary = {"exit_code": code, "forecasts_staged": None, "alerts_staged": None}
    logger.info(
        "Quarterly cycle complete: %s forecasts staged, %s alerts staged. "
        "Nothing is published until an administrator confirms it.",
        summary.get("forecasts_staged"), summary.get("alerts_staged"),
    )
    return summary


REBUILD_JOB_ID = "aipheed_rebuild_served_record"
# Rule 1, retraining: off by default. With AIPHEED_REBUILD_RECORD=1 the served E49-family record is rebuilt each
# quarter (scripts/rebuild_served_record.py) into data/rebuild/<YYYYMMDD>/ -- never data/e49/; promoting it is a
# separate human decision. An hour after the quarterly cycle by default.
REBUILD_ENABLED = os.getenv("AIPHEED_REBUILD_RECORD", "0").strip() == "1"
REBUILD_CRON_HOUR = os.getenv("AIPHEED_REBUILD_CRON_HOUR", "4").strip()


def run_rebuild_record(dry_run: bool | None = None) -> dict:
    """Rebuild the served record for the current origin (scripts/rebuild_served_record.rebuild). With dry_run (or
    AIPHEED_SCHEDULER_DRY_RUN=1) it builds in a temporary directory that is deleted afterwards."""
    from scripts.rebuild_served_record import rebuild

    dry = dry_run if dry_run is not None else dry_run_default()
    res = rebuild(dry_run=dry)
    summary = {k: res[k] for k in ("out_dir", "dry_run", "origin", "forecast_quarter", "content_sha256")}
    logger.info("Served-record rebuild (%s): %s", "dry run" if dry else "written", summary)
    return summary


NEWS_JOB_ID = "aipheed_news_incremental"
# Daily at 02:00 PHT: active-quarter news is collected throughout the quarter, not only after it ends.
NEWS_CRON_HOUR = "2"


def run_news_incremental() -> dict:
    """E28: daily incremental news collection for the active quarter (and the just-closed quarter during the first
    45 days of a new one, for late-indexed articles), then retry of failed windows, then scoring of new articles.
    Quarters after config/authorization.json's authorized_until are refused by the collector, not collected."""
    from scripts.news_collect import main as news_main

    out = {"incremental": news_main(["incremental"])}
    out["retry_failed"] = news_main(["backfill"])          # idempotent: only unfinished authorized windows
    out["score"] = news_main(["score"])
    logger.info("News incremental run: %s", out)
    return out


def start_scheduler():
    """
    Start the APScheduler background scheduler and register the quarterly job.

    Returns the scheduler, or None when it is disabled or APScheduler is not
    installed — the API still serves published forecasts either way.
    """
    global _scheduler

    if not ENABLED:
        logger.info(
            "Scheduler disabled (AIPHEED_ENABLE_SCHEDULER is not 1). The "
            "quarterly cycle can still be run by hand with "
            "scripts/run_quarterly_pipeline.py."
        )
        return None

    if _scheduler is not None:
        return _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler is not installed — the quarterly cycle will not run "
            "automatically. Install apscheduler or run the pipeline by hand."
        )
        return None

    _scheduler = BackgroundScheduler(timezone="Asia/Manila")
    _scheduler.add_job(
        run_quarterly_cycle,
        trigger=CronTrigger(month=CRON_MONTHS, day=CRON_DAY, hour=CRON_HOUR),
        id=JOB_ID,
        name="aiPHeed quarterly pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if REBUILD_ENABLED:
        _scheduler.add_job(
            run_rebuild_record,
            trigger=CronTrigger(month=CRON_MONTHS, day=CRON_DAY, hour=REBUILD_CRON_HOUR),
            id=REBUILD_JOB_ID,
            name="aiPHeed served-record rebuild (not served)",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    _scheduler.add_job(
        run_news_incremental,
        trigger=CronTrigger(hour=NEWS_CRON_HOUR, minute=0),
        id=NEWS_JOB_ID,
        name="aiPHeed daily news collection",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: quarterly cycle at %s:00 on day %s of months %s "
        "(Asia/Manila).", CRON_HOUR, CRON_DAY, CRON_MONTHS,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler on application shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
