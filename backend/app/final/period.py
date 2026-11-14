"""
The forecasting period, worked out from the clock (Asia/Manila) and the serving configuration. Nothing here is hard-coded to a
quarter or a month: every label comes from the date.

Issue rule (data/final/serving.json "issue_rule"):
  monthly    {"cadence": "monthly", "day": 10}   (owner instruction 2026-11-14) the data are updated and a forecast is issued every
             month at 00:00 Philippine time on day `day`, with information published BEFORE that moment (exclusive cut-off).
             Issue id "YYYY-MM" (e.g. "2026-11" = issued 10 November 2026).
  quarterly  {"month_of_quarter": 2, "day": 1}    the earlier rule (1 Feb, 1 May, 1 Aug, 1 Nov). Issue id "YYYY-Qn". The first
             FINAL issue "2026-Q4" (cut-off 2026-11-01) has this id; it is kept, superseded by "2026-11".
An issue id of either form is understood everywhere: `issue_datetime`, `base_quarter`, `targets`.

Horizon: an issue forecasts Leads 1..max_lead counted from the quarter that contains its issue date (target = that quarter + lead),
the lead definition FINAL was validated with. max_lead is the validated maximum reliable lead in serving.json.

Tests and live end-to-end runs control the clock with `now` or the AIPHEED_NOW environment variable (app.quarterly.target.now_ph).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache

from app.paths import BACKEND_DIR
from app.quarterly.target import PH, now_ph, quarter_of, shift

SERVING = BACKEND_DIR / "data" / "final" / "serving.json"
DEFAULT_RULE = {"month_of_quarter": 2, "day": 1}             # the quarterly rule (legacy ids "YYYY-Qn")
QUARTERLY_ID = re.compile(r"^\d{4}-Q[1-4]$")
MONTHLY_ID = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@lru_cache(maxsize=1)
def serving() -> dict:
    return json.loads(SERVING.read_text(encoding="utf-8"))


def clear_cache() -> None:
    serving.cache_clear()


def _rule(cfg: dict | None = None) -> dict:
    return (cfg or serving()).get("issue_rule", {})


def monthly(cfg: dict | None = None) -> bool:
    return _rule(cfg).get("cadence") == "monthly"


def max_lead(cfg: dict | None = None) -> int:
    cfg = cfg or serving()
    lead = int(cfg["max_lead"])
    validated = int(cfg.get("validated_max_lead", lead))
    if lead < 1 or lead > validated:
        raise ValueError(f"max_lead {lead} is outside the validated range 1..{validated}")
    return lead


def issue_datetime(issue_id: str, cfg: dict | None = None) -> datetime:
    """The issue moment (information cut-off, exclusive) of an issue id, monthly ("YYYY-MM") or quarterly ("YYYY-Qn")."""
    if MONTHLY_ID.match(issue_id):
        day = int(_rule(cfg).get("day", 10)) if monthly(cfg) else 10
        return datetime(int(issue_id[:4]), int(issue_id[5:7]), day, tzinfo=PH)
    if not QUARTERLY_ID.match(issue_id):
        raise ValueError(f"not an issue id: {issue_id!r}")
    rule = {**DEFAULT_RULE, **({} if monthly(cfg) else _rule(cfg))}
    y, q = int(issue_id[:4]), int(issue_id[-1])
    return datetime(y, 3 * (q - 1) + int(rule["month_of_quarter"]), int(rule["day"]), tzinfo=PH)


def base_quarter(issue_id: str, cfg: dict | None = None) -> str:
    """The quarter that contains the issue date: leads are counted from it."""
    return issue_id if QUARTERLY_ID.match(issue_id) else quarter_of(issue_datetime(issue_id, cfg))


def issue_label(issue_id: str, cfg: dict | None = None) -> str:
    """Plain label: 'issued 10 November 2026' for a monthly id, 'Q4 2026' for a quarterly one."""
    if MONTHLY_ID.match(issue_id):
        return issue_datetime(issue_id, cfg).strftime("%d %B %Y").lstrip("0")
    return f"{issue_id[5:]} {issue_id[:4]}"


def published_by(issue_id: str, cfg: dict | None = None) -> str:
    """The date by which an issue's figures had been published: the cut-off, unless the issue carries a recorded exception."""
    n = (cfg or serving()).get("issue_notes", {}).get(issue_id, {})
    return n.get("published_by") or issue_datetime(issue_id, cfg).date().isoformat()


def issue_note(issue_id: str, cfg: dict | None = None) -> str | None:
    """A recorded disclosure about one issue (e.g. figures published after its cut-off), shown wherever that issue is described."""
    return (cfg or serving()).get("issue_notes", {}).get(issue_id, {}).get("note")


def quarter_index(quarter: str) -> int:
    return int(quarter[:4]) * 4 + int(quarter[-1]) - 1


def label(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def _month_id(y: int, m: int) -> str:
    while m < 1:
        y, m = y - 1, m + 12
    while m > 12:
        y, m = y + 1, m - 12
    return f"{y}-{m:02d}"


def latest_issue(now: datetime | str | None = None, cfg: dict | None = None) -> str:
    """The id of the newest issue whose issue moment has passed."""
    t = now_ph(now)
    if monthly(cfg):
        this = _month_id(t.year, t.month)
        return this if t >= issue_datetime(this, cfg) else _month_id(t.year, t.month - 1)
    cal = quarter_of(t)
    return cal if t >= issue_datetime(cal, cfg) else shift(cal, -1)


latest_issue_quarter = latest_issue          # earlier name, kept for callers


def next_issue(issue_id: str, cfg: dict | None = None) -> str:
    if MONTHLY_ID.match(issue_id) or monthly(cfg):
        d = issue_datetime(issue_id, cfg)
        return _month_id(d.year, d.month + 1)
    return shift(issue_id, 1)


def targets(issue_id: str, cfg: dict | None = None) -> list[dict]:
    b = base_quarter(issue_id, cfg)
    return [{"lead": k, "quarter": shift(b, k)} for k in range(1, max_lead(cfg) + 1)]


def status_of(target_quarter: str, calendar_quarter: str) -> str:
    """'past' (the quarter is over), 'current' (we are in it) or 'future'."""
    d = quarter_index(target_quarter) - quarter_index(calendar_quarter)
    return "past" if d < 0 else "current" if d == 0 else "future"


def period(now: datetime | str | None = None, cfg: dict | None = None) -> dict:
    cfg = cfg or serving()
    t = now_ph(now)
    cal = quarter_of(t)
    issue = latest_issue(t, cfg)
    nxt = next_issue(issue, cfg)
    tg = [{**x, "status": status_of(x["quarter"], cal)} for x in targets(issue, cfg)]
    return {
        "now_ph": t.isoformat(timespec="seconds"),
        "timezone": "Asia/Manila",
        "current_quarter": cal,
        "cadence": "monthly" if monthly(cfg) else "quarterly",
        "issue_quarter": issue,                                   # the issue id (field name kept for the ledger, API and database)
        "issue_label": issue_label(issue, cfg),
        "base_quarter": base_quarter(issue, cfg),
        "issue_date": issue_datetime(issue, cfg).isoformat(),
        "information_cutoff": issue_datetime(issue, cfg).isoformat() + " (exclusive)",
        "published_by": published_by(issue, cfg),
        "issue_note": issue_note(issue, cfg),
        "next_issue_quarter": nxt,
        "next_issue_date": issue_datetime(nxt, cfg).isoformat(),
        "max_lead": max_lead(cfg),
        "targets": tg,
        "forecast_quarters": [x["quarter"] for x in tg],
        "model_id": cfg["model_id"],
        "issue_rule": _rule(cfg) if monthly(cfg) else {**DEFAULT_RULE, **_rule(cfg)},
        "lead_basis": cfg.get("lead_basis", ""),
    }
