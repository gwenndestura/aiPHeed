"""
E168 early-warning alert candidates (Objective: forecast maps and early-warning alerts), from the served E168 history.

Rules (thresholds from /config: alert 0.60):
  E168_REGIONAL_HIGH  mean P(HIGH) of the five provinces >= 0.60 for the quarter (one CALABARZON alert).
  E168_PROVINCE_HIGH  a province's P(HIGH) >= 0.60.
  E168_SUDDEN_RISE    a province's P(HIGH) rose by >= 0.20 from the previous quarter and is >= 0.65.
Candidates are only STAGED (same review queue as app/quarterly/alerts_e31.py). A DA Region IV-A administrator confirms or
dismisses each one; nothing reaches the public dashboard without confirmation.
"""
from __future__ import annotations

from app.quarterly.alerts_e31 import REGION_CODE
from app.services import e166_serving as SRV
from app.services import reference as ref

ALERT = 0.60
RISE_MIN, RISE_FLOOR = 0.20, 0.65
STATEMENT = ("Model-generated early-warning candidate from the thesis model E168, for review by DA Region IV-A. Not an "
             "official food-insecurity classification and not a confirmed emergency.")


def candidates(quarter: str) -> list[dict]:
    if quarter not in SRV.quarters():
        return []
    rows = {r["province"]: r["p_high"] for r in SRV._q(quarter)["forecasts"]}
    prev_q = SRV.previous(quarter)
    prev = {r["province"]: r["p_high"] for r in SRV._q(prev_q)["forecasts"]} if prev_q else {}
    out = []
    mean = sum(rows.values()) / len(rows)
    if mean >= ALERT:
        out.append({"quarter": quarter, "province_code": REGION_CODE, "alert_reason": "E168_REGIONAL_HIGH", "threshold_exceeded": True,
                    "prev_risk_probability": None, "risk_delta": None, "evidence": {"mean_p_high": round(mean, 4)}, "statement": STATEMENT})
    for name, p in rows.items():
        code = ref.province_code(name.lower())
        if p >= ALERT:
            out.append({"quarter": quarter, "province_code": code, "alert_reason": "E168_PROVINCE_HIGH", "threshold_exceeded": True,
                        "prev_risk_probability": None, "risk_delta": None, "evidence": {"p_high": p}, "statement": STATEMENT})
        p0 = prev.get(name)
        if p0 is not None and p - p0 >= RISE_MIN and p >= RISE_FLOOR:
            out.append({"quarter": quarter, "province_code": code, "alert_reason": "E168_SUDDEN_RISE", "threshold_exceeded": True,
                        "prev_risk_probability": p0, "risk_delta": round(p - p0, 4), "evidence": {"previous_quarter": prev_q},
                        "statement": STATEMENT})
    return out


async def stage(db, quarter: str) -> dict:
    """Insert candidates not already present (same quarter, area and reason). Idempotent."""
    from sqlalchemy import select

    from app.db.models import AlertRecord
    from app.db.repository.alert_repo import AlertRepository

    repo = AlertRepository(db)
    res = {"staged": [], "existing": []}
    for c in candidates(quarter):
        q = select(AlertRecord).where(AlertRecord.quarter == c["quarter"], AlertRecord.province_code == c["province_code"],
                                      AlertRecord.alert_reason == c["alert_reason"])
        if (await db.execute(q)).scalar_one_or_none() is not None:
            res["existing"].append(c)
            continue
        await repo.insert({k: c[k] for k in ("quarter", "province_code", "alert_reason", "threshold_exceeded",
                                             "prev_risk_probability", "risk_delta")})
        res["staged"].append(c)
    return res
