"""
app/quarterly/update.py
-----------------------
One quarterly update cycle. It checks every declared input requirement against the registry, applies the
publication-time rules, and writes ONE forecast record that the API, the dashboard and the PDF report all
read, so they cannot disagree on the target quarter, the supporting-news window or the cutoff.

A forecast is produced only when every requirement passes AND the cutoff has been reached AND a forecaster
is supplied. Otherwise the record carries status INSUFFICIENT_DATA (or BLOCKED for authorization/integrity
failures) with the exact list of what is missing; stale data are never relabelled as a new forecast.

Requirement kinds (config "requirements"):
    {"id": ..., "kind": "news",      "quarter": "<reference quarter>", "source_ids": [...]}
    {"id": ..., "kind": "indicator", "quarter": "<latest quarter needed>", "source_ids": [...]}
    {"id": ..., "kind": "label",     "quarter": "<latest round quarter needed>", "source_ids": [...]}
    {"id": ..., "kind": "static",    "source_ids": [...]}
    {"id": ..., "kind": "model",     "source_ids": [...]}
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from app.quarterly.config import ForecastPeriod
from app.quarterly.eligibility import classify_news, news_summary
from app.quarterly.periods import PH_TZ, Quarter, to_ph
from app.quarterly.registry import Registry, SnapshotStore

PROVINCES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]  # Cavite, Laguna, Quezon, Rizal, Batangas (geocoder.py)
OK, MISSING, UNAUTHORIZED, HASH_MISMATCH, NOT_AVAILABLE, STALE = (
    "OK", "MISSING", "UNAUTHORIZED", "HASH_MISMATCH", "NOT_AVAILABLE_BY_CUTOFF", "STALE")


def check_requirement(req: dict, reg: Registry, period: ForecastPeriod) -> dict:
    ids = req.get("source_ids") or []
    entries = [reg.latest(i) for i in ids if reg.latest(i) is not None]
    entries = [e for e in entries if e.kind == req["kind"]] or [e for e in reg.by_kind(req["kind"]) if not ids]
    res = {"id": req["id"], "kind": req["kind"], "quarter": req.get("quarter"), "sources": [], "status": MISSING,
           "detail": "no registered source"}
    if not entries:
        return res
    best = None
    for e in entries:
        s = {"source_id": e.source_id, "vintage": e.vintage, "sha256": e.sha256, "observation_end": e.observation_end,
             "available_at": e.available_at, "authorized": e.authorized}
        if not e.authorized:
            s["status"] = UNAUTHORIZED
        elif not e.verify():
            s["status"] = HASH_MISMATCH
        elif e.kind not in ("static", "model") and (e.available_at is None or to_ph(e.available_at) > period.cutoff):
            s["status"] = NOT_AVAILABLE
        elif req.get("quarter") and (e.observation_end is None or
                                     Quarter.parse(e.observation_end) < Quarter.parse(req["quarter"])):
            s["status"] = STALE
        else:
            s["status"] = OK
        res["sources"].append(s)
        if s["status"] == OK:
            best = s
    need_all = req["kind"] == "static" or req.get("all_required", False)
    if need_all and any(s["status"] != OK for s in res["sources"]):
        best = None
    if need_all and len(res["sources"]) < len(ids):
        best = None
        res["sources"] += [{"source_id": i, "status": MISSING} for i in ids if reg.latest(i) is None]
    if best:
        res.update(status=OK, detail=", ".join(f"{s['source_id']} v{s['vintage']}" for s in res["sources"]
                                               if s["status"] == OK))
    else:
        order = [UNAUTHORIZED, HASH_MISMATCH, NOT_AVAILABLE, STALE, MISSING]
        st = min((s["status"] for s in res["sources"] if s["status"] != OK),
                 key=lambda x: order.index(x) if x in order else 9)
        res.update(status=st, detail="; ".join(f"{s['source_id']}: {s['status']}" for s in res["sources"]))
    return res


def run_update(period: ForecastPeriod, reg: Registry, out_dir: str | Path, *, store: SnapshotStore | None = None,
               news_loader: Callable | None = None, forecaster: Callable | None = None,
               now: pd.Timestamp | None = None) -> dict:
    period.validate()
    now = to_ph(now if now is not None else pd.Timestamp.now(tz=PH_TZ))
    checks = [check_requirement(r, reg, period) for r in period.requirements]
    cutoff_reached = now >= period.cutoff
    news_block = {"window_start": period.news_window_start.isoformat(), "window_end": period.news_window_end.isoformat(),
                  "quarter": str(period.reference_quarter), "display": period.reference_quarter.display(),
                  "quarter_complete": period.quarter_complete, "eligible": 0, "by_province": {p: 0 for p in PROVINCES},
                  "limited_signal": {p: True for p in PROVINCES}, "articles": []}
    news_ok = [c for c in checks if c["kind"] == "news" and c["status"] == OK]
    if news_ok and news_loader is not None:
        frames = [news_loader(reg.latest(s["source_id"])) for c in news_ok for s in c["sources"] if s["status"] == OK]
        cls = classify_news(pd.concat(frames, ignore_index=True), period)
        news_block.update(news_summary(cls, PROVINCES))
        el = cls[cls["eligibility"] == "ELIGIBLE"].sort_values("published_ph")
        news_block["articles"] = [{"title": r.get("title"), "link": r.get("link"), "province_code": r.get("province_code"),
                                   "published_ph": r["published_ph"].isoformat()} for _, r in el.iterrows()]
    if store is not None:
        for c in checks:
            for s in c["sources"]:
                if s["status"] == OK:
                    store.ingest(reg.latest(s["source_id"]))
    blocked = [c for c in checks if c["status"] in (UNAUTHORIZED, HASH_MISMATCH)]
    missing = [c for c in checks if c["status"] != OK]
    reasons = [f"{c['id']}: {c['status']} ({c['detail']})" for c in missing]
    if not cutoff_reached:
        reasons.append(f"cutoff {period.cutoff.isoformat()} not yet reached at run time; "
                       f"the reference quarter's news is incomplete")
    status = "BLOCKED" if blocked else ("READY" if not reasons else "INSUFFICIENT_DATA")
    forecast = None
    if status == "READY" and forecaster is not None:
        forecast = forecaster(period, reg)
    elif status == "READY":
        status, forecast = "INSUFFICIENT_DATA", None
        reasons.append("no promoted forecaster supplied")
    content = {"period": period.to_dict(), "status": status, "missing": reasons, "requirements": checks,
               "supporting_news": news_block, "forecast": forecast,
               "labels": {"target": f"Forecast target: {period.target_quarter.display()}",
                          "news": f"Supporting news: {period.reference_quarter.display()}"
                                  + ("" if period.quarter_complete else " — incomplete quarter"),
                          "cutoff": f"Information cutoff: {period.cutoff.isoformat()} (Asia/Manila)",
                          "caveat": "Relative ordinal risk estimates; not official food insecurity classifications."}}
    blob = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
    rec = {**content, "content_sha256": hashlib.sha256(blob).hexdigest(),
           "generated_at": datetime.now(timezone.utc).isoformat(), "run_clock": now.isoformat(),
           "cutoff_reached": cutoff_reached}
    return write_record(rec, Path(out_dir))


def write_record(rec: dict, out_dir: Path) -> dict:
    """Idempotent: an identical content hash does not create a new history entry."""
    tq = rec["period"]["target_quarter"]
    d = out_dir / tq
    d.mkdir(parents=True, exist_ok=True)
    latest = d / "forecast_record.json"
    if latest.exists():
        old = json.loads(latest.read_text(encoding="utf-8"))
        if old.get("content_sha256") == rec["content_sha256"]:
            return {**old, "unchanged": True}
        hist = d / "history"
        hist.mkdir(exist_ok=True)
        (hist / f"{old['generated_at'].replace(':', '').replace('-', '')}.json").write_text(
            json.dumps(old, indent=2, default=str), encoding="utf-8")
    latest.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
    (out_dir / "latest.json").write_text(json.dumps({"target_quarter": tq, "record": f"{tq}/forecast_record.json"}),
                                         encoding="utf-8")
    return rec


def load_latest(out_dir: str | Path) -> dict | None:
    out_dir = Path(out_dir)
    ptr = out_dir / "latest.json"
    if not ptr.exists():
        return None
    p = json.loads(ptr.read_text(encoding="utf-8"))
    return json.loads((out_dir / p["record"]).read_text(encoding="utf-8"))
