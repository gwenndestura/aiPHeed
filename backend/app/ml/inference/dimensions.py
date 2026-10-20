"""E72: the served FIRI v2 estimate decomposed along the food-security framework (FAO 1996/2006 dimensions; IPC 3.1
separation of outcome evidence from contributing factors). Nothing here changes the served number: every indicator's
exact push on FIRI v2 (thesis_system.pushes, weight x (score - 0.5) / indicators in its domain) is re-grouped by the
food-security role of the indicator, so the dimension pushes add up exactly to FIRI - 0.5.

Roles of the FIRI v2 indicators:
  ACCESS (economic access)        A1 food-price-pressure forecast, A2 headline inflation, A3 wholesale rice price,
                                  E1 unemployment change (national), E2 remittance decline (national)
  AVAILABILITY                    C3 palay/corn production drop, C4 fisheries production drop
  STABILITY (shock exposure)      C1 El Nino alert, C2 typhoons within 300 km
  UTILIZATION                     no indicator in the data: reported as not observed, never imputed
  VULNERABILITY (cross-cutting)   V1 poverty and population density (static structural profile)
  OUTCOME EVIDENCE (regional)     H1 regional hunger outlook (SWS Balance Luzon, the same for every province)
  NEWS SIGNAL                     N1 FSSI-v3 (reporting, not a measurement of conditions)
"""
from __future__ import annotations

ROLE_OF = {"A1": "ACCESS", "A2": "ACCESS", "A3": "ACCESS", "E1": "ACCESS", "E2": "ACCESS",
           "C3": "AVAILABILITY", "C4": "AVAILABILITY", "C1": "STABILITY", "C2": "STABILITY",
           "V1": "VULNERABILITY", "H1": "OUTCOME", "N1": "NEWS"}
ORDER = ("ACCESS", "AVAILABILITY", "STABILITY", "UTILIZATION", "VULNERABILITY", "OUTCOME", "NEWS")
LABEL = {"ACCESS": "Access (affordability, jobs, remittances)", "AVAILABILITY": "Availability (crop and fish production)",
         "STABILITY": "Stability (typhoon and El Nino shocks)", "UTILIZATION": "Utilization (nutrition, water, health)",
         "VULNERABILITY": "Vulnerability (poverty and density)", "OUTCOME": "Observed regional hunger (SWS)",
         "NEWS": "News warning signals"}
KIND = {"ACCESS": "dimension", "AVAILABILITY": "dimension", "STABILITY": "dimension", "UTILIZATION": "dimension",
        "VULNERABILITY": "cross-cutting risk factor", "OUTCOME": "outcome evidence (regional)", "NEWS": "signal"}


def breakdown(res: dict) -> list[dict]:
    """Exact dimension pushes of a FIRI v2 result (the dict of thesis_system.firi_for)."""
    from app.ml.inference import thesis_system as T
    pu = T.pushes(res)
    out = []
    for role in ORDER:
        ks = [k for k, r in ROLE_OF.items() if r == role]
        obs = [k for k in ks if res["indicators"].get(k, {}).get("score") is not None]
        if role == "UTILIZATION":
            out.append({"key": role, "label": LABEL[role], "kind": KIND[role], "status": "not_observed", "push": None,
                        "indicators": []})
            continue
        out.append({"key": role, "label": LABEL[role], "kind": KIND[role],
                    "status": "observed" if obs else "missing",
                    "push": round(sum(pu.get(k, 0.0) for k in obs), 6) if obs else None,
                    "indicators": [{"key": k, "label": res["indicators"][k]["label"],
                                    "push": round(pu.get(k, 0.0), 6) if k in obs else None,
                                    "status": res["indicators"][k].get("status") or ("observed" if k in obs else "missing")}
                                   for k in ks if k in res["indicators"]]})
    return out


def shares(res: dict) -> dict[str, float]:
    """Share of the total absolute push carried by each role (0-1)."""
    b = [d for d in breakdown(res) if d["push"] is not None]
    tot = sum(abs(d["push"]) for d in b) or 1.0
    return {d["key"]: abs(d["push"]) / tot for d in b}


def without_outcome(res: dict) -> float | None:
    """FIRI v2 recomputed without the regional hunger domain (weights renormalised over the other available domains):
    how far the provincial evidence alone would place the province. Diagnostic only; never served as the estimate."""
    from app.ml.inference import thesis_system as T
    w = T._norm_weights(res)
    doms = {d: v for d, v in res["domains"].items() if v is not None and d != "H" and d in w}
    if len(doms) < 3:
        return None
    tot = sum(w[d] for d in doms)
    return sum(w[d] * v for d, v in doms.items()) / tot


def text(res: dict) -> str:
    b = breakdown(res)
    parts = []
    for d in b:
        if d["status"] == "not_observed":
            parts.append(f"{d['label']}: not observed (no data; not counted)")
        elif d["push"] is None:
            parts.append(f"{d['label']}: no value at the issue date (missing is not zero)")
        else:
            word = "raises" if d["push"] > 0.0005 else "lowers" if d["push"] < -0.0005 else "is neutral for"
            parts.append(f"{d['label']} {word} the index ({d['push']:+.3f})")
    wo = without_outcome(res)
    tail = (f" Without the regional hunger reading, the provincial evidence alone would give {wo:.2f}." if wo is not None else "")
    return ("BY FOOD-SECURITY DIMENSION (exact split of the index minus 0.5; contributing factors, not measured "
            "outcomes): " + "; ".join(parts) + "." + tail)
