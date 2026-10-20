"""
app/ml/inference/thesis_system.py
---------------------------------
The final aiPHeed thesis system (AIPHEED_LEAD2_MODEL=thesis). FINAL_THESIS_SYSTEM_REPORT.md documents every choice.

Outputs, kept separate and named for what they are:
  1. Exploratory food-price-pressure score (the map colour, the province score and the LGU index): the E56-TUNED
     LightGBM Lead-2 record (data/e58/e58_record.json), unchanged. Its label T43 equals provincial food-price pressure on
     every evaluated row, so it is NOT a food-insecurity probability.
  2. Regional hunger outlook: SWS Balance Luzon involuntary hunger, the only food-insecurity outcome measured every
     quarter; Lead-2 outlook = the latest approved round posted before the issue date (no method beat it in E69), with
     an interval from its own past Lead-2 errors. Computed at runtime from data/inputs/sws_rounds.csv.
  3. Food-insecurity risk outlook per province (E69 Scale 2, convergence of evidence), computed at runtime from the
     served record: ELEVATED = hunger expected above 11.3% AND (affordability hazard OR El Nino advisory with a local
     palay/corn drop of 10% or more); WATCH = hunger expected high AND an El Nino advisory only. Not a probability.
  4. News evidence (Objective 1): the improved pipeline (classifier v2, de-duplication), FSSI-v3 for the origin
     quarter (shown only when SUFFICIENT), and the province-quarter BERTopic topics. A warning signal, not proof.
  5. Model evaluation (Objectives 2 and 4): data/thesis/final_evaluation.json, computed from sealed predictions.

No silent fallback: with AIPHEED_STRICT_MODEL=1 (the thesis-demo configuration) the API refuses to start when a
required artifact is missing or fails its integrity check (validate()).
"""
from __future__ import annotations

import csv
import functools
import json
import math
import os
from datetime import date
from pathlib import Path

from app.ml.inference import climate_watch as CW
from app.ml.inference import e41_lead2 as LEAD2

MODE = "thesis"
SWS = Path(os.getenv("AIPHEED_SWS_ROUNDS", "data/inputs/sws_rounds.csv"))
EVALUATION = Path(os.getenv("AIPHEED_FINAL_EVALUATION", "data/thesis/final_evaluation.json"))
TOPIC_PROPS = Path("data/news_v3/topic_proportions.csv")
TOPIC_INFO = Path("data/news_v3/topic_info.csv")
E69_DISCLOSURE = Path(os.getenv("AIPHEED_E69_DISCLOSURE", "data/e69/e69_disclosure.json"))
FIRI_HISTORY = Path(os.getenv("AIPHEED_FIRI_HISTORY", "data/thesis/firi_history.csv"))
FIRI_EVALUATION = Path(os.getenv("AIPHEED_FIRI_EVALUATION", "data/thesis/firi_evaluation.json"))
FEATURES_DIR = Path("data/e56/model")
REQUIRED = (LEAD2.RECORD_E58, SWS, EVALUATION, TOPIC_PROPS, TOPIC_INFO, E69_DISCLOSURE, CW.INPUTS,
            Path("data/inputs/lgu_vulnerability.csv"), FIRI_HISTORY, FIRI_EVALUATION, Path("data/thesis/firi_anchors.json"))
HUNGER_LINE, SIGMA_DEFAULT = 11.3, 4.0
# E68 T-AFF headline P60 (2021-Q1..2022-Q4, numpy.percentile), the province's usual headline inflation
HEADLINE_USUAL = {"PH040100000": 5.013333, "PH040200000": 4.653333, "PH040300000": 5.06,
                  "PH040400000": 6.073333, "PH040500000": 5.546667}
MODEL_NAME = ("aiPHeed thesis system v2: Food-Insecurity Risk Index FIRI v1 (proxy composite of affordability, vulnerability, "
              "climate/production, household economy and regional hunger; Lead-2) with the E56-TUNED LightGBM "
              "food-price-pressure forecast as its affordability component")


def active() -> bool:
    return LEAD2.mode() == MODE


def relabel(text: str | None) -> str | None:
    """The record's stored explanation says 'probability of HIGH food-insecurity risk'; in the thesis system the number
    is named for what it is (the record file itself is not changed)."""
    if not text:
        return text
    return (text.replace("estimated probability of HIGH food-insecurity risk", "exploratory food-price-pressure score")
            .replace("probability of HIGH food-insecurity risk", "exploratory food-price-pressure score"))


def validate() -> list[str]:
    """Problems that must stop a strict thesis-demo start (empty list = ready)."""
    probs = [f"missing {p}" for p in REQUIRED if not Path(p).exists()]
    if not probs:
        try:
            rec = LEAD2.record()
            f = FEATURES_DIR / f"features_{rec['targetQuarter'].replace('-', '')}.csv"
            if not f.exists():
                probs.append(f"missing {f} (the model's inference features for the served target)")
            if firi_for(rec, rec["targetQuarter"], next(iter(rec["provinces"]))) is None:
                probs.append("FIRI not computable for the served target")
        except Exception as e:  # integrity / format
            probs.append(f"record: {e}")
        try:
            json.loads(EVALUATION.read_text(encoding="utf-8"))["objective2"]
        except Exception as e:
            probs.append(f"final evaluation: {e}")
        try:
            from app.news import pipeline_v3 as P3
            if P3.classifier_sha() != P3.CLASSIFIER_V2_SHA256:
                probs.append("news classifier v2 differs from its frozen version")
        except Exception as e:
            probs.append(f"news pipeline: {e}")
    return probs


# ------------------------------------------------------------------------------------------------ quarters
def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def issue_of(t: int) -> str:
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 1).isoformat()


# ------------------------------------------------------------------------------------------------ regional hunger
@functools.lru_cache(maxsize=2)
def _rounds(path: str, mtime: int) -> tuple[tuple[int, float, str], ...]:
    with open(path, newline="", encoding="utf-8") as f:
        return tuple((qi(r["quarter"]), float(r["H"]), r["published"][:10]) for r in csv.DictReader(f)
                     if str(r["definition_A"]) == "True")


def _posted(issue: str) -> dict[int, float]:
    rows = [r for r in _rounds(str(SWS), SWS.stat().st_mtime_ns) if r[2] < issue]
    acc: dict[int, list[float]] = {}
    for q, h, _ in rows:
        acc.setdefault(q, []).append(h)
    return {q: sum(v) / len(v) for q, v in sorted(acc.items())}


def _base(hs: dict[int, float], t: int) -> tuple[float | None, int | None]:
    ks = [q for q in hs if q <= t]
    return (hs[ks[-1]], ks[-1]) if ks else (None, None)


def regional_hunger(t: int, lead: int = 2) -> dict:
    """Lead-2 outlook of SWS Balance Luzon hunger at origin t (issue = first day of quarter t+1): the latest approved
    round posted before the issue date, sigma = RMSE of that rule's own past Lead-2 errors known at the issue (>= 4
    pairs, else 4.0 points). Identical to E69 R0 (checked against the sealed E69 outlook by a test)."""
    issue = issue_of(t)
    hs = _posted(issue)
    b, bq = _base(hs, t)
    errs = []
    for tp in range(qi("2021-Q2"), t - lead + 1):             # pairs (t', t'+lead) whose target was posted by now
        if tp + lead not in hs:
            continue
        bp, _ = _base(_posted(issue_of(tp)), tp)
        if bp is not None:
            errs.append(hs[tp + lead] - bp)
    sigma = math.sqrt(sum(e * e for e in errs) / len(errs)) if len(errs) >= 4 else SIGMA_DEFAULT
    if b is None:
        return {"issueDate": issue, "targetQuarter": qs(t + lead), "status": "INSUFFICIENT DATA"}
    p = 1 - 0.5 * (1 + math.erf((HUNGER_LINE - b) / (sigma * math.sqrt(2))))
    return {"issueDate": issue, "targetQuarter": qs(t + lead), "status": "OK", "latestReading": round(b, 1),
            "latestReadingQuarter": qs(bq), "dataAgeQuarters": t - bq, "expectedHunger": round(b, 1),
            "interval80": [round(b - 1.2816 * sigma, 1), round(b + 1.2816 * sigma, 1)], "sigma": round(sigma, 3),
            "probabilityAbove11_3": round(p, 3), "pairs": len(errs),
            "method": "latest approved SWS round posted before the issue date (no tested method was better, E69)",
            "geography": "Balance Luzon (region); SWS publishes no provincial figure"}


# ------------------------------------------------------------------------------------------------ provincial outlook
def outlook(rec: dict, code: str) -> dict | None:
    """E69 tier for the record's target quarter, from the record's own observations at its issue date."""
    p = rec.get("provinces", {}).get(code)
    if p is None:
        return None
    t = qi(rec["originQuarter"])
    rh = regional_hunger(t)
    obs = p["observed"]
    food = (obs.get("foodInflationLatestMonths") or {}).get("value")
    gap = (obs.get("foodMinusHeadline") or {}).get("value")
    headline = None if food is None or gap is None else round(food - gap, 2)
    pp = ((p.get("forecast") or {}).get("components") or {}).get("probabilityPricePressure")
    cl = obs.get("climate", {})
    prods = [v for v in (cl.get("palayProductionYoY"), cl.get("cornProductionYoY")) if v is not None]
    exposure = None if not prods else min(prods) <= -10.0
    hazard, status = CW.hazard(rec["origin"])
    if rh["status"] != "OK":
        tier, H = "INSUFFICIENT DATA", None
    else:
        H = rh["probabilityAbove11_3"] >= 0.5
        A = bool((pp is not None and pp >= 0.5) or (headline is not None and headline > HEADLINE_USUAL[code]))
        if H and (A or (hazard and exposure)):
            tier = "ELEVATED"
        elif H and hazard:
            tier = "WATCH"
        else:
            tier = "NO ELEVATED SIGNAL"
    return {"tier": tier, "issueDate": rec["origin"], "targetQuarter": rec["targetQuarter"],
            "components": {"regionalHungerElevated": H, "probabilityHungerElevated": rh.get("probabilityAbove11_3"),
                           "affordabilityHazard": None if rh["status"] != "OK" else A,
                           "pricePressureScore": None if pp is None else round(pp, 4),
                           "headlineAtIssue": headline, "headlineUsual": round(HEADLINE_USUAL[code], 2),
                           "foodInflationAtIssue": food, "climateHazard": bool(hazard), "climateStatus": status,
                           "localProductionExposure": exposure, "palayYoY": cl.get("palayProductionYoY"),
                           "cornYoY": cl.get("cornProductionYoY")},
            "rule": "ELEVATED = H and (A or (C and X)); WATCH = H and C; otherwise NO ELEVATED SIGNAL",
            "meaning": "convergence-of-evidence outlook for planning; not a probability and not a validated provincial forecast"}


@functools.lru_cache(maxsize=1)
def _e69() -> dict:
    return json.loads(E69_DISCLOSURE.read_text(encoding="utf-8"))


def outlook_for(rec: dict, quarter: str, code: str) -> dict | None:
    """Runtime outlook for the record's target; the sealed E69 outlook for the earlier issued quarter (2026-Q4)."""
    if quarter == rec.get("targetQuarter"):
        return outlook(rec, code)
    name = rec["provinces"][code]["name"]
    o = _e69()["riskOutlook"].get(quarter, {}).get(name)
    return None if o is None else {**o, "targetQuarter": quarter, "source": "sealed E69 outlook (issued earlier)"}


# ------------------------------------------------------------------------------------------------ FIRI
@functools.lru_cache(maxsize=2)
def _firi_history(path: str, mtime: int) -> dict:
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["target"], r["province_code"])] = r
    return out


def _features(rec: dict) -> dict:
    path = FEATURES_DIR / f"features_{rec['targetQuarter'].replace('-', '')}.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return {r["province_code"]: r for r in csv.DictReader(f)}


def firi_for(rec: dict, quarter: str, code: str) -> dict | None:
    """FIRI of a province for a Lead-2 target: computed at runtime from the served record and the model's own inference
    features for the record's target; from the frozen history (built by the evaluation runner) for earlier quarters."""
    from app.ml.inference import firi as FI
    from app.news import pipeline_v3 as P3
    if quarter == rec.get("targetQuarter"):
        t = qi(rec["originQuarter"])
        p = rec["provinces"][code]
        pp = ((p.get("forecast") or {}).get("components") or {}).get("probabilityPricePressure")
        rh = regional_hunger(t)
        res = FI.score(FI.raw_indicators(code, _features(rec)[code], pp, rec["origin"], rec["originQuarter"],
                                         CW.hazard(rec["origin"])[0], rh.get("probabilityAbove11_3"), P3.fssi_v3(code, t)))
        return {**res, "targetQuarter": quarter, "issueDate": rec["origin"], "source": "computed at runtime"}
    h = _firi_history(str(FIRI_HISTORY), FIRI_HISTORY.stat().st_mtime_ns).get((quarter, code))
    if h is None or not h["FIRI"]:
        return None
    ind = json.loads(h["indicators_json"])
    from app.ml.inference import firi as FI
    for k, v in ind.items():
        v.update({"label": FI.LABELS[k], "domain": FI.DOMAIN_OF[k], "note": ""})
    dom = {d: (float(h[f"dom_{d}"]) if h.get(f"dom_{d}") not in (None, "") else None) for d in FI.DOMAINS}
    avail = {d: v for d, v in dom.items() if v is not None}
    firi = float(h["FIRI"])
    return {"firi": firi, "class": h["class"], "domains": dom, "domainsAvailable": len(avail),
            "shares": {d: (v / len(avail)) / firi for d, v in avail.items()}, "indicators": ind,
            "targetQuarter": quarter, "issueDate": h["issue_date"], "source": f"evaluation history ({h['kind']})"}


def index_rows(rows: list[dict], quarter: str) -> list[dict]:
    """Province rows with the FIRI estimate as the served score (risk_probability: the number the map, the LGU index
    and the trend use); the LightGBM food-price-pressure score is kept as price_pressure_score. A province whose FIRI
    cannot be computed is left out, never filled."""
    rec = LEAD2.record()
    out = []
    for r in rows:
        fr = firi_for(rec, quarter, r["province_code"])
        if fr is None or fr["firi"] is None:
            continue
        what = ("Lead-2 estimate" if r.get("estimate_kind") == "forecast" else
                "earlier Lead-2 estimate" if r.get("estimate_kind") == "earlier_forecast" else "back-test estimate")
        out.append({**r, "price_pressure_score": r["risk_probability"], "risk_probability": round(fr["firi"], 6),
                    "score_type": "food_insecurity_risk_index",
                    "score_definition": "FIRI v1 proxy composite (0-1), not a probability",
                    "band": "High" if fr["firi"] >= 0.5 else "Low",
                    "confidence_statement": (f"{r['province_name']}, {quarter}: estimated food-insecurity risk index "
                                             f"{fmt_index(fr['firi'])} ({fr['class']}; {what} issued {r.get('origin')}), from "
                                             f"{fr['domainsAvailable']} of 6 indicator domains. The LightGBM "
                                             f"food-price-pressure forecast is {r['risk_probability']:.0%}.")})
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


FIRI_THRESHOLD = 0.5


def fmt_index(v: float) -> str:
    """FIRI as text: two decimals, or four when two would round a LOW value up to the threshold (0.4998 is
    shown as 0.4998, never as "0.50")."""
    return f"{v:.4f}" if v < FIRI_THRESHOLD and round(v, 2) >= FIRI_THRESHOLD else f"{v:.2f}"


FIVE_GROUPS = {"market": ("A1", "A2", "A3"), "climate": ("C1", "C2", "C3"), "fish_kill": ("C4",), "employment": ("E1",),
               "ofw_remittance": ("E2",)}
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance"}


def contributions(res: dict) -> dict[str, float]:
    """Exact additive contribution of every indicator to FIRI: score / (indicators available in its domain x domains
    available). They sum to FIRI."""
    n_dom = res["domainsAvailable"]
    per_dom = {}
    for k, v in res["indicators"].items():
        if v["score"] is not None and res["domains"].get(v["domain"]) is not None:
            per_dom.setdefault(v["domain"], []).append(k)
    return {k: res["indicators"][k]["score"] / (len(ks) * n_dom) for d, ks in per_dom.items() for k in ks}


def firi_drivers(rec: dict, quarter: str, code: str, base: dict) -> dict:
    """The five approved driver bars, explaining the served number (FIRI): each group's exact contribution. Regional
    hunger and household vulnerability are not among the five groups: their share is reported as otherPct (and named
    in the summary). News shares are kept from the model drivers."""
    res = firi_for(rec, quarter, code)
    if res is None or res["firi"] is None:
        return base
    con = contributions(res)
    news = {d["driver_group"]: d.get("trigger_proportion") for d in base.get("drivers", [])}
    drivers = []
    for g, ks in FIVE_GROUPS.items():
        c = sum(con.get(k, 0.0) for k in ks)
        drivers.append({"driver_group": g, "driver_label": GROUP_LABELS[g], "group_shap": round(c, 6),
                        "direction": "increases_risk" if c > 0 else "no_effect", "trigger_proportion": news.get(g)})
    other = sum(con.get(k, 0.0) for k in ("V1", "H1"))
    return {**base, "drivers": drivers, "other_pct": round(100 * other / res["firi"], 1), "firi": res}


def group_status(rec: dict, quarter: str, code: str | None, key: str, pct: int) -> str:
    """Card status of a factor group for the served FIRI: contributes / no_effect, or insufficient_data when every
    indicator of the group is missing at the issue date (region scope: in every province)."""
    ks = FIVE_GROUPS.get(key, ())
    codes = [code] if code else list(rec["provinces"])
    missing = True
    for c in codes:
        res = firi_for(rec, quarter, c)
        if res and any(res["indicators"][k]["score"] is not None for k in ks):
            missing = False
            break
    if missing:
        return "insufficient_data"
    return "contributes" if pct > 0 else "no_effect"


_FMT = {"A1": lambda x: f"{x:.0%} chance of food-price pressure", "A2": lambda x: f"{x:+.1f} points vs the province's usual level",
        "A3": lambda x: f"{x:+.1f}% year on year", "C1": lambda x: "in force" if x >= 0.5 else "not in force",
        "C2": lambda x: f"{x:.0f} in the quarter", "C3": lambda x: f"production {-x:+.1f}% year on year (the lower of palay and corn)",
        "C4": lambda x: f"production {-x:+.1f}% year on year", "E1": lambda x: f"unemployment rate {x:+.2f} points year on year",
        "E2": lambda x: f"remittances {-x:+.1f}% year on year (USD)"}
# the 2021-2023 reference range of the national economy indicators is the post-lockdown recovery (unemployment falling
# 1.1-2.7 points a year, remittances growing 1.3-6.0%), so ordinary values score near 1: stated on the card (limitation)
_SATURATED = {"E1": "the 2021-2023 reference years were the post-lockdown recovery, when unemployment fell 1.1-2.7 points a "
                    "year, so any smaller fall or a rise scores 1; this domain therefore raises the index in most quarters",
              "E2": "the 2021-2023 reference years had remittance growth of 1.3-6.0%, so slower growth scores near 1"}
_WHY = {"incomplete": "quarter still in progress when the data were fetched, not counted",
        "missing": "no published value at the issue date, not counted (missing is not zero)",
        "too_few_articles": "too few articles, not counted", "unavailable_at_issue": "not yet published, not counted"}


def group_evidence(rec: dict, quarter: str, code: str, key: str) -> str | None:
    """THESIS: the card text of a factor group: each FIRI indicator in the group with its value, its 0-1 score and its
    status (replaces the price-model attribution text, which describes a different score)."""
    res = firi_for(rec, quarter, code)
    if not res or key not in FIVE_GROUPS:
        return None
    parts = []
    for k in FIVE_GROUPS[key]:
        i = res["indicators"][k]
        if i["score"] is None:
            parts.append(f"{i['label']}: {_WHY.get(i['status'], i['status'])}")
        else:
            parts.append(f"{i['label']}: {_FMT[k](float(i['x']))} (score {i['score']:.2f} of 1"
                         + (f"; {_SATURATED[k]})" if k in _SATURATED else ")"))
    return ("In the risk index (FIRI v1, each indicator scored 0-1 against its 2021-2023 range): " + "; ".join(parts)
            + ". The bar is this group's exact share of the index.")


def firi_public(res: dict) -> dict:
    """The served FIRI object (API field riskOutlook in thesis mode)."""
    from app.ml.inference import firi as FI
    doms = [{"key": d, "label": FI.DOMAINS[d], "score": None if v is None else round(v, 3),
             "share": round(res["shares"].get(d, 0.0), 3) if v is not None else None,
             "indicators": [{"key": k, "label": i["label"], "value": None if i["x"] is None else round(float(i["x"]), 3),
                             "score": None if i["score"] is None else round(float(i["score"]), 3), "status": i["status"]}
                            for k, i in res["indicators"].items() if i["domain"] == d]}
            for d, v in res["domains"].items()]
    return {"index": None if res["firi"] is None else round(res["firi"], 4), "class": res["class"],
            "tier": res["class"], "issueDate": res.get("issueDate"), "targetQuarter": res.get("targetQuarter"),
            "domainsAvailable": res["domainsAvailable"], "domains": doms, "threshold": FI.THRESHOLD,
            "method": ("FIRI v1: six equally weighted domains (affordability, household vulnerability, climate and food "
                       "production, household economy, news, regional hunger); indicators scored against their "
                       "2021-2023 reference range; HIGH at 0.5. A proxy composite, not a probability and not validated "
                       "against food-insecurity outcomes (none exist for CALABARZON provinces)."),
            "source": res.get("source")}


def _why_missing(res: dict, d: str) -> str:
    """Why a domain is out of the index: no usable 2021-2023 reference range, or no value published at the issue date."""
    from app.ml.inference import firi as FI
    anc = FI.anchors()["indicators"]
    ks = [k for k, i in res["indicators"].items() if i["domain"] == d]
    if all(k in FI.CONTINUOUS and not anc.get(k, {}).get("usable") for k in ks):
        return f"{FI.DOMAINS[d].lower()}: too little data in the 2021-2023 reference period"
    return f"{FI.DOMAINS[d].lower()}: no value published by the issue date"


def firi_text(res: dict, name: str, quarter: str) -> str:
    from app.ml.inference import firi as FI
    order = sorted([(d, v) for d, v in res["domains"].items() if v is not None], key=lambda kv: -kv[1])
    parts = [f"{FI.DOMAINS[d]} {v:.2f}" for d, v in order]
    top = [FI.DOMAINS[d] for d, v in order if v >= 0.5][:3]
    missing = [FI.DOMAINS[d] for d, v in res["domains"].items() if v is None]
    return (f"ESTIMATED FOOD-INSECURITY RISK for {name}, {quarter}: {res['class']} (risk index {fmt_index(res['firi'])} on a 0-1 "
            f"scale; HIGH at 0.50). Domain scores: {'; '.join(parts)}."
            + (f" Mainly raised by {', '.join(top)}." if top else "")
            + (f" Not in the index: {', '.join(missing)} ({'; '.join(_why_missing(res, d) for d in res['domains'] if res['domains'][d] is None)})."
               if missing else "")
            + " The index combines proxy indicators (prices, poverty and density, climate and crop production, national "
              "jobs and remittances, and regional hunger, which is the same for every province). It is an estimate for "
              "planning, not a probability and not a measured food-insecurity rate.")


# ------------------------------------------------------------------------------------------------ input status
# typhoon quarters still in progress when pagasa_climate.parquet was fetched (fetched_at 2026-09-09, E66 D-E66-5): the
# served model stores the partial count as a number, so it is disclosed as a placeholder
INCOMPLETE_TYPHOON_QUARTERS = {"2026-Q3"}
NEWS_MIN = 10


def input_status(rec: dict, code: str) -> list[dict]:
    """Every input of the record's target forecast at its issue date, classified as observed | observed_zero |
    missing | stale | substituted | too_few_articles | not_collected, from the record's own observations (the same
    classes as E68; checked against the E68 disclosure by a test)."""
    o = rec["provinces"][code]["observed"]
    fr = (rec.get("dataFreshness") or {}).get("latestPredictorPeriods", {})
    oq, t = rec["originQuarter"], qi(rec["originQuarter"])
    out = []

    def add(key, label, group, value, period, status, note):
        out.append({"key": key, "label": label, "group": group, "value": value, "period": period, "status": status,
                    "ageQuarters": None, "note": note})

    def obs(v):
        return "missing" if v is None else "observed"

    cpi = next((v for k, v in fr.items() if k.startswith("PSA CPI YoY")), "latest months")
    food = (o.get("foodInflationLatestMonths") or {}).get("value")
    gap = (o.get("foodMinusHeadline") or {}).get("value")
    add("food_cpi", "Food inflation (PSA CPI, province)", "market", food, f"to {cpi}", obs(food), "Months published after the issue date are not used.")
    add("headline_cpi", "Headline inflation (PSA CPI, province)", "market", None if food is None or gap is None else round(food - gap, 2),
        f"to {cpi}", obs(gap), "Used through the food-minus-headline gap.")
    h = o.get("hungerRegional") or {}
    st = "missing" if h.get("value") is None else ("stale" if (h.get("ageQuarters") or 0) >= 2 else "observed")
    out.append({"key": "sws_hunger", "label": "Hunger (SWS, Balance Luzon region)", "group": "hunger", "value": h.get("value"),
                "period": h.get("quarter"), "status": st, "ageQuarters": h.get("ageQuarters"),
                "note": "Regional figure, the same for all five provinces."})
    cl = o.get("climate", {})
    tc = cl.get("typhoonsWithin300km")
    tcs = ("substituted" if cl.get("quarter") in INCOMPLETE_TYPHOON_QUARTERS else
           "missing" if tc is None else "observed_zero" if tc == 0 else "observed")
    add("typhoons", "Typhoons within 300 km (IBTrACS)", "climate", tc, cl.get("quarter"), tcs,
        "Quarter still in progress when the data were fetched: the count so far is used." if tcs == "substituted" else
        "0 means no storm passed within 300 km." if tcs == "observed_zero" else "Count of storms.")
    add("enso", "ENSO phase (NOAA ONI, observed)", "climate", None, qs(t - 1), obs(cl.get("ensoPhasePreviousQuarter")),
        f"{cl.get('ensoPhasePreviousQuarter')}; observed only, without its strength.")
    add("enso_outlook", "PAGASA El Nino outlook", "climate", None, "issue date", "not_collected",
        "Shown in the risk outlook, not a model input.")
    add("rainfall_drought", "Rainfall, dry spell and drought", "climate", None, "-", "not_collected",
        "No dated 2021-2026 PAGASA dry-spell/drought archive is available.")
    for k, lab in (("palayProductionYoY", "Palay production (PSA, province)"), ("cornProductionYoY", "Corn production (PSA, province)")):
        add(k, lab, "climate", cl.get(k), qs(t - 1), obs(cl.get(k)), "Year-on-year change.")
    fi = o.get("fisheries", {})
    for k, lab in (("fisheriesProductionYoY", "Fisheries production (PSA, province)"), ("aquacultureYoY", "Aquaculture production (PSA, province)")):
        add(k, lab, "fish_kill", fi.get(k), fi.get("quarter"), obs(fi.get(k)), "Production, not fish-kill events.")
    add("fish_kill_events", "Fish-kill events", "fish_kill", None, "-", "not_collected", "No official fish-kill event series exists.")
    em = o.get("employment", {})
    add("unemployment", "Unemployment rate (PSA LFS)", "employment", em.get("unemploymentRate"), em.get("quarter"),
        obs(em.get("unemploymentRate")), "National figure, the same for all five provinces.")
    ofw = o.get("ofwRemittance", {})
    add("remit_usd_yoy", "OFW cash remittances in US dollars (BSP)", "ofw_remittance", ofw.get("remittanceUsdYoY"),
        ofw.get("latestRemittanceQuarter"), obs(ofw.get("remittanceUsdYoY")),
        "National; missing values are treated as unknown, not as no change.")
    add("fx_yoy", "USD/PHP exchange rate", "ofw_remittance", ofw.get("usdPhpYoY"), qs(t - 1), obs(ofw.get("usdPhpYoY")), "National.")
    nw = o.get("news", {})
    n = nw.get("articles") or 0
    for k, v in (nw.get("triggerShares") or {}).items():
        stn = "too_few_articles" if n < NEWS_MIN else ("observed_zero" if v == 0 else "observed")
        add(f"news_{k}", f"News titles on {k.replace('_', ' ')}", "news", v, nw.get("quarter"), stn,
            f"Share of {int(n)} titles about the province this quarter.")
    return out


# ------------------------------------------------------------------------------------------------ news (Objective 1)
@functools.lru_cache(maxsize=1)
def _topics() -> tuple[dict, dict]:
    names = {}
    with open(TOPIC_INFO, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            words = r["Representation"].strip("[]").replace("'", "").split(", ")
            names[r["Topic"]] = ", ".join(words[:3])
    props = {}
    with open(TOPIC_PROPS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            props[(r["province_code"], r["quarter"])] = {k: float(v) for k, v in r.items() if k.startswith("topic_") and v}
    return names, props


def news_evidence(rec: dict, code: str) -> dict:
    from app.news import pipeline_v3 as P3
    t = qi(rec["originQuarter"])
    f = P3.fssi_v3(code, t)
    mine = [a for a in P3.asof(t) if a["province_code"] == code]
    names, props = _topics()
    pr = props.get((code, rec["originQuarter"]), {})
    # only real BERTopic topics (topic_<id>_pct); the outlier and "other" columns are not topics
    top = sorted(((k, v) for k, v in pr.items() if k.split("_")[1].lstrip("-").isdigit() and v > 0),
                 key=lambda kv: -kv[1])[:3]
    topics = [{"topic": names.get(k.split("_")[1], k), "share": round(v, 3)} for k, v in top]
    return {"quarter": rec["originQuarter"], "publishedBefore": rec["origin"], "articles": f["n"],
            "outlets": len({a["outlet"] for a in mine}), "fssiStatus": f["status"],
            "fssi": f["fssi"] if f["status"] == "SUFFICIENT" else None, "fssiMeanIntensity": f["mean_intensity"],
            "fssiBiasWeight": f["bias_weight"], "topics": topics,
            "note": ("Classifier v2 (AI-annotated evaluation, not human-validated), syndication de-duplicated, titles only, "
                     "collected retrospectively. FSSI-v3 is shown only with at least 5 articles: the bias weight inflates "
                     "small counts. News is a warning signal, not proof of food insecurity, and not a model input.")}


# ------------------------------------------------------------------------------------------------ evaluation
@functools.lru_cache(maxsize=1)
def _evaluation(mtime: int) -> dict:
    return json.loads(EVALUATION.read_text(encoding="utf-8"))


def evaluation() -> dict:
    return _evaluation(EVALUATION.stat().st_mtime_ns)


@functools.lru_cache(maxsize=1)
def _firi_eval(mtime: int) -> dict:
    return json.loads(FIRI_EVALUATION.read_text(encoding="utf-8"))


def firi_evaluation() -> dict:
    return _firi_eval(FIRI_EVALUATION.stat().st_mtime_ns)


def model_performance() -> dict:
    e = evaluation()
    o2, o4 = e["objective2"], e["objective4"]
    fe = firi_evaluation()
    firi = {"leads": [{"lead": x["lead"], "rows": x["rows"], "reliable": x["reliable"], "shareHIGH": x["FIRI_class_rate_HIGH"],
                       **{k: x["FIRI"][k] for k in ("accuracy", "precision_HIGH", "recall_HIGH", "recall_LOW", "f1_HIGH",
                                                     "auc_roc", "brier", "confusion")}} for x in fe["leads"]],
            "objective4": {k: {"brier_diff_firi_minus_baseline": v["brier_diff_firi_minus_baseline"], "ci95": v["ci95"],
                               "firi_better_by_rule": v["firi_better_by_rule"]} for k, v in fe["objective4"]["comparisons"].items()},
            "regionalOutcome": fe["regionalOutcome"], "domainsUsed": fe["domainsUsed"], "newsDomain": fe["newsDomain"],
            "evidenceStatus": fe["evidenceStatus"]}
    return {"model": MODEL_NAME, "firi": firi, "evidenceStatus": e["evidenceStatus"], "target": e["target"],
            "leads": [{"lead": x["lead"], "quarters": x["quarters"], "rows": x["rows"], "reliable": x["reliable"],
                       **{k: x["metrics"]["LightGBM E56-TUNED P(HIGH)"][k] for k in
                          ("accuracy", "precision_HIGH", "recall_HIGH", "f1_HIGH", "auc_roc", "brier")}} for x in o2["leads"]],
            "reliabilityCriterion": o2["reliabilityCriterion"], "furthestReliableLead": o2["furthestReliableLead"],
            "verdict": o2["verdict"],
            "baselines": {k: {m: v[m] for m in ("accuracy", "brier", "auc_roc", "recall_HIGH")} for k, v in o4["models"].items()},
            "goal75": e["goal75"]}


def _f(v, d=2):
    return "--" if v is None else f"{v:.{d}f}"


def performance_tables(perf: dict | None = None) -> dict:
    """Plain rows for the PDF / report views: Objective 2 (leads) and Objective 4 (baselines), and the statements."""
    perf = perf or model_performance()
    leads = [[f"Lead {x['lead']} ({x['quarters']} quarters, {x['rows']} rows)", _f(x["accuracy"]), _f(x["precision_HIGH"]),
              _f(x["recall_HIGH"]), _f(x["f1_HIGH"]), _f(x["auc_roc"]), _f(x["brier"], 3), "yes" if x["reliable"] else "no"]
             for x in perf["leads"]] + [["Lead 4 (not computable under the information cutoffs)", "n/a", "", "", "", "", "", "no"]]
    base = [[k, _f(v["accuracy"]), _f(v["recall_HIGH"]), _f(v["auc_roc"]), _f(v["brier"], 3)] for k, v in perf["baselines"].items()]
    fi = perf.get("firi")
    if fi:
        leads += [[f"FIRI lead {x['lead']} ({x['rows']} rows)", _f(x["accuracy"]), _f(x["precision_HIGH"]), _f(x["recall_HIGH"]),
                   _f(x["f1_HIGH"]), _f(x["auc_roc"]), _f(x["brier"], 3), "yes" if x["reliable"] else "no"] for x in fi["leads"]]
    sentences = [
        f"Target: {perf['target']}",
        f"Reliability criterion (set before scoring): {perf['reliabilityCriterion']}. Result: {perf['verdict']}.",
        perf["goal75"], perf["evidenceStatus"],
        ("The province score is the estimated food-insecurity risk index FIRI v1 (a proxy composite; HIGH at 0.5). It was "
         "scored against the same T43 rows (FIRI rows in the lead table) and against observed regional hunger: "
         f"accuracy {fi['regionalOutcome']['accuracy']:.2f} over {fi['regionalOutcome']['quarters']} quarters (always "
         f"elevated: {fi['regionalOutcome']['always_elevated_accuracy']:.2f}); the hunger outcome shares its SWS source with "
         "the index. "
         "No result validates FIRI as a food-insecurity rate." if fi else
         "The province score is an exploratory food-price-pressure score.")]
    return {"leadHeader": ["Lead", "Accuracy", "Precision", "Recall", "F1", "AUC-ROC", "Brier", "Reliable"],
            "leadRows": leads, "baselineHeader": ["Model (45 identical rows)", "Accuracy", "Recall HIGH", "AUC-ROC", "Brier"],
            "baselineRows": base, "sentences": sentences}


# ------------------------------------------------------------------------------------------------ summary text
def _pct(x):
    return f"{x:.0%}"


def for_summary(rec: dict, quarter: str, code: str | None, kind: str, result: str, cfsw: dict | None,
                items: list[dict] | None) -> dict | None:
    """Fields and one plain-language passage: the FIRI estimate first, then (issued and earlier forecasts) hunger,
    climate, news, data status and the model; back-test quarters carry the FIRI estimate only."""
    target_q = rec.get("targetQuarter")
    t = qi(rec["originQuarter"]) if quarter == target_q else qi(quarter) - 2
    rh = regional_hunger(t)
    perf = model_performance()
    lead2 = next((x for x in perf["leads"] if x["lead"] == 2), None)
    parts = []
    names = {k: rec["provinces"][k]["name"] for k in rec["provinces"]}
    if code:
        name = names[code]
        fr = firi_for(rec, quarter, code)
        if fr is None or fr["firi"] is None:
            parts.append(f"ESTIMATED FOOD-INSECURITY RISK for {name}, {quarter}: INSUFFICIENT DATA (fewer than 4 of 6 "
                         "indicator domains available).")
        else:
            parts.append(firi_text(fr, name, quarter) + (
                " The LightGBM food-price-pressure forecast (one indicator of the affordability domain) is LOW; a LOW "
                "price score does not mean low food-insecurity risk." if result == "LOW" and fr["class"] == "HIGH" else ""))
        risk = firi_public(fr) if fr else None
        o = outlook_for(rec, quarter, code)
        news = news_evidence(rec, code) if quarter == target_q else None
    else:
        frs = {names[k]: firi_for(rec, quarter, k) for k in rec["provinces"]}
        ok = {n: f for n, f in frs.items() if f and f["firi"] is not None}
        mean = sum(f["firi"] for f in ok.values()) / len(ok) if ok else None
        cls = {}
        for n, f in ok.items():
            cls.setdefault(f["class"], []).append(f"{n} {fmt_index(f['firi'])}")
        parts.append(f"ESTIMATED FOOD-INSECURITY RISK, {quarter}: " + "; ".join(f"{c} in {', '.join(v)}" for c, v in cls.items())
                     + (f" (regional mean index {fmt_index(mean)}; HIGH at 0.50)." if mean is not None else ".")
                     + " A proxy composite of prices, poverty and density, climate and crop production, national jobs and "
                       "remittances, and regional hunger; an estimate for planning, not a probability.")
        risk = {"tiers": {n: f["class"] for n, f in ok.items()}, "index": None if mean is None else round(mean, 4),
                "provinces": {n: round(f["firi"], 4) for n, f in ok.items()}}
        news, o = None, None
    if kind == "backtest":
        parts.append(f"Back-test estimate made with information published before {issue_of(t)}; development evidence, "
                     "not a forecast issued live.")
        return {"lead": parts[0], "sentence": " ".join(parts[1:]), "modelIdentity": None, "riskOutlook": risk,
                "regionalHungerOutlook": None, "newsEvidence": None}
    if rh["status"] == "OK":
        parts.append(f"REGIONAL HUNGER (SWS, Balance Luzon; no provincial figure exists): latest {rh['latestReading']:.1f}% "
                     f"({rh['latestReadingQuarter']}); outlook about {rh['expectedHunger']:.1f}% (80% range "
                     f"{rh['interval80'][0]:.1f}-{rh['interval80'][1]:.1f}%), {_pct(rh['probabilityAbove11_3'])} chance above "
                     "11.3%. No tested method has forecast hunger two quarters ahead better than the latest reading.")
    if code and o and o.get("components", {}).get("climateHazard") is not None:
        c = o["components"]
        palay = "n/a" if c["palayYoY"] is None else format(c["palayYoY"], "+.1f") + "%"
        corn = "n/a" if c["cornYoY"] is None else format(c["cornYoY"], "+.1f") + "%"
        parts.append(f"CLIMATE: {c['climateStatus']}. Local production at the issue date: palay {palay}, corn {corn} "
                     "year on year. "
                     "No dated rainfall or drought record exists for 2021-2026, and the one El Nino in the data (2023-24) "
                     "came with falling inflation, so the score cannot include an El Nino price effect.")
    if news:
        fs = (f"FSSI-v3 {news['fssi']:.2f}" if news["fssi"] is not None else
              f"too few articles for a Food Stress Sentiment Index ({news['articles']})")
        tp = "; ".join(x["topic"] for x in news["topics"]) or "none"
        parts.append(f"NEWS ({news['quarter']}, published before {news['publishedBefore']}): {news['articles']} relevant "
                     f"article{'s' if news['articles'] != 1 else ''} from {news['outlets']} outlet{'s' if news['outlets'] != 1 else ''}; "
                     f"{fs}; main BERTopic topics: {tp}. The news list can include earlier quarters when a quarter has "
                     "few articles. News is a warning signal, not proof of food insecurity; it is not part of the risk index because the "
                     "2021-2023 reference period has too few sufficient FSSI values.")
    if items:
        miss = sorted({i["label"].split(" (")[0] for i in items if i["status"] == "missing"})
        nc = sorted({i["label"].split(" (")[0] for i in items if i["status"] == "not_collected"})
        ph = sorted({i["label"].split(" (")[0] for i in items if i["status"] in ("substituted", "stale", "too_few_articles")})
        obs = sum(i["status"] in ("observed", "observed_zero") for i in items)
        parts.append(f"DATA AT THE ISSUE DATE: {obs} of {len(items)} inputs observed" +
                     (f"; missing: {', '.join(miss)}" if miss else "") + (f"; incomplete or thin: {', '.join(ph)}" if ph else "") +
                     (f"; not collected: {', '.join(nc)}" if nc else "") + ". Missing values are treated as unknown, not as no risk.")
    if lead2:
        parts.append(f"MODEL: {MODEL_NAME}; Lead-2 score issued {rec['origin'] if quarter == rec.get('targetQuarter') else issue_of(t)}. "
                     f"Back-test (examined rows, not unseen): Lead-2 accuracy {lead2['accuracy']:.2f}, AUC {lead2['auc_roc']:.2f}; "
                     f"{perf['verdict']}; the >75% goal is not demonstrated.")
    ident = {"servingMode": MODE, "modelVersion": MODEL_NAME, "servedModel": (rec["provinces"][next(iter(rec["provinces"]))]
             ["forecast"].get("servedModel") if quarter == rec.get("targetQuarter") else "E56-TUNED LightGBM (earlier issue)"),
             "lead": 2, "issued": rec["origin"] if quarter == rec.get("targetQuarter") else issue_of(t),
             "targetQuarter": quarter, "evidenceStatus": "development evidence only; not validated",
             "lead2Accuracy": perf["goal75"]}
    return {"lead": parts[0], "sentence": " ".join(parts[1:]), "modelIdentity": ident, "riskOutlook": risk,
            "regionalHungerOutlook": rh, "newsEvidence": news}
