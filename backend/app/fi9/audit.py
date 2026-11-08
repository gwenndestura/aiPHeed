"""Independent final audit of FI9: recomputes the reported metrics from the saved predictions with separate code,
and checks timing, availability, independence, selection and the served forecast.

    python -m app.fi9.audit run          # writes data/fi9/out/audit.json; exit code 1 if any check fails
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

from app.fi6.target import labels
from app.fi9 import MODEL, OUT
from app.fi9 import quarters as Q

TOL = 1e-9


def _auc(y, p):
    """Mann-Whitney AUC by explicit pair counting (independent of sklearn)."""
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return None
    return float(sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg)))


def _recompute(g: pd.DataFrame) -> dict:
    tp = fp = tn = fn = 0
    for yy, cc in zip(g["y"], g["cls"]):
        tp += yy == 1 and cc == 1
        fp += yy == 0 and cc == 1
        tn += yy == 0 and cc == 0
        fn += yy == 1 and cc == 0
    n = tp + fp + tn + fn
    return {"accuracy": (tp + tn) / n, "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "brier": sum((p - y) ** 2 for p, y in zip(g["p"], g["y"])) / n,
            "roc_auc": _auc(g["y"].to_numpy(), g["p"].to_numpy())}


def run() -> dict:
    from app.fi9.evaluate import CONFIGS, summarize
    from app.fi9.protocol import PROTOCOL, check
    from app.fi9.serve import predict

    pr = pd.read_csv(OUT / "lead1_predictions.csv")
    ev = json.loads((OUT / "lead1_evaluation.json").read_text())
    res: dict = {"checks": {}, "details": {}}
    C = res["checks"]
    C["protocol_lock_matches"] = check() == ev["protocol_sha256"]

    # 1. metrics recomputed independently, every configuration and period
    yr = pr["target_quarter"].str[:4].astype(int)
    (d0, d1), (t0, t1) = PROTOCOL["split"]["development_target_years"], PROTOCOL["split"]["test_target_years"]
    subsets = {"full": pr, "development": pr[yr.between(d0, d1)], "test": pr[yr.between(t0, t1)]}
    worst = 0.0
    for per, g in subsets.items():
        for tag in CONFIGS:
            mine = _recompute(g[g["tag"] == tag])
            rep = ev["periods"][per]["models"][tag]
            for k, v in mine.items():
                if v is not None and rep[k] is not None:
                    worst = max(worst, abs(v - rep[k]))
                elif (v is None) != (rep[k] is None):
                    worst = np.inf
    C["metrics_recomputed_match"] = bool(worst < 1e-6)
    res["details"]["max_metric_difference"] = worst

    # 2. timing and availability of every walk-forward forecast
    C["every_target_is_next_quarter"] = bool((pr["target_quarter"].map(Q.index) == pr["issue_quarter"].map(Q.index) + 1).all())
    C["issue_date_inside_issue_quarter"] = bool(all(Q.qi_of(d) == Q.index(q) for d, q in zip(pr["issue_date"], pr["issue_quarter"])))
    C["training_targets_published_by_issue"] = bool((pd.to_datetime(pr["train_max_target_published"]) <= pd.to_datetime(pr["issue_date"])).all())
    C["target_published_after_issue"] = bool((pd.to_datetime(pr["target_published"]) > pd.to_datetime(pr["issue_date"])).all())

    # 3. predictors: published by the issue date (dataset values equal the latest vintage value available then)
    X = pd.read_csv(OUT / "forecast_time_dataset_h1.csv")
    V = pd.read_csv(OUT / "data_vintage_long.csv", parse_dates=["available_from", "period_end"])
    mism = {}
    for feat, (src, ind) in {"cpi_food_yoy": ("cpi", "yoy_food"), "unemp_rate": ("lfs", "unemp_rate"), "remit_yoy": ("remit", "remit_yoy"),
                             "poverty_inc": ("poverty", "poverty_inc"), "oni": ("oni", "oni"), "hunger_last": ("sws", "hunger")}.items():
        v = V[(V["source_key"] == src) & (V["indicator"] == ind)].sort_values(["available_from", "period_end"])
        bad = 0
        for d, val in zip(pd.to_datetime(X["issue_date"]), X[feat]):
            known = v[v["available_from"] <= d]
            if not len(known):
                bad += not pd.isna(val)
                continue
            exp = known.sort_values("period_end")["value"].iloc[-1]
            bad += not (pd.isna(val) or abs(float(val) - float(exp)) < 1e-6)
        mism[feat] = bad
    C["predictors_equal_vintage_values_known_at_issue"] = bool(sum(mism.values()) == 0)
    res["details"]["vintage_mismatches"] = mism

    # 4. independence: one SWS label per target quarter, no duplicates, no survey/province record used as a label
    lab = labels().set_index("quarter")
    C["no_duplicate_forecasts"] = bool(not pr.duplicated(["tag", "target_quarter"]).any())
    C["same_target_quarters_for_every_configuration"] = bool(pr.groupby("tag")["target_quarter"].apply(frozenset).nunique() == 1)
    C["labels_are_sws_balance_luzon_only"] = bool((pr["y"] == pr["target_quarter"].map(lab["y"])).all())
    res["details"]["independent_outcome_quarters_evaluated"] = int(pr["target_quarter"].nunique())
    res["details"]["sws_quarters_with_label"] = int(lab["y"].notna().sum())

    # 5. test observations cannot affect selection: scramble test outcomes, selection must not change
    rng = np.random.default_rng(0)
    scr = pr.copy()
    m = scr["target_quarter"].str[:4].astype(int).between(t0, t1)
    for tag in scr["tag"].unique():
        idx = scr.index[m & (scr["tag"] == tag)]
        scr.loc[idx, "y"] = rng.permutation(scr.loc[idx, "y"].to_numpy())
    C["selection_independent_of_test_outcomes"] = summarize(scr)["selection"]["selected"] == ev["selection"]["selected"]

    # 6. served forecast: artifact integrity, reproducible inference, dates
    art = json.loads((MODEL / "lead1_model.json").read_text())
    body = {k: v for k, v in art.items() if k != "sha256"}
    C["artifact_sha256_valid"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == art["sha256"]
    f = json.loads((OUT / "forecast.json").read_text())
    C["served_model_is_selected_model"] = art["model"] == ev["selection"]["selected"] == f["model"]
    C["served_artifact_matches"] = f["artifact_sha256"] == art["sha256"]
    if f.get("status") != "unavailable":
        again = predict(art, f["inputs"])
        C["served_forecast_reproduces"] = again["class"] == f["forecast"]["class"] and round(again["level_pp"]) == f["forecast"]["projected_hunger_pct"]
        C["served_probability_bounded"] = f["forecast"]["p_high"] is None or 0 <= f["forecast"]["p_high"] <= 1
    C["served_target_is_next_quarter"] = Q.index(f["target_quarter"]) == Q.index(f["issue_quarter"]) + 1
    C["served_training_cutoff_before_issue"] = pd.Timestamp(art["training_data_cutoff"]) <= pd.Timestamp(f["issue_date"])
    res["details"]["served"] = {k: f.get(k) for k in ["issue_date", "target_quarter", "status", "forecast"]}
    res["all_passed"] = bool(all(C.values()))
    (OUT / "audit.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__" and sys.argv[1:] == ["run"]:
    r = run()
    print(json.dumps(r["checks"], indent=1), "\nALL PASSED" if r["all_passed"] else "\nFAILED")
    sys.exit(0 if r["all_passed"] else 1)
