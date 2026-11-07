"""
app/quarterly/alerts_e168.py
----------------------------
Early-warning alert CANDIDATES from the approved E168 food-insecurity forecast (Objective 5: "forecast maps and
early-warning alerts"), replacing the E31 rules while E168 is the registry's production model.

Rule (documented on every candidate):
  E168_HIGH   the province's E168 probability of HIGH (HFIAS moderate+severe >= 50 %) is >= 0.50 at a lead that meets the
              acceptance rule (Leads 1-3).
A candidate is only STAGED. It reaches the public dashboard only after a DA Region IV-A administrator confirms it
(app/api/v1/alerts.py) and is shown as a model-generated warning for review, never as a confirmed emergency.
Staging is idempotent (same quarter, province and reason are never inserted twice).

    python -m app.quarterly.alerts_e168          -> prints the candidates
"""
from __future__ import annotations

import json
import sys

REASON = "E168_HIGH"
P_HIGH = 0.50
STATEMENT = ("Model-generated early-warning candidate (E168 food-insecurity forecast) for review by DA Region IV-A. Not "
             "an official food-insecurity classification and not a confirmed emergency.")


def candidates() -> list[dict]:
    from app.ml.inference import e168_system as E
    if not E.active():
        return []
    rl = E.reliable_lead() or 0
    out = []
    for (code, quarter), r in sorted(E.rows().items(), key=lambda kv: (kv[0][1], kv[0][0])):
        p = float(r["probability"])
        if int(r["lead"]) <= rl and p >= P_HIGH:
            out.append({"quarter": quarter, "province_code": code, "alert_reason": REASON, "threshold_exceeded": True,
                        "prev_risk_probability": None, "risk_delta": None,
                        "evidence": {"lead": int(r["lead"]), "p_high": p, "score_pct": float(r["score_pct"])},
                        "statement": STATEMENT})
    return out


async def stage(db) -> dict:
    from sqlalchemy import select

    from app.db.models import AlertRecord
    from app.db.repository.alert_repo import AlertRepository

    repo = AlertRepository(db)
    res = {"staged": [], "existing": []}
    for c in candidates():
        q = select(AlertRecord).where(AlertRecord.quarter == c["quarter"], AlertRecord.province_code == c["province_code"],
                                      AlertRecord.alert_reason == c["alert_reason"])
        if (await db.execute(q)).scalar_one_or_none() is not None:
            res["existing"].append(c)
            continue
        await repo.insert({k: c[k] for k in ("quarter", "province_code", "alert_reason", "threshold_exceeded",
                                             "prev_risk_probability", "risk_delta")})
        res["staged"].append(c)
    return res


async def stage_on_startup() -> None:
    """Called from app.main's lifespan; never blocks startup."""
    try:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            res = await stage(db)
        print(f"E168 alerts: {len(res['staged'])} staged, {len(res['existing'])} already present")
    except Exception as exc:                 # a missing table or database must not stop the API
        print(f"E168 alerts not staged: {exc}")


if __name__ == "__main__":
    print(json.dumps(candidates(), indent=1)) if sys.argv[1:] in ([], ["list"]) else None
