"""FI9 Lead-1 outlook: training writes an artifact at issue time; inference is a pure function of artifact + inputs.

    python -m app.fi9.serve issue [--as-of YYYY-MM-DD]

The served forecaster is the one the locked protocol selected (data/fi9/out/lead1_evaluation.json): damped
persistence with a training-only decision threshold. Its parameters (phi, sigma, tau) are fitted on rows whose
target was published by the issue date and written to data/fi9/model/lead1_model.json with a sha256. The API and
the dashboard only read the files written here; nothing is trained on a request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.fi5 import rankings as R
from app.fi7 import models as M
from app.fi7.design import Designer
from app.fi9 import MODEL, OUT, VERSION
from app.fi9 import quarters as Q
from app.fi9.protocol import digest

SELECTED_KIND = {"Damped persistence (statistical)": "damped_tau", "Naive persistence (latest reading)": "persist"}
REQUIRED = ["hunger_last", "baseline_known", "hunger_age_q", "threshold_known", "moe_last"]
CONTEXT = {   # domain -> (feature, plain name, unit, geographic level)
    "market": [("cpi_food_yoy", "Food CPI inflation", "% y/y", "Region IV-A"), ("cpi_rice_yoy", "Rice CPI inflation", "% y/y", "Region IV-A"),
               ("world_rice_yoy", "World rice price", "% y/y", "world")],
    "climate": [("rain_anom_3m", "3-month rainfall anomaly", "SD", "CALABARZON"), ("tc_exposure_4q", "Storm passages, last 4 quarters", "count", "CALABARZON (200 km)"),
                ("oni", "ENSO index (ONI)", "deg C", "global")],
    "employment": [("unemp_rate", "Unemployment rate", "%", "national"), ("unemp_yoy", "Unemployment change", "pp y/y", "national")],
    "remittance": [("remit_yoy", "OFW remittances", "% y/y", "national")],
    "poverty": [("poverty_inc", "Poverty incidence", "% of population", "Region IV-A")],
}


def today() -> pd.Timestamp:
    """The serving clock: AIPHEED_NOW when set (tests, replays), else today's date."""
    return pd.Timestamp(os.getenv("AIPHEED_NOW") or datetime.now().date().isoformat()).normalize()


def conformal_halfwidth(tr: pd.DataFrame, min_train: int = 20) -> float:
    """95% half-width from out-of-sample level errors on the training rows (FI9-R adoption, data/fi9r/out/adoption.json).

    Each training row's level forecast uses only rows published by its own issue date; the errors come from the FI7
    inner-fold region (positions >= max(20, 60% of the training rows)); finite-sample quantile ceil((n+1)*0.95)/n.
    """
    L = tr.reset_index(drop=True)
    err = []
    for i, r in L.iterrows():
        past = L[L["target_published"] <= pd.Timestamp(r["issue_date"])]
        if len(past) < min_train:
            err.append(np.nan)
            continue
        dm = M.make("damped", []).fit(past, past["delta_target"].to_numpy(float))
        err.append(abs(float(r["hunger_target"]) - float(dm.predict_level(L.loc[[i]])[0])))
    e = np.asarray(err, float)[max(M.MIN_INNER_TRAIN, int(len(L) * 0.6)):]
    e = np.sort(e[~np.isnan(e)])
    k = min(len(e) - 1, int(np.ceil((len(e) + 1) * 0.95)) - 1)
    return float(e[k])


def train(as_of=None) -> tuple[dict, Designer, int]:
    ev = json.loads((OUT / "lead1_evaluation.json").read_text())
    sel = ev["selection"]["selected"]
    kind = SELECTED_KIND[sel]
    D = Designer("operational", as_of=pd.Timestamp(as_of) if as_of else today())     # issue date = min(scheduled, today)
    issue_qi = D.issue_qis[-1]
    d = D.dates[issue_qi]
    X = D.frame(1)
    tr = X[X["y"].notna() & (X["target_published"] <= d)]
    m = M.fit(M.make(kind, []), kind, tr)
    inner = getattr(m, "inner", m)
    params = {"phi": float(getattr(inner, "phi", 1.0)), "sigma": float(m.sigma), "tau": float(getattr(m, "tau", 0.5)),
              "conformal_halfwidth_95": conformal_halfwidth(tr)}
    body = {"model": sel, "kind": kind, "version": VERSION, "params": params, "protocol_sha256": digest(),
            "issue_quarter": Q.label(issue_qi), "issue_date": d.date().isoformat(),
            "n_training_rows": int(len(tr)), "training_targets": [tr["target_quarter"].min(), tr["target_quarter"].max()],
            "training_data_cutoff": str(pd.Timestamp(tr["target_published"].max()).date()),
            "formula": "level = normal + phi**age * (latest - normal); p_high = 1 - Phi((line - level) / sigma); class = p_high >= tau; "
                       "interval = level +/- conformal_halfwidth_95 (adopted by FI9-R: the Gaussian level +/- 1.96 sigma "
                       "covered only 89% of past outcomes)"}
    body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    (MODEL / "lead1_model.json").write_text(json.dumps(body, indent=1))
    return body, D, issue_qi


def predict(artifact: dict, row: dict) -> dict:
    """Pure inference: the same artifact and inputs always give the same output."""
    missing = [k for k in REQUIRED if row.get(k) is None or pd.isna(row.get(k))]
    if missing:
        raise ValueError(f"required inputs missing: {missing}")
    p = artifact["params"]
    age = float(row["hunger_age_q"]) if artifact["kind"] == "damped_tau" else 0.0
    phi = p["phi"] if artifact["kind"] == "damped_tau" else 1.0
    level = float(row["baseline_known"]) + phi ** age * (float(row["hunger_last"]) - float(row["baseline_known"]))
    ph = float(1 - norm.cdf((float(row["threshold_known"]) - level) / p["sigma"]))
    hw = p.get("conformal_halfwidth_95", 1.96 * p["sigma"])
    return {"p_high": ph, "class": "HIGH" if ph >= p["tau"] else "LOW", "level_pp": level,
            "level_interval95_pp": [level - hw, level + hw]}


def _reassessment() -> dict:
    """FI9-R evidence shown with the forecast (baseline comparison, interval coverage); {} if absent."""
    from app.paths import BACKEND_DIR
    p = BACKEND_DIR / "data" / "fi9r" / "out" / "reassessment.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _baselines(D: Designer, issue_qi: int, tr: pd.DataFrame, live: pd.DataFrame) -> dict:
    """Baseline and challenger forecasts registered next to the served one (prospective comparison)."""
    from app.fi9r.evaluate import local_level
    nv = M.make("persist", []).fit(tr, tr["delta_target"].to_numpy(float))
    pn = float(nv.predict_proba(live)[0])
    ll = local_level(D.q[D.q["published"] <= D.dates[issue_qi]], issue_qi + 1)
    sd = float(np.sqrt(ll["var_state"] + ll["r_next"]))
    pl = float(1 - norm.cdf((float(live["threshold_known"].iloc[0]) - ll["m"]) / sd))
    base = float(tr["y"].mean())
    return {"naive_persistence": {"p_high": round(pn, 4), "class": "HIGH" if pn >= 0.5 else "LOW",
                                  "level_pp": float(live["hunger_last"].iloc[0])},
            "climatology_always_low": {"p_high": round(base, 4), "class": "LOW"},
            "local_level_challenger": {"p_high": round(pl, 4), "level_pp": round(ll["m"], 2)}}


def _context(row: dict) -> dict:
    out = {}
    for dom, feats in CONTEXT.items():
        out[dom] = [{"indicator": n, "value": None if pd.isna(row.get(f, np.nan)) else round(float(row[f]), 2), "unit": u,
                     "geographic_level": g} for f, n, u, g in feats]
    return out


def issue(as_of=None) -> dict:
    ev = json.loads((OUT / "lead1_evaluation.json").read_text())
    sel = ev["selection"]
    art, D, issue_qi = train(as_of)
    d = D.dates[issue_qi]
    row = D.row(issue_qi, issue_qi + 1)
    sws = D.q[D.q["published"] <= d]
    vint = pd.read_csv(OUT / "data_vintage_long.csv", parse_dates=["available_from"]) if (OUT / "data_vintage_long.csv").exists() else None
    latest_pub = str(vint.loc[vint["available_from"] <= d, "available_from"].max().date()) if vint is not None else None
    meta = {"version": VERSION, "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "as_of": (pd.Timestamp(as_of) if as_of else today()).date().isoformat(),
            "current_quarter": Q.label(issue_qi), "issue_quarter": Q.label(issue_qi), "issue_date": d.date().isoformat(),
            "scheduled_issue_date": Q.scheduled_issue(issue_qi).date().isoformat(),
            "target_quarter": Q.label(issue_qi + 1), "horizon": "Lead 1 (next calendar quarter)",
            "model": art["model"], "model_version": VERSION, "artifact_sha256": art["sha256"],
            "training_data_cutoff": art["training_data_cutoff"], "protocol_sha256": art["protocol_sha256"],
            "latest_observation_quarter": row.get("last_reading_quarter"),
            "latest_observation_published": str(sws["published"].iloc[-1].date()) if len(sws) else None,
            "latest_data_publication_date": latest_pub,
            "what_is_forecast": "Whether SWS involuntary hunger in Balance Luzon (Luzon outside Metro Manila) in the target "
                                "quarter will be significantly above its five-year normal (beyond the survey margin of error).",
            "geographic_scope": "Balance Luzon (regional). CALABARZON is ~34% of its population. Not a CALABARZON, provincial "
                                "or municipal measurement or forecast.",
            "measurement_type": "forecast of a directly measured regional survey outcome (experience-based hunger), not "
                                "observed prevalence",
            "validation_status": sel["lead1_status"], "validation_checks": sel["validated_lead1_checks"],
            "probability_display": sel["probability_display"]}
    try:
        f = predict(art, row)
    except ValueError as exc:
        body = {**meta, "status": "unavailable", "reason": str(exc)}
        (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
        return body
    show_p = sel["probability_display"].startswith("calibrated")
    rt = ev["periods"]["full"]["models"][art["model"]]["reliability_table"]
    b = next(x for x in rt if float(x["bin"][:3]) <= f["p_high"] < float(x["bin"][4:]) + (x["bin"].endswith("1.0") * 0.01))
    p_note = (f"In the walk-forward test, {b['n']} past forecasts fell in the {b['bin']} range and "
              f"{round(100 * b['observed']) if b['observed'] is not None else '–'}% of them were followed by a HIGH quarter "
              f"(mean forecast {round(100 * b['mean_p']) if b['mean_p'] is not None else '–'}%). Few cases: read the probability as approximate.")
    lvl, line = float(row["hunger_last"]), float(row["threshold_known"])
    full = _reassessment().get("periods", {}).get("full", {}).get("models", {})
    c0, nv = full.get("C0 damped persistence (FI9)", {}), full.get("Naive persistence", {})
    cov = c0.get("interval_conformal") or {}
    from app.fi5.sources import sws_rounds
    rr = sws_rounds()
    last_n = rr.loc[rr["quarter"] == row.get("last_reading_quarter"), "bl_n"].dropna().tolist()
    design_note = (f"The latest reading came from a round with {int(last_n[0])} Balance Luzon respondents. Since 2023, rounds "
                   "with 300 respondents have read about 5 points lower than larger rounds, so part of the quarter-to-quarter "
                   "swing is survey design, not hunger." if len(last_n) == 1 else None)
    body = {**meta, "status": "provisional" if sel["lead1_status"] == "provisional" else "validated",
            "forecast": {"class": f["class"], "p_high": round(f["p_high"], 2) if show_p else None, "probability_note": p_note,
                         "projected_hunger_pct": round(f["level_pp"]), "projected_hunger_interval95_pct":
                         [max(0, round(f["level_interval95_pp"][0])), round(f["level_interval95_pp"][1])],
                         "interval_note": (f"Range method: errors of past out-of-sample forecasts (conformal). It contained the "
                                           f"published result in {round(100 * cov['coverage'])}% of {cov['n']} past quarters. The "
                                           "projected number is the latest reading drifting toward normal, not a model of causes."
                                           if cov else None),
                         "significance_line_pct": round(line, 1), "decision_threshold_tau": round(art["params"]["tau"], 2),
                         "class_rule": (f"HIGH is raised when the probability is at least {art['params']['tau']:.2f}, the threshold "
                                        "that best balanced missed HIGH quarters and false alarms in training (fixed in FI7)")},
            "baseline_comparison": ({"statement": (f"Over {c0['n']} past quarters this outlook was no better than simply "
                                                   f"carrying the latest reading forward (Brier score {c0['brier']:.3f} vs "
                                                   f"{nv['brier']:.3f}; lower is better). It is a structured persistence forecast, "
                                                   "not a demonstrated gain in skill."),
                                     "naive_persistence_accuracy": round(nv["accuracy"], 3), "model_accuracy": round(c0["accuracy"], 3),
                                     "always_low_accuracy": round(full["Always LOW"]["accuracy"], 3),
                                     "model_balanced_accuracy": round(c0["balanced_accuracy"], 3)} if c0 and nv else None),
            "limitations": [
                "Regional only: Balance Luzon, of which CALABARZON is about a third. Not a CALABARZON, provincial or LGU figure.",
                "Provisional: not reliable once the alternating survey quarters are set aside, and not better than persistence.",
                "Only 11 HIGH quarters since 2010; the recall estimate could plausibly be anywhere from 0 to 0.8.",
                "SWS release dates before 2021 follow a rule, not the recorded release, which affects the historical scores.",
                "The first untouched test is this forecast itself, scored when the target quarter's SWS result is published."],
            "survey_design_note": design_note,
            "latest_reading_pct": lvl, "normal_pct": round(float(row["baseline_known"]), 1),
            "inputs": {k: float(row[k]) for k in REQUIRED},
            "explanation": (f"The outlook carries forward the latest SWS reading for Balance Luzon ({lvl:.1f}%, "
                            f"{row.get('last_reading_quarter')}) and lets it drift back toward the five-year normal "
                            f"({float(row['baseline_known']):.1f}%) by the fitted factor {art['params']['phi']:.2f} per quarter. "
                            f"The significantly-above-normal line is {line:.1f}%. No other indicator changes this number: "
                            "at this issue date no domain or news input improved the forecast or beat the latest reading. "
                            "News did improve a LightGBM model's probabilities when issued on the last day of the quarter, "
                            "but that model was still not better than the latest reading (docs/fi9n)."),
            "domain_context": {"note": "Latest values known on the issue date, shown as context. They are not inputs of the "
                                       "served model, and the ablation found no measurable Lead-1 contribution from any of them.",
                               "domains": _context(row)},
            "data_coverage": {"required_inputs_present": True,
                              "context_values_missing": sum(1 for v in _context(row).values() for x in v if x["value"] is None)}}
    (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
    from app.fi9 import prospective as PR
    X = D.frame(1)
    tr = X[X["y"].notna() & (X["target_published"] <= d)]
    PR.append({"issue_date": meta["issue_date"], "issue_quarter": meta["issue_quarter"], "target_quarter": meta["target_quarter"],
               "generated_utc": meta["issued_utc"], "model": art["model"], "model_version": VERSION, "artifact_sha256": art["sha256"],
               "training_data_cutoff": art["training_data_cutoff"], "latest_input_publication": latest_pub,
               "latest_observation_quarter": meta["latest_observation_quarter"],
               "forecast": {"class": f["class"], "p_high": round(f["p_high"], 4), "level_pp": round(f["level_pp"], 2),
                            "interval95_pct": [round(f["level_interval95_pp"][0], 2), round(f["level_interval95_pp"][1], 2)]},
               "baselines": _baselines(D, issue_qi, tr, pd.DataFrame([row]))})
    status = (f"Balance Luzon next-quarter outlook ({art['model']}, {body['status']}) used only as a common regional scale "
              "factor; the order of LGUs comes from PSA poverty and density; a priority, not measured or forecast hunger")
    lg = R.rank_lgus(f["p_high"], {"forecast_target_quarter": meta["target_quarter"], "forecast_status": status})
    lg.to_csv(OUT / "lgu_priority.csv", index=False, lineterminator="\n")
    R.province_priority(lg).assign(forecast_basis=status).to_csv(OUT / "province_priority.csv", index=False, lineterminator="\n")
    return body


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["issue"])
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    b = issue(a.as_of)
    print(json.dumps({k: b.get(k) for k in ["current_quarter", "issue_date", "target_quarter", "status", "forecast", "reason"]}, indent=1))
