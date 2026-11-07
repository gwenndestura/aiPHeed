"""
app/ml/inference/e168_system.py
-------------------------------
The approved food-insecurity model (registry e168-lgbm-1.0) on the dashboard's map, province ranking, LGU ranking,
explanation cards, summary, reports and early warnings. Same interface as app.ml.inference.ch1_system, which it replaces
through app.ml.inference.map_engine while E168 is the registry's production model (AIPHEED_MAP_MODEL=ch1 keeps CH1).

Rows: data/e168/out/dashboard_rows.csv (app.e168.dashboard_export). It is the same 2026-Q4 issue as the approved artifact
data/e168/out/live_2027.json (the export asserts identical values) plus each trigger group's exact additive contribution
to the LightGBM change (pred_contrib, logit scale). Evidence: data/e168/out/lead_horizon.json and thesis_metrics.json
(pooled metrics), acceptance rule = owner decision 2026-11-07 (accuracy >= 75 % and better than the latest survey).
"""
from __future__ import annotations

import csv
import functools
import json
import os
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data" / "e168" / "out"
ROWS = DATA / "dashboard_rows.csv"
MODEL_ID = "e168-lgbm-1.0"
ISSUE = "2026-10-01"
SEAL = "f8228fae"
# The thesis's five triggers (Chapter III, Algorithm 2): market, climate, employment, OFW remittance and fish kill. Poverty
# and density are model inputs but belong to the LGU weighting (Objective 3); their push is reported in otherPct, not as a bar.
GROUPS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fisheries production",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
OTHER_COLS = ("shap_poverty", "shap_other")
SHOWN_GROUPS = dict(GROUPS)

INDICATOR = {
    "id": "e168_food_insecurity_risk",
    "name": "Food-insecurity risk (E168 LightGBM): probability that the province is HIGH",
    "is_food_insecurity_measurement": False,
    "food_insecurity_forecast": {"endpoint": "/api/v1/final/food-insecurity/outlook",
                                 "status": f"approved model {MODEL_ID} (owner-defined acceptance 2026-11-07)"},
    "definition": ("Forecast probability that the share of households with moderate or severe food insecurity (FNRI "
                   "HFIAS) in the province is 50% or more (HIGH). E168 starts from the latest published provincial survey "
                   "level and adds a constrained LightGBM forecast of the change, from the five trigger groups (market and "
                   "prices, climate, fisheries production (fish kill), employment and OFW remittances; news signals inside each "
                   "group; poverty and density also enter the model and weight the city and municipal ranking). HIGH at 0.50."),
    "unit": "probability 0-1 (HIGH at 0.50)",
    "horizon": ("issued 2026-10-01; Lead 1 = 2027-Q1, Lead 2 = 2027-Q2, Lead 3 = 2027-Q3. Leads 1-3 meet the project "
                "acceptance rule (accuracy >= 75% and better than the latest survey)."),
    "source": ("FNRI NNS/ENNS provincial HFIAS (2013-2021); PSA provincial CPI, LFS, poverty, production and population; "
               "BSP remittances; PAGASA/NOAA climate; IBTrACS; news (XLM-RoBERTa events, BERTopic topics)"),
    "caveat": ("A forecast risk class, not a measured food-insecurity rate. It was validated on 72 provincial forecasts from "
               "3 survey rounds (2018, 2019, 2021): accuracy 75.0% at one quarter ahead against 62.5% for the latest "
               "survey alone. It tends to over-predict by about 3 points (about 2 in 5 HIGH calls were false alarms) and "
               "rarely misses a HIGH province."),
}
RISK_LEVEL_BASIS = ("Band of the E168 probability (>= 0.50 is HIGH): HIGH means the forecast share of households with "
                    "moderate or severe food insecurity (HFIAS) is 50% or more. A forecast risk class, not a measured rate.")
LGU_BASIS = ("Relative position within the province: the province's E168 HIGH probability re-weighted by PSA poverty "
             "incidence (60%) and population density (40%), as Objective 3 specifies. Not a measured or official municipal "
             "food-insecurity rate or forecast; the ranking has not been checked against municipal outcomes.")
LGU_LEVEL_BASIS = ("Colour = the province's E168 risk class (HIGH when the province probability is 0.50 or more). The number "
                   "and rank are this city's or municipality's priority within the province: the province probability "
                   "re-weighted by PSA poverty incidence (60%) and population density (40%). Not a measured or official "
                   "municipal food-insecurity rate; the ranking has not been checked against municipal outcomes.")
EVENT = "food-insecurity risk (E168: probability that HFIAS moderate+severe is 50% or more)"
NATIONAL = ("Caution: this input is a national figure, the same for all five provinces, and removing it did not change "
            "E168's validation accuracy.")
GROUP_NOTES = {"employment": NATIONAL, "ofw_remittance": NATIONAL,
               "news": "News signals are inside the five groups; removing them did not change E168's validation Brier score."}
TRIGGER_STATUS_NOTES = {
    "contributes": "This factor is an input of the approved E168 food-insecurity model and moved this forecast in the "
                   "direction shown (model influence, not a cause).",
    "no_effect": "This factor is an input of the approved E168 model but did not measurably move this forecast.",
    "no_model_input": "The E168 model has no input for this factor, so it neither raised nor lowered the forecast.",
    "no_data": "No official data series exists for this factor, so it is not part of the forecast. Missing data is not "
               "evidence of low risk.",
    "data_not_in_model": "Official data for this factor exist, but E168 does not use them for this forecast.",
    "stale": "The latest official observation for this factor is more than two quarters old at the forecast date.",
    "insufficient_data": "None of this factor's inputs had a published value at the issue date, so no contribution is "
                         "reported. Missing data is not evidence of low risk.",
    "not_recorded": "Trigger contributions are recorded only for the issued E168 forecasts.",
}


@functools.lru_cache(maxsize=4)
def _production(path: str, mtime: int) -> str | None:
    try:
        from app import registry as R
        return R.production()["model_id"]
    except Exception:
        return None


def active() -> bool:
    if os.getenv("AIPHEED_MAP_MODEL", "auto").lower() not in ("auto", "e168") or not ROWS.exists():
        return False
    from app import registry as R
    reg = R.DIR / "registry.json"
    return reg.exists() and _production(str(reg), reg.stat().st_mtime_ns) == MODEL_ID


@functools.lru_cache(maxsize=2)
def _rows(path: str, mtime: int) -> dict[tuple[str, str], dict]:
    with open(path, newline="", encoding="utf-8") as f:
        # observed: empty until FNRI publishes the target survey (a forecast is never shown with an outcome it lacks)
        return {(r["province_code"], r["quarter"]): {**r, "observed": ""} for r in csv.DictReader(f)}


@functools.lru_cache(maxsize=4)
def _rows_path(reg_mtime: int) -> Path:
    try:
        from app.e168 import serve
        p = serve.artifact().parent / "dashboard_rows.csv"
        if p.exists():
            return p
    except Exception:
        pass
    return ROWS


def rows_path() -> Path:
    """The dashboard rows beside the approved artifact (a promoted quarterly issue keeps its own rows), else the 2026-Q4 export."""
    from app import registry as R
    reg = R.DIR / "registry.json"
    return _rows_path(reg.stat().st_mtime_ns if reg.exists() else 0)


def rows() -> dict[tuple[str, str], dict]:
    p = rows_path()
    return _rows(str(p), p.stat().st_mtime_ns)


def state_token() -> str:
    p = rows_path()
    return f"+e168:{p}:{p.stat().st_mtime_ns}"


def overlay_report() -> list[str]:
    return []


def _f(x) -> float | None:
    return None if x in (None, "", "nan") else float(x)


@functools.lru_cache(maxsize=1)
def evaluation() -> dict:
    H = json.loads((DATA / "lead_horizon.json").read_text(encoding="utf-8"))
    tm_path = DATA / "thesis_metrics.json"
    T = json.loads(tm_path.read_text(encoding="utf-8")) if tm_path.exists() else {}
    rl = H.get("horizon_75pct_and_beats_persistence") or 0
    leads, hz = {}, {}
    for k, v in H["leads"].items():
        t = T.get(str(k)) or {}
        m = t.get("E168", {})
        n = v["rows"]
        always_low = round(1 - (t.get("n_high", 0) / n), 3) if t else None
        z = 1.645                                   # Wilson 90 % interval for the pooled accuracy
        a = v["accuracy"]
        c, h = (a + z * z / (2 * n)) / (1 + z * z / n), z * ((a * (1 - a) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
        ok75, beats = a >= 0.75, bool(v["beats_persistence_C2"])
        leads[str(k)] = {"n": n, "n_quarters": len(t.get("folds", {})) or 3, "high_share": round(1 - always_low, 3) if always_low is not None else None,
                         "reliable": int(k) <= rl, "accuracy_ci90": [round(c - h, 3), round(c + h, 3)],
                         "baseline_accuracy": {"ALWAYS-LOW": always_low, "PERSISTENCE": v["persistence_accuracy"]},
                         "metrics": {"n": n, "accuracy": a, "balanced_accuracy": round((v["high_recall"] + v["low_recall"]) / 2, 3),
                                     "precision": m.get("precision_high", v["precision"]), "recall": m.get("recall_high", v["high_recall"]),
                                     "f1": m.get("f1_high"), "auc": m.get("auc_roc"), "brier": v["brier"], "tp": v["correct"], "tn": 0,
                                     "persistence_accuracy": v["persistence_accuracy"]}}
        hz[str(k)] = {"n": n, "n_quarters": leads[str(k)]["n_quarters"], "accuracy": a, "always_low_accuracy": always_low,
                      "reliable": int(k) <= rl, "criteria": {"accuracy_at_least_75": ok75, "better_than_latest_survey": beats},
                      "quarters_after_issue": int(k), "quarters_after_newest_sws": []}
    horizon_block = {"leads_evaluated": sorted(int(k) for k in H["leads"]), "testable_horizon_R1": max(int(k) for k in H["leads"]),
                     "max_reliable_lead": rl, "individually_passing_leads": [int(k) for k, v in hz.items() if all(v["criteria"].values())],
                     "why_not_longer": "Lead 4 accuracy is below 75% (the model still beats the latest survey up to Lead 6).",
                     "leads": hz}
    return {"model": MODEL_ID, "max_reliable_lead": rl, "leads": leads, "horizon": horizon_block,
            "skill_horizon": H.get("skill_horizon_beats_persistence"), "seal_sha256": SEAL, "seal_issue_date": "ENNS 2022 forecasts",
            "protocol_name": "owner-defined acceptance (2026-11-07)",
            "acceptance_rule": "accuracy >= 75% and Brier significantly better than reusing the latest survey (set 2026-11-07, after the results were known)"}


def structural() -> bool:
    return False


def indicator() -> dict:
    return INDICATOR


def reliable_lead() -> int | None:
    return evaluation()["max_reliable_lead"]


def horizon() -> dict:
    ev = evaluation()
    return {"generated_max_lead": max((int(r["lead"]) for r in rows().values()), default=None),
            "evaluated_leads": [int(k) for k in ev["leads"]], "testable_max_lead": max(int(k) for k in ev["leads"]),
            "reliable_max_lead": ev["max_reliable_lead"], "individually_passing_leads": [int(k) for k, v in ev["leads"].items() if v["reliable"]],
            "why_not_longer": "Lead 4 accuracy 73.6% is below 75% (it still beats the latest survey up to Lead 6).",
            "reliable_quarters_after_newest_sws": None}


def status(r: dict) -> str:
    return "reliable" if (reliable_lead() or 0) >= int(r["lead"]) else "experimental"


def covers(quarter: str) -> bool:
    return any(q == quarter for _, q in rows())


def row(code: str, quarter: str) -> dict | None:
    return rows().get((code, quarter))


def kind(r: dict) -> str:
    return "forecast"


def reliability_text(r: dict) -> str:
    lead = int(r["lead"])
    v = evaluation()["leads"].get(str(lead))
    if v and v["reliable"]:
        return (f"Lead-{lead} forecast: meets the acceptance rule (accuracy {v['metrics']['accuracy']:.3f} on {v['n']} past "
                f"provincial forecasts; latest survey alone {v['metrics']['persistence_accuracy']:.3f})")
    return f"Lead-{lead} forecast: below the acceptance rule, experimental"


def province_row(code: str, name: str, quarter: str, base: dict | None) -> dict | None:
    r = row(code, quarter)
    if r is None:
        return None
    p = float(r["probability"])
    what = (f"{reliability_text(r)}; issued {r['issue_date']}; forecast HFIAS moderate+severe {float(r['score_pct']):.1f}% "
            f"(90% range {float(r['range90_low']):.1f}-{float(r['range90_high']):.1f}%); the outcome is not yet published.")
    out = dict(base or {})
    out.update({
        "province_code": code, "province_name": name, "quarter": quarter,
        "risk_probability": round(p, 6), "risk_label": None, "observed_label": None, "observed_S1": None,
        "data_sufficiency_flag": "SUFFICIENT", "forecast_horizon_quarters": int(r["lead"]),
        "horizon_label": what, "origin": r["issue_date"], "verification_date": r["issue_date"],
        "mode": f"E168_LEAD{int(r['lead'])}_FORECAST", "estimate_kind": "forecast",
        "score_type": "e168_high_probability", "score_definition": INDICATOR["definition"],
        "band": "High" if p >= 0.5 else "Low",
        "confidence_statement": (f"{name}, {quarter}: {'HIGH' if p >= 0.5 else 'LOW'} food-insecurity risk "
                                 f"(probability {p:.2f}). {what}")})
    return out


def province_rows(base_rows: list[dict], quarter: str, names: dict[str, str]) -> list[dict]:
    by = {r["province_code"]: r for r in base_rows}
    out = [x for code, name in names.items() if (x := province_row(code, name, quarter, by.get(code))) is not None]
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


GROUP_KEYS = tuple(GROUPS)


def group_status(code: str | None, quarter: str, key: str, pct: int) -> str | None:
    if key not in GROUPS:
        return None
    return "contributes" if pct > 0 else "no_effect"


def _rs(code: str | None, quarter: str) -> list[dict]:
    return [r for (c, q), r in rows().items() if q == quarter and (code is None or c == code)]


def _shap(r: dict, col: str) -> float:
    return abs(_f(r.get(col)) or 0.0)


def other_share(rs: list[dict]) -> float:
    """Share of the change attribution outside the five trigger bars: poverty and density, and forecast timing."""
    oth = sum(_shap(r, c) for r in rs for c in OTHER_COLS)
    tot = sum(_shap(r, f"shap_{g}") for r in rs for g in GROUPS) + oth
    return 100 * oth / tot if tot else 0.0


def evidence_note(code: str | None, quarter: str, other_pct: float | None = None, group: str | None = None) -> str:
    rs = _rs(code, quarter)
    base = (f" The forecast starts from the latest published survey level (about {float(rs[0]['baseline_pct']):.0f}% for "
            f"this province)" if code and rs else " The forecast starts from each province's latest published survey level")
    if other_pct is None:
        other_pct = other_share(rs)
    other = (f" Poverty and density (which also weight the city and municipal ranking) and forecast timing account for "
             f"another {other_pct:.0f}% of the change, not shown in the bars." if other_pct else "")
    note = ("The bars show each trigger group's push (exact LightGBM contributions, log-odds, rescaled to 100%) on E168's "
            "forecast change in household food insecurity. News signals are counted inside their group. They are model "
            f"influence, not causes.{base}; the bars explain only the change from it.{other}")
    return f"{note} {GROUP_NOTES[group]}" if group in GROUP_NOTES and group != "news" else note


def _val(r: dict, c: str) -> float | None:
    return _f(r.get(f"val_{c}"))


def plain_evidence(code: str | None, quarter: str, group: str) -> str | None:
    if code is None:
        return GROUP_NOTES.get(group)
    r = row(code, quarter)
    if r is None:
        return None
    none = "No published value was available at this forecast's issue date; missing data is not a sign of low risk."
    v = lambda c: _val(r, c)
    # Only values whose unit is unambiguous are quoted (provincial food inflation in %, cyclone count, ONI in deg C); the
    # other inputs enter the model transformed (logits, standardised changes), so they are named, not quoted.
    if group == "market":
        return none if v("cpi_food_yoy") is None else (
            f"Provincial food inflation (PSA CPI) was {v('cpi_food_yoy'):.1f}% year on year at the issue date; rice prices "
            "and the change since the last survey are also inputs.")
    if group == "climate":
        parts = [None if v("c_tc_4q") is None else f"{int(round(v('c_tc_4q')))} tropical cyclone(s) in the last four quarters.",
                 None if v("oni") is None else f"ONI (El Nino index) {v('oni'):+.1f} deg C.",
                 "Agricultural production changes and soil and rainfall anomalies are also inputs."]
        return " ".join(p for p in parts if p)
    if group == "fish_kill":
        return ("Fisheries production (PSA, provincial): its year-on-year change is an input; a fall pushes risk up."
                if v("c_fish_yoy") is not None else none)
    if group == "employment":
        return ("National unemployment (PSA LFS): its level and its change since the last survey are inputs. " + NATIONAL
                if v("unemp_rate") is not None else none)
    if group == "ofw_remittance":
        return ("OFW cash remittances (BSP, national): their year-on-year change is an input. " + NATIONAL
                if v("remit_yoy") is not None else none)
    if group == "poverty":
        return ("PSA provincial poverty incidence, subsistence incidence and poverty gap (the latest release usable at the "
                "issue date) and population density; they change only when PSA publishes a new round."
                if v("p_poverty") is not None else none)
    return None


def drivers(code: str, quarter: str, base: dict) -> dict:
    r = row(code, quarter)
    if r is None:
        return base
    ds = []
    for g, lab in GROUPS.items():
        c = _f(r.get(f"shap_{g}")) or 0.0
        ds.append({"driver_group": g, "driver_label": lab, "group_shap": round(c, 6),
                   "direction": "increases_risk" if c > 0 else "protective" if c < 0 else "no_effect",
                   "trigger_proportion": None})
    return {**base, "drivers": ds, "article_count": (base or {}).get("article_count", 0),
            "other_pct": round(other_share([r]), 1), "ch1": r}


def sentence(code: str | None, name: str, quarter: str, mean_p: float | None = None) -> str | None:
    if code is None:
        rs = _rs(None, quarter)
        if not rs:
            return None
        high = sum(float(r["probability"]) >= 0.5 for r in rs)
        top = max(rs, key=lambda r: float(r["score_pct"]))
        return (f"FOOD-INSECURITY RISK for CALABARZON, {quarter} (E168 forecast): {high} of {len(rs)} provinces HIGH; highest "
                f"forecast share {top['province']} {float(top['score_pct']):.0f}% of households moderately or severely "
                f"food insecure (HIGH at 50%); {reliability_text(rs[0])}.")
    r = row(code, quarter)
    if r is None:
        return None
    p = float(r["probability"])
    return (f"FOOD-INSECURITY RISK for {name}, {quarter} (E168 forecast): {'HIGH' if p >= 0.5 else 'LOW'} (probability "
            f"{p:.2f}; forecast {float(r['score_pct']):.1f}% of households moderately or severely food insecure, 90% range "
            f"{float(r['range90_low']):.0f}-{float(r['range90_high']):.0f}%; HIGH at 50%); {reliability_text(r)}.")


def early_warning(quarter: str, code: str | None) -> list[dict]:
    """A province is flagged only when E168 classes it HIGH (probability >= 0.50); otherwise a 'no warning' block."""
    out = []
    for r in _rs(code, quarter):
        p = float(r["probability"])
        warn = p >= 0.5
        out.append({"provinceCode": r["province_code"], "province": r["province"], "warn": warn,
                    "level": "HIGH" if warn else "LOW", "direction": "E168 HIGH" if warn else "below HIGH",
                    "text": (f"Early warning (model-generated, for DA review): {r['province']} is forecast HIGH for {quarter} "
                             f"(probability {p:.2f})." if warn else
                             f"No early warning: E168 forecasts {r['province']} below HIGH for {quarter} (probability {p:.2f}).")})
    return out


REPORT_COVER = ("<b>The number below is E168's forecast probability that the province is HIGH food-insecurity risk</b>: "
                "that 50% or more of households are moderately or severely food insecure (FNRI HFIAS), from 0 to 1, HIGH "
                "at 0.50. E168 starts from the latest published provincial survey level and adds a constrained LightGBM "
                "forecast of the change from the five trigger groups. <b>It is a forecast risk class, not a measured "
                "food-insecurity rate</b>. Approved under the project acceptance rule (accuracy of at least 75% and better "
                "than the latest survey) at 1 to 3 quarters ahead.")
REPORT_FOOTER = ("E168 food-insecurity risk forecast (probability of HIGH, HFIAS moderate+severe >= 50%) -- not an official "
                 "food insecurity classification.")
REPORT_BARS_NOTE = ("Red bars pushed E168's forecast change up, green bars pulled it down; groups with no effect are not "
                    "shown. Relative model influence, not causes.")


def text(name: str) -> str:
    return globals()[name]


def model_line() -> str:
    ev = evaluation()
    l1 = ev["leads"]["1"]["metrics"]
    return (f"E168 ({MODEL_ID}): latest provincial HFIAS survey level + constrained LightGBM change (five trigger groups, "
            f"news inside groups) + calibration. Leads 1-{ev['max_reliable_lead']} meet the acceptance rule (Lead 1 accuracy "
            f"{l1['accuracy']:.3f} on {l1['n']} provincial forecasts; latest survey alone {l1['persistence_accuracy']:.3f}).")


def driver_text(triggers: list[dict], hunger: float | None = None, other_pct: float | None = None) -> str:
    up = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "increases_risk"]
    down = [f"{t['label']} {t['pct']}%" for t in triggers if t["pct"] > 0 and t["direction"] == "protective"]
    other = (f" Poverty and density (used for the city and municipal ranking) and forecast timing account for another "
             f"{other_pct:.0f}% of that influence." if other_pct else "")
    return ("Each bar is a trigger group's relative influence (exact LightGBM contributions, rescaled to 100%) on E168's "
            "forecast change from the latest survey level. "
            + ("Pushing it up: " + ", ".join(up) + ". " if up else "")
            + ("Pulling it down: " + ", ".join(down) + ". " if down else "")
            + "They show what moved the model, not causes." + other)


def reliability_sentences() -> list[str]:
    ev = evaluation()
    out = []
    for k in ("1", "2", "3"):
        m = ev["leads"][k]["metrics"]
        out.append(f"Lead {k}: accuracy {m['accuracy']:.3f} on {m['n']} provincial forecasts (latest survey alone "
                   f"{m['persistence_accuracy']:.3f}), HIGH precision {m['precision']:.2f}, recall {m['recall']:.2f}"
                   + (f", F1 {m['f1']:.2f}, AUC {m['auc']:.2f}" if m.get("f1") is not None else "") + ".")
    out.append("Acceptance rule (owner decision 2026-11-07, set after the results were known): accuracy of at least 75% and a "
               "Brier score significantly better than reusing the latest survey. Leads 1-3 meet it; Lead 4 (73.6%) does not.")
    out.append("Evidence limits: 72 forecasts from 3 survey rounds; only 5 are CALABARZON provinces (all observed LOW). "
               f"Forecasts for the ENNS 2022 round are sealed (SHA-256 {SEAL}).")
    return out


def method_rows() -> tuple[list[str], list[list[str]]]:
    head = ["Lead", "Rows", "Accuracy", "Precision", "Recall", "F1", "AUC", "Brier", "Reliable"]
    out = []
    for k, v in sorted(evaluation()["leads"].items(), key=lambda kv: int(kv[0])):
        if int(k) > 6:
            continue
        m = v["metrics"]
        out.append([k, str(m["n"]), f"{m['accuracy']:.3f}", f"{m['precision']:.2f}", f"{m['recall']:.2f}",
                    "-" if m.get("f1") is None else f"{m['f1']:.2f}", "-" if m.get("auc") is None else f"{m['auc']:.2f}",
                    f"{m['brier']:.3f}", "yes" if v["reliable"] else "no"])
    return head, out


def data_status(code: str | None, quarter: str) -> tuple[str, str]:
    rs = _rs(code, quarter)
    if not rs:
        return "unavailable", "The input values of this forecast were not recorded."
    labels = {"cpi_food_yoy": "provincial food inflation", "unemp_rate": "unemployment", "remit_yoy": "OFW remittances",
              "p_poverty": "poverty incidence", "c_tc_4q": "tropical cyclones"}
    missing = [lab for c, lab in labels.items() if any(_val(r, c) is None for r in rs)]
    if not missing:
        return "sufficient", "Every main input had a published value at the issue date."
    return "limited", ("No published value at the issue date for: " + ", ".join(missing) + ". Missing data is left blank, "
                       "never counted as low risk.")


def identity(code: str | None, quarter: str) -> dict | None:
    rs = _rs(code, quarter)
    if not rs:
        return None
    r = rs[0]
    return {"servingMode": "thesis", "servedModel": MODEL_ID, "modelVersion": model_line(), "lead": int(r["lead"]),
            "issued": r["issue_date"], "targetQuarter": quarter,
            "evidenceStatus": "meets the acceptance rule" if status(r) == "reliable" else "experimental",
            "lead2Accuracy": next((s for s in reliability_sentences() if s.startswith("Lead 2")), ""),
            "seal": SEAL, "dataCutoff": r["issue_date"], "swsReadingUsed": None, "issueTrigger": "quarter_start"}
