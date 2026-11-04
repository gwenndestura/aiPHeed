"""
app/cb6_auto/job.py
-------------------
The automatic quarterly update. run_daily() is safe to run any number of times; the scheduler runs it every morning.

  every day      news collection (and scoring, when enabled)
  issue date     (first day of a quarter) collect every source, build the origin's input row with the unchanged as-of rules,
                 score the FROZEN booster, append the forecast to the served rows, stage it for administrator review
  retries        a stale source is retried daily for RETRY_STALE_DAYS, then the forecast goes out with the source recorded as
                 stale and its inputs missing; after CATCH_UP_DAYS an issue with no forecast is recorded MISSED, never back-filled

A forecast once written is never rewritten. Rule 1: a new forecast stays withheld from public endpoints until an administrator
approves it (foodinsecurity_system.unapproved_pairs reads the served rows, so this holds even if staging itself fails).
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import logging
import math
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.cb6_auto import config as C
from app.cb6_auto import features as F
from app.cb6_auto import fetchers as K
from app.cb6_auto import frozen as Z
from app.cb6_auto import news as NW

logger = logging.getLogger(__name__)
PH_TZ = "Asia/Manila"
MODEL_ROW_NAME = "ALLBASE-CB6"
VALUES = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "ONI_last", "tc_mean", "R_C3", "R_C4", "W_rice_yoy"]
RATIO_GROUPS = ("market", "climate", "fish_kill", "employment", "ofw_remittance")
AVAIL_GROUPS = ("market", "climate", "fish_kill", "hunger", "news", "employment", "ofw_remittance", "supply")
SOURCE_FILES = ("cpi_backcast_ACP28.csv", "cpi_ACP22.csv", "cpi_rice_region.csv", "palay_corn_EVCP0.csv", "fisheries_GVFP1.csv",
                "sws_area_rounds_full.csv", "cov_oni.csv", "pinksheet_monthly_1960.csv", "typhoons_province_quarter.csv",
                "tidy_stocks_national.csv", "n1r_history.csv", "shap_history.csv")
NOT_COLLECTED_NEWS = ("Province news: the automatic quarterly job does not compute the provincial early-warning check.")


class NotConfigured(RuntimeError):
    pass


def served_dir() -> Path:
    """The served export the dashboard reads. Must be an explicit folder outside the image's committed export."""
    v = os.getenv("AIPHEED_FI_DATA_DIR")
    if not v or not os.getenv("AIPHEED_CB6_STATE_DIR"):
        raise NotConfigured("AIPHEED_FI_DATA_DIR and AIPHEED_CB6_STATE_DIR must both be set; refusing to write into the "
                            "committed export")
    p = Path(v)
    if p.resolve() == (C.BACKEND / "data" / "foodinsecurity_engine_cb6").resolve():
        raise NotConfigured("AIPHEED_FI_DATA_DIR points at the committed export; refusing to write into it")
    return p


def ensure_state() -> None:
    """Idempotent first-start setup of the persistent folders. Stored forecasts and fetched data are never overwritten; the
    evaluation and LGU tables, which the job never edits, follow the deployed image."""
    C.sources_dir().mkdir(parents=True, exist_ok=True)
    for f in SOURCE_FILES:
        if not (C.sources_dir() / f).exists():
            shutil.copyfile(C.SEED / f, C.sources_dir() / f)
    out = served_dir()
    out.mkdir(parents=True, exist_ok=True)
    src = C.BACKEND / "data" / "foodinsecurity_engine_cb6"
    if not (out / "rows.csv").exists():
        shutil.copyfile(src / "rows.csv", out / "rows.csv")
    for f in ("evaluation.json", "lgu_vulnerability.csv"):
        shutil.copyfile(src / f, out / f)


# ================================================================================================ ledger and log
def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def _append_jsonl(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def ledger() -> list[dict]:
    return _read_jsonl(C.ledger_path())


def _log(rec: dict) -> dict:
    _append_jsonl(C.run_log_path(), rec)
    logger.info("cb6 update: %s", {k: rec.get(k) for k in ("status", "issue_date", "target_quarter", "stale")})
    if rec.get("status") in ("MISSED", "FAILED", "NOT_CONFIGURED") or rec.get("needs_human"):
        logger.error("cb6 update needs attention: %s", {k: rec.get(k) for k in ("status", "issue_date", "needs_human", "error")})
    return rec


def _clean(x):
    if isinstance(x, (float, np.floating)):
        return None if math.isnan(float(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def write_ledger_entry(entry: dict) -> dict:
    """Append-only, hash-chained; one entry per issue date."""
    rows = ledger()
    if any(e["issue_date"] == entry["issue_date"] for e in rows):
        raise ValueError(f"issue {entry['issue_date']} is already in the ledger; a forecast is never rewritten")
    prev = rows[-1]["entry_hash"] if rows else None
    body = {**entry, "prev_hash": prev}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    rec = {**body, "entry_hash": h}
    _append_jsonl(C.ledger_path(), rec)
    return rec


def verify_ledger() -> bool:
    prev = None
    for e in ledger():
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        if body.get("prev_hash") != prev:
            return False
        if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != e["entry_hash"]:
            return False
        prev = e["entry_hash"]
    return True


# ================================================================================================ served rows
def group_shap(shap: dict) -> dict:
    return {g: float(sum(shap.get(c, 0.0) or 0.0 for c in cs)) for g, cs in F.GROUPS.items()}


def _hist_group(h: pd.DataFrame, g: str) -> pd.Series:
    cs = [f"shap_{c}" for c in F.GROUPS[g] if f"shap_{c}" in h]
    return sum((h[c].fillna(0) for c in cs), pd.Series(0.0, index=h.index))


def relative_drivers(hist: pd.DataFrame, t: int, lead: int, gs: dict) -> dict:
    """export_cb6: this forecast's group SHAP / the group's mean |SHAP| over this lead's forecasts issued up to this one."""
    w = hist[(hist["lead"] == lead) & (hist["t"] < t) & ~hist["fallback"].astype(str).str.lower().eq("true")]
    out = {}
    for g in RATIO_GROUPS:
        v = pd.concat([_hist_group(w, g).abs(), pd.Series([abs(gs[g])])], ignore_index=True)
        typ = float(v.mean())
        out[f"avg8_shap_{g}"] = round(gs[g] / typ, 6) if typ > 0 else 0.0
    out["avg8_n"] = int(len(w) + 1)
    return out


def served_rows(x: dict, scored: dict, poverty: list[dict], hist: pd.DataFrame, psa_newest_month: str, news: dict,
                model_sha: str) -> list[dict]:
    """The five province rows of one forecast, in the layout of OBJECTIVES_AUDIT/runner/export_cb6.py."""
    t, k = int(x["t"]), int(x["lead"])
    p = float(scored["p"])
    gs = group_shap(scored["shap"])
    av = {g: int(any(pd.notna(x.get(c)) for c in F.GROUPS[g])) for g in AVAIL_GROUPS}
    n = news.get("scored")
    regional = (f"Regional news (project corpus, {F.qs(t)}, {n} scored articles): category comparison not computed by the "
                "automatic job" if n else "Regional news: no corpus value before the issue date.")
    base = {"quarter": F.qs(t + k), "issue_date": F.issue(t), "lead": k, "origin": F.qs(t), "probability": round(p, 6),
            "pi_hunger": round(p, 6), "class": "HIGH" if p >= 0.5 else "LOW", "observed": "", "observed_hunger": "",
            "pi_price": "", "price_band": "", "sws_newest_q": x.get("sws_newest_q") or "",
            "sws_newest_published": x.get("sws_newest_published") or "",
            "h_last": "" if pd.isna(x["h_last"]) else round(float(x["h_last"]), 2), "psa_newest_month": psa_newest_month,
            "cfg": f"frozen:{model_sha[:8]}", "fallback": False,
            **{f"shap_{g}": round(v, 6) for g, v in gs.items()}, **{f"avail_{g}": a for g, a in av.items()},
            **{f"val_{c}": ("" if pd.isna(x.get(c)) else round(float(x[c]), 4)) for c in VALUES},
            **relative_drivers(hist, t, k, gs), "regional_news_text": regional, "regional_news_n": n or "",
            "news_flag": False, "news_flag_family": "", "province_news_n": "", "province_news_text": NOT_COLLECTED_NEWS,
            "model": MODEL_ROW_NAME, "seal_sha256": ""}
    top = max(float(v["pov_families_2023"]) for v in poverty)   # the weight, unrounded (evaluation.json rounds it to 4 places)
    return [{**base, "province_code": v["province_code"], "province": v["province"],
             "score": round(p * float(v["pov_families_2023"]) / top, 6),
             "pov_families_2023": v["pov_families_2023"], "pov_families_2023_cv": v["pov_families_2023_cv"],
             "pov_weight": round(float(v["pov_families_2023"]) / top, 6), "food_pov_2023": v["food_pov_2023"],
             "food_pov_2023_cv": v["food_pov_2023_cv"]} for v in poverty]


def append_served(rows_path: Path, new: list[dict]) -> None:
    """Add rows; refuses any province-quarter already present. The replace is atomic, so a reader never sees half a file."""
    with open(rows_path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        head, old = rd.fieldnames, list(rd)
    have = {(r["province_code"], r["quarter"]) for r in old}
    clash = [(r["province_code"], r["quarter"]) for r in new if (r["province_code"], r["quarter"]) in have]
    if clash:
        raise ValueError(f"served rows already hold {clash[:2]}; a forecast is never rewritten")
    missing = [c for c in head if any(c not in r for r in new)]
    if missing:
        raise ValueError(f"new rows lack columns {missing}")
    tmp = rows_path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=head, extrasaction="ignore")
        w.writeheader()
        w.writerows(old)
        w.writerows(new)
    os.replace(tmp, rows_path)


def stage(quarter: str) -> dict:
    """Seed the review rows and alert candidates of a new forecast (Rule 1 and Rule 7). Own engine: this runs on the
    scheduler's thread, outside the web server's event loop."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.config import settings
    from app.ml.inference import foodinsecurity_system as FI
    from app.services import review as RV

    async def go():
        eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        try:
            async with async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)() as db:
                await RV.ensure_rows(db, quarter)
                res = await FI.stage_alerts(db, quarter)
                await db.commit()
                return {"alerts_staged": len(res["staged"])}
        finally:
            await eng.dispose()
    return asyncio.run(go())


# ================================================================================================ the run
def quarter_start(now: pd.Timestamp) -> str:
    return f"{now.year}-{(now.month - 1) // 3 * 3 + 1:02d}-01"


def issues_between(first: str, last: str) -> list[str]:
    a, b = F.origin_of_issue(first), F.origin_of_issue(last)
    return [F.issue(t) for t in range(a, b + 1)]


def _record_missed(before: str, done: set) -> None:
    logged = {r["issue_date"] for r in _read_jsonl(C.run_log_path()) if r.get("status") == "MISSED"}
    for iss in issues_between(C.FIRST_AUTO_ISSUE, before):
        if iss < before and iss not in done and iss not in logged:
            _log({"status": "MISSED", "issue_date": iss, "note": "no forecast within the catch-up window; never back-filled",
                  "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def _retry_staging(entry: dict) -> None:
    marker = C.state_dir() / f"staged_{entry['issue_date']}.ok"
    if marker.exists():
        return
    try:
        res = stage(entry["served_quarter"])
        marker.write_text(json.dumps(res), encoding="utf-8")
    except Exception as e:  # noqa: BLE001  (the forecast stays withheld by the Rule 1 gate; retried tomorrow)
        logger.exception("cb6 update: staging failed for %s", entry["served_quarter"])
        _log({"status": "STAGING_FAILED", "issue_date": entry["issue_date"], "error": f"{type(e).__name__}: {e}"[:300],
              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def run_due(now: pd.Timestamp | None = None, fetchers: dict | None = None, news_fn=None) -> dict:
    """Forecast the current quarter's issue date if it is due. Returns the run record, also written to run_log.jsonl."""
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=PH_TZ)
    now = now.tz_localize(PH_TZ) if now.tzinfo is None else now.tz_convert(PH_TZ)
    stamp = {"run_clock": now.isoformat(), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        ensure_state()
    except NotConfigured as e:
        return {"status": "NOT_CONFIGURED", "error": str(e), **stamp}
    iss = quarter_start(now)
    if iss < C.FIRST_AUTO_ISSUE:
        return {"status": "NOTHING_DUE", "reason": f"the first automatic issue is {C.FIRST_AUTO_ISSUE}", **stamp}
    entries = {e["issue_date"]: e for e in ledger()}
    _record_missed(iss, set(entries))
    if iss in entries:
        _repair_rows(entries[iss])
        _retry_staging(entries[iss])
        return {"status": "NOTHING_DUE", "reason": f"issue {iss} already forecast", "issue_date": iss, **stamp}
    days = (now.normalize().tz_localize(None) - pd.Timestamp(iss)).days
    if days > C.CATCH_UP_DAYS:
        return _log({"status": "MISSED", "issue_date": iss, "note": f"{days} days after the issue date; never back-filled", **stamp})

    t = F.origin_of_issue(iss)
    report = {"issue_date": iss, "origin": F.qs(t), "days_after_issue": days, **stamp}
    report["sources"] = K.collect_all(C.sources_dir(), fetchers)
    report["needs_human"] = report["sources"].get("sws_hunger", {}).get("needs_human", [])
    try:
        report["news"] = (news_fn or NW.n1r_asof)(t)
    except Exception as e:  # noqa: BLE001  (news problems leave the input missing, never stop the forecast)
        report["news"] = {"error": f"{type(e).__name__}: {e}"[:300], "n1r": math.nan}
    n1r_val = report["news"].get("n1r", math.nan)
    n1r_file = C.sources_dir() / "n1r_history.csv"
    nh = pd.read_csv(n1r_file)
    if pd.notna(n1r_val) and t not in set(nh["t"]):
        pd.concat([nh, pd.DataFrame([{"t": t, "N1R": n1r_val}])], ignore_index=True).to_csv(n1r_file, index=False, lineterminator="\n")

    d = F.load(C.sources_dir())
    fresh = F.freshness(d, t)
    stale = sorted(k for k, ok in fresh.items() if not ok)
    report["stale"] = stale
    blocking = [s for s in stale if s != "news_n1r_quarter_t" or C.news_scoring_enabled()]
    unparsed = [x for x in report["needs_human"] if x["published"] < iss]
    if (blocking or unparsed) and days < C.RETRY_STALE_DAYS:
        return _log({"status": "WAITING", "retry": "tomorrow", "blocking": blocking, **report})

    rows = F.rows_origin(d, t, leads=(1, 2))
    scored = Z.score(rows)
    man = Z.manifest()
    hist = pd.read_csv(C.sources_dir() / "shap_history.csv")
    ev = json.loads((served_dir() / "evaluation.json").read_text(encoding="utf-8"))
    fo = d.idx["food"]
    m = int(fo[fo.index <= F.m0_of(t)].index.max())
    served_x = next(i for i, r in enumerate(rows) if r["lead"] == C.SERVED_LEAD)
    new = served_rows(rows[served_x], scored[served_x], ev["province_poverty"], hist, f"{m // 12}-{m % 12 + 1:02d}",
                      report["news"], man["model_sha256"])
    forecasts = [{"lead": int(r["lead"]), "target_quarter": F.qs(t + int(r["lead"])), "p_high": s["p"],
                  "class": "HIGH" if s["p"] >= .5 else "LOW", "inputs": {c: _clean(r.get(c)) for c in man["columns"]},
                  "shap": s["shap"]} for r, s in zip(rows, scored)]
    entry = write_ledger_entry({"issue_date": iss, "origin": F.qs(t), "model": "C-B6 frozen", "model_sha256": man["model_sha256"],
                                "served_lead": C.SERVED_LEAD, "served_quarter": F.qs(t + C.SERVED_LEAD), "forecasts": forecasts,
                                "stale_sources": stale, "cutoffs": F.cutoffs(d, t), "news": {k: _clean(v) for k, v in report["news"].items()},
                                "source_sha256": K.file_hashes(C.sources_dir()), "run_clock": now.isoformat(),
                                "served_rows": new})
    append_served(served_dir() / "rows.csv", new)
    h_rows = [{"t": t, "lead": f["lead"], "q": t + f["lead"], "p": f["p_high"], "fallback": False,
               **{f"shap_{c}": v for c, v in f["shap"].items()}} for f in forecasts]
    pd.concat([hist, pd.DataFrame(h_rows)], ignore_index=True).to_csv(C.sources_dir() / "shap_history.csv", index=False,
                                                                      lineterminator="\n")
    _retry_staging(entry)
    return _log({"status": "FORECAST_STAGED", "target_quarter": entry["served_quarter"], "entry_hash": entry["entry_hash"],
                 "p_high": {f["target_quarter"]: f["p_high"] for f in forecasts}, **report})


def _repair_rows(entry: dict) -> None:
    """A crash between the ledger write and the rows write is finished from the ledger, never recomputed."""
    rows_path = served_dir() / "rows.csv"
    with open(rows_path, newline="", encoding="utf-8") as f:
        have = {(r["province_code"], r["quarter"]) for r in csv.DictReader(f)}
    if not all((r["province_code"], r["quarter"]) in have for r in entry["served_rows"]):
        append_served(rows_path, [r for r in entry["served_rows"] if (r["province_code"], r["quarter"]) not in have])


def run_daily(now: pd.Timestamp | None = None) -> dict:
    """The scheduler's job: news, then the quarterly step. A lock keeps two runs apart; one over 6 hours old is treated as
    left behind by a crash."""
    C.state_dir().mkdir(parents=True, exist_ok=True)
    lock = C.state_dir() / "run.lock"
    if lock.exists() and time.time() - lock.stat().st_mtime < 6 * 3600:
        return {"status": "BUSY"}
    lock.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    out: dict = {}
    try:
        clock = None if now is None else pd.Timestamp(now).to_pydatetime()
        try:
            out["news"] = NW.collect(clock)
            if C.news_scoring_enabled():
                out["news_scoring"] = NW.score_new()
        except Exception as e:  # noqa: BLE001  (news problems never stop the forecast)
            out["news_error"] = f"{type(e).__name__}: {e}"[:300]
            logger.exception("cb6 update: news step failed")
        out["update"] = run_due(now)
        return out
    finally:
        lock.unlink(missing_ok=True)


def status(limit: int = 10) -> dict:
    rows = ledger()
    return {"frozen_model_sha256": Z.manifest()["model_sha256"], "ledger_ok": verify_ledger(),
            "issued": [{k: e[k] for k in ("issue_date", "served_quarter", "stale_sources", "entry_hash")} for e in rows],
            "recent_runs": [{k: r.get(k) for k in ("status", "issue_date", "run_clock", "stale", "blocking", "needs_human", "error",
                                                   "target_quarter")} for r in _read_jsonl(C.run_log_path())[-limit:]]}
