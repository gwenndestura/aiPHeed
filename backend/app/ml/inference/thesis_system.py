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
REQUIRED = (LEAD2.RECORD_E58, SWS, EVALUATION, TOPIC_PROPS, TOPIC_INFO, E69_DISCLOSURE, CW.INPUTS,
            Path("data/inputs/lgu_vulnerability.csv"))
HUNGER_LINE, SIGMA_DEFAULT = 11.3, 4.0
# E68 T-AFF headline P60 (2021-Q1..2022-Q4, numpy.percentile), the province's usual headline inflation
HEADLINE_USUAL = {"PH040100000": 5.013333, "PH040200000": 4.653333, "PH040300000": 5.06,
                  "PH040400000": 6.073333, "PH040500000": 5.546667}
MODEL_NAME = "aiPHeed thesis system v1 (E56-TUNED LightGBM Lead-2 score + E69 two-scale food-insecurity risk outlook)"


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
            LEAD2.record()
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


def regional_hunger(t: int) -> dict:
    """Lead-2 outlook of SWS Balance Luzon hunger at origin t (issue = first day of quarter t+1): the latest approved
    round posted before the issue date, sigma = RMSE of that rule's own past Lead-2 errors known at the issue (>= 4
    pairs, else 4.0 points). Identical to E69 R0 (checked against the sealed E69 outlook by a test)."""
    issue = issue_of(t)
    hs = _posted(issue)
    b, bq = _base(hs, t)
    errs = []
    for tp in range(qi("2021-Q2"), t - 1):
        if tp + 2 not in hs:
            continue
        bp, _ = _base(_posted(issue_of(tp)), tp)
        if bp is not None:
            errs.append(hs[tp + 2] - bp)
    sigma = math.sqrt(sum(e * e for e in errs) / len(errs)) if len(errs) >= 4 else SIGMA_DEFAULT
    if b is None:
        return {"issueDate": issue, "targetQuarter": qs(t + 2), "status": "INSUFFICIENT DATA"}
    p = 1 - 0.5 * (1 + math.erf((HUNGER_LINE - b) / (sigma * math.sqrt(2))))
    return {"issueDate": issue, "targetQuarter": qs(t + 2), "status": "OK", "latestReading": round(b, 1),
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


def model_performance() -> dict:
    e = evaluation()
    o2, o4 = e["objective2"], e["objective4"]
    return {"model": MODEL_NAME, "evidenceStatus": e["evidenceStatus"], "target": e["target"],
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
    sentences = [
        f"Target: {perf['target']}",
        f"Reliability criterion (set before scoring): {perf['reliabilityCriterion']}. Result: {perf['verdict']}.",
        perf["goal75"], perf["evidenceStatus"],
        "The province score is an exploratory food-price-pressure score; the food-insecurity risk outlook combines it "
        "with the regional hunger outlook, climate and production evidence and is not a validated probability."]
    return {"leadHeader": ["Lead", "Accuracy", "Precision", "Recall", "F1", "AUC-ROC", "Brier", "Reliable"],
            "leadRows": leads, "baselineHeader": ["Model (45 identical rows)", "Accuracy", "Recall HIGH", "AUC-ROC", "Brier"],
            "baselineRows": base, "sentences": sentences}


# ------------------------------------------------------------------------------------------------ summary text
def _pct(x):
    return f"{x:.0%}"


def for_summary(rec: dict, quarter: str, code: str | None, kind: str, result: str, cfsw: dict | None,
                items: list[dict] | None) -> dict | None:
    """Fields and one plain-language passage for an issued or earlier Lead-2 forecast (None for back-tests)."""
    if kind not in ("forecast", "earlier_forecast"):
        return None
    t = qi(rec["originQuarter"]) if quarter == rec.get("targetQuarter") else qi(quarter) - 2
    rh = regional_hunger(t)
    perf = model_performance()
    lead2 = next((x for x in perf["leads"] if x["lead"] == 2), None)
    parts = []
    if code:
        name = rec["provinces"][code]["name"]
        o = outlook_for(rec, quarter, code)
        c = o["components"] if o else {}
        if o:
            why = []
            if c.get("regionalHungerElevated"):
                why.append(f"regional hunger is expected to stay above 11.3% ({_pct(c['probabilityHungerElevated'])})")
            if c.get("affordabilityHazard"):
                why.append(f"headline inflation ({c['headlineAtIssue']:.1f}%) is above {name}'s usual 2021-2022 level "
                           f"({c['headlineUsual']:.1f}%), so a peso buys less" if (c.get("pricePressureScore") or 0) < 0.5
                           else f"food-price pressure is likely ({_pct(c['pricePressureScore'])})")
            if c.get("climateHazard"):
                why.append("a PAGASA El Nino advisory was in force at the issue date" +
                           (" and local palay or corn production had fallen 10% or more" if c.get("localProductionExposure") else ""))
            parts.append(f"FOOD-INSECURITY RISK OUTLOOK for {name}, {quarter}: {o['tier']}" +
                         (f" ({'; '.join(why)})." if o["tier"] in ("ELEVATED", "WATCH") else ".") +
                         (" The LOW price score does not mean low food-insecurity risk." if result == "LOW" and
                          o["tier"] in ("ELEVATED", "WATCH") else "") +
                         " This outlook combines evidence for planning; it is not a probability and has not been validated "
                         "against provincial outcomes.")
        news = news_evidence(rec, code) if quarter == rec.get("targetQuarter") else None
    else:
        tiers = {rec["provinces"][k]["name"]: (outlook_for(rec, quarter, k) or {}).get("tier") for k in rec["provinces"]}
        groups = {}
        for n, tr in tiers.items():
            groups.setdefault(tr, []).append(n)
        parts.append(f"FOOD-INSECURITY RISK OUTLOOK, {quarter}: " + "; ".join(f"{t_} in {', '.join(v)}" for t_, v in groups.items() if t_)
                     + ". Evidence combined for planning; not a probability and not validated against provincial outcomes.")
        news, o = None, None
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
                     "few articles. News is a warning signal, not proof of food insecurity, and not a model input.")
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
    return {"lead": parts[0], "sentence": " ".join(parts[1:]), "modelIdentity": ident, "riskOutlook": o if code else
            {"tiers": {rec["provinces"][k]["name"]: (outlook_for(rec, quarter, k) or {}).get("tier") for k in rec["provinces"]}},
            "regionalHungerOutlook": rh, "newsEvidence": news}
