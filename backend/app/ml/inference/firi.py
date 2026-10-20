"""
app/ml/inference/firi.py
------------------------
aiPHeed Food-Insecurity Risk Index (FIRI v1), frozen in
aipheed-backend-aligned/experiments/FINAL_Thesis_System/FIRI_PROTOCOL.md (sha in runner/FIRI_PROTOCOL_SHA256.txt).

A proxy composite on a 0-1 scale (not a probability) of the relative risk that households in a province face food
insecurity in the Lead-2 target quarter, from six equally weighted domains: A affordability, V vulnerability, C climate
and production, E household economy (national), N news (FSSI-v3), H regional hunger (Balance Luzon). Continuous
indicators are scored clip((x - P10) / (P90 - P10), 0, 1) with P10/P90 from the 2021-2022 window
(data/thesis/firi_anchors.json); probabilities and the official hazard flag are used as they are. Missing indicators
are dropped, never zero; FIRI needs >= 4 of 6 domains; HIGH at FIRI >= 0.5.

The same functions build the evaluation history (runner) and the served value (thesis_system): training/serving parity.
"""
from __future__ import annotations

import csv
import functools
import json
import math
import os
from pathlib import Path

ANCHORS = Path(os.getenv("AIPHEED_FIRI_ANCHORS", "data/thesis/firi_anchors.json"))
VULN = Path("data/inputs/lgu_vulnerability.csv")
PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
             "PH040500000": "Batangas"}
HEADLINE_P60 = {"PH040100000": 5.013333, "PH040200000": 4.653333, "PH040300000": 5.06,
                "PH040400000": 6.073333, "PH040500000": 5.546667}
DOMAINS = {"A": "Affordability", "V": "Household vulnerability", "C": "Climate and food production",
           "E": "Household economy (national)", "N": "News warning signals", "H": "Regional hunger (Balance Luzon)"}
CONTINUOUS = ("A2", "A3", "C2", "C3", "C4", "E1", "E2", "N1")
LABELS = {"A1": "Food-price-pressure forecast (LightGBM, Lead-2)", "A2": "Headline inflation above the usual level",
          "A3": "Wholesale rice price change", "V1": "Poverty and population density",
          "C1": "PAGASA El Nino alert/advisory in force", "C2": "Typhoons within 300 km", "C3": "Palay/corn production drop",
          "C4": "Fisheries production drop", "E1": "Unemployment change (national)", "E2": "Remittance decline (national)",
          "N1": "Food Stress Sentiment Index (FSSI-v3)", "H1": "Regional hunger outlook above 11.3%"}
DOMAIN_OF = {k: k[0] for k in LABELS}
# Amendment 1: V1 is a static structural profile at every origin (publication-timing deviation, disclosed); the
# original rule (V1 missing before 2025-07-01) is the strict sensitivity (v_strict=True)
V_AVAILABLE_FROM = "2025-07-01"
INCOMPLETE_TYPHOON_QUARTERS = {"2026-Q3"}
THRESHOLD, MIN_DOMAINS = 0.5, 4


def _f(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


@functools.lru_cache(maxsize=1)
def vulnerability() -> dict[str, float]:
    """V1 per province: 0.6 x poverty_norm + 0.4 x density_norm, min-max across the five provinces."""
    acc: dict[str, dict] = {}
    names = {v: k for k, v in PROVINCES.items()}
    with open(VULN, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a = acc.setdefault(names[r["province"]], {"pov": [], "pop": 0.0, "area": 0.0})
            pv = _f(r["poverty_lgu_estimate"])
            if pv is not None:
                a["pov"].append(pv)
            a["pop"] += float(r["population_2024"])
            a["area"] += float(r["land_area_km2"])
    pov = {p: sum(a["pov"]) / len(a["pov"]) for p, a in acc.items()}
    den = {p: a["pop"] / a["area"] for p, a in acc.items()}

    def mm(d):
        lo, hi = min(d.values()), max(d.values())
        return {k: (v - lo) / (hi - lo) for k, v in d.items()}
    pn, dn = mm(pov), mm(den)
    return {p: 0.6 * pn[p] + 0.4 * dn[p] for p in acc}


def raw_indicators(code: str, feat: dict, p_price: float | None, issue_date: str, origin_quarter: str,
                   hazard: bool | None, hunger_p: float | None, fssi: dict | None, v_strict: bool = False) -> dict[str, dict]:
    """Raw x and status of every indicator for one province at one issue date (PROTOCOL section 2 and 5)."""
    out = {}

    def put(k, x, status=None, note=""):
        out[k] = {"x": x, "status": status or ("observed" if x is not None else "missing"), "note": note}

    put("A1", _f(p_price))
    fn, gap = _f(feat.get("F_now")), _f(feat.get("gap_now"))
    put("A2", None if fn is None or gap is None else (fn - gap) - HEADLINE_P60[code])
    put("A3", _f(feat.get("rice_whsl_yoy")))
    if not v_strict or issue_date >= V_AVAILABLE_FROM:
        put("V1", vulnerability()[code])
    else:
        put("V1", None, "unavailable_at_issue", "PSA SAE 2021 / POPCEN 2024 assumed available from 2025-07-01")
    put("C1", None if hazard is None else (1.0 if hazard else 0.0))
    if origin_quarter in INCOMPLETE_TYPHOON_QUARTERS:
        put("C2", None, "incomplete", "quarter in progress when the data were fetched")
    else:
        put("C2", _f(feat.get("tc_count")))
    crops = [v for v in (_f(feat.get("palay_yoy")), _f(feat.get("corn_yoy"))) if v is not None]
    put("C3", -min(crops) if crops else None)
    fy = _f(feat.get("fish_yoy"))
    put("C4", None if fy is None else -fy)
    put("E1", _f(feat.get("ur_yoy")))
    ry = _f(feat.get("remit_usd_yoy"))
    put("E2", None if ry is None else -ry)
    if fssi and fssi.get("status") == "SUFFICIENT" and fssi.get("fssi") is not None:
        put("N1", float(fssi["fssi"]))
    else:
        put("N1", None, "too_few_articles" if fssi and fssi.get("n") else "missing",
            f"{(fssi or {}).get('n', 0)} articles (FSSI needs at least 5)")
    put("H1", _f(hunger_p))
    return out


@functools.lru_cache(maxsize=2)
def _anchors(path: str, mtime: int) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def anchors() -> dict:
    return _anchors(str(ANCHORS), ANCHORS.stat().st_mtime_ns)


def score(raw: dict[str, dict], anc: dict | None = None) -> dict:
    """Indicator scores, domain scores, FIRI, class and the explanation (PROTOCOL sections 3-4)."""
    anc = anc or anchors()
    ind = {}
    for k, r in raw.items():
        x = r["x"]
        s = None
        if x is not None:
            if k in CONTINUOUS:
                a = anc["indicators"].get(k)
                if a and a.get("usable"):
                    s = min(1.0, max(0.0, (x - a["p10"]) / (a["p90"] - a["p10"])))
            else:
                s = min(1.0, max(0.0, x))
        ind[k] = {**r, "score": s, "label": LABELS[k], "domain": DOMAIN_OF[k]}
    dom = {}
    for d in DOMAINS:
        ss = [v["score"] for v in ind.values() if v["domain"] == d and v["score"] is not None]
        dom[d] = sum(ss) / len(ss) if ss else None
    avail = {d: v for d, v in dom.items() if v is not None}
    firi = (sum(avail.values()) / len(avail)) if len(avail) >= MIN_DOMAINS else None
    shares = ({d: (v / len(avail)) / firi if firi else 0.0 for d, v in avail.items()} if firi else {})
    return {"firi": firi, "class": None if firi is None else ("HIGH" if firi >= THRESHOLD else "LOW"),
            "domains": dom, "domainsAvailable": len(avail), "shares": shares, "indicators": ind}


# ------------------------------------------------------------------------------------------------ FIRI v2 (FIRI2_PROTOCOL.md)
# Expanding-window mid-rank percentile normalization against the indicator's own values at strictly earlier origins
# (>= 8, else missing: insufficient_history), optional domain weights (redundancy or walk-forward evidence weights).
V2_MIN_PRIOR = 8
NATIONAL = ("C1", "C2", "E1", "E2", "H1")       # one value per origin (identical for the five provinces)


def percentile(x: float, prior: list[float]) -> float:
    """Mid-rank percentile of x among earlier values: (#below + 0.5 x #equal) / n."""
    below = sum(1 for v in prior if v < x)
    equal = sum(1 for v in prior if v == x)
    return (below + 0.5 * equal) / len(prior)


def score_v2(raw: dict[str, dict], prior: dict[str, list[float]], weights: dict[str, float] | None = None) -> dict:
    """FIRI v2: indicator scores (percentile for continuous indicators, 0-1 indicators as they are), domain scores,
    the weighted index over the available domains (>= 4), class and exact shares."""
    ind = {}
    for k, r in raw.items():
        x, s, status = r["x"], None, r["status"]
        if x is not None:
            if k in CONTINUOUS:
                pv = prior.get(k) or []
                if len(pv) >= V2_MIN_PRIOR:
                    s = percentile(float(x), pv)
                else:
                    status = "insufficient_history"
            else:
                s = min(1.0, max(0.0, float(x)))
        ind[k] = {**r, "status": status, "score": s, "label": LABELS[k], "domain": DOMAIN_OF[k],
                  "priorValues": len(prior.get(k) or []) if k in CONTINUOUS else None}
    dom = {}
    for d in DOMAINS:
        ss = [v["score"] for v in ind.values() if v["domain"] == d and v["score"] is not None]
        dom[d] = sum(ss) / len(ss) if ss else None
    avail = {d: v for d, v in dom.items() if v is not None}
    w = {d: (weights or {}).get(d, 1.0) if weights else 1.0 for d in avail}
    tot = sum(w.values())
    wn = {d: w[d] / tot for d in avail} if tot > 0 else {d: 1.0 / len(avail) for d in avail} if avail else {}
    firi = sum(wn[d] * avail[d] for d in avail) if len(avail) >= MIN_DOMAINS else None
    shares = {d: wn[d] * avail[d] / firi for d in avail} if firi else {}
    return {"firi": firi, "class": None if firi is None else ("HIGH" if firi >= THRESHOLD else "LOW"),
            "domains": dom, "domainsAvailable": len(avail), "shares": shares, "weights": wn, "indicators": ind,
            "version": "v2"}
