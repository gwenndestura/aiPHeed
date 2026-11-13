"""
The forecasting period, worked out from the clock (Asia/Manila) and the serving configuration. Nothing here is hard-coded to a
quarter: every label comes from the date.

Issue rule (data/final/serving.json "issue_rule"): a quarter's forecast is issued at 00:00 Philippine time on day `day` of the
quarter's `month_of_quarter`-th month (default: the 1st of the second month, i.e. 1 Feb, 1 May, 1 Aug, 1 Nov), with information
published BEFORE that moment (exclusive cut-off). This is the rule of FINAL's sealed issue (2026-Q4, cut-off 2026-11-01).
Until a quarter's issue day, the latest issue is the previous quarter's.

Horizon: the issue forecasts Leads 1..max_lead (target = issue quarter + lead). max_lead is the validated maximum reliable lead
time in serving.json; it is never larger than the leads the model was validated for.

Tests and live end-to-end runs control the clock with `now` or the AIPHEED_NOW environment variable (app.quarterly.target.now_ph).
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache

from app.paths import BACKEND_DIR
from app.quarterly.target import PH, now_ph, quarter_of, shift

SERVING = BACKEND_DIR / "data" / "final" / "serving.json"
DEFAULT_RULE = {"month_of_quarter": 2, "day": 1}


@lru_cache(maxsize=1)
def serving() -> dict:
    return json.loads(SERVING.read_text(encoding="utf-8"))


def clear_cache() -> None:
    serving.cache_clear()


def max_lead(cfg: dict | None = None) -> int:
    cfg = cfg or serving()
    lead = int(cfg["max_lead"])
    validated = int(cfg.get("validated_max_lead", lead))
    if lead < 1 or lead > validated:
        raise ValueError(f"max_lead {lead} is outside the validated range 1..{validated}")
    return lead


def issue_datetime(quarter: str, cfg: dict | None = None) -> datetime:
    rule = {**DEFAULT_RULE, **(cfg or serving()).get("issue_rule", {})}
    y, q = int(quarter[:4]), int(quarter[-1])
    month = 3 * (q - 1) + int(rule["month_of_quarter"])
    return datetime(y, month, int(rule["day"]), tzinfo=PH)


def quarter_index(quarter: str) -> int:
    return int(quarter[:4]) * 4 + int(quarter[-1]) - 1


def label(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def latest_issue_quarter(now: datetime | str | None = None, cfg: dict | None = None) -> str:
    t = now_ph(now)
    cal = quarter_of(t)
    return cal if t >= issue_datetime(cal, cfg) else shift(cal, -1)


def targets(issue_quarter: str, cfg: dict | None = None) -> list[dict]:
    return [{"lead": k, "quarter": shift(issue_quarter, k)} for k in range(1, max_lead(cfg) + 1)]


def status_of(target_quarter: str, calendar_quarter: str) -> str:
    """'past' (the quarter is over), 'current' (we are in it) or 'future'."""
    d = quarter_index(target_quarter) - quarter_index(calendar_quarter)
    return "past" if d < 0 else "current" if d == 0 else "future"


def period(now: datetime | str | None = None, cfg: dict | None = None) -> dict:
    cfg = cfg or serving()
    t = now_ph(now)
    cal = quarter_of(t)
    issue = latest_issue_quarter(t, cfg)
    nxt = shift(issue, 1)
    tg = [{**x, "status": status_of(x["quarter"], cal)} for x in targets(issue, cfg)]
    return {
        "now_ph": t.isoformat(timespec="seconds"),
        "timezone": "Asia/Manila",
        "current_quarter": cal,
        "issue_quarter": issue,
        "issue_date": issue_datetime(issue, cfg).isoformat(),
        "information_cutoff": issue_datetime(issue, cfg).isoformat() + " (exclusive)",
        "next_issue_quarter": nxt,
        "next_issue_date": issue_datetime(nxt, cfg).isoformat(),
        "max_lead": max_lead(cfg),
        "targets": tg,
        "forecast_quarters": [x["quarter"] for x in tg],
        "model_id": cfg["model_id"],
        "issue_rule": {**DEFAULT_RULE, **cfg.get("issue_rule", {})},
        "lead_basis": cfg.get("lead_basis", ""),
    }
