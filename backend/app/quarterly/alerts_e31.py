"""
app/quarterly/alerts_e31.py
---------------------------
Early-warning alert CANDIDATES from the E31 record (Objective 5: "forecast maps and early-warning alerts").

E31 found that nothing in the code base ever staged an alert (AlertRepository.insert had no caller), so the review
workflow (STAGED -> CONFIRMED / DISMISSED by a DA administrator, app/api/v1/alerts.py) could never produce one.

Evidence requirements (every rule must hold; documented on each candidate):
  REGIONAL_HUNGER_HIGH    P(regional SWS hunger above the threshold) >= 0.80 for the nowcast/forecast quarter.
                          ONE alert for CALABARZON, never five provincial copies: the hunger signal is regional.
  PROVINCE_PRICE_PRESSURE the province estimate is STRONG (P >= 0.80) AND its MEASURED relative food inflation in the
                          latest released quarter is at least +1.0 pp (the 75th percentile of all 2021-2026 province-
                          quarters: price pressure in the top quarter of its own history; PSA, province-specific).
  SUDDEN_RISE             the province estimate rose by >= 0.20 from the previous quarter's estimate OF THE SAME MODE
                          (a nowcast is never compared with an older, less informed forecast) and is >= 0.65.
  ROLLING_THRESHOLD       Rule 7 (Chapter III, p.49: "an alert will fire when a province's forecast exceeds the
                          rolling historical threshold"): the province estimate exceeds the 75th percentile of
                          its own previous published estimates (every earlier quarter's served estimate for that
                          province, made at an earlier origin; trailing, no look-ahead), with at least 4 of them.
A forecast-quarter candidate is dropped when the nowcast quarter already carries the same reason for the same area.
A candidate is only STAGED. It reaches the public dashboard only after a DA Region IV-A administrator confirms it,
and it is always shown as a model-generated warning for review, never as a confirmed food-security emergency or an
official finding.
"""
from __future__ import annotations

REGION_CODE = "PH040000000"
P_STRONG = 0.80
D_MIN_PP = 1.0
RISE_MIN = 0.20
RISE_FLOOR = 0.65
ROLLING_PCTL = 75
ROLLING_MIN_PRIOR = 4
REASON_TEXT = {
    "REGIONAL_HUNGER_HIGH": "Regional hunger: P(regional SWS hunger above the threshold) is at least 0.80.",
    "PROVINCE_PRICE_PRESSURE": ("Price pressure: the province estimate is at least 0.80 and its latest measured relative "
                                "food inflation is above +1.0 pp."),
    "SUDDEN_RISE": ("Sudden rise: the province estimate rose by at least 0.20 from the previous quarter's estimate of the "
                    "same mode and is at least 0.65."),
    "ROLLING_THRESHOLD": ("Rolling historical threshold (thesis Rule 7): the province estimate exceeds the 75th percentile "
                          "of its own previous published estimates (trailing, no look-ahead, at least 4 earlier quarters)."),
}


def rolling_threshold(rec: dict, quarter: str, code: str) -> dict | None:
    """The 75th percentile of a province's own previous published estimates: the served estimate of every earlier
    quarter (one row per quarter, as served), each made at an earlier origin. None with fewer than 4."""
    import numpy as np

    by_q = {}
    for q in rec["quarters"]:
        by_q.setdefault(q["quarter"], q)
    prior = [(x, by_q[x]["provinces"][code]["p_high"]) for x in sorted(by_q)
             if x < quarter and code in by_q[x]["provinces"]]
    if len(prior) < ROLLING_MIN_PRIOR:
        return None
    return {"threshold": round(float(np.percentile([p for _, p in prior], ROLLING_PCTL)), 4), "n_prior": len(prior),
            "prior_quarters": [prior[0][0], prior[-1][0]], "percentile": ROLLING_PCTL}
STATEMENT = ("Model-generated early-warning candidate for review by DA Region IV-A. Not an official food-insecurity "
             "classification and not a confirmed emergency.")


def candidates(rec: dict, target_quarter: str | None = None) -> list[dict]:
    """target_quarter (default: the dashboard's dynamic target, app/quarterly/target.py) limits staging to the quarter
    every other surface shows; pass "all" for every nowcast/forecast quarter in the record."""
    if target_quarter is None:
        from app.quarterly.target import forecast_target

        target_quarter = forecast_target()["target_quarter"]
    from app.quarterly.target import default_lead   # = max_lead() unless the lead-2 preview is on: no lead-2 alerts

    qs = [q for q in rec["quarters"] if q["mode"] in ("NOWCAST", "FORECAST") and q.get("lead", 1) <= default_lead()
          and (target_quarter == "all" or q["quarter"] == target_quarter)]
    by_q = {}
    for q in rec["quarters"]:
        by_q.setdefault(q["quarter"], q)
    order = sorted(by_q)
    out = []
    pn = rec["provinces_now"]
    for q in qs:
        if (q.get("p_regional_H_above_threshold") or 0) >= P_STRONG:
            out.append({"quarter": q["quarter"], "province_code": REGION_CODE, "alert_reason": "REGIONAL_HUNGER_HIGH",
                        "threshold_exceeded": True, "prev_risk_probability": None, "risk_delta": None,
                        "evidence": {"mode": q["mode"], "p_regional_H_above_threshold": q["p_regional_H_above_threshold"],
                                     "H_forecast": q["H_forecast"], "threshold": q["threshold"],
                                     "latest_round": rec["regional_hunger"]["latest"]}, "statement": STATEMENT})
        i = order.index(q["quarter"])
        prev = by_q[order[i - 1]] if i > 0 else None
        if prev is not None and (prev["mode"] == "NOWCAST") != (q["mode"] == "NOWCAST"):
            prev = None
        for code, v in q["provinces"].items():
            d_meas = pn.get(code, {}).get("measured_relative_food_inflation_pp", {})
            d_last = list(d_meas.values())[-1] if d_meas else None
            if v["p_high"] >= P_STRONG and d_last is not None and d_last > D_MIN_PP:
                out.append({"quarter": q["quarter"], "province_code": code, "alert_reason": "PROVINCE_PRICE_PRESSURE",
                            "threshold_exceeded": True, "prev_risk_probability": None, "risk_delta": None,
                            "evidence": {"mode": q["mode"], "p_high": v["p_high"], "measured_D_pp_latest": d_last,
                                         "drivers": v.get("drivers")}, "statement": STATEMENT})
            roll = rolling_threshold(rec, q["quarter"], code)
            if roll is not None and v["p_high"] > roll["threshold"]:
                out.append({"quarter": q["quarter"], "province_code": code, "alert_reason": "ROLLING_THRESHOLD",
                            "threshold_exceeded": True, "prev_risk_probability": None, "risk_delta": None,
                            "evidence": {"mode": q["mode"], "p_high": v["p_high"], **roll,
                                         "definition": REASON_TEXT["ROLLING_THRESHOLD"]}, "statement": STATEMENT})
            if prev is not None and code in prev["provinces"]:
                p0 = prev["provinces"][code]["p_high"]
                if v["p_high"] - p0 >= RISE_MIN and v["p_high"] >= RISE_FLOOR:
                    out.append({"quarter": q["quarter"], "province_code": code, "alert_reason": "SUDDEN_RISE",
                                "threshold_exceeded": True, "prev_risk_probability": p0,
                                "risk_delta": round(v["p_high"] - p0, 4),
                                "evidence": {"mode": q["mode"], "previous_quarter": prev["quarter"],
                                             "previous_mode": prev["mode"]}, "statement": STATEMENT})
    for c in out:
        c["reason_text"] = REASON_TEXT[c["alert_reason"]]
    now_keys = {(c["province_code"], c["alert_reason"]) for c in out if c["evidence"]["mode"] == "NOWCAST"}
    return [c for c in out if c["evidence"]["mode"] == "NOWCAST" or (c["province_code"], c["alert_reason"]) not in now_keys]


async def stage(db, rec: dict, target_quarter: str | None = None) -> dict:
    """Insert candidates not already present (same quarter, province and reason). Idempotent."""
    from sqlalchemy import select

    from app.db.models import AlertRecord
    from app.db.repository.alert_repo import AlertRepository

    repo = AlertRepository(db)
    res = {"staged": [], "existing": []}
    for c in candidates(rec, target_quarter):
        q = select(AlertRecord).where(AlertRecord.quarter == c["quarter"], AlertRecord.province_code == c["province_code"],
                                      AlertRecord.alert_reason == c["alert_reason"])
        if (await db.execute(q)).scalar_one_or_none() is not None:
            res["existing"].append(c)
            continue
        row = {k: c[k] for k in ("quarter", "province_code", "alert_reason", "threshold_exceeded",
                                 "prev_risk_probability", "risk_delta")}
        await repo.insert(row)
        res["staged"].append(c)
    return res
