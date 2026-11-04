"""
app/ml/inference/foodinsecurity_system.py
-----------------------------------------
The served food-insecurity forecast (AIPHEED_MAP_MODEL=foodinsecurity, with AIPHEED_LEAD2_MODEL=thesis).

Target (CH3_AMENDMENT.md section 2): SWS involuntary hunger in Balance Luzon above 11.3% in the target quarter (the
quarter mean of non-commissioned rounds). Model: C-b (NEW_MODEL/NEWS_V2; FOOD_INSECURITY_SYSTEM/PLAN.md revision 4;
the team's main model, pending adviser confirmation): the IMPROVE_V2 reference LightGBM with one NLP input, the
FSSI-v3 anomaly against its own past 8 quarters, on the stacked rows of leads 1-15, refitted walk-forward at every
origin from 1998-Q3. The NLP input is included and changes no classification; the texts say so. Algorithm 3 (the paper's 75% rule) gives a Maximum Reliable Lead Time of 2 quarters, so only Leads 1 and 2
are served; it fails the stricter R1-R7 rules at every lead, and the text says so.

Province design (FOOD_INSECURITY_SYSTEM/PLAN.md revision 2):
- score = regional probability x PSA 2023 poverty incidence among families / the highest province's, so provinces get
  different scores; the class and colour are the regional class (HIGH at a regional probability of 0.50) and the
  weighting never changes them;
- context only, never changing score, class, colour or rank: the P0H4 food-price pressure band, PSA 2023 food poverty
  (with its precision), the E112 regional news sentence and the E85 provincial news sentence and early-warning flag.
LGUs: 0.6 x PSA 2021 poverty + 0.4 x density within the province (Lucena: its own PSA Table 2a value), times the
province score; colour = the regional class.

Rule 1: an issued forecast stays STAGED (withheld from the public endpoints) until an administrator approves it.
Rule 7: a HIGH forecast and a provincial news flag on an issued forecast are staged as alert candidates for human
confirmation; nothing notifies DSWD or any agency automatically.

Rows are exported by aipheed-backend-aligned/experiments/FOOD_INSECURITY_SYSTEM/runner/export_fi.py
(backend/data/foodinsecurity_engine/). The interface follows ch1_system so the dashboard and report code serve either.
"""
from __future__ import annotations

import csv
import functools
import json
import os
from pathlib import Path

NAME = "foodinsecurity"
# AIPHEED_FI_DATA_DIR (local demonstrations only) points the mode at another export of the same layout, e.g. the C-E
# demo (backend/data/foodinsecurity_engine_ce); unset, the served C-b export is used.
DATA = Path(os.getenv("AIPHEED_FI_DATA_DIR") or Path(__file__).resolve().parents[3] / "data" / "foodinsecurity_engine")
LGU_VULNERABILITY = DATA / "lgu_vulnerability.csv"
FORECAST_FROM = "2026-10-01"                 # issue dates from here on are prospective forecasts
H_LINE = 11.3
LOW_PRECISION_CV = 30.0
LUCENA = "045624000"

SHOWN_GROUPS = ("market", "climate", "fish_kill", "employment", "ofw_remittance")
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance", "hunger": "Past SWS hunger"}
NOT_INPUT = ("employment", "ofw_remittance")  # not inputs of the model (BSP remittances not retrieved)
try:                                            # an export may declare its own (C-E has every group as an input)
    NOT_INPUT = tuple(json.loads((DATA / "evaluation.json").read_text(encoding="utf-8"))["not_input_groups"])
except (OSError, KeyError, ValueError):
    pass
OTHER_GROUPS = ("hunger", "news", "lead")     # inputs outside the five bars: reported as the other share

REGIONAL = ("The food-insecurity classification is regional; the province score weights it by PSA poverty incidence "
            "and never changes the class.")
FNRI = ("Face validity: the DOST-FNRI 2023 National Nutrition Survey found 19.1% of CALABARZON households moderately "
        "or severely food insecure (95% CI 17.0-21.1), a different measure from SWS hunger, cited as context only.")
REVIEW_FLAG = ("HIGH forecast: flagged for human confirmation by a DA Region IV-A administrator before any action; no "
               "notification is sent to DSWD or any agency automatically.")
NEWS_FLAG_NOTE = ("province news early-warning flag: descriptive context, not a validated predictor, staged for human "
                  "confirmation and never public; no notification is sent to DSWD or any agency automatically")

MODEL_DEFAULT = ("one LightGBM trained walk-forward on SWS hunger since 1998 and on PSA prices, climate, production, "
                 "world-price and news inputs")
NEWS_DEFAULT = "The NLP input (the FSSI anomaly) is included and changes no classification against the same model without news."
LEAD_NAMES = {1: "that quarter", 2: "the next quarter", 3: "two quarters later", 4: "three quarters later"}
_INDICATOR_BASE = {
    "id": "regional_food_insecurity_forecast",
    "name": "Food-insecurity forecast: regional (Balance Luzon) SWS hunger above 11.3%, weighted by provincial poverty",
    "unit": ("priority score 0-1 (the regional probability weighted by provincial poverty); the class comes from the "
             "regional probability (HIGH at 0.50)"),
    "source": ("SWS hunger (four survey areas, non-commissioned rounds); PSA Region IV-A CPI (food, all items, rice); "
               "NOAA ONI; IBTrACS; PSA crop and fisheries production; World Bank Pink Sheet; news (regional FSSI, "
               "GDELT price news, project corpus categories); PSA 2023 poverty incidence among families (Table 1) for "
               "the province weight; PSA 2021 city and municipal SAE and 2024 population for the LGU ranking"),
}
EVENT = "regional food insecurity (probability that Balance Luzon SWS hunger is above 11.3%)"
COMBINATION = ("not combined into the class: the class is the regional hunger forecast alone; the province score "
               "weights it by PSA poverty incidence; the province's food-price pressure is context and changes nothing")
LGU_BASIS = ("Relative position within the province by PSA 2021 poverty incidence (60%) and population density (40%), "
             "as Objective 3 specifies, times the province's poverty-weighted score (Lucena: its own PSA 2021 value "
             "from Table 2a). Every city and municipality shares the regional food-insecurity class. Not a measured "
             "or official municipal food-insecurity rate; the ranking has not been checked against municipal "
             "outcomes.")
LGU_LEVEL_BASIS = ("Colour = the regional food-insecurity class (HIGH when the regional probability is 0.50 or more), "
                   "the same in every province; the weighting never lowers it. The number and rank are this city's or "
                   "municipality's priority: the province's poverty-weighted score times its PSA poverty (60%) and "
                   "density (40%) index within the province. Not a measured or official municipal food-insecurity "
                   "rate.")
EXPLAINABILITY_NOTE = (
    "The class shown is the forecast that SWS hunger in Balance Luzon is above 11.3% in the quarter, the same for every "
    "province. " + REGIONAL + " The province score is the regional probability times the province's PSA 2023 poverty "
    "incidence among families divided by the highest province's. The food-price pressure band (the price part of the "
    "P0H4 forecast), PSA food poverty and the news sentences are context and change neither the score nor the class. "
    "The bars are SHAP values of the regional forecast, the same for every province; past SWS hunger is the largest "
    "input and, with the news inputs, is reported as the other share. " + FNRI + " Shares describe the model's inputs, "
    "not causes.")
RISK_LEVEL_BASIS = ("Regional class (HIGH when the regional probability is 0.50 or more): HIGH means Balance Luzon SWS "
                    "hunger is forecast above 11.3%, the same for every province. The score beside it is weighted by "
                    "provincial poverty and never changes the class.")
REPORT_TABLE_NOTE = ("Risk level: the regional class (HIGH at a regional probability of 0.50 and above), the same for "
                     "every province. The number is the poverty-weighted priority score (regional probability x PSA "
                     "2023 poverty among families / the highest province's) and sets the order. The main factor is the "
                     "indicator group with the largest relative influence on the regional forecast.")
REPORT_SHAP_NOTE = ("Influence is relative SHAP on the regional food-insecurity forecast (the same for every province), "
                    "rescaled to 100%; it is model influence, not a cause.")
REPORT_COVER = ("<b>The class below is the forecast that regional SWS hunger (Balance Luzon) is above 11.3%</b>, HIGH at "
                "a probability of 0.50, the same for every province. Each province's number is that probability "
                "weighted by its PSA poverty incidence; it orders the provinces and never changes the class. "
                "Food-price pressure, food poverty and news are context. <b>It is a forecast of regional hunger, not a "
                "measured provincial food-insecurity rate</b>.")
REPORT_FOOTER = ("Forecast that Balance Luzon SWS hunger is above 11.3% (regional), weighted by provincial poverty -- "
                 "not an official food-insecurity classification.")
REPORT_BARS_NOTE = ("Red bars pushed the regional food-insecurity forecast up, green bars pulled it down; groups with no "
                    "effect are not shown. Relative model influence, not causes.")
NOT_INPUT_NOTE = "This indicator is not an input of the regional food-insecurity model; it has no bar value."
GROUP_NOTES = {g: NOT_INPUT_NOTE for g in NOT_INPUT}
RULE_NAMES = {"R1": "enough quarters", "R2": "accuracy", "R3": "balanced accuracy", "R4": "beating the baselines",
              "R5": "Brier score", "R6": "precision and recall", "R7": "stability"}


# ---------------------------------------------------------------------------------------------- serving switch and rows
def requested() -> bool:
    return os.getenv("AIPHEED_MAP_MODEL", "firi").lower() == NAME


def exported() -> bool:
    return (DATA / "rows.csv").exists() and (DATA / "evaluation.json").exists()


def active() -> bool:
    return requested() and exported()


@functools.lru_cache(maxsize=2)
def _rows(path: str, mtime: int) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["province_code"], r["quarter"]): r for r in csv.DictReader(f)}


def rows() -> dict[tuple[str, str], dict]:
    p = DATA / "rows.csv"
    return _rows(str(p), p.stat().st_mtime_ns)


@functools.lru_cache(maxsize=1)
def _evaluation(mtime: int) -> dict:
    return json.loads((DATA / "evaluation.json").read_text(encoding="utf-8"))


def evaluation() -> dict:
    return _evaluation((DATA / "evaluation.json").stat().st_mtime_ns)


def m3_served() -> bool:
    return False


def is_m3(r: dict) -> bool:
    return False


def reliable_lead() -> int | None:
    return evaluation().get("max_reliable_lead")


def _first_failing_lead(ev: dict) -> tuple[int, float] | None:
    """The first evaluated lead that fails the 75% rule, with its accuracy (None when every evaluated lead passes)."""
    for k in sorted(ev.get("leads", {}), key=int):
        v = ev["leads"][k]
        if not v.get("alg3_pass"):
            return int(k), float(v["metrics"]["accuracy"])
    return None


def indicator() -> dict:
    """The served indicator, its horizon, reliability and NLP statements derived from the served evaluation.json (no
    metric is written here); an unreadable evaluation gives an explicit 'unavailable' statement instead."""
    try:
        ev = evaluation()
        mrlt = int(ev["max_reliable_lead"])
        leads = ev["leads"]
        served = [int(k) for k in (ev.get("served_leads") or sorted(leads, key=int))]
    except (OSError, ValueError, KeyError, TypeError):
        return {**_INDICATOR_BASE, "definition": None, "evaluationAvailable": False,
                "horizon": "reliability metadata unavailable: the served evaluation.json is missing or invalid",
                "caveat": "Reliability metadata unavailable; no reliability statement is made."}
    shown = " and ".join(f"Lead {k} = {LEAD_NAMES.get(k, f'{k - 1} quarters later')}" for k in served)
    fail = _first_failing_lead(ev)
    stop = (f"; Lead {fail[0]} fails the 75% rule ({fail[1]:.3f}), so nothing beyond Lead {fail[0] - 1} is reliable"
            if fail else "")
    rules = "; ".join(f"Lead {k}: {', '.join(leads[str(k)].get('failed') or []) or 'none'}" for k in served
                      if str(k) in leads)
    news = ev.get("news_effect_text")
    news = (news[0].upper() + news[1:] + ".") if news else NEWS_DEFAULT
    return {**_INDICATOR_BASE, "evaluationAvailable": True,
            "definition": ("The forecast probability that SWS involuntary hunger in Balance Luzon (the share of families "
                           "that went hungry at least once in the past three months) is above 11.3% in the target "
                           f"quarter, from {ev.get('model_description') or MODEL_DEFAULT}. The class is regional: HIGH at "
                           "a probability of 0.50, the same for every province. The province score is that probability "
                           "times the province's PSA 2023 poverty incidence among families divided by the highest "
                           "province's; it orders the provinces and never changes the class. Food-price pressure, food "
                           "poverty and news are shown beside it as context."),
            "source": _INDICATOR_BASE["source"] + ("; " + ev["sources_extra"] if ev.get("sources_extra") else ""),
            "horizon": (f"issued on the first day of a quarter; served: {shown}. The paper's 75% accuracy rule "
                        f"(Algorithm 3) gives a Maximum Reliable Lead Time of {mrlt} quarters{stop}. Stricter rules "
                        f"R1-R7 failed: {rules}"),
            "caveat": ("A forecast of regional hunger, not a measured provincial rate: SWS reports hunger for Balance "
                       "Luzon only, so every province has the same class. " + REGIONAL + " " + FNRI + " Development "
                       f"evidence: the scored quarters were examined while the model was built ({ev.get('model', '?')}); "
                       f"the stricter rules R1-R7 fail ({rules}). " + news)}


def model_performance() -> dict:
    """/config modelPerformance in this mode: the served evaluation's own metrics per evaluated lead (not FIRI's)."""
    ev = evaluation()
    served = [int(k) for k in (ev.get("served_leads") or sorted(ev["leads"], key=int))]
    perf = {}
    for k, v in sorted(ev["leads"].items(), key=lambda x: int(x[0])):
        m = v["metrics"]
        perf[k] = {"n": v["n"], "period": v.get("period"), "accuracy": m["accuracy"], "balanced": m["balanced"],
                   "precision": m["precision"], "recall": m["recall"], "f1": m["f1"], "rocAuc": m["auc"],
                   "brier": m["brier"], "confusion": {"tp": m["TP"], "fp": m["FP"], "fn": m["FN"], "tn": m["TN"]},
                   "alg3Pass": v["alg3_pass"], "failedRules": v.get("failed") or [], "served": int(k) in served}
    return {"model": ev.get("model"), "modelVersion": model_line(), "planSha256": ev.get("plan_sha256") or None,
            "seal": ev.get("seal_sha256") or None, "maxReliableLead": ev.get("max_reliable_lead"),
            "servedLeads": served, "evidenceStatus": ev.get("evidence_status"), "leads": perf,
            "evaluation": "walk-forward development evidence from the served evaluation.json"}


def serving_model() -> dict:
    """/config servingModel in this mode: the served model's identity, from the served rows and evaluation."""
    ev = evaluation()
    fut = sorted((r for r in rows().values() if kind(r) == "forecast"), key=lambda r: (r["quarter"], int(r["lead"])))
    r = fut[-1] if fut else None
    return {"mode": "foodinsecurity", "model": ev.get("model"), "modelVersion": model_line(),
            "planSha256": ev.get("plan_sha256") or None, "seal": ev.get("seal_sha256") or None,
            "maxReliableLead": ev.get("max_reliable_lead"), "servedLeads": ev.get("served_leads"),
            "issued": r["issue_date"] if r else None, "targetQuarter": r["quarter"] if r else None,
            "lead": int(r["lead"]) if r else None,
            "strict": os.getenv("AIPHEED_STRICT_MODEL", "") in ("1", "true", "True")}


def __getattr__(name: str):
    """INDICATOR is derived from the served evaluation at every access (PEP 562)."""
    if name == "INDICATOR":
        return indicator()
    raise AttributeError(name)


def horizon() -> dict:
    ev = evaluation()
    fail = _first_failing_lead(ev)
    return {"generated_max_lead": max((int(r["lead"]) for r in rows().values()), default=None),
            "evaluated_leads": sorted(int(k) for k in ev["leads"]), "testable_max_lead": None,
            "reliable_max_lead": reliable_lead(), "individually_passing_leads": [int(k) for k, v in ev["leads"].items()
                                                                                if v["alg3_pass"]],
            "why_not_longer": (f"Lead {fail[0]} is the first lead below 75% mean walk-forward accuracy "
                               f"({fail[1]:.3f}); Algorithm 3 stops there" if fail else
                               "every evaluated lead passes the 75% rule; no longer lead was evaluated"),
            "reliable_quarters_after_newest_sws": None}


def status(r: dict) -> str:
    return "reliable" if (reliable_lead() or 0) >= int(r["lead"]) else "experimental"


def covers(quarter: str) -> bool:
    return any(q == quarter for _, q in rows())


def row(code: str, quarter: str) -> dict | None:
    return rows().get((code, quarter))


def _f(x) -> float | None:
    return None if x in (None, "", "nan") else float(x)


def kind(r: dict) -> str:
    """retrospective (walk-forward, outcome known or quarter past) or forecast (issued 2026-10-01 or later)."""
    return "forecast" if r["issue_date"] >= FORECAST_FROM else "retrospective"


def is_high(r: dict) -> bool:
    return float(r["probability"]) >= 0.5


def score(r: dict) -> float:
    """The province score: the regional probability weighted by PSA 2023 poverty among families (PLAN section 2)."""
    return float(r["score"])


def is_flagged(r: dict) -> bool:
    return str(r.get("news_flag")) == "True"


def _clause(text: str | None) -> str:
    """A context sentence from the export, without its final full stop, so it can sit inside one sentence."""
    return (text or "").strip().rstrip(".")


# ---------------------------------------------------------------------------------------------- text
def latest_sws(r: dict) -> str:
    return (f"latest SWS Balance Luzon hunger reading {float(r['h_last']):.1f}% ({r['sws_newest_q']}, published "
            f"{r['sws_newest_published']})")


def past_text(r: dict) -> str | None:
    """'past forecast; actual: HIGH/LOW' for a walk-forward quarter (None for an issued forecast)."""
    if kind(r) == "forecast":
        return None
    if r.get("observed"):
        return f"past forecast; actual: {r['observed']} (SWS hunger {float(r['observed_hunger']):.1f}%)"
    return "past forecast; actual: no label (no regular SWS round that quarter)"


def _max_poverty() -> float:
    return max(float(p["pov_families_2023"]) for p in evaluation()["province_poverty"])


def score_text(r: dict) -> str:
    return (f"province score {score(r):.2f} = regional probability {float(r['probability']):.2f} x PSA 2023 poverty "
            f"among families {float(r['pov_families_2023']):.1f}% / {_max_poverty():.1f}% (highest province)")


def price_text(r: dict) -> str:
    if not r.get("price_band"):
        return "food-price pressure: not available"
    return (f"food-price pressure: {r['price_band']} (P0H4 price part {float(r['pi_price']):.2f}; context, does not "
            "change the score)")


def food_poverty_text(r: dict) -> str:
    cv = float(r["food_pov_2023_cv"])
    low = "; low precision (CV > 30%)" if cv > LOW_PRECISION_CV else ""
    return (f"provincial food poverty 2023: {float(r['food_pov_2023']):.1f}% of families (CV {cv:.1f}%{low}), not used "
            "for ranking")


def province_context(r: dict) -> str:
    return "; ".join((score_text(r), price_text(r), food_poverty_text(r), _clause(r.get("province_news_text"))))


def reliability_text(r: dict) -> str:
    lead = int(r["lead"])
    ev = evaluation()
    L = ev["leads"]
    if lead <= (reliable_lead() or 0):
        m = L[str(lead)]["metrics"]
        failed = ", ".join(f"{x} ({RULE_NAMES.get(x, x)})" for x in L[str(lead)]["failed"])
        return (f"Lead-{lead} forecast: passes the paper's 75% accuracy rule (accuracy {m['accuracy']:.3f} on "
                f"{L[str(lead)]['n']} past quarters; Maximum Reliable Lead Time {reliable_lead()}) but fails the "
                f"stricter reliability rules R1-R7 ({failed}); {news_effect_text(lead)}")
    return f"Lead-{lead} forecast: beyond the Maximum Reliable Lead Time ({reliable_lead()} quarters)"


def news_effect_text(lead: int) -> str:
    """What the NLP input does to the forecast, from the evaluation (C-b against the same model without news)."""
    ev = evaluation()
    if ev.get("news_effect_text"):
        return ev["news_effect_text"]
    e = (ev.get("news_effect") or {}).get(str(lead)) or {}
    share = (ev.get("news_shap_share_lead1") or {}).get("N1 News", 0.0)
    return (f"the NLP input (FSSI anomaly) is included and carries {share:.1f}% of SHAP influence; it changed "
            f"{e.get('calls_differing', 0)} of {e.get('n_quarters', 0)} classifications against the same model without "
            f"news (accuracy {e.get('acc_a', float('nan')):.3f} vs {e.get('acc_b', float('nan')):.3f})")


def _class(r: dict) -> str:
    return "HIGH" if is_high(r) else "LOW"


def province_row(code: str, name: str, quarter: str, base: dict | None) -> dict | None:
    r = row(code, quarter)
    if r is None:
        return None
    p, s = float(r["probability"]), score(r)
    k = kind(r)
    obs = r["observed"] or None
    if k == "forecast":
        what = (f"{reliability_text(r)}; issued {r['issue_date']} with the {latest_sws(r)}; the outcome is not yet "
                f"published. {REGIONAL}")
    else:
        what = (f"Walk-forward Lead-{r['lead']} forecast made as of {r['issue_date']} with information published before "
                f"it (development evidence); {past_text(r)}. {REGIONAL}")
    # PLAN section 8.1: a province news flag is never named in public text; it exists only as a staged alert candidate
    flags = f" {REVIEW_FLAG}" if is_high(r) and k == "forecast" else ""
    out = dict(base or {})
    out.update({
        "province_code": code, "province_name": name, "quarter": quarter,
        "risk_probability": round(s, 6), "risk_label": None, "observed_label": obs, "observed_S1": None,
        "data_sufficiency_flag": "SUFFICIENT", "forecast_horizon_quarters": int(r["lead"]),
        "horizon_label": what, "origin": r["issue_date"], "verification_date": r["issue_date"],
        "mode": f"FOODINSECURITY_LEAD{int(r['lead'])}_{'FORECAST' if k == 'forecast' else 'BACKTEST'}",
        "estimate_kind": "forecast" if k == "forecast" else "backtest",
        "price_pressure_score": _f(r.get("pi_price")), "hunger_condition_probability": p,
        "regional_probability": p, "class_level": "high" if is_high(r) else "low",
        "score_type": "poverty_weighted_regional_food_insecurity_score", "score_definition": indicator()["definition"],
        "band": "High" if is_high(r) else "Low",
        "confidence_statement": (f"{name}, {quarter}: {_class(r)} food-insecurity risk (regional probability {p:.2f}; "
                                 f"{province_context(r)}). {what}{flags}")})
    return out


def _priority(r: dict) -> tuple:
    """Province order: the poverty-weighted score (the class is regional and the same for every province)."""
    return (-score(r), r["province_code"])


def province_rows(base_rows: list[dict], quarter: str, names: dict[str, str]) -> list[dict]:
    by = {r["province_code"]: r for r in base_rows}
    keyed = []
    for code, name in names.items():
        out = province_row(code, name, quarter, by.get(code))
        if out is not None:
            keyed.append((_priority(row(code, quarter)), out))
    keyed.sort(key=lambda x: x[0])
    return [o for _, o in keyed]


# ---------------------------------------------------------------------------------------------- LGUs
def lgu_vulnerability_path() -> Path:
    """lgu_vulnerability.csv as served in this mode: the input copy with Lucena's own PSA Table 2a value."""
    return LGU_VULNERABILITY


def lgu_class_probability(quarter: str) -> float | None:
    """The probability that sets every LGU's colour: the regional one, never the poverty-weighted score."""
    r = next((r for (_, q), r in rows().items() if q == quarter), None)
    return None if r is None else float(r["probability"])


def lgu_poverty_provenance(code: str) -> dict | None:
    """Lucena's poverty provenance (the other 141 LGUs keep the PSA SAE wording)."""
    if code != LUCENA:
        return None
    lu = evaluation()["lucena"]
    if lu["own"]:
        return {"povertyEstimateKind": "PSA 2021 official estimate for the City of Lucena (Table 2a)",
                "povertyValueUsed": lu["value"],
                "povertyLimitation": (f"Lucena is a highly urbanized city, not in the PSA municipal SAE table; its "
                                      f"value is PSA's own 2021 estimate for the City of Lucena (Table 2a, poverty "
                                      f"incidence among population, CV {lu['cv']:.0f}%), published to the whole per "
                                      f"cent. Source: {lu['url']}")}
    return {"povertyEstimateKind": "province substitute (no municipal estimate)", "povertyValueUsed": lu["value"],
            "povertyLimitation": ("Quezon province value, not a Lucena estimate: PSA Table 2a has no 2021 value for "
                                  f"the City of Lucena. Source: {lu['url']}")}


# ---------------------------------------------------------------------------------------------- driver bars
GROUP_KEYS = SHOWN_GROUPS


def group_status(code: str | None, quarter: str, key: str, pct: int) -> str | None:
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs or f"avail_{key}" not in rs[0]:
        return None
    if key in NOT_INPUT:
        return "no_model_input"
    if not any(str(r[f"avail_{key}"]) == "1" for r in rs):
        return "insufficient_data"
    return "contributes" if pct > 0 else "no_effect"


def _other_abs(r: dict) -> float:
    return sum(abs(_f(r.get(f"shap_{g}")) or 0.0) for g in OTHER_GROUPS)


def evidence_note(code: str | None, quarter: str, other_pct: float | None = None, group: str | None = None) -> str:
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if evaluation().get("driver_view") == "relative":
        note = ("The bars compare each driver's push on THIS quarter's forecast (SHAP, log-odds) with its own usual push "
                "(its average over the forecasts issued up to this one), shared among these five groups. A larger bar "
                "means the driver is pushing harder than usual; past SWS hunger, the strongest input, is not one of the "
                "five. They are model influence, not shares of hunger caused by each factor.")
        if rs and code:
            note += f" Province context: {province_context(rs[0])}."
        return note
    if evaluation().get("driver_view") == "trailing8":
        n = int(float(rs[0].get("avg8_n") or 0)) if rs else 0
        note = (f"The bars show each driver's share of the model's push (mean |SHAP|, log-odds) among these five groups, "
                f"averaged over the {n} forecasts issued up to this one (this quarter's and the 7 before it); past SWS "
                "hunger, the strongest input, is not one of the five. Shares under 0.5% round to 0%. They are model "
                "influence, not shares of hunger caused by each factor.")
        if rs and code:
            note += f" Province context: {province_context(rs[0])}."
        return note
    other = (f"; past SWS hunger and the news inputs account for the remaining {other_pct:.0f}%"
             if other_pct is not None else "; past SWS hunger and the news inputs account for the rest")
    note = ("The bars show each driver's share of the total push (SHAP, log-odds) on the regional food-insecurity "
            f"forecast{other}. They are the same for every province, because the forecast is regional. A 0% bar means "
            "the input had a value but did not move this forecast. They are model influence, not shares of hunger "
            "caused by each factor.")
    if rs and code:
        note += f" Province context: {province_context(rs[0])}."
    return f"{note} {GROUP_NOTES[group]}" if group in GROUP_NOTES else note


QUARTER_MONTHS = {1: "Jan-Mar", 2: "Apr-Jun", 3: "Jul-Sep", 4: "Oct-Dec"}


def _q_before(issue_date: str, back: int) -> str:
    i = int(issue_date[:4]) * 4 + (int(issue_date[5:7]) - 1) // 3 - back
    return f"{QUARTER_MONTHS[i % 4 + 1]} {i // 4}"


def _change(v: float, unit: str) -> str:
    return f"{abs(v):.1f}{unit} {'higher' if v > 0 else 'lower'}" if round(v, 1) else "about the same"


def market_evidence(code: str | None, quarter: str) -> str | None:
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs:
        return None
    r = rs[0]
    food, rice = _f(r.get("val_R_food_yoy")), _f(r.get("val_R_rice_yoy"))
    facts = " ".join(x for x in (
        None if food is None else f"Region IV-A food inflation was {food:.1f}% year on year (PSA CPI through "
                                  f"{r['psa_newest_month']}).",
        None if rice is None else f"Rice prices were {_change(rice, '%')} than a year earlier.") if x)
    if code is None:
        return facts or None
    if not r.get("price_band"):
        return f"{facts} This province's food-price pressure is not available.".strip()
    return (f"{facts} This province's food-price pressure is {r['price_band']}: a {float(r['pi_price']):.0%} chance "
            f"that its food prices in {quarter} rise faster than usual (P0H4 price part). It is context and changes "
            "neither the score nor the class.").strip()


def plain_evidence(code: str | None, quarter: str, group: str) -> str | None:
    """The card sentence for a group, from the values the regional forecast used at its issue date."""
    if group == "market":
        return market_evidence(code, quarter)
    if group in NOT_INPUT:
        return NOT_INPUT_NOTE
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs:
        return None
    r, d = rs[0], rs[0]["issue_date"]
    none = "No published value was available at this forecast's issue date; missing data is not a sign of low risk."
    v = {c: _f(r.get(f"val_{c}")) for c in ("ONI_last", "tc_mean", "R_C3", "R_C4")}
    if group == "climate":
        parts = [None if v["ONI_last"] is None else f"The Oceanic Nino Index was {v['ONI_last']:+.1f} at the issue "
                                                     "date (El Nino at +0.5 or more).",
                 None if v["tc_mean"] is None else f"On average {v['tc_mean']:.1f} typhoon(s) passed within 300 km of "
                                                   f"the provinces in {_q_before(d, 1)}.",
                 None if v["R_C3"] is None else f"The weaker of the regional rice and corn harvests in "
                                                f"{_q_before(d, 2)} was {_change(-v['R_C3'], '%')} than a year earlier."]
        return " ".join(p for p in parts if p) or none
    if group == "fish_kill":
        return none if v["R_C4"] is None else (f"Regional fisheries production in {_q_before(d, 2)} was "
                                               f"{_change(-v['R_C4'], '%')} than a year earlier.")
    if group == "hunger":
        return f"The forecast starts from the {latest_sws(r)}; the threshold is {H_LINE}%."
    if group == "poverty":
        return (f"PSA 2023 poverty incidence among families {float(r['pov_families_2023']):.1f}% (CV "
                f"{float(r['pov_families_2023_cv']):.1f}%): it weights the province score and never changes the "
                f"class. {food_poverty_text(r)[0].upper()}{food_poverty_text(r)[1:]}.")
    if group == "news":
        return f"{_clause(r.get('regional_news_text'))}. {_clause(r.get('province_news_text'))}." if code else \
            f"{_clause(r.get('regional_news_text'))}."
    return None


def drivers(code: str, quarter: str, base: dict) -> dict:
    """Driver bars from the regional forecast's SHAP (log-odds), grouped into the five dashboard drivers; past SWS
    hunger, the news inputs and the lead go to other_abs (otherPct)."""
    r = row(code, quarter)
    if r is None:
        return base
    news = {d["driver_group"]: d.get("trigger_proportion") for d in base.get("drivers", [])}
    avg = ({g: _f(r.get(f"avg8_shap_{g}")) or 0.0 for g in SHOWN_GROUPS}
           if evaluation().get("driver_view") in ("trailing8", "relative") else None)
    if avg:                                     # C-E demo: trailing-8 influence of this quarter's forecast
        ds = [{"driver_group": g, "driver_label": GROUP_LABELS[g], "group_shap": float(avg.get(g, 0.0)),
               "direction": "increases_risk" if avg.get(g, 0.0) > 0 else "protective" if avg.get(g, 0.0) < 0 else
               "no_effect", "trigger_proportion": news.get(g)} for g in SHOWN_GROUPS]
        return {**base, "drivers": ds, "other_abs": 0.0, "other_pct": 0.0, "ch1": r}
    ds = []
    for g in SHOWN_GROUPS:
        c = 0.0 if g in NOT_INPUT else (_f(r.get(f"shap_{g}")) or 0.0)
        ds.append({"driver_group": g, "driver_label": GROUP_LABELS[g], "group_shap": round(c, 6),
                   "direction": "increases_risk" if c > 0 else "protective" if c < 0 else "no_effect",
                   "trigger_proportion": news.get(g)})
    other = _other_abs(r)
    total = sum(abs(d["group_shap"]) for d in ds) + other or 1.0
    return {**base, "drivers": ds, "other_abs": other, "other_pct": round(100 * other / total, 1), "ch1": r}


# ---------------------------------------------------------------------------------------------- summary
def sentence(code: str | None, name: str, quarter: str, mean_p: float | None = None) -> str | None:
    """One sentence for the summary line (only the first sentence is shown): the regional class and probability, the
    actual outcome for a past quarter, the latest SWS reading, the regional statement, the province score and context
    (or, for the region, the provinces by score and the regional news), the reliability of the lead and, for an issued
    HIGH forecast, the human-confirmation flag."""
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs:
        return None
    r = rs[0]
    p = float(r["probability"])
    past = past_text(r)
    head = (f"FOOD-INSECURITY RISK for {name}, {quarter}: {_class(r)} (regional probability {p:.2f} that Balance Luzon "
            f"SWS hunger is above {H_LINE}%{'; ' + past if past else ''}; {latest_sws(r)}; classification is regional, "
            "the province score weights it by PSA poverty and never changes the class")
    if code is None:
        order = sorted(rs, key=_priority)
        ctx = ("; provinces by poverty-weighted score: " + ", ".join(
            f"{x['province']} {score(x):.2f} (food-price pressure {x['price_band'] or 'n/a'})" for x in order)
            + f"; {_clause(r.get('regional_news_text'))}")
    else:
        ctx = f"; {name}: {province_context(r)}"
    flag = f"; {REVIEW_FLAG[:-1]}" if is_high(r) and kind(r) == "forecast" else ""
    return f"{head}{ctx}; {reliability_text(r)}{flag}."


def data_status(code: str | None, quarter: str) -> tuple[str, str]:
    rs = [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]
    if not rs:
        return "unavailable", "The input values of this forecast were not recorded."
    labels = {"market": "CPI and world prices", "climate": "climate and crop production", "fish_kill": "fisheries",
              "hunger": "SWS hunger", "news": "news"}
    missing = [lab for g, lab in labels.items() if str(rs[0].get(f"avail_{g}")) != "1"]
    if not missing:
        return "sufficient", "Every input group had a published value at the issue date."
    return "limited", ("No published value at the issue date for: " + ", ".join(missing) + ". Missing data is left "
                       "blank, never counted as low risk.")


def model_line() -> str:
    ev = evaluation()
    if ev.get("model_line"):
        return f"{ev['model_line']} {REGIONAL}"
    m1, m2 = ev["leads"]["1"]["metrics"], ev["leads"]["2"]["metrics"]
    return (f"C-b: one LightGBM (stacked leads, walk-forward from 1998; IMPROVE_V2 reference inputs plus the FSSI "
            f"anomaly as its NLP input) forecasting "
            f"P(Balance Luzon SWS hunger > {H_LINE}%). Maximum Reliable Lead Time {reliable_lead()} quarters under the "
            f"paper's 75% rule (Algorithm 3; development accuracy Lead 1 {m1['accuracy']:.3f}, Lead 2 "
            f"{m2['accuracy']:.3f}, Lead 3 {ev['leads']['3']['metrics']['accuracy']:.3f}); "
            f"{ev['max_reliable_lead_r1_r7']} under the stricter rules R1-R7. {REGIONAL}")


def identity(code: str | None, quarter: str) -> dict | None:
    r = next((r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)), None)
    if r is None:
        return None
    return {"servingMode": "thesis", "servedModel": r.get("model") or "NEWS_V2-CB", "modelVersion": model_line(),
            "lead": int(r["lead"]), "issued": r["issue_date"], "targetQuarter": quarter,
            "evidenceStatus": ("passes the paper's 75% rule, fails R1-R7 (development evidence)"
                               if status(r) == "reliable" else "beyond the reliable horizon"),
            "lead2Accuracy": next((s for s in reliability_sentences() if s.startswith("Lead 2")), ""),
            "seal": r.get("seal_sha256") or None}


# ---------------------------------------------------------------------------------------------- reports
def driver_text(triggers: list[dict], hunger: float | None = None) -> str:
    up = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "increases_risk"]
    down = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "protective"]
    return ("Each bar is the indicator group's relative influence (SHAP, rescaled to 100%) on the regional "
            "food-insecurity forecast, the same for every province. "
            + ("Pushing it up: " + ", ".join(up) + ". " if up else "")
            + ("Pulling it down: " + ", ".join(down) + ". " if down else "")
            + "Past SWS hunger, the largest input, and the news inputs are reported as the other share. They show "
              "what moved the model, not causes.")


def reliability_sentences() -> list[str]:
    ev = evaluation()
    out = []
    for k in ("1", "2"):
        L = ev["leads"][k]
        m = L["metrics"]
        out.append(f"Lead {k} passed Algorithm 3, the paper's 75% rule (mean walk-forward accuracy >= 0.75): accuracy "
                   f"{m['accuracy']:.3f} ({m['TP'] + m['TN']}/{L['n']} quarters, {L['period']}; persistence "
                   f"{L['persistence_accuracy']:.3f}), precision {m['precision']:.2f}, recall {m['recall']:.2f}, AUC "
                   f"{m['auc']:.2f}, Brier {m['brier']:.3f}; it fails the stricter rules "
                   f"{', '.join(f'{x} ({RULE_NAMES.get(x, x)})' for x in L['failed'])}.")
    m3 = ev["leads"]["3"]["metrics"]
    out.append(f"Lead 3 failed (accuracy {m3['accuracy']:.3f}), so the Maximum Reliable Lead Time is "
               f"{reliable_lead()} quarters and nothing beyond Lead 2 is shown; under R1-R7 it is "
               f"{ev['max_reliable_lead_r1_r7']}.")
    out.append(f"NLP: {news_effect_text(1)[0].upper()}{news_effect_text(1)[1:]}. With news available only from 2021, "
               "it adds no measurable predictive value (Objective 1 evaluated).")
    out.append(f"Development evidence: every scored quarter was examined while the model was built. The Lead-2 "
               f"forecast issued {ev['seal_issue_date']} is sealed (SHA-256 {ev['seal_sha256'][:8]}, after the results "
               "were known) and will be scored when SWS publishes that quarter.")
    out.append(FNRI)
    return out


def method_rows() -> tuple[list[str], list[list[str]]]:
    head = ["Lead", "Rows", "Accuracy", "Precision", "Recall", "F1", "AUC", "Brier", "Reliable"]
    out = []
    for k, v in sorted(evaluation()["leads"].items(), key=lambda kv: int(kv[0])):
        m = v["metrics"]
        out.append([k, str(v["n"]), f"{m['accuracy']:.3f}", f"{m['precision']:.2f}", f"{m['recall']:.2f}",
                    f"{m['f1']:.2f}", f"{m['auc']:.2f}", f"{m['brier']:.3f}",
                    "75% rule only" if v["reliable"] else "no"])
    return head, out


# ---------------------------------------------------------------------------------------------- Rules 1 and 7
def forecast_quarters(quarter: str | None = None) -> list[str]:
    return sorted({q for (_, q), r in rows().items() if kind(r) == "forecast" and (quarter is None or q == quarter)})


def unapproved_pairs(published: set[tuple[str, str]], quarter: str | None = None) -> set[tuple[str, str]]:
    """Rule 1: (province_id, quarter) of every issued forecast that no administrator has approved (PUBLISHED review
    record). They are withheld from the public endpoints like a rejection; walk-forward quarters are not gated."""
    from app.services import reference as ref

    out = set()
    for (code, q), r in rows().items():
        if kind(r) == "forecast" and (quarter is None or q == quarter):
            pid = ref.CODE_TO_SLUG.get(code)
            if pid and (pid, q) not in published:
                out.add((pid, q))
    return out


REGION_CODE = "PH040000000"
ALERT_REASON = "REGIONAL_FOOD_INSECURITY_HIGH"
NEWS_ALERT_REASON = "PROVINCE_NEWS_EARLY_WARNING"


def alert_candidates(quarter: str | None = None) -> list[dict]:
    """Rule 7: ONE regional candidate per issued HIGH forecast quarter (the classification is regional, so never five
    provincial copies), and one provincial candidate per issued forecast whose province news flag is raised. Staged
    only; an administrator confirms or dismisses it. Nothing here notifies anyone."""
    out = []
    for q in forecast_quarters(quarter):
        rs = sorted((r for (_, qq), r in rows().items() if qq == q), key=lambda r: r["province_code"])
        if is_high(rs[0]):
            out.append({"quarter": q, "province_code": REGION_CODE, "alert_reason": ALERT_REASON,
                        "threshold_exceeded": True, "prev_risk_probability": None, "risk_delta": None,
                        "probability": float(rs[0]["probability"]), "lead": int(rs[0]["lead"]),
                        "statement": REVIEW_FLAG})
        for r in rs:
            if is_flagged(r):
                out.append({"quarter": q, "province_code": r["province_code"], "alert_reason": NEWS_ALERT_REASON,
                            "threshold_exceeded": False, "prev_risk_probability": None, "risk_delta": None,
                            "probability": float(r["probability"]), "lead": int(r["lead"]),
                            "statement": f"{_clause(r['province_news_text'])}; {NEWS_FLAG_NOTE}."})
    return out


async def stage_alerts(db, quarter: str | None = None) -> dict:
    """Insert the candidates not already present as STAGED alerts (idempotent). No automatic caller and no
    notification: an administrator runs and reviews it."""
    from sqlalchemy import select

    from app.db.models import AlertRecord
    from app.db.repository.alert_repo import AlertRepository

    repo = AlertRepository(db)
    res = {"staged": [], "existing": []}
    for c in alert_candidates(quarter):
        q = select(AlertRecord).where(AlertRecord.quarter == c["quarter"], AlertRecord.province_code == c["province_code"],
                                      AlertRecord.alert_reason == c["alert_reason"])
        if (await db.execute(q)).scalar_one_or_none() is not None:
            res["existing"].append(c)
            continue
        await repo.insert({k: c[k] for k in ("quarter", "province_code", "alert_reason", "threshold_exceeded",
                                             "prev_risk_probability", "risk_delta")})
        res["staged"].append(c)
    return res
