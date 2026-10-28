"""
app/ml/inference/sws_reissue.py
-------------------------------
SWS-release re-issue of Lead-2+ forecasts: the P0H4-U issue schedule as a deployable, append-only process.

The served P0H4 issues every lead on the first day of a quarter. Its Lead-2+ hunger part then rests on an SWS reading
that is often two quarters old, although SWS publishes a newer one a few weeks into the quarter. This module re-issues
those forecasts after the release, with the same model:

- the price part pi_P is the quarter-start LightGBM output, unchanged (the model is not refitted);
- the hunger part is recomputed exactly as in FORECAST_RESEARCH fr_lib.pi_h:
  pi_H = Phi((h_last - 11.3) / max(sigma_h, 0.5)), h_last the newest Balance Luzon reading published before the issue
  date, sigma_h the RMS of the h-step changes of the four SWS areas published before the issue date (>= 8 changes);
- P = pi_H x pi_P, HIGH if P >= 0.50.

Schedule (FORECAST_RESEARCH S-AB, schedule B for Leads >= 2): for origin quarter t, the re-issue date is the day after
SWS publishes quarter t's Balance Luzon reading, at the latest day 1 of month 3 of quarter t+1 (the window cap); when
no reading arrives by the cap, the forecasts are re-issued at the cap with what is published. Lead 1 is not re-issued.

Guarantees:
- **history is append-only**: rows are never edited or deleted; a re-issue adds rows that supersede the earlier issue;
- **idempotent**: an origin is re-issued once per schedule-B date; repeated or overlapping runs add nothing. When SWS
  publishes a second round for the same quarter before the cap, the date moves and the forecasts are re-issued again
  (the quarter's rounds are averaged, as in fr_lib.known), superseding the earlier re-issue;
- **cut-off**: every row records its issue date and data cut-off; only SWS rounds published before the issue date
  enter, and nothing is issued for a date after `now`; SWS entries published after `now` are refused.

Off by default: the scheduler registers the daily job only when AIPHEED_SWS_REISSUE=1, and the dashboard keeps
serving the default export (app.ml.inference.ch1_system) until that switch is authorised.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

AREAS = ("NCR", "BL", "VIS", "MIN")
H_LINE, POOL_MIN, SIGMA_FLOOR = 11.3, 8, 0.5
DATA = Path(__file__).resolve().parents[3] / "data" / "ch1_reissue"
SWS_STORE = DATA / "sws_rounds.csv"
HISTORY = DATA / "forecast_history.csv"
RUN_LOG = DATA / "reissue_log.jsonl"
SWS_COLS = ["area", "q", "H", "published", "fw_end", "moe"]
HIST_COLS = ["forecast_id", "province_code", "province", "target_quarter", "lead", "origin_quarter", "issue_date",
             "issue_schedule", "trigger", "data_cutoff", "sws_q_used", "sws_published_used", "h_last", "sigma_h",
             "pi_hunger", "pi_price", "probability", "class", "psa_newest_month", "model", "supersedes", "recorded_at"]


def enabled() -> bool:
    return os.getenv("AIPHEED_SWS_REISSUE", "0").strip() == "1"


# ---------------------------------------------------------------------------------------------------- quarters, dates
def qindex(label: str) -> int:
    y, q = label.split("-Q")
    return int(y) * 4 + int(q) - 1


def qlabel(t: int) -> str:
    return f"{t // 4}-Q{t % 4 + 1}"


def origin(t: int) -> date:
    """Quarter-start issue date of origin quarter t: day 1 of quarter t+1."""
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 1)


def window_cap(t: int) -> date:
    o = origin(t)
    return date(o.year, o.month + 2, 1)


def _d(x) -> date:
    return x if isinstance(x, date) and not isinstance(x, datetime) else pd.Timestamp(x).date()


# ---------------------------------------------------------------------------------------------------- SWS store
def load_sws(path: Path = SWS_STORE) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=SWS_COLS)
    r = pd.read_csv(path)
    r["published"] = r["published"].astype(str).str[:10]
    return r


def enter_sws_reading(area: str, quarter: str, H: float, published: str, fw_end: str, moe: float,
                      now: date | None = None, path: Path = SWS_STORE) -> str:
    """Manual entry of one SWS round. Returns 'added' or 'duplicate' (identical row already present).
    Refuses an unknown area, a hunger rate outside 0-100, a publication after `now`, fieldwork ending after
    publication, a fieldwork end before the quarter starts, and a different value for an existing (area, q, published)."""
    now = _d(now or date.today())
    if area not in AREAS:
        raise ValueError(f"unknown SWS area {area!r}")
    q = qindex(quarter)
    H, moe = float(H), float(moe)
    if not 0 <= H <= 100 or math.isnan(H):
        raise ValueError(f"hunger rate {H} outside 0-100")
    pub, fw = _d(published), _d(fw_end)
    if pub > now:
        raise ValueError(f"published {pub} is after now {now}: future data refused")
    if fw > pub:
        raise ValueError("fieldwork ends after publication")
    if fw < date(q // 4, (q % 4) * 3 + 1, 1):
        raise ValueError("fieldwork ends before the quarter starts")
    r = load_sws(path)
    same = r[(r["area"] == area) & (r["q"] == q) & (r["published"] == pub.isoformat())]
    if len(same):
        if np.isclose(float(same["H"].iloc[0]), H) and np.isclose(float(same["moe"].iloc[0]), moe):
            return "duplicate"
        raise ValueError(f"{area} {quarter} published {pub} already entered with H={same['H'].iloc[0]}")
    row = pd.DataFrame([{"area": area, "q": q, "H": H, "published": pub.isoformat(), "fw_end": fw.isoformat(), "moe": moe}])
    _atomic_write(pd.concat([r, row], ignore_index=True)[SWS_COLS], path)
    return "added"


def known(r: pd.DataFrame, iss: date, area: str) -> list[tuple[int, float, str]]:
    """(quarter, mean H, last publication) of every round of `area` published strictly before `iss`."""
    x = r[(r["area"] == area) & (r["published"] < _d(iss).isoformat())]
    return [(int(q), float(g["H"].mean()), g["published"].max()) for q, g in sorted(x.groupby("q"))]


def pi_hunger(r: pd.DataFrame, iss: date, target_q: int) -> dict | None:
    """fr_lib.pi_h on the store; None when the pooled sigma is not estimable."""
    kn = known(r, iss, "BL")
    if not kn:
        return None
    q_last, h_last, pub = kn[-1]
    h = target_q - q_last
    errs = []
    for a in AREAS:
        d = {x[0]: x[1] for x in known(r, iss, a)}
        errs += [d[q + h] - d[q] for q in d if q + h in d]
    if len(errs) < POOL_MIN:
        return None
    sig = math.sqrt(float(np.mean(np.square(errs))))
    return {"pi_H": float(norm.cdf((h_last - H_LINE) / max(sig, SIGMA_FLOOR))), "h_last": h_last, "sigma_h": sig,
            "sws_q_used": qlabel(q_last), "sws_published_used": pub}


def reissue_date(r: pd.DataFrame, t: int, now: date) -> tuple[date, str] | None:
    """The schedule-B date for origin t as determinable at `now`, with its trigger; None if not yet due."""
    now, o, cap = _d(now), origin(t), window_cap(t)
    bl = r[(r["area"] == "BL") & (r["q"] == t) & (r["published"] < now.isoformat())]
    if len(bl):
        d = _d(bl["published"].max()) + timedelta(days=1)
        if d <= cap:
            d = max(d, o)
            return (d, "sws_release") if d <= now else None
    return (cap, "window_cap") if now >= cap else None


# ---------------------------------------------------------------------------------------------------- history
def load_history(path: Path = HISTORY) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=HIST_COLS)
    return pd.read_csv(path, dtype={"province_code": str, "issue_date": str, "supersedes": str})


def _fid(province_code: str, target: str, lead: int, issue_date: str, trigger: str) -> str:
    return hashlib.sha1(f"{province_code}|{target}|{lead}|{issue_date}|{trigger}".encode()).hexdigest()[:16]


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, lineterminator="\n", float_format="%.10g")
    os.replace(tmp, path)


def _append(rows: list[dict], path: Path) -> int:
    """Append rows whose forecast_id is new; existing rows are written back unchanged (append-only)."""
    h = load_history(path)
    seen = set(h["forecast_id"])
    new = [x for x in rows if x["forecast_id"] not in seen]
    if new:
        out = pd.concat([h, pd.DataFrame(new)[HIST_COLS]], ignore_index=True) if len(h) else pd.DataFrame(new)[HIST_COLS]
        _atomic_write(out, path)
    return len(new)


def record_quarter_start(rows: pd.DataFrame, path: Path = HISTORY, recorded_at: str | None = None) -> int:
    """Import quarter-start (schedule A) forecasts, e.g. the served export rows of one issue, into the history.
    Needs: province_code, province, quarter, issue_date, lead, pi_hunger, pi_price, probability, sws_newest_q,
    sws_newest_published, h_last, psa_newest_month, model."""
    stamp = recorded_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    for x in rows.itertuples():
        iss = str(x.issue_date)[:10]
        t = qindex(x.quarter) - int(x.lead)
        out.append({"forecast_id": _fid(x.province_code, x.quarter, int(x.lead), iss, "quarter_start"),
                    "province_code": x.province_code, "province": x.province, "target_quarter": x.quarter,
                    "lead": int(x.lead), "origin_quarter": qlabel(t), "issue_date": iss, "issue_schedule": "A",
                    "trigger": "quarter_start", "data_cutoff": iss, "sws_q_used": x.sws_newest_q,
                    "sws_published_used": str(x.sws_newest_published)[:10], "h_last": x.h_last, "sigma_h": np.nan,
                    "pi_hunger": x.pi_hunger, "pi_price": x.pi_price, "probability": x.probability,
                    "class": "HIGH" if x.probability >= .5 else "LOW", "psa_newest_month": x.psa_newest_month,
                    "model": x.model, "supersedes": "", "recorded_at": stamp})
    return _append(out, path)


def reissue(now: date | None = None, sws_path: Path = SWS_STORE, path: Path = HISTORY,
            log_path: Path | None = RUN_LOG, recorded_at: str | None = None) -> dict:
    """Re-issue every due origin's Lead-2+ quarter-start forecasts once. Safe to call any number of times."""
    now = _d(now or date.today())
    stamp = recorded_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    r, h = load_sws(sws_path), load_history(path)
    summary = {"now": now.isoformat(), "reissued_origins": [], "rows_added": 0, "skipped": []}
    if not len(h):
        return summary
    qs = h[(h["trigger"] == "quarter_start") & (h["lead"] >= 2)]
    reissued = h[h["trigger"] != "quarter_start"]
    last_b = reissued.groupby("origin_quarter")["issue_date"].max().to_dict()
    latest = h.sort_values("issue_date").groupby(["province_code", "target_quarter"])["forecast_id"].last().to_dict()
    rows = []
    for oq, g in qs.groupby("origin_quarter"):
        t = qindex(oq)
        due = reissue_date(r, t, now)
        if due is None:
            continue
        iss, trig = due
        # a second round of the same quarter published before the cap moves the date: re-issue again (supersede)
        if iss > now or (oq in last_b and iss.isoformat() <= last_b[oq]):
            continue
        for x in g.itertuples():
            ph = pi_hunger(r, iss, qindex(x.target_quarter))
            if ph is None:
                summary["skipped"].append(f"{x.province_code} {x.target_quarter}: pooled sigma not estimable")
                continue
            p = ph["pi_H"] * float(x.pi_price)
            rows.append({"forecast_id": _fid(x.province_code, x.target_quarter, int(x.lead), iss.isoformat(), trig),
                         "province_code": x.province_code, "province": x.province, "target_quarter": x.target_quarter,
                         "lead": int(x.lead), "origin_quarter": oq, "issue_date": iss.isoformat(), "issue_schedule": "B",
                         "trigger": trig, "data_cutoff": iss.isoformat(), "sws_q_used": ph["sws_q_used"],
                         "sws_published_used": ph["sws_published_used"], "h_last": ph["h_last"],
                         "sigma_h": ph["sigma_h"], "pi_hunger": ph["pi_H"], "pi_price": float(x.pi_price),
                         "probability": p, "class": "HIGH" if p >= .5 else "LOW", "psa_newest_month": x.psa_newest_month,
                         "model": x.model, "supersedes": latest.get((x.province_code, x.target_quarter), x.forecast_id),
                         "recorded_at": stamp})
        summary["reissued_origins"].append({"origin": oq, "issue_date": iss.isoformat(), "trigger": trig})
    summary["rows_added"] = _append(rows, path) if rows else 0
    if log_path is not None and (summary["rows_added"] or summary["skipped"]):
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**summary, "recorded_at": stamp}) + "\n")
    return summary


def current(now: date | None = None, path: Path = HISTORY) -> pd.DataFrame:
    """The forecast in force at `now` for each (province, target quarter): the latest issue on or before `now`."""
    now = _d(now or date.today()).isoformat()
    h = load_history(path)
    h = h[h["issue_date"] <= now]
    return h.sort_values(["issue_date", "lead"], ascending=[True, False]).groupby(
        ["province_code", "target_quarter"], as_index=False).tail(1).reset_index(drop=True)


def run_daily(now: date | None = None, export_rows: Path | None = None) -> dict:
    """Scheduler entry: record the served export's quarter-start rows (idempotent), then re-issue what is due."""
    from app.ml.inference import ch1_system as CH1
    src = Path(export_rows) if export_rows else CH1.DATA / "rows.csv"
    rows = pd.read_csv(src, dtype={"province_code": str})
    rows = rows[rows["issue_schedule"].fillna("A") == "A"]
    added = record_quarter_start(rows)
    return {"quarter_start_rows_recorded": added, **reissue(now)}
