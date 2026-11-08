"""
app/api/v1/fi9.py
-----------------
Read-only routes for FI9 (app.fi9, docs/fi9): the Lead-1 (next calendar quarter) food-insecurity outlook for
Balance Luzon selected by the locked protocol, its evaluation, model card, data vintage and the 142-LGU priority.

Files are written by `python -m app.fi9.evaluate run` and `python -m app.fi9.serve issue`; nothing is trained on a
request. A forecast issued in an earlier quarter is never returned as current: /fi9/outlook answers 503 with the
reason (stale or unavailable) and the command that re-issues it. 503 also when a file is missing.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.fi9 import MODEL, OUT, VERSION
from app.fi9 import quarters as Q
from app.fi9.serve import today

router = APIRouter(prefix="/fi9")
REISSUE = "python -m app.fi9.serve issue"
NOTE = ("Lead-1 outlook of SWS involuntary hunger in Balance Luzon (Luzon outside Metro Manila; CALABARZON ~34%). "
        "Regional only: province and LGU figures are vulnerability-adjusted priorities, not measured or forecast hunger. "
        "Added alongside the existing dashboard model, which it does not replace.")


@lru_cache(maxsize=32)
def _read(path: str, mtime: float):
    p = Path(path)
    return json.loads(p.read_text()) if p.suffix == ".json" else pd.read_csv(p, dtype={"lgu_psgc": str, "province_code": str})


def _load(name: str, base: Path = OUT):
    p = base / name
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"{name} not generated yet (see docs/fi9/IMPLEMENTATION_AND_DEPLOYMENT.md)")
    return _read(str(p), p.stat().st_mtime)


def _records(df):
    return json.loads(df.to_json(orient="records"))


@router.get("/quarters")
def quarters(date: str | None = None):
    """Issue and target quarter for a date (default: the serving clock). Lead 1 = the next calendar quarter."""
    try:
        d = pd.Timestamp(date) if date else today()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid date {date!r}") from exc
    return {"date": d.date().isoformat(), **Q.lead1(d)}


@router.get("/outlook")
def outlook():
    f = _load("forecast.json")
    now = Q.lead1(today())
    if f.get("status") == "unavailable":
        raise HTTPException(status_code=503, detail={"status": "unavailable", "reason": f.get("reason"), "reissue": REISSUE})
    if f["issue_quarter"] != now["issue_quarter"]:
        raise HTTPException(status_code=503, detail={
            "status": "stale", "reason": f"the stored forecast was issued in {f['issue_quarter']} for {f['target_quarter']}; "
                                         f"the current quarter is {now['current_quarter']}", "reissue": REISSUE})
    return {"note": NOTE, "served_by": VERSION, **f, **_class_and_news(f)}


def _class_and_news(f: dict) -> dict:
    """Both-class track record of the served model (FI9-Z) and the news status at this issue timing (FI9-X).

    Read from saved evaluations; nothing is computed from outcomes on request. Empty when the files are absent."""
    out: dict = {}
    if f.get("forecast", {}).get("p_high") is not None:
        out["p_low"] = round(1 - f["forecast"]["p_high"], 2)
    z = OUT.parent.parent / "fi9z" / "out" / "evaluation.json"
    if z.exists():
        e = _read(str(z), z.stat().st_mtime)
        m = e["evaluation"]["OP1"]["C0 damped persistence (production)"]
        c = m["full"]
        req = e.get("class_requirements") or {}
        out["class_performance"] = {
            "period": "walk-forward, target quarters 2010-Q1 to 2026-Q3", "n_quarters": c["n"], "n_high": c["n_high"], "n_low": c["n_low"],
            "high_caught": c["tp"], "high_missed": c["fn"], "false_high": c["fp"], "low_correct": c["tn"],
            "high_recall": round(c["high_recall"], 2), "high_precision": round(c["high_precision"], 2),
            "low_recall": round(c["low_recall"], 2), "low_precision": round(c["low_precision"], 2),
            "balanced_accuracy": round(c["balanced_accuracy"], 2), "macro_f1": round(c["macro_f1"], 2), "accuracy": round(c["accuracy"], 2),
            "requirements_failed": [k for k, ok in m["checks"].items() if not ok],
            "plain": (f"In {c['n']} past quarters it caught {c['tp']} of {c['n_high']} HIGH quarters and raised {c['fp']} false alarms in "
                      f"{c['n_low']} LOW quarters. It misses too many HIGH quarters to meet the project's HIGH-recall requirement (0.60), "
                      "and it is not better than simply repeating the latest reading."), **req}
    x = OUT.parent.parent / "fi9x" / "out" / "challenger_register.jsonl"
    if x.exists():
        from app.fi9 import prospective as PR
        recs = [r for r in PR.read(x) if r["origin"] == "OP1" and r["target_quarter"] == f.get("target_quarter")]
        if recs:
            out["news_context"] = {"news_stress_index_z": recs[0].get("news_index_z"),
                                   "status": "News is processed and shown as context. At this issue timing it has not improved the "
                                             "forecast over the latest reading, so it is not used to set the outlook (FI9-X).",
                                   "lightgbm_with_news_p_high": recs[0]["models"].get("LightGBM (government + news R1)", {}).get("p_high")}
    return out


@router.get("/evaluation")
def evaluation(period: str = Query("full", pattern="^(full|development|test|full_without_sawtooth)$")):
    ev = _load("lead1_evaluation.json")
    return {"note": NOTE, "protocol_sha256": ev["protocol_sha256"], "selection": ev["selection"],
            "reproduces_fi7_lead1": ev["reproduces_fi7_lead1"], "sawtooth_quarters": ev["sawtooth_quarters"],
            "period": period, **ev["periods"][period]}


@router.get("/model")
def model():
    return {"note": NOTE, "artifact": _load("lead1_model.json", MODEL), "protocol": _load("PROTOCOL_LOCK.json")}


@router.get("/audit")
def audit():
    return _load("audit.json")


@router.get("/provincial-measurements")
def provincial_measurements():
    """Historical provincial survey measurements, separate from the regional forecast and from the LGU priority."""
    base = OUT.parent.parent / "fi_labels" / "clean"
    hf = _load("published_hfias_2015_calabarzon.csv", base)
    wb = _load("owner_workbook_records_verified.csv", base)
    keep = ["record_id", "province", "reference_year", "label_name", "label_value", "unit", "verification_status_aipheed",
            "primary_value", "verification_source"]
    return {"note": "Measured at survey dates; not forecasts and not quarterly. HFIAS (2015) and FIES (2023, regional only) are "
                    "different instruments and are not comparable. Subsistence incidence is income-based food poverty, not "
                    "experienced food insecurity. ENNS provincial values are unverified secondary figures.",
            "fnri_2015_hfias": _records(hf),
            "food_insecurity_records": _records(wb[~wb["record_id"].str.startswith("PSA")][keep]),
            "food_poverty_records": _records(wb[wb["record_id"].str.startswith("PSA")][keep])}


@router.get("/register")
def register():
    """The append-only prospective register (hash-chained) and any scores of published targets."""
    from app.fi9 import prospective as PR
    recs = PR.read()
    scores = json.loads(PR.SCORES.read_text()) if PR.SCORES.exists() else {"n_scored": 0}
    return {"intact": PR.verify(), "n_records": len(recs), "records": recs, "scores": scores}


@router.get("/priority/alternatives")
def priority_alternatives(province: str | None = None):
    """Read-only comparison of weighting scenarios (FI9-X validation). The served ranking stays /fi9/priority."""
    base = OUT.parent.parent / "fi9x" / "out"
    j = _load("priority_validation.json", base)
    lg = _load("priority_alternatives_lgu.csv", base)
    if province:
        lg = lg[lg["province_name"].str.lower() == province.lower()]
        if lg.empty:
            raise HTTPException(status_code=404, detail=f"unknown province {province}")
    return {"note": "Comparison only, not the served ranking. Provincial validation: FNRI 2015 HFIAS, one wave, five provinces; "
                    "no LGU-level food-insecurity outcome exists. Served since 2026-11-03 (owner-approved): moderate poverty "
                    "weighting (0.65/0.35) for provinces; equal weights kept for LGUs "
                    "(docs/fi9x/FI9X_POVERTY_WEIGHTING_VALIDATION_REPORT.md).",
            "formula": j["formula"], "provinces": _records(_load("priority_alternatives_province.csv", base)),
            "provincial_validation": {k: v["mod_sev"] for k, v in j["provincial"]["scenarios"].items()},
            "lgus": _records(lg)}


@router.get("/priority")
def priority(province: str | None = None, lgu_psgc: str | None = None, limit: int = Query(142, ge=1, le=142)):
    t = _load("lgu_priority.csv")
    if province:
        t = t[t["province_name"].str.lower() == province.lower()]
        if t.empty:
            raise HTTPException(status_code=404, detail=f"unknown province {province}")
    if lgu_psgc:
        t = t[t["lgu_psgc"] == lgu_psgc]
        if t.empty:
            raise HTTPException(status_code=404, detail=f"unknown LGU code {lgu_psgc}")
    return {"note": NOTE, "n": int(len(t)), "provinces": _records(_load("province_priority.csv")), "rows": _records(t.head(limit))}
