"""
scripts/evaluate_governing_model.py

Reproduces the governing 45-candidate configuration (MODEL-B2) from
config/governing_model.json and checks it against the frozen evidence. It also
re-runs the 12-feature comparison under the same protocol for disclosure.
Nothing here selects, tunes or serves a model: the configuration is fixed by
the JSON file, and every comparison uses its folds, timing, seed and cut-off.

    python -m scripts.evaluate_governing_model

Writes evidence/2026-10-09_governing_45/. Exits 1 if reproduction fails.
"""

from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import binomtest
from sklearn.metrics import (f1_score, precision_score, recall_score,
                             roc_auc_score)

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
CFG = Path("config/governing_model.json")
OUT = Path("evidence/2026-10-09_governing_45")
KEYS = ["target_quarter", "province_code"]


def walk(d, cols, cfg, weighted=True, min_train=None):
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    start = min_train or cfg["walk_forward"]["outer_min_target_quarters"]
    rows = []
    for i in range(start, len(tq)):
        tr = d[d["target_quarter"].map(R.qi) < R.qi(tq[i])]
        te = d[d["target_quarter"] == tq[i]]
        params = dict(cfg["lightgbm_params"])
        if weighted:
            pos = tr["y"].mean()
            params["scale_pos_weight"] = float((1 - pos) / pos)
        m = LGBMClassifier(**params).fit(tr[cols], tr["y"])
        p = m.predict_proba(te[cols])[:, 1]
        rows.append(pd.DataFrame({"target_quarter": tq[i], "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": p,
                                  "pred": (p >= cfg["decision_threshold"]).astype(int)}))
    return pd.concat(rows, ignore_index=True)


def metrics(r):
    y, pred = r["y"].values, r["pred"].values
    fold = r.assign(c=(r["y"] == r["pred"]).astype(float)).groupby("target_quarter")["c"].mean()
    yr = r.assign(c=(r["y"] == r["pred"]).astype(float), yr=r["target_quarter"].str[:4]).groupby("yr")["c"].mean()
    return {"n": int(len(r)), "correct": int((y == pred).sum()),
            "accuracy_mean_fold": round(float(fold.mean()), 4),
            "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
            "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y, r["p"])), 4),
            "accuracy_by_year": yr.round(4).to_dict()}


def mcnemar(a, b):
    ca, cb = (a["y"] == a["pred"]).values, (b["y"] == b["pred"]).values
    x, z = int((ca & ~cb).sum()), int((~ca & cb).sum())
    return {"first_right_second_wrong": x, "second_right_first_wrong": z,
            "exact_p_two_sided": round(float(binomtest(x, x + z, 0.5).pvalue), 4) if x + z else 1.0}


def main() -> int:
    cfg = json.loads(CFG.read_text())
    fs = cfg["feature_set"]
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    # ---- feature-set integrity: the 45 candidates are exactly the fused matrix
    fused = pd.read_parquet("data/processed/features_fused.parquet")
    fused_cand = [c for c in fused.columns if c not in ("province_code", "quarter", "cpi_dev")]
    checks.append(("45 candidates == features_fused.parquet columns (excluding keys and cpi_dev)",
                   fused_cand == fs["candidates_section_3_3_2_6"] and len(fused_cand) == 45, len(fused_cand)))
    checks.append(("model inputs == 45 candidates + cpi_dev + sws_hunger (47)",
                   fs["model_inputs"] == fs["candidates_section_3_3_2_6"] + ["cpi_dev", "sws_hunger"]
                   and fs["n_model_inputs"] == 47, fs["n_model_inputs"]))
    checks.append(("no label column among inputs",
                   not any(c in fs["model_inputs"] for c in ("label_stress", "stress_score", "y")), ""))

    f, labels, cols = A.frame_t2()
    checks.append(("timing-valid frame produces the configured inputs in order", cols == fs["model_inputs"], len(cols)))
    d = R.pairs(f, labels, 1)
    frame = d[["province_code", "t", "target_quarter", "y"] + cols].sort_values(["target_quarter", "province_code"])
    frame_sha = hashlib.sha256(pd.util.hash_pandas_object(frame.round(10), index=False).values.tobytes()).hexdigest()
    checks.append(("input frame hash matches frozen MODEL-B2", frame_sha == cfg["frozen_from"]["input_frame_sha256"], frame_sha[:12]))

    # ---- reproduce
    gov = walk(d, cols, cfg)
    m_gov = metrics(gov)
    exp = cfg["expected_results"]
    saved = pd.read_csv(exp["reference_predictions"])
    mg = gov.merge(saved, on=KEYS, suffixes=("", "_saved"))
    pred_sha = hashlib.sha256(gov[KEYS + ["y", "pred"]].to_csv(index=False).encode()).hexdigest()
    checks += [
        ("test folds == configured quarters",
         sorted(gov["target_quarter"].unique()) == cfg["walk_forward"]["test_quarters"], gov["target_quarter"].nunique()),
        ("55 rows matched to frozen predictions", len(mg) == len(saved) == len(gov) == exp["n_outer_test_rows"], len(mg)),
        ("identical predictions", bool((mg["pred"] == mg["pred_saved"]).all()), ""),
        ("identical probabilities (< 1e-12)", float((mg["p"] - mg["p_saved"]).abs().max()) < 1e-12,
         f"{float((mg['p'] - mg['p_saved']).abs().max()):.1e}"),
        ("predictions hash", pred_sha == exp["predictions_sha256"], pred_sha[:12]),
        ("45/55 correct", m_gov["correct"] == exp["correct"], m_gov["correct"]),
        ("mean fold accuracy 0.8182", m_gov["accuracy_mean_fold"] == exp["accuracy_mean_fold"], m_gov["accuracy_mean_fold"]),
        ("weighted F1 0.8200", m_gov["f1_weighted"] == exp["f1_weighted"], m_gov["f1_weighted"]),
        ("ROC-AUC 0.8278", m_gov["roc_auc"] == exp["roc_auc"], m_gov["roc_auc"]),
    ]
    gov.to_csv(OUT / "governing_predictions.csv", index=False)

    # ---- disclosure comparisons, same protocol (nothing is chosen from these)
    eq5 = list(EQUATION5_FEATURES)
    cand = fs["candidates_section_3_3_2_6"]
    runs = {
        "governing_47_weighted (MODEL-B2)": gov,
        "governing_47_default (MODEL-B)": walk(d, cols, cfg, weighted=False),
        "eq5_12_weighted": walk(d, eq5, cfg),
        "eq5_12_default": walk(d, eq5, cfg, weighted=False),
        "candidates_45_only_weighted (no cpi_dev, no sws_hunger)": walk(d, cand, cfg),
        "candidates_45_plus_cpi_dev_weighted (no sws_hunger)": walk(d, cand + ["cpi_dev"], cfg),
    }
    comparison = {k: metrics(v) for k, v in runs.items()}
    paired = {"governing_47 vs eq5_12 (both weighted)": mcnemar(gov, runs["eq5_12_weighted"]),
              "governing_47 vs eq5_12 (both default)": mcnemar(runs["governing_47_default (MODEL-B)"], runs["eq5_12_default"])}

    # Provenance of the earlier "12 features = 0.618" figure: it came from the
    # frame without the strict-timing shift of government series (T1).
    f1_, lab1, _ = R.load()
    d1 = R.pairs(f1_, lab1, 1)
    r_t1 = R.walk(d1, eq5, None)
    r_t1["pred"] = (r_t1["p"] >= 0.5).astype(int)
    provenance = {"eq5_12_default_on_T1_frame": metrics(r_t1),
                  "note": "Earlier documents report 0.618 for the 12-feature set; that run used the T1 frame "
                          "(government series of quarter t). Under the governing strict timing (T2) the same "
                          "12-feature default model scores the value in comparison['eq5_12_default']."}

    passed = all(ok for _, ok, _ in checks)
    out = {"config_file": str(CFG), "config_sha256": hashlib.sha256(CFG.read_bytes()).hexdigest(),
           "checks": [{"check": n, "pass": bool(ok), "detail": str(v)} for n, ok, v in checks],
           "reproduction_pass": passed, "governing_metrics": m_gov,
           "comparison_same_protocol": comparison, "paired_tests": paired, "provenance_0618": provenance}
    (OUT / "governing_evaluation.json").write_text(json.dumps(out, indent=2, default=str))

    w = max(len(n) for n, _, _ in checks) + 2
    for n, ok, v in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:<{w}} {v}")
    print(f"{sum(ok for _, ok, _ in checks)}/{len(checks)} checks passed")
    for k, v in comparison.items():
        print(f"  {k:58s} {v['correct']}/55 acc={v['accuracy_mean_fold']} f1={v['f1_weighted']} auc={v['roc_auc']} {v['accuracy_by_year']}")
    print("  paired:", json.dumps(paired))
    print("  T1 provenance eq5 default:", provenance["eq5_12_default_on_T1_frame"]["accuracy_mean_fold"])
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
