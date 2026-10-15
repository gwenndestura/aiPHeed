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

logger = logging.getLogger(__name__)

_scheduler = None

# The pipeline runs shortly after each quarter closes, once the source agencies
# have published that quarter's releases. 03:00 on the 15th of January, April,
# July and October — the first month of each quarter, mid-month.
CRON_MONTHS = "1,4,7,10"
CRON_DAY = "15"
CRON_HOUR = "3"

JOB_ID = "aipheed_quarterly_cycle"

# Off by default so importing the app in a test or a script does not start a
# background thread. Set AIPHEED_ENABLE_SCHEDULER=1 in the deployed environment.
ENABLED = os.getenv("AIPHEED_ENABLE_SCHEDULER", "0").strip() == "1"


def run_quarterly_cycle() -> dict:
    """
    One quarterly cycle, in the order Figure 3.6.2 lays out.

    Both data tracks are collected, the NLP track is scored and aggregated, the
    two are fused, the model is retrained, forecasts are produced at the
    Maximum Reliable Lead Time, SHAP attributions are computed, province
    probabilities are disaggregated to the 142 LGUs, and any province breaching
    its rolling alert threshold is staged for review.

    Returns the run summary produced by the pipeline runner.
    """
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
