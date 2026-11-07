"""
E175: Lead-2 C1 analysis. Reads existing outputs only (E168, E171, E172, E173); runs no model, fits nothing, scores nothing new.

    cd backend && python ../experiments/E175_LEAD2_C1/analysis.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.e156 import leads as LD
from app.paths import BACKEND_DIR

HERE = Path(__file__).resolve().parent
D = BACKEND_DIR / "data"
pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))


def c1(correct: int, n: int = 72, major: float = 47 / 72) -> dict:
    ne = n / (1 + (LD.PER_CELL - 1) * LD.SHARED)
    acc = correct / n
    lo = acc - 1.96 * np.sqrt(acc * (1 - acc) / ne)
    return {"correct": correct, "accuracy": acc, "n_eff": ne, "low_bound": lo, "majority": major, "C1": bool(acc > major and lo > major)}


def error_analysis() -> pd.DataFrame:
    F = pd.read_csv(D / "e168" / "out" / "oof.csv")
    g = F[F["lead"] == 2].copy()
    g["pred_HIGH"] = g["L"] >= 0.5
    g["true_HIGH"] = g["y_high"] == 1
    g["correct"] = g["pred_HIGH"] == g["true_HIGH"]
    g["error_type"] = np.select([g["correct"], g["pred_HIGH"]], ["correct", "false HIGH (LOW predicted HIGH)"], "false LOW (HIGH predicted LOW)")
    g["p_high"] = g["L"].round(4)
    g["margin_from_0.5"] = (g["L"] - 0.5).abs().round(4)
    g["near_threshold_0.05"] = g["margin_from_0.5"] < 0.05
    g["forecast_score_pct"] = pct(g["mu_L"]).round(1)
    g["observed_pct"] = pct(g["y_true"]).round(1)
    g["anchor_minus_observed_logit"] = (g["mu_ANCHOR"] - g["y_true"]).round(3)
    g["model_minus_observed_logit"] = (g["mu_L"] - g["y_true"]).round(3)
    g["issue_config"] = g["tag"]
    g["training_survey_transitions"] = np.where(g["survey"] == "ENNS2021", 3, 1)
    cols = ["province", "region", "survey", "lead", "true_HIGH", "pred_HIGH", "correct", "error_type", "p_high", "margin_from_0.5",
            "near_threshold_0.05", "forecast_score_pct", "observed_pct", "anchor_minus_observed_logit", "model_minus_observed_logit",
            "issue_config", "training_survey_transitions"]
    return g[cols].sort_values(["correct", "margin_from_0.5"])


def comparison() -> pd.DataFrame:
    rows = []
    srcs = [("E168", "E168 locked (served)", D / "e172" / "out" / "results.json", "E168", "pre-registered, locked"),
            ("E171", "E171 pre-declared", D / "e171" / "out" / "results.json", "E171", "pre-declared; LightGBM/ElasticNet"),
            ("E172", "E172 pre-declared (LightGBM)", D / "e172" / "out" / "results.json", "E172", "pre-declared; failed its rule"),
            ("SIMPLE", "E172 SIMPLE diagnostic (LightGBM)", D / "e172" / "out" / "results.json", "SIMPLE", "post-hoc diagnostic; frozen in E173"),
            ("BAG", "E172 5-seed bagging (LightGBM)", D / "e172" / "out" / "results.json", "BAG", "diagnostic"),
            ("E166", "E166 (reference, not LightGBM)", D / "e172" / "out" / "results.json", "E166", "pre-registered; reference only")]
    for key, name, f, arm, status in srcs:
        r = json.loads(f.read_text())
        l = next(x for x in r["reliability"][arm]["leads"] if x["lead"] == 2)
        c = l["confusion"]
        rows.append({"model": name, "lead": 2, "correct": c["tp"] + c["tn"], "rows": l["rows"], "accuracy": l["accuracy"],
                     "low_bound": l["accuracy_95_low_effective_n"], "majority": l["majority_rule"], "false_HIGH": c["fp"], "false_LOW": c["fn"],
                     "balanced_accuracy": l["balanced_accuracy"], "f1": l["f1"], "roc_auc": l["auc"], "brier": l["brier_soft"],
                     **{k: bool(v) for k, v in l["criteria"].items()}, "evidence_status": status})
    return pd.DataFrame(rows)


def main():
    E = error_analysis()
    E.to_csv(HERE / "lead2_error_analysis.csv", index=False, lineterminator="\n")
    C = comparison()
    C.to_csv(HERE / "evaluation_comparison.csv", index=False, lineterminator="\n")
    err = E[~E["correct"]]
    by = E.groupby("survey")["correct"].agg(["sum", "count"])
    print(json.dumps({"c1_55": c1(55), "c1_56": c1(56)}, indent=1, default=float))
    print("errors:", len(err), err["error_type"].value_counts().to_dict(), "near threshold (<0.05):", int(err["near_threshold_0.05"].sum()))
    print(by.to_string())
    print("mean anchor bias by survey (logit):", E.groupby("survey")["anchor_minus_observed_logit"].mean().round(3).to_dict())
    print("mean model bias by survey (logit):", E.groupby("survey")["model_minus_observed_logit"].mean().round(3).to_dict())
    print(C[["model", "correct", "low_bound", "C1", "C2", "C3", "C4", "C5", "C6", "brier", "roc_auc", "evidence_status"]].to_string(index=False))
    print({p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in (HERE / "lead2_error_analysis.csv", HERE / "evaluation_comparison.csv")})


if __name__ == "__main__":
    main()
