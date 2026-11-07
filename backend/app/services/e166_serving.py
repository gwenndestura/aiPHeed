"""
app/services/e166_serving.py
----------------------------
Serves the thesis model E166 through the EXISTING dashboard routes for EVERY quarter on the timeline (owner decision
2026-11-06: "implemented to the whole system, not only 2027-Q1"); the frontend is unchanged.

Each quarter T is E166 run as of the issue quarter T-1 (one quarter ahead) with only information published before that
date (app.e166.history). 2027-Q1 is the sealed live forecast; earlier quarters are back-forecasts with no provincial
survey to check them against, and say so.

It produces records in the formats app.services.dashboard already consumes:
    province_records(q)      -> raw province forecast rows (_province_forecasts)
    municipal_frame(q)       -> the LGU frame (_municipal_frame)
    drivers(code, q)         -> grouped driver rows (_drivers)

Only in the normal serving mode: an operator who deliberately selects a research mode (AIPHEED_LEAD2_MODEL other than
the default) gets that mode unchanged. AIPHEED_E166_SERVE=0 switches E166 off everywhere.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os

import pandas as pd

from app.paths import backend_path
from app.services import reference as ref

# Which thesis model is served (owner decision 2026-11-06: "use E168 from now on"); AIPHEED_THESIS_MODEL=e166 serves E166.
MODEL = os.environ.get("AIPHEED_THESIS_MODEL", "e168").lower()
NAME = {"e168": "E168", "e166": "E166"}.get(MODEL, MODEL.upper())
HIST = backend_path(f"data/{MODEL}/out/history")
LIVE = "2027-Q1"
STATUS = {
    "e168": ("Retrospectively validated on DOST-FNRI surveys: reliable up to three quarters ahead by the study's 75% accuracy "
             "rule, and passes all six strict reliability criteria (C1-C6) one quarter ahead. Risk indicator only; not an "
             "official food-insecurity classification."),
    "e166": ("Retrospectively validated: passes all six reliability criteria (C1-C6) at one and two quarters ahead; adoption "
             "pending the adviser's decision. Risk indicator only; not an official food-insecurity classification."),
}.get(MODEL, "Risk indicator only; not an official food-insecurity classification.")
METHOD = {
    "e168": ("the province's last DOST-FNRI survey (shrunk toward its history) adjusted by a LightGBM model of the five trigger "
             "groups and news signals, with temperature-shrunk scores"),
    "e166": ("the province's last DOST-FNRI survey (shrunk toward its history) adjusted by the five trigger groups and news "
             "signals through automatic model selection, with temperature-shrunk scores"),
}.get(MODEL, "the thesis model")

INDICATOR = {
    "id": f"{MODEL}_high_food_insecurity_probability",
    "name": f"Probability of HIGH food-insecurity risk (thesis model {NAME}{', LightGBM' if MODEL == 'e168' else ''})",
    "definition": (f"Probability that the province's HFIAS moderate-or-severe food insecurity is at or above 50% in the target "
                   f"quarter, from {NAME}: {METHOD}. HIGH when the probability is 0.50 or more, equivalent to a forecast score "
                   "of 50 or more."),
    "unit": "probability (0-1)",
    "horizon": ("One quarter ahead: each quarter is forecast at the start of the previous quarter with information published "
                "before that date. 2027-Q1 is the live forecast; earlier quarters are back-forecasts made the same way."),
    "source": ("DOST-FNRI HFIAS provincial rounds (2013-2021), PSA CPI, poverty and regional accounts, NASA POWER, IBTrACS, "
               "PSA farm and fisheries output, LFS and BSP series, and the Filipino-English news pipeline (FSSI)"),
    "caveat": STATUS,
}

STATUS_NOTES = {
    "contributes": f"This factor group is an input of the thesis model ({NAME}) and moved this forecast in the direction shown, "
                   "relative to the province's last DOST-FNRI survey.",
    "no_effect": f"This factor group is an input of the thesis model ({NAME}) but did not measurably move this forecast.",
    "no_model_input": f"The thesis model ({NAME}) has no separate input for this factor group in this forecast.",
}
# The dashboard's five risk drivers (the paper's five trigger categories). Each input, official or news, counts toward the
# trigger group it belongs to (market news -> Market, climate news -> Climate, ...). Inputs outside the five (general
# food-stress news / FSSI, poverty and density, survey age) are reported as the "other" share, as before.
GROUP_OF = {"market": "market", "climate": "climate", "employment": "employment", "remittance": "ofw_remittance"}
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Production", "employment": "Employment (national)",
          "ofw_remittance": "OFW Remittance (national)"}
ORDER = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
RANKING_METHOD = ("risk = province P(HIGH) x (0.6 x poverty_norm + 0.4 x density_norm), min-max within province "
                  "(PSA 2021 small-area poverty, 2020 census density)")
EXPLAINABILITY_NOTE = (f"Thesis model {NAME}. Most of each forecast comes from the province's last DOST-FNRI survey; the bars "
                       "show how much each factor group moved the forecast up or down from that survey. They describe the "
                       "model, not causes. " + STATUS)


@functools.lru_cache(maxsize=1)
def quarters() -> tuple[str, ...]:
    if not HIST.exists():
        return ()
    return tuple(sorted((p.stem for p in HIST.glob("20??-Q?.json")), key=ref.quarter_index))


def enabled() -> bool:
    from app.ml.inference import e41_lead2 as E41L2
    return os.environ.get("AIPHEED_E166_SERVE", "1") != "0" and not E41L2.active() and bool(quarters())


def covers(quarter: str | None) -> bool:
    return quarter is not None and enabled() and quarter in quarters()


def previous(quarter: str) -> str | None:
    i = ref.quarter_index(quarter) - 1
    p = f"{i // 4}-Q{i % 4 + 1}"
    return p if covers(p) else None


@functools.lru_cache(maxsize=32)
def _q(quarter: str) -> dict:
    return json.loads((HIST / f"{quarter}.json").read_text())


def model_articles(province_code: str | None, quarter: str) -> int:
    """Articles the thesis model used for this province-quarter (the last complete quarter before its issue date); the
    region is the sum over the five provinces. The LIMITED_SIGNAL rule (fewer than 5) applies to this count."""
    rows = _q(quarter)["forecasts"]
    if province_code is None:
        return int(sum(r["articles_last_quarter"] for r in rows))
    name = _name(province_code, quarter)
    return int(next((r["articles_last_quarter"] for r in rows if r["province"] == name), 0))


def validate() -> list[str]:
    """Strict-mode readiness: serving enabled, every quarter present, the live forecast equal to its seal."""
    import json as _json
    problems = []
    if not enabled():
        problems.append("serving disabled (AIPHEED_E166_SERVE=0, a Lead-2 research mode active, or no history files)")
    expected = [f"{y}-Q{q}" for y in range(2023, 2028) for q in range(1, 5)]
    expected = expected[:expected.index(LIVE) + 1]
    missing = [q for q in expected if q not in quarters()]
    if missing:
        problems.append(f"missing quarters: {missing}")
    seal = HIST.parent / f"sealed_{LIVE}.json"
    if not seal.exists():
        problems.append(f"sealed forecast missing: {seal.name}")
    elif LIVE in quarters() and _json.loads(seal.read_text())["forecasts"] != _q(LIVE)["forecasts"]:
        problems.append("live forecast differs from its seal")
    return problems


def shown_articles(province_code: str, quarter: str) -> int:
    """The article count the dashboard shows for this province-quarter (news panel and province card). The LIMITED_SIGNAL
    flag uses this same count, so the number on screen and the flag never disagree (paper: fewer than 5 articles)."""
    return model_articles(province_code, quarter)


def _flag(province_code: str, quarter: str) -> str:
    return "LIMITED_SIGNAL" if shown_articles(province_code, quarter) < 5 else "SUFFICIENT"


def province_records(quarter: str) -> list[dict]:
    q = _q(quarter)
    live = quarter == LIVE
    out = []
    for r in q["forecasts"]:
        code = ref.province_code(r["province"].lower())
        if code is None:
            continue
        kind = (f"Forecast issued {q['issue_date']} for {quarter} (one quarter ahead) by the thesis model {NAME}." if live else
                f"Back-forecast for {quarter} by the thesis model {NAME}, made as of {q['issue_date']} with information "
                "published before that date. No provincial survey exists for this quarter to check it against.")
        out.append({
            "province_code": code, "province_name": r["province"], "quarter": quarter,
            "risk_probability": float(r["p_high"]), "risk_label": None,
            "confidence_statement": (f"{kind} Forecast score {r['score']:.1f} on the HFIAS moderate-or-severe scale (90% range "
                                     f"{r['low90']:.1f} to {r['high90']:.1f}); probability of HIGH {r['p_high']:.3f}; class "
                                     f"{r['class']}. " + STATUS),
            "horizon_label": (f"Next quarter (forecast issued {q['issue_date']}, one quarter ahead)" if live else
                              f"One quarter ahead (back-forecast as of {q['issue_date']})"),
            "forecast_horizon_quarters": 1,
            "verification_date": f"{q['issue_date']}T00:00:00+08:00 (exclusive)",
            "data_sufficiency_flag": _flag(code, quarter),
            "mode": "FORECAST", "origin": q["issue_date"], "information_cutoff": q["issue_date"], "provenance": f"{NAME} (app.{MODEL}.history)",
            "observed_S1": None, "observed_label": None,
        })
    return out


def municipal_frame(quarter: str) -> pd.DataFrame:
    d = pd.DataFrame(_q(quarter)["lgus"])
    sha = hashlib.sha256((HIST / f"{quarter}.json").read_bytes()).hexdigest()
    q = _q(quarter)
    return pd.DataFrame({
        "lgu_code": d["lgu_code"].astype(str).str.zfill(9),
        "risk_index": d["risk_index"],
        "rank_region": d["rank_in_region"],
        "rank_in_province": d["rank_in_province"],
        "tied": d.duplicated("risk_index", keep=False),
        "disaggregation_label": d["disaggregation_label"],
        "data_sufficiency_flag": [_flag(ref.province_code(p.lower()), quarter) for p in d["province_name"]],
        "province_probability": d["province_risk_prob"],
        "vulnerability_index": d["vulnerability"],
        "estimate_source": [{"mode": "FORECAST", "origin": q["issue_date"], "quarter": quarter,
                             "score_type": INDICATOR["id"]}] * len(d),
        "ranking_method": RANKING_METHOD,
        "rows_sha256": sha,
    })


@functools.lru_cache(maxsize=32)
def _contrib(quarter: str) -> pd.DataFrame:
    s = pd.DataFrame(_q(quarter)["contributions"])
    if s.empty:
        return pd.DataFrame(columns=["province", "feature", "group", "source", "contribution", "ui_group"])

    def ui_group(row) -> str | None:
        if row["feature"] == "c_fish_yoy":
            return "fish_kill"
        return GROUP_OF.get(row["group"])             # FSSI / poverty / survey age -> the "other" share
    s["ui_group"] = s.apply(ui_group, axis=1)
    return s


def _name(code: str | None, quarter: str) -> str | None:
    return next((r["province"] for r in _q(quarter)["forecasts"] if ref.province_code(r["province"].lower()) == code), None)


def drivers(province_code: str, quarter: str) -> dict:
    name = _name(province_code, quarter)
    s = _contrib(quarter)
    s = s[s["province"] == name]
    total = float(s["contribution"].abs().sum()) or 1.0
    other = float(s[s["ui_group"].isna()]["contribution"].abs().sum())
    rows = []
    for g in ORDER:
        v = float(s[s["ui_group"] == g]["contribution"].sum())
        rows.append({"driver_group": g, "driver_label": LABELS[g], "group_shap": round(v, 6),
                     "abs_shap": round(float(s[s["ui_group"] == g]["contribution"].abs().sum()), 6),   # share numerator
                     "direction": "increases_risk" if v >= 0 else "protective", "trigger_proportion": None})
    arts = next((r["articles_last_quarter"] for r in _q(quarter)["forecasts"] if r["province"] == name), 0)
    # driver share = sum |SHAP| of the group's inputs / sum |SHAP| of all served inputs; other_abs = the remainder
    return {"drivers": rows, "article_count": arts, "other_pct": round(other / total * 100, 1), "other_abs": round(other, 6),
            "evidence_quarter": quarter}


def trigger_status(key: str, pct: int, quarter: str) -> str:
    present = set(_contrib(quarter)["ui_group"].dropna())
    if key not in present:
        return "no_model_input"
    return "contributes" if pct > 0 else "no_effect"


def evidence_note(province_code: str | None, key: str, quarter: str) -> str | None:
    s = _contrib(quarter)
    if province_code:
        s = s[s["province"] == _name(province_code, quarter)]
    s = s[s["ui_group"] == key]
    if s.empty:
        return None
    top = s.groupby("feature")["contribution"].sum().abs().sort_values(ascending=False).head(2).index.tolist()
    return "Largest inputs in this group: " + "; ".join(FEATURE_LABELS.get(f, f) for f in top) + "."


FEATURE_LABELS = {
    "a_net_since": "area food-stress news (FSSI), change since the last survey", "a_e_net": "area food-stress news (FSSI)",
    "n_e_net": "national food-stress news (FSSI)", "n_net_since": "national food-stress news (FSSI), change since the last survey",
    "p_e_net": "province food-stress news (FSSI)", "p_net_since": "province food-stress news (FSSI), change since the last survey",
    "n_e_market": "national market news", "n_e_hunger": "national hunger news", "a_e_hunger": "area hunger news",
    "rain_since": "rainfall change since the last survey", "soil_since": "soil moisture change since the last survey",
    "agri_since": "farm output change since the last survey", "tc_rate_since": "typhoon rate since the last survey",
    "c_rain_anom_6m": "rainfall anomaly (6 months)", "c_soil_anom_3m": "soil moisture anomaly (3 months)", "c_tc_4q": "typhoons (4 quarters)",
    "c_agri_yoy": "farm output growth", "c_fish_yoy": "fisheries output growth", "oni": "El Nino index",
    "cpi_food_yoy": "food inflation", "cpi_rice_yoy": "rice inflation", "cpi_food_rel_nat": "food inflation vs national",
    "cpi_since": "food prices since the last survey", "cpi_food_3m": "food inflation (3 months)", "cpi_food_accel": "food inflation acceleration",
    "unemp_rate": "unemployment rate", "unemp_yoy": "unemployment change", "unemp_chg_since": "unemployment change since the last survey",
    "income_growth": "regional household consumption growth", "remit_yoy": "remittance growth", "remit_since": "remittances since the last survey",
    "p_poverty": "poverty incidence (relative)", "p_subsistence": "subsistence incidence (relative)", "p_poverty_gap": "poverty gap (relative)",
    "p_density": "population density (relative)", "income_rel": "regional household consumption (relative)",
}


# ------------------------------------------------------------------ validated performance (PDF Method section, /config)
@functools.lru_cache(maxsize=1)
def performance() -> dict:
    """The served thesis model's locked retrospective results: leads 1-8 and the Lead-1 baseline comparison."""
    import json

    r = json.loads(backend_path(f"data/{MODEL}/out/results.json").read_text())
    rel = r["reliability"]["TS"] if MODEL == "e166" else r["reliability"]
    leads = [{"lead": x["lead"], "rows": x["rows"], "correct": x["confusion"]["tp"] + x["confusion"]["tn"], "accuracy": x["accuracy"],
              "precision": x["precision"], "recall": x["high_recall"], "f1": x["f1"], "auc": x["auc"], "brier": x["brier_soft"],
              "meets75": x["accuracy"] >= 0.75, "strictC1toC6": bool(x["reliable"]),
              "failedCriteria": [k for k, v in x["criteria"].items() if not v]} for x in rel["leads"]]
    paper = 0
    for x in leads:
        if not x["meets75"]:
            break
        paper = x["lead"]
    names = {"PERS": "B1 Persistence (last survey)", "LR": "B2 Logistic regression, combined", "LR_GOV": "B3 Logistic regression, government",
             "LR_NEWS": "B4 Logistic regression, news (NLP)", "GOV": "B5 LightGBM, government", "NEWS": "B6 LightGBM, news (NLP)",
             "PSA": "PSA poverty only"}
    if MODEL == "e166":
        b = json.loads(backend_path("data/e166/out/objectives/baseline_results.json").read_text())["leads"]["1"]["metrics"]
    else:
        b = {k: v["metrics"] for k, v in r["lead1_vs"].items()}
    base = {names[k]: {m: b[k][m] for m in ("accuracy", "f1", "auc", "brier")} for k in names if k in b}
    return {"model": INDICATOR["name"], "target": INDICATOR["definition"], "status": STATUS,
            "validation": "Rolling origin over DOST-FNRI ENNS 2018, 2019 and 2021 (72 province rows per lead); each forecast uses "
                          "only information published before its issue date.",
            "reliabilityRule": "At least 75% accuracy (the study's rule); six strict criteria C1-C6 reported as a robustness check.",
            "maxReliableLeadTime": paper, "maxReliableLeadStrict": rel["maximum_reliable_lead"],
            "accuracy": leads[0]["accuracy"], "precision": leads[0]["precision"], "recall": leads[0]["recall"], "f1": leads[0]["f1"],
            "rocAuc": leads[0]["auc"], "brier": leads[0]["brier"], "leads": leads, "baselines": base}


# labels for the remaining news-signal inputs (prefix: p = province, a = SWS area, n = national; e = tone, tp = share of articles)
_SCOPE = {"p": "province", "a": "area", "n": "national"}
_TOPIC = {"market": "market", "climate": "climate", "employment": "employment", "remittance": "remittance", "poverty": "poverty",
          "hunger": "hunger", "response": "government-response"}
for _s, _w in _SCOPE.items():
    for _t, _tw in _TOPIC.items():
        FEATURE_LABELS.setdefault(f"{_s}_e_{_t}", f"{_w} {_tw} news")
        FEATURE_LABELS.setdefault(f"{_s}_tp_{_t}", f"{_w} share of {_tw} news")
FEATURE_LABELS.setdefault("p_intensity", "province news volume")
FEATURE_LABELS.setdefault("p_tg_hard", "province hardship news (trigger keywords)")
FEATURE_LABELS.setdefault("p_tg_resp", "province response news (trigger keywords)")
FEATURE_LABELS.setdefault("p_tg_net", "province net trigger news")
FEATURE_LABELS.setdefault("r_e_net", "regional food-stress news (FSSI)")
FEATURE_LABELS.setdefault("h2", "province survey history (two rounds)")
FEATURE_LABELS.setdefault("gap_q", "quarters since the last survey")
FEATURE_LABELS.setdefault("lead", "forecast lead")
