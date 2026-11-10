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
import math
import os
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[3] / "data" / "e168" / "out"
ROWS = DATA / "dashboard_rows.csv"
MODEL_ID = "e168-lgbm-1.0"
ISSUE = "2026-10-01"
SEAL = "f8228fae"
# E184 (docs/e184/PROTOCOL.md): E168 with synthetic training data balanced 50/50, same artifact schema. It is served by
# this adapter only when the owner has promoted it in the registry; with E168 in production nothing below changes.
E184_ID = "e184-lgbm-syn50-1.0"
FAMILY = (MODEL_ID, E184_ID)
E184_DATA = Path(__file__).resolve().parents[3] / "data" / "e184" / "out"
# The thesis's five triggers (Chapter III, Algorithm 2): market, climate, employment, OFW remittance and fish kill.
# Fish kill is measured by a PROXY, PSA provincial fisheries production year-on-year (c_fish_yoy): no public fish-kill event
# series exists, so the label says so. Employment and OFW remittances are national series (the same for every province).
# Poverty and density are model inputs but belong to the LGU weighting (Objective 3); with forecast timing and survey
# history they are shown as "Other model inputs", so the five bars plus Other add to 100 % of |contribution| (nothing is
# rescaled away). Contributions are exact LightGBM pred_contrib values, which add, so a bar is the sum of its stored columns.
GROUPS = {"market": "Market / Prices", "climate": "Climate Stress", "employment": "Employment (national)",
          "ofw_remittance": "OFW Remittance (national)", "fish_kill": "Fish Kill (fisheries production proxy)"}
BAR_COLS = {"market": ("shap_market",), "climate": ("shap_climate",), "employment": ("shap_employment",),
            "ofw_remittance": ("shap_ofw_remittance",), "fish_kill": ("shap_fish_kill",)}
OTHER_COLS = ("shap_poverty", "shap_other")
SHOWN_GROUPS = dict(GROUPS)
# PDF report wording (app.services.report_data_e31 reads it through the map engine)
REPORT_NOUN = ("food-insecurity risk (E168 forecast probability that 50% or more of households are moderately or severely "
               "food insecure; not a measured rate)")
REPORT_DATA_NOUN = "E168 food-insecurity risk forecast (probability of HIGH; not a measured rate)"

INDICATOR = {
    "id": "e168_food_insecurity_risk",
    "name": "Food-insecurity risk (E168 LightGBM): probability that the province is HIGH",
    "is_food_insecurity_measurement": False,
    "food_insecurity_forecast": {"endpoint": "/api/v1/final/food-insecurity/outlook",
                                 "status": f"approved model {MODEL_ID} (owner-defined acceptance 2026-11-07)"},
    "definition": ("Forecast probability that the share of households with moderate or severe food insecurity (FNRI "
                   "HFIAS) in the province is 50% or more (HIGH). E168 starts from the latest published provincial survey "
                   "level and adds a constrained LightGBM forecast of the change, from the five trigger groups (market and "
                   "prices; climate; employment and OFW remittances, both national series; and fish kill, measured by the "
                   "proxy of provincial fisheries production change, not by fish-kill event records), with news signals "
                   "inside each group. Poverty and density are also inputs and weight the city and municipal ranking. "
                   "HIGH at 0.50."),
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
NATIONAL = "This is a national figure, the same for all five provinces."
GROUP_NOTES = {"employment": NATIONAL, "ofw_remittance": NATIONAL,
               "news": "News reports are counted inside the five groups."}
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


def served_id() -> str:
    """The production model of this adapter's family (E168, or E184 once the owner promotes it); E168 otherwise."""
    from app import registry as R
    reg = R.DIR / "registry.json"
    prod = _production(str(reg), reg.stat().st_mtime_ns) if reg.exists() else None
    return prod if prod in FAMILY else MODEL_ID


def active() -> bool:
    if os.getenv("AIPHEED_MAP_MODEL", "auto").lower() not in ("auto", "e168") or not ROWS.exists():
        return False
    from app import registry as R
    reg = R.DIR / "registry.json"
    return reg.exists() and _production(str(reg), reg.stat().st_mtime_ns) in FAMILY


def not_served_reasons() -> list[str]:
    """Why E168 is not on the map engine (empty when it is). Used by the strict start-up check."""
    from app import registry as R
    reg = R.DIR / "registry.json"
    out = []
    if os.getenv("AIPHEED_MAP_MODEL", "auto").lower() not in ("auto", "e168"):
        out.append(f"AIPHEED_MAP_MODEL={os.getenv('AIPHEED_MAP_MODEL')} overrides the approved model")
    if not ROWS.exists():
        out.append(f"served rows missing: {ROWS}")
    prod = _production(str(reg), reg.stat().st_mtime_ns) if reg.exists() else None
    if prod not in FAMILY:
        out.append(f"registry production model is {prod!r}, not {MODEL_ID}" + (f" or {E184_ID}" if E184_ID else ""))
    return out


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


def evaluation() -> dict:
    """The served model's own evaluation (E168's, or E184's once it is in production)."""
    return _evaluation(served_id())


@functools.lru_cache(maxsize=4)
def _evaluation(mid: str) -> dict:
    base = DATA if mid == MODEL_ID else E184_DATA
    H = json.loads((base / "lead_horizon.json").read_text(encoding="utf-8"))
    tm_path = base / "thesis_metrics.json"
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
        # confusion counts from the stored HIGH count, recall and precision (previously tp held the number correct, tn 0)
        nh, rec_h, prec_h = t.get("n_high"), m.get("recall_high", v["high_recall"]), m.get("precision_high", v["precision"])
        tp = round(rec_h * nh) if nh else None
        fp = round(tp / prec_h - tp) if tp and prec_h else None
        cm = ({"tp": tp, "fp": fp, "fn": nh - tp, "tn": n - nh - fp} if tp is not None and fp is not None
              else {"tp": None, "fp": None, "fn": None, "tn": None})
        leads[str(k)] = {"n": n, "n_quarters": len(t.get("folds", {})) or 3, "high_share": round(1 - always_low, 3) if always_low is not None else None,
                         "reliable": int(k) <= rl, "accuracy_ci90": [round(c - h, 3), round(c + h, 3)],
                         "baseline_accuracy": {"ALWAYS-LOW": always_low, "PERSISTENCE": v["persistence_accuracy"]},
                         "metrics": {"n": n, "accuracy": a, "balanced_accuracy": round((v["high_recall"] + v["low_recall"]) / 2, 3),
                                     "precision": m.get("precision_high", v["precision"]), "recall": m.get("recall_high", v["high_recall"]),
                                     "f1": m.get("f1_high"), "auc": m.get("auc_roc"), "brier": v["brier"], **cm, "correct": v["correct"],
                                     "persistence_accuracy": v["persistence_accuracy"]}}
        hz[str(k)] = {"n": n, "n_quarters": leads[str(k)]["n_quarters"], "accuracy": a, "always_low_accuracy": always_low,
                      "reliable": int(k) <= rl, "criteria": {"accuracy_at_least_75": ok75, "better_than_latest_survey": beats},
                      "quarters_after_issue": int(k), "quarters_after_newest_sws": []}
    horizon_block = {"leads_evaluated": sorted(int(k) for k in H["leads"]), "testable_horizon_R1": max(int(k) for k in H["leads"]),
                     "max_reliable_lead": rl, "individually_passing_leads": [int(k) for k, v in hz.items() if all(v["criteria"].values())],
                     "why_not_longer": "Lead 4 accuracy is below 75% (the model still beats the latest survey up to Lead 6).",
                     "leads": hz}
    return {"model": mid, "max_reliable_lead": rl, "leads": leads, "horizon": horizon_block,
            "skill_horizon": H.get("skill_horizon_beats_persistence"), "seal_sha256": SEAL if mid == MODEL_ID else _e184_seal(),
            "seal_issue_date": "ENNS 2022 forecasts",
            "protocol_name": "owner-defined acceptance (2026-11-07)",
            "acceptance_rule": "accuracy >= 75% and Brier significantly better than reusing the latest survey (set 2026-11-07, after the results were known)"}


evaluation.cache_clear = _evaluation.cache_clear


def _e184_seal() -> str:
    p = E184_DATA / "sealed_enns2022.json"
    if not p.exists():
        return "not sealed"
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


@functools.lru_cache(maxsize=2)
def _relabels(mid: str) -> tuple[tuple[str, str], ...]:
    """Text replacements when E184 is the served model: its own name, id, seal and accuracy instead of E168's."""
    if mid == MODEL_ID:
        return ()
    m = _evaluation(mid)["leads"]
    a1, p1 = m["1"]["metrics"]["accuracy"] * 100, m["1"]["metrics"]["persistence_accuracy"] * 100
    return (
        ("accuracy 75.0% at one quarter ahead against 62.5% for the latest survey alone. It tends to over-predict by about 3 "
         "points (about 2 in 5 HIGH calls were false alarms) and rarely misses a HIGH province.",
         f"accuracy {a1:.1f}% at one quarter ahead against {p1:.1f}% for the latest survey alone. It was trained on the real "
         "survey rows plus an equal number of labelled synthetic rows (never used in testing)."),
        ("Lead 4 (73.6%) does not.", "E184 was evaluated at Leads 1-3."),
        ("Lead 4 accuracy 73.6% is below 75% (it still beats the latest survey up to Lead 6).", "E184 was evaluated at Leads 1-3 only."),
        ("Lead 4 accuracy is below 75% (the model still beats the latest survey up to Lead 6).", "E184 was evaluated at Leads 1-3 only."),
        (MODEL_ID, E184_ID),
        ("E168 LightGBM", "E184 LightGBM with balanced synthetic training data"),
        (SEAL, _e184_seal()),
        ("E168", "E184"),
    )


def relabel(obj):
    """Return `obj` with E168's name, id, seal and accuracy sentences replaced by E184's when E184 is the production model.
    With E168 in production it returns `obj` itself, unchanged."""
    reps = _relabels(served_id())
    if not reps:
        return obj

    def sub(x):
        if isinstance(x, str):
            for a, b in reps:
                x = x.replace(a, b)
            return x
        if isinstance(x, dict):
            return {k: sub(v) for k, v in x.items()}
        if isinstance(x, list):
            return [sub(v) for v in x]
        if isinstance(x, tuple):
            return tuple(sub(v) for v in x)
        return x
    return sub(obj)


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


def _shift_q(q: str, k: int) -> str:
    i = int(q[:4]) * 4 + int(q[-1]) - 1 + k
    return f"{i // 4}-Q{i % 4 + 1}"


@functools.lru_cache(maxsize=4)
def _earlier_issues(served_cutoff: str) -> dict[tuple[str, str], tuple[float, str]]:
    """Lead-1 forecasts from E168 issues made before the served one (data/e168/issues/*, data/e168/out/previous_quarter_*):
    {(province code, target quarter): (P(HIGH), information cut-off)}, the latest issue before the served cut-off winning."""
    from app.e168.dashboard_export import CODES
    out: dict[tuple[str, str], tuple[float, str]] = {}
    files = list((DATA.parent / "issues").glob("*/live.json")) + list(DATA.glob("previous_quarter_*.json"))
    for f in files:
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        cut = d.get("information_cutoff") or f"{d['issue_quarter'][:4]}-{3 * int(d['issue_quarter'][-1]) - 2:02d}-01"
        if cut >= served_cutoff:
            continue
        for r in d.get("provinces", []):
            k = (CODES.get(r["province"]), r["target_quarter"])
            if r.get("lead") == 1 and k[0] and (k not in out or out[k][1] < cut):
                out[k] = (float(r["p_high"]), cut)
    return out


def previous(code: str, quarter: str) -> dict | None:
    """The forecast for the quarter before `quarter`, to show the change from last quarter: the same served issue's
    forecast for that quarter when it has one (Leads 2-3), else the Lead-1 forecast an earlier issue made for it."""
    prev_q = _shift_q(quarter, -1)
    r = row(code, prev_q)
    if r is not None:
        return {"quarter": prev_q, "probability": float(r["probability"]), "basis": "same forecast"}
    rs = list(rows().values())
    if not rs:
        return None
    hit = _earlier_issues(str(_issue(rs[0]).date()))
    if (code, prev_q) in hit:
        p, cut = hit[(code, prev_q)]
        return {"quarter": prev_q, "probability": p, "basis": f"forecast made {cut}"}
    return None


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
    from app.e168 import robust as RB
    warn = RB.warning(r)                     # E183: rows staged since E183 say when inputs were missing and filled
    if warn:
        what = f"{what} {warn}"
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


def bar_value(r: dict, group: str) -> float:
    """Signed LightGBM contribution of one trigger bar: the sum of its stored columns (BAR_COLS)."""
    return sum(_f(r.get(c)) or 0.0 for c in BAR_COLS[group])


def other_share(rs: list[dict]) -> float:
    """Share of the change attribution outside the five trigger bars: poverty, density, forecast timing, survey history."""
    oth = sum(_shap(r, c) for r in rs for c in OTHER_COLS)
    tot = sum(abs(bar_value(r, g)) for r in rs for g in GROUPS) + oth
    return 100 * oth / tot if tot else 0.0


def evidence_note(code: str | None, quarter: str, other_pct: float | None = None, group: str | None = None) -> str:
    rs = _rs(code, quarter)
    base = (f" The forecast starts from the latest published survey level (about {float(rs[0]['baseline_pct']):.0f}% for "
            f"this province)" if code and rs else " The forecast starts from each province's latest published survey level")
    if other_pct is None:
        other_pct = other_share(rs)
    other = (f" Poverty and density (which also weight the city and municipal ranking), forecast timing and survey history "
             f"account for the remaining {other_pct:.0f}%, shown as \"Other model inputs\"." if other_pct else "")
    note = ("The bars show each trigger group's share of the absolute LightGBM contributions (log-odds) to E168's "
            "forecast change in household food insecurity. News signals are counted inside their group. They are model "
            f"influence, not causes.{base}; the bars explain only the change from it.{other}")
    return f"{note} {GROUP_NOTES[group]}" if group in GROUP_NOTES and group != "news" else note


def _val(r: dict, c: str) -> float | None:
    return _f(r.get(f"val_{c}"))


# ------------------------------------------------------------------------------------------------- plain evidence
# What each trigger card says to the public: the actual figure the forecast used, the period it refers to, why it
# matters for food, and how many percentage points it moved this province's forecast. The points come from the stored
# exact LightGBM contributions (the forecast with the group's push minus the forecast without it), so the cards and the
# bars describe the same numbers. Periods follow the release rules of each series at the issue date.
_MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def _issue(r: dict) -> pd.Timestamp:
    return pd.Timestamp(str(r.get("issue_date") or ISSUE)[:10])


def _month_name(ts: pd.Timestamp) -> str:
    return f"{_MONTH[ts.month - 1]} {ts.year}"


def _latest_month(issue: pd.Timestamp, lag_days: int, source: str | None = None) -> pd.Timestamp:
    """The newest month whose figure was public on the issue date: month end + lag_days <= issue, or (live refresh) a
    month already in the public download on or before the issue date (app.e168.live_data.first_seen)."""
    m = (issue - pd.offsets.MonthBegin(1)).normalize()
    while (m + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=lag_days) > issue:
        m = m - pd.offsets.MonthBegin(1)
    if source:
        from app.e168 import live_data as LD
        seen = [pd.Timestamp(p + "-01") for p in LD._seen_cached().get(source, {})
                if len(p) == 7 and LD.usable(source, p, pd.Timestamp(p + "-01") + pd.offsets.MonthEnd(0), issue)]
        if seen and max(seen) > m:
            m = max(seen)
    return m


@functools.lru_cache(maxsize=8)
def _production_quarters(name: str, issue: str) -> tuple[str, ...]:
    """The eight quarters the forecast actually compared for farm ('agri') or fish production: the same files and release
    rule as app.e147.features (four newest published quarters vs the four before). The files may end long before the
    issue date, so the period is read from the data, never assumed."""
    from app.e137 import features as F
    from app.e147 import features as Fe
    fname, col, labs = {"agri": ("palay_corn_quarterly.csv", "Ecosystem/Croptype", ("Palay", "Corn")),
                        "fish": ("fisheries_quarterly.csv", "Subsector", ("FISHERIES",))}[name]
    try:
        cols = list(F._quarterly(fname, col, labs).columns) + list(Fe._quarterly_late(name).columns)
        src = {"agri": "palay_corn_q", "fish": "fisheries_q"}[name]
        return tuple(F._published_quarters(sorted(set(cols)), pd.Timestamp(issue), src)[-8:])
    except Exception:
        return ()


def _period_words(qs: tuple[str, ...]) -> str:
    """'2023' for a calendar year of quarters, else 'Q3 2025 to Q2 2026'."""
    if len(qs) == 4 and qs[0][:4] == qs[-1][:4] and qs[0].endswith("1") and qs[-1].endswith("4"):
        return qs[0][:4]
    return f"Q{qs[0][-1]} {qs[0][:4]} to Q{qs[-1][-1]} {qs[-1][:4]}"


def _production_period(name: str, issue: pd.Timestamp) -> tuple[str, str, bool] | None:
    """(this year's period, the year before, stale) for the production comparison the forecast used."""
    qs = _production_quarters(name, str(issue.date()))
    if len(qs) < 8:
        return None
    last = qs[-1]
    last_end = pd.Timestamp(year=int(last[:4]), month=3 * int(last[-1]), day=1) + pd.offsets.MonthEnd(0)
    return _period_words(qs[4:]), _period_words(qs[:4]), (issue - last_end).days > 365


def _production_text(name: str, issue: pd.Timestamp) -> tuple[str, str]:
    """Words for 'in <period> (...)' and 'than in <previous period>'."""
    p = _production_period(name, issue)
    if p is None:
        return "in the latest year", "the year before"
    this, prev, stale = p
    return (f"in {this}" + (" (the newest figures in the system)" if stale else "")), prev


def _pp(r: dict, group: str) -> float:
    """Percentage points of households this group moved the forecast (with its push minus without it)."""
    score = float(r["score_pct"])
    lg = math.log(score / (100 - score))
    without = 100 / (1 + math.exp(-(lg - bar_value(r, group))))
    return score - without


def _effect(r: dict, group: str) -> str:
    pp = _pp(r, group)
    if abs(pp) < 0.05:
        return f"It barely changed {r['province']}'s forecast."
    return f"This {'raised' if pp > 0 else 'lowered'} {r['province']}'s forecast by about {abs(pp):.1f} points."


def _change(x: float, more: str = "higher", less: str = "lower", unit: str = "%") -> str:
    return f"{abs(x):.1f}{unit} {more if x >= 0 else less}"


def _enso(oni: float, when: str) -> str:
    strength = "strong" if abs(oni) >= 1.5 else "moderate" if abs(oni) >= 1.0 else "weak"
    if oni >= 0.5:
        return (f"A {strength} El Niño was under way in {when} (sea temperature {oni:+.1f} °C above normal), which "
                "usually means less rain.")
    if oni <= -0.5:
        return f"A {strength} La Niña was under way in {when} (sea temperature {oni:+.1f} °C), which usually means more rain."
    return f"There was no El Niño or La Niña in {when}."


def _remit_year(issue: pd.Timestamp) -> int:
    return issue.year - 1 if issue >= pd.Timestamp(year=issue.year, month=2, day=15) else issue.year - 2


def plain_evidence(code: str | None, quarter: str, group: str) -> str | None:
    rs = _rs(code, quarter)
    if not rs:
        return None
    if code is None:
        return _region_evidence(rs, group)
    r = rs[0]
    none = "No figures had been published yet when this forecast was made. That does not mean the risk is low."
    v = lambda c: _val(r, c)
    issue = _issue(r)
    if group == "market":
        x, rice = v("cpi_food_yoy"), v("cpi_rice_yoy")
        if x is None:
            return none
        when = _month_name(_latest_month(issue, 9, "cpi"))
        rice_txt = f", and rice prices were {_change(rice)}" if rice is not None else ""
        why = ("Rising food prices make it harder for families to buy enough food." if _pp(r, group) >= 0 else
               "Taken together, food prices here were not rising fast enough to raise the risk.")
        return f"In {when}, food prices in {r['province']} were {_change(x)} than a year before{rice_txt}. {why} {_effect(r, group)}"
    if group == "climate":
        tc, oni, agri = v("c_tc_4q"), v("oni"), v("c_agri_yoy")
        parts = []
        if tc is not None:
            n = int(round(tc))
            parts.append(f"{n} typhoon{'s' if n != 1 else ''} passed near the province from "
                         f"{_month_name(issue - pd.DateOffset(years=1))} to {_month_name(issue - pd.DateOffset(months=1))}.")
        if oni is not None:
            parts.append(_enso(oni, _month_name(_latest_month(issue, 10, "oni"))))
        if agri is not None:
            when, prev = _production_text("agri", issue)
            parts.append(f"Rice and corn harvests {when} were {_change(100 * (math.exp(agri) - 1))} than in {prev}.")
        rain, soil = v("c_rain_anom_6m"), v("c_soil_anom_3m")
        word = lambda z: "wetter than usual" if z > 0.5 else ("drier than usual" if z < -0.5 else "close to normal")
        if rain is not None:
            rm = (issue - pd.Timedelta(days=30)).to_period("M") - 1
            parts.append(f"Rainfall from {_month_name((rm - 5).to_timestamp())} to {_month_name(rm.to_timestamp())} was {word(rain)}.")
        if soil is not None:
            sm = issue.to_period("M") - 3
            parts.append(f"Soil from {_month_name((sm - 2).to_timestamp())} to {_month_name(sm.to_timestamp())} was {word(soil)}.")
        parts.append("Typhoons, dry weather and poor harvests can cut food supply and income." if _pp(r, group) >= 0 else
                     "Taken together, weather and harvests were not bad enough to raise the risk here.")
        return " ".join(parts) + " " + _effect(r, group)
    if group == "fish_kill":
        f = v("c_fish_yoy")
        if f is None:
            return none
        why = ("A smaller catch means less fish to eat and less income for fishing families." if f < 0 else
               "A bigger catch means more fish to eat and more income for fishing families.")
        when, prev = _production_text("fish", issue)
        return (f"The fish catch in {r['province']} {when} was {_change(100 * (math.exp(f) - 1))} than in {prev}. "
                f"{why} {_effect(r, group)}")
    if group == "employment":
        rate, yoy = v("unemp_rate"), v("unemp_yoy")
        if rate is None:
            return none
        m = _latest_month(issue, 45, "lfs")
        yoy_txt = f", {_change(yoy, unit=' points')} than in {_MONTH[m.month - 1]} {m.year - 1}" if yoy is not None else ""
        return (f"Unemployment in the whole country was {rate:.1f}% in {_month_name(m)} (the latest figure when this "
                f"forecast was made){yoy_txt}. "
                + ("When more people are out of work, families have less money for food. " if (yoy or 0) >= 0 else
                   "With fewer people out of work, more families have income for food. ")
                + f"{_effect(r, group)} {NATIONAL}")
    if group == "ofw_remittance":
        x = v("remit_yoy")
        if x is None:
            return none
        y = _remit_year(issue)
        return (f"Money sent home by OFWs in {y} was {_change(x, 'more', 'less')} than in {y - 1} (the latest yearly "
                f"figure). This money helps many families buy food. {_effect(r, group)} {NATIONAL}")
    if group == "poverty":
        return ("How poor the province is and how crowded it is (latest government figures)."
                if v("p_poverty") is not None else none)
    return None


def _region_evidence(rs: list[dict], group: str) -> str | None:
    """The CALABARZON card: national figures once, provincial figures as a range, and the average effect."""
    r = rs[0]
    issue = _issue(r)

    def vals(c):
        return [x for x in (_val(q, c) for q in rs) if x is not None]

    def rng(xs, f=lambda x: x):
        ys = [f(x) for x in xs]
        return f"{min(ys):+.1f}% to {max(ys):+.1f}%"

    pps = [_pp(q, group) for q in rs]
    avg = sum(pps) / len(pps)
    eff = ("On average it barely changed the provinces' forecasts." if abs(avg) < 0.05 else
           f"On average it {'raised' if avg > 0 else 'lowered'} each province's forecast by about {abs(avg):.1f} points.")
    if group == "market" and vals("cpi_food_yoy"):
        rice = vals("cpi_rice_yoy")
        return (f"In {_month_name(_latest_month(issue, 9, "cpi"))}, food prices changed by {rng(vals('cpi_food_yoy'))} across "
                f"the five provinces compared with a year before" + (f" (rice: {rng(rice)})" if rice else "") + f". {eff}")
    if group == "climate":
        oni = vals("oni")
        lead = (_enso(oni[0], _month_name(_latest_month(issue, 10, "oni"))) + " ") if oni else ""
        return lead + "Typhoons, soil moisture and farm harvests also count. " + eff
    if group == "fish_kill" and vals("c_fish_yoy"):
        when, prev = _production_text("fish", issue)
        return (f"The fish catch {when} changed by {rng(vals('c_fish_yoy'), lambda x: 100 * (math.exp(x) - 1))} across "
                f"the five provinces compared with {prev}. {eff}")
    if group == "employment" and vals("unemp_rate"):
        m = _latest_month(issue, 45, "lfs")
        yoy = vals("unemp_yoy")
        return (f"Unemployment in the whole country was {vals('unemp_rate')[0]:.1f}% in {_month_name(m)}"
                + (f", {_change(yoy[0], unit=' points')} than a year before" if yoy else "") + f". {eff} {NATIONAL}")
    if group == "ofw_remittance" and vals("remit_yoy"):
        y = _remit_year(issue)
        return (f"Money sent home by OFWs in {y} was {_change(vals('remit_yoy')[0], 'more', 'less')} than in {y - 1}. "
                f"{eff} {NATIONAL}")
    return GROUP_NOTES.get(group)


def drivers(code: str, quarter: str, base: dict) -> dict:
    r = row(code, quarter)
    if r is None:
        return base
    ds = []
    for g, lab in GROUPS.items():
        c = bar_value(r, g)
        ds.append({"driver_group": g, "driver_label": lab, "group_shap": round(c, 6),
                   "direction": "increases_risk" if c > 0 else "protective" if c < 0 else "no_effect",
                   "trigger_proportion": None})
    return {**base, "drivers": ds, "article_count": (base or {}).get("article_count", 0),
            "other_pct": round(other_share([r]), 1), "other_abs": sum(_shap(r, c) for c in OTHER_COLS), "ch1": r}


def model_performance() -> dict:
    """/api/v1/config modelPerformance while E168 is served: its own evaluation, not the retired thesis system's."""
    ev = evaluation()
    return {"model": f"{MODEL_ID} (E168 LightGBM)", "target": INDICATOR["definition"], "maxReliableLead": ev["max_reliable_lead"],
            "acceptanceRule": ev["acceptance_rule"], "leads": {k: v["metrics"] for k, v in ev["leads"].items()}}


def data_used() -> dict:
    """The newest data the served forecast used, source by source, read with the same release rules as the model: the
    period of each input, where it comes from and at what level. Shown on the dashboard under 'Latest data used'."""
    rs = list(rows().values())
    if not rs:
        return {"cutoff": None, "items": []}
    issue = _issue(rs[0])
    from app.e168 import live_data as LD
    a, p = LD._live_dates()
    checked = p if a is not None and a == issue.normalize() else issue
    m = _month_name

    def prod(name):
        qs = _production_quarters(name, issue.date().isoformat())
        return f"{_period_words(qs[4:])}, compared with {_period_words(qs[:4])}" if len(qs) == 8 else "not available"
    rm = (issue - pd.Timedelta(days=30)).to_period("M") - 1
    sm = issue.to_period("M") - 3
    oni_m = _latest_month(issue, 10, "oni")
    news_from = (issue - pd.DateOffset(months=3)).normalize()
    last_day = issue - pd.Timedelta(days=1)
    def rng(a: pd.Timestamp, b: pd.Timestamp) -> str:           # 'Apr–Sep 2026' or 'Nov 2025–Oct 2026'
        return f"{a:%b}–{b:%b %Y}" if a.year == b.year else f"{a:%b %Y}–{b:%b %Y}"

    def prod_short(name):
        qs = _production_quarters(name, issue.date().isoformat())
        if len(qs) != 8:
            return "not available"
        q0, q1 = qs[4], qs[-1]
        return rng(pd.Timestamp(year=int(q0[:4]), month=3 * int(q0[-1]) - 2, day=1), pd.Timestamp(year=int(q1[:4]), month=3 * int(q1[-1]), day=1))
    short = {   # (short label, short period) for the dashboard; the long fields stay for reports
        "market": ("Food prices", f"{_latest_month(issue, 9, 'cpi'):%b %Y}"),
        "agri": ("Rice & corn harvest", prod_short("agri")),
        "rain": ("Rainfall", rng((rm - 5).to_timestamp(), rm.to_timestamp())),
        "soil": ("Soil moisture", rng((sm - 2).to_timestamp(), sm.to_timestamp())),
        "tc": ("Typhoons", rng(issue - pd.DateOffset(years=1), issue - pd.DateOffset(months=1))),
        "oni": ("El Niño", rng(oni_m - pd.DateOffset(months=2), oni_m)),
        "employment": ("Unemployment", f"{_latest_month(issue, 45, 'lfs'):%b %Y}"),
        "ofw_remittance": ("OFW remittances", str(_remit_year(issue))),
        "fish_kill": ("Fish catch", prod_short("fish")),
        "news": ("News", rng(news_from, last_day)),
        "poverty": ("Poverty & population", "2023, 2024"),
    }
    items = [
        {"group": "market", "name": "Food and rice prices (CPI)", "source": "PSA", "level": "Province",
         "period": m(_latest_month(issue, 9, "cpi")), "note": "Compared with the same month a year before"},
        {"group": "climate", "name": "Rice and corn harvest", "source": "PSA", "level": "Province", "period": prod("agri")},
        {"group": "climate", "name": "Rainfall", "source": "NASA POWER", "level": "Province",
         "period": f"{m((rm - 5).to_timestamp())} to {m(rm.to_timestamp())}", "note": "Compared with 2000-2009"},
        {"group": "climate", "name": "Soil moisture", "source": "NASA POWER", "level": "Province",
         "period": f"{m((sm - 2).to_timestamp())} to {m(sm.to_timestamp())}", "note": "Compared with 2000-2009"},
        {"group": "climate", "name": "Typhoons passing within 150 km", "source": "NOAA IBTrACS", "level": "Province",
         "period": f"{m(issue - pd.DateOffset(years=1))} to {m(issue - pd.DateOffset(months=1))}"},
        {"group": "climate", "name": "El Niño / La Niña (ONI)", "source": "NOAA", "level": "Global",
         "period": f"{m(oni_m - pd.DateOffset(months=2))} to {m(oni_m)} average"},
        {"group": "employment", "name": "Unemployment rate", "source": "PSA Labor Force Survey", "level": "National",
         "period": m(_latest_month(issue, 45, "lfs")), "note": "Compared with the same month a year before"},
        {"group": "ofw_remittance", "name": "Money sent home by OFWs", "source": "BSP (World Bank series)", "level": "National",
         "period": f"{_remit_year(issue)} full year", "note": "Compared with the year before"},
        {"group": "fish_kill", "name": "Fish catch", "source": "PSA", "level": "Province", "period": prod("fish")},
        {"group": "news", "name": "News reports", "source": "Rappler, Vera Files, Newsbytes, PCIJ and earlier archives",
         "level": "Province, area and national", "period": f"{news_from.day} {m(news_from)} to {last_day.day} {m(last_day)}"},
        {"group": "poverty", "name": "Poverty and population", "source": "PSA", "level": "Province",
         "period": "2023 poverty round; 2024 census"},
    ]
    for it, k in zip(items, ("market", "agri", "rain", "soil", "tc", "oni", "employment", "ofw_remittance", "fish_kill", "news", "poverty")):
        it["label"], it["when"] = short[k]
    return {"cutoff": issue.date().isoformat(), "data_through": last_day.date().isoformat(),
            "checked_online": checked.date().isoformat(), "items": items}


def serving_model() -> dict:
    """/api/v1/config servingModel while E168 is served."""
    return {"mode": "e168", "model": MODEL_ID, "issued": ISSUE, "targetQuarter": "2027-Q1", "lead": 1,
            "servedLeads": [1, 2, 3], "strict": os.getenv("AIPHEED_STRICT_MODEL", "") in ("1", "true", "True")}


def sentence(code: str | None, name: str, quarter: str, mean_p: float | None = None) -> str | None:
    # Plain words for the general public; the first sentence is the headline the dashboard shows.
    period = f"{_MONTHS.get(quarter[-2:], quarter)} {quarter[:4]}" if len(quarter) == 7 else quarter
    if code is None:
        rs = _rs(None, quarter)
        if not rs:
            return None
        high = sum(float(r["probability"]) >= 0.5 for r in rs)
        top = max(rs, key=lambda r: float(r["score_pct"]))
        return (f"In CALABARZON, {period}: {high} of {len(rs)} provinces at high risk. The highest is {top['province']}, where "
                f"about {float(top['score_pct']):.0f} in 100 households are expected to have moderate or severe trouble "
                f"getting enough food (high risk means 50 in 100 or more). {_plain_reliability(rs[0])}")
    r = row(code, quarter)
    if r is None:
        return None
    p = float(r["probability"])
    chance = "less than 1 in 100" if p < 0.005 else f"about {round(p * 100)} in 100"
    return (f"{name}, {period}: {'high' if p >= 0.5 else 'low'} risk. About {float(r['score_pct']):.0f} in 100 households are "
            f"expected to have moderate or severe trouble getting enough food (most likely between "
            f"{float(r['range90_low']):.0f} and {float(r['range90_high']):.0f}). High risk means 50 in 100 or more; the "
            f"chance of that is {chance}. {_plain_reliability(r)}")


_MONTHS = {"Q1": "January-March", "Q2": "April-June", "Q3": "July-September", "Q4": "October-December"}


def _plain_reliability(r: dict) -> str:
    v = evaluation()["leads"].get(str(int(r["lead"])))
    if v and v["reliable"]:
        return (f"In tests on past surveys, forecasts made this far ahead were right {v['metrics']['accuracy'] * 100:.0f}% "
                f"of the time.")
    return "Forecasts this far ahead were less reliable in past tests, so treat this as a rough guide."


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
    labels = {"cpi_food_yoy": "food prices", "unemp_rate": "unemployment", "remit_yoy": "money sent home by OFWs",
              "p_poverty": "poverty", "c_tc_4q": "typhoons"}
    missing = [lab for c, lab in labels.items() if any(_val(r, c) is None for r in rs)]
    if not missing:
        return "complete", "All the main figures had been published when this forecast was made."
    return "incomplete", ("Not yet published when this forecast was made: " + ", ".join(missing) + ". Missing figures are "
                          "left out, never counted as low risk.")


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
