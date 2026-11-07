"""
Scheduled E168 refresh: when a new quarter begins, issue E168's forecast for the next quarter (exactly as
app.e168.history.one: only data published before the issue date) and stage E168 alert candidates for review.

Existing history files and the sealed 2027-Q1 forecast are never rewritten: a quarter is written only when it is missing.

    python -m app.e168.refresh            run once (what the scheduler calls)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

from app.fi5.target import qindex, qlabel

logger = logging.getLogger(__name__)


def next_target(today: date | None = None) -> str:
    """The quarter after the current calendar quarter (E168 forecasts one quarter ahead from the quarter's start)."""
    d = today or date.today()
    return qlabel(qindex(f"{d.year}-Q{(d.month - 1) // 3 + 1}") + 1)


def ensure_forecast(target: str) -> bool:
    """Write the E168 forecast for `target` if it is missing. Returns True if a new quarter was written."""
    from app.e144 import data as SWSD
    from app.e168 import history as H
    from app.e168 import lgbm as L
    from app.services import e166_serving as SRV

    if (H.HIST / f"{target}.json").exists():
        return False
    SW = L.sws_forecasts(SWSD.sws_quarterly(), qindex(target) - 1)
    H.one(target, SW)
    idx = H.HIST / "index.json"
    meta = json.loads(idx.read_text())
    meta["quarters"] = sorted(set(meta["quarters"]) | {target})
    meta["last"] = max(meta["quarters"])
    idx.write_text(json.dumps(meta, indent=1), newline="\n")
    SRV.quarters.cache_clear()
    SRV._q.cache_clear()
    logger.info("E168: issued forecast for %s", target)
    return True


async def _stage(quarter: str) -> dict:
    from app.db.database import AsyncSessionLocal
    from app.e168 import alerts as A

    async with AsyncSessionLocal() as db:
        res = await A.stage(db, quarter)
        await db.commit()
    return res


def run(today: date | None = None) -> dict:
    target = next_target(today)
    written = ensure_forecast(target)
    from app.services import e166_serving as SRV
    staged = asyncio.run(_stage(target)) if target in SRV.quarters() else {"staged": [], "existing": []}
    summary = {"target": target, "forecast_written": written, "alerts_staged": len(staged["staged"]),
               "alerts_existing": len(staged["existing"])}
    logger.info("E168 refresh: %s", summary)
    return summary


if __name__ == "__main__":
    print(run())
