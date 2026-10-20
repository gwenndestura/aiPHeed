"""
app/quarterly/target.py
-----------------------
The ONE place that decides which quarter the dashboard forecasts: the calendar quarter after the one in which the
dashboard is viewed, in Asia/Manila time. Every API, the map, the LGU ranking, explanations, alerts and the PDF ask
this function; nothing else computes a target.

Forecasts are issued at fixed quarter-start origins (00:00 PHT on the first day of the current quarter), so a
quarter has exactly one forecast record however often the page is refreshed. Information published after the origin
(for example a hunger round posted mid-quarter) enters at the next origin. Relative to the latest complete data
quarter the target is two quarters ahead (E37/E38 lead 2).

AIPHEED_MAX_LEAD (default 1) is the longest lead the system serves, counted from the latest complete data quarter.
At 1 the target is the current calendar quarter (the E36 one-quarter-ahead forecast) and lead-2 record rows (the E38
next-quarter forecast) are not served; AIPHEED_MAX_LEAD=2 restores the next-calendar-quarter target and those rows.

Tests and live end-to-end runs control the clock with the `now` argument or the AIPHEED_NOW environment variable
(an ISO timestamp; a naive value is read as Philippine time). Production never sets it.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

PH = ZoneInfo("Asia/Manila")


def now_ph(now: datetime | str | None = None) -> datetime:
    if now is None:
        now = os.getenv("AIPHEED_NOW") or None
    if now is None:
        return datetime.now(PH)
    if isinstance(now, str):
        now = datetime.fromisoformat(now)
    return now.replace(tzinfo=PH) if now.tzinfo is None else now.astimezone(PH)


def quarter_of(dt: datetime) -> str:
    return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"


def shift(quarter: str, k: int) -> str:
    y, q = int(quarter[:4]), int(quarter[-1])
    i = y * 4 + (q - 1) + k
    return f"{i // 4}-Q{i % 4 + 1}"


def quarter_start(quarter: str) -> datetime:
    return datetime(int(quarter[:4]), 3 * int(quarter[-1]) - 2, 1, tzinfo=PH)


def lead2_preview() -> bool:
    """The lead-2 row is served as a labelled experimental preview, and the dashboard opens on it (defaultQuarter,
    app.quarterly.preview.default_quarter), while the other defaults (current quarter, forecast target, quarter
    resolution, PDF, LGU ranking, alerts) stay on lead 1. On by default (researchers' decision, final integration);
    AIPHEED_LEAD2_PREVIEW=0 turns it off."""
    return os.getenv("AIPHEED_LEAD2_PREVIEW", "1").strip() != "0"


def max_lead() -> int:
    """Longest served lead (1 = one quarter ahead of the latest complete data quarter)."""
    lead = int(os.getenv("AIPHEED_MAX_LEAD", "1"))
    return max(lead, 2) if lead2_preview() else lead


def default_lead() -> int:
    """The lead the defaults use: 1 with the lead-2 preview on, otherwise the served maximum (unchanged)."""
    return 1 if lead2_preview() else max_lead()


def forecast_target(now: datetime | str | None = None) -> dict:
    """The dashboard's forecast target and its issue rule, for the given (or current) Philippine time."""
    t = now_ph(now)
    cal = quarter_of(t)
    lead = default_lead()
    target = shift(cal, lead - 1)
    origin = quarter_start(cal)
    return {
        "now_ph": t.isoformat(timespec="seconds"),
        "calendar_quarter": cal,
        "target_quarter": target,
        "origin": origin.date().isoformat(),
        "information_cutoff": f"{origin.date().isoformat()}T00:00:00+08:00 (exclusive)",
        "latest_complete_data_quarter": shift(cal, -1),
        "lead_from_latest_data_quarter": lead,
        "rule": ("next calendar quarter after the one in which the dashboard is viewed" if lead >= 2 else
                 "calendar quarter in which the dashboard is viewed (one quarter ahead of the latest complete data "
                 "quarter)") + " (Asia/Manila); forecasts are issued at the start of the current quarter with "
                "information published before it",
    }
