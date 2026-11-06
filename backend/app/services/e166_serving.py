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

HIST = backend_path("data/e166/out/history")
LIVE = "2027-Q1"
STATUS = ("Retrospectively validated: passes all six reliability criteria (C1-C6) at one and two quarters ahead; adoption "
          "pending the adviser's decision. Risk indicator only; not an official food-insecurity classification.")

INDICATOR = {
    "id": "e166_high_food_insecurity_probability",
    "name": "Probability of HIGH food-insecurity risk (thesis model E166)",
    "definition": ("Probability that the province's HFIAS moderate-or-severe food insecurity is at or above 50% in the target "
                   "quarter, from E166: the province's last DOST-FNRI survey (shrunk toward its history) adjusted by the five "
                   "trigger groups and news signals through automatic model selection, with temperature-shrunk scores. "
                   "HIGH when the probability is 0.50 or more, equivalent to a forecast score of 50 or more."),
    "unit": "probability (0-1)",
    "horizon": ("One quarter ahead: each quarter is forecast at the start of the previous quarter with information published "
                "before that date. 2027-Q1 is the live forecast; earlier quarters are back-forecasts made the same way."),
    "source": ("DOST-FNRI HFIAS provincial rounds (2013-2021), PSA CPI, poverty and regional accounts, NASA POWER, IBTrACS, "
               "PSA farm and fisheries output, LFS and BSP series, and the Filipino-English news pipeline (FSSI)"),
    "caveat": STATUS,
}

STATUS_NOTES = {
    "contributes": "This factor group is an input of the thesis model (E166) and moved this forecast in the direction shown, "
                   "relative to the province's last DOST-FNRI survey.",
    "no_effect": "This factor group is an input of the thesis model (E166) but did not measurably move this forecast.",
    "no_model_input": "The thesis model (E166) has no separate input for this factor group in this forecast.",
}
GROUP_OF = {"market": "market", "climate": "climate", "employment": "employment", "remittance": "ofw_remittance", "poverty": "poverty"}
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill", "employment": "Employment",
          "ofw_remittance": "OFW Remittance", "poverty": "Poverty & Vulnerability", "news": "News Signals"}
ORDER = ["market", "climate", "fish_kill", "employment", "ofw_remittance", "poverty", "news"]
RANKING_METHOD = ("risk = province P(HIGH) x (0.6 x poverty_norm + 0.4 x density_norm), min-max within province "
                  "(PSA 2021 small-area poverty, 2020 census density)")
EXPLAINABILITY_NOTE = ("Thesis model E166. Most of each forecast comes from the province's last DOST-FNRI survey; the bars "
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


def province_records(quarter: str) -> list[dict]:
    q = _q(quarter)
    live = quarter == LIVE
    out = []
    for r in q["forecasts"]:
        code = ref.province_code(r["province"].lower())
        if code is None:
            continue
        kind = (f"Forecast issued {q['issue_date']} for {quarter} (one quarter ahead) by the thesis model E166." if live else
                f"Back-forecast for {quarter} by the thesis model E166, made as of {q['issue_date']} with information "
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
            "data_sufficiency_flag": "LIMITED_SIGNAL" if r["articles_last_quarter"] < 5 else "SUFFICIENT",
            "mode": "FORECAST", "origin": q["issue_date"], "information_cutoff": q["issue_date"], "provenance": "E166 (app.e166.history)",
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
        "data_sufficiency_flag": d["data_sufficiency_flag"],
        "province_probability": d["province_risk_prob"],
        "vulnerability_index": d["vulnerability"],
        "estimate_source": [{"mode": "FORECAST", "origin": q["issue_date"], "quarter": quarter,
                             "score_type": "e166_high_food_insecurity_probability"}] * len(d),
        "ranking_method": RANKING_METHOD,
        "rows_sha256": sha,
    })


@functools.lru_cache(maxsize=32)
def _contrib(quarter: str) -> pd.DataFrame:
    s = pd.DataFrame(_q(quarter)["contributions"])
    if s.empty:
        return pd.DataFrame(columns=["province", "feature", "group", "source", "contribution", "ui_group"])

    def ui_group(row) -> str | None:
        if row["source"] == "news":
            return "news"
        if row["feature"] == "c_fish_yoy":
            return "fish_kill"
        return GROUP_OF.get(row["group"])             # timing inputs (survey age, lead) go to the "other" share
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
                     "direction": "increases_risk" if v >= 0 else "protective", "trigger_proportion": None})
    arts = next((r["articles_last_quarter"] for r in _q(quarter)["forecasts"] if r["province"] == name), 0)
    return {"drivers": rows, "article_count": arts, "other_pct": round(other / total * 100, 1), "evidence_quarter": quarter}


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
