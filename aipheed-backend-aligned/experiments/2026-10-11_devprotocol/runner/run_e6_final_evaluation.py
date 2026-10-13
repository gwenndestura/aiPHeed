"""
E6: one-time final evaluation of the revised pipeline (protocol ../E6_REVISED_SCORING_PROTOCOL.md).

Evaluates the SERVED artifact data/revised/revised_forecasts_retrospective.parquet (tau0 = 10.843) and an
evaluation-only artifact built here with the approved 14.345 (leakage-affected). Labels are read only after
both prediction artifacts exist and are registered.

    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e6_final_evaluation.py --execute --authorized-by "<name>"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_here = Path(__file__).parent
for _name, _file in (("run_exploratory", "run_exploratory.py"), ("run_e3_compact_lgbm", "run_e3_compact_lgbm.py")):
    if _name not in sys.modules:
        _s = importlib.util.spec_from_file_location(_name, _here / _file)
        _m = importlib.util.module_from_spec(_s)
        sys.modules[_name] = _m
        _s.loader.exec_module(_m)
E1, E3 = sys.modules["run_exploratory"], sys.modules["run_e3_compact_lgbm"]

EXP = Path("experiments/2026-10-11_devprotocol")
RUNS = EXP / "runs"
PROTOCOL = EXP / "E6_REVISED_SCORING_PROTOCOL.md"
SERVED = Path("data/revised/revised_forecasts_retrospective.parquet")
TEST = E1.TEST_PRIMARY
UNEVALUABLE = ["2025-Q2", "2025-Q3"]
FORBIDDEN = ("app.tasks", "app.api", "app.main", "app.services", "scripts.run_quarterly_pipeline",
             "uvicorn", "fastapi", "apscheduler")
PROTECTED_GLOBS = E3.PROTECTED_GLOBS + (
    "experiments/2026-10-11_devprotocol/runs/20261011T*/*", "data/revised/*",
    "experiments/2026-10-11_devprotocol/E6_REVISED_SCORING_PROTOCOL.md")


def assert_isolated():
    bad = sorted(m for m in sys.modules if m.startswith(FORBIDDEN))
    if bad:
        raise RuntimeError(f"serving/production modules loaded: {bad}")


# ---------------------------------------------------------------- predictors from an artifact (label-free)
def predictors(a: pd.DataFrame) -> pd.DataFrame:
    a = a[a["target_quarter"].isin(TEST)].copy()
    tau = a["tau"].values
    out = []

    def add(name, score, pred):
        out.append(pd.DataFrame({"target_quarter": a["target_quarter"].values, "province_code": a["province_code"].values,
                                 "model": name, "score": score, "pred": pred,
                                 "classification": np.where(pred == 1, "HIGH", "LOW")}))
    cls = a["classification"].values
    p = a["probability"].values
    out.append(pd.DataFrame({"target_quarter": a["target_quarter"].values, "province_code": a["province_code"].values,
                             "model": "Revised LightGBM", "score": p,
                             "pred": np.where(cls == "HIGH", 1, np.where(cls == "LOW", 0, -1)),
                             "classification": cls}))
    s3 = a["sws_hunger"].values + 2 * a["cpi_rel"].values
    add("Equation 3 rule", s3 - tau, (s3 > tau).astype(int))
    add("Carry-forward", a["last_published_stress"].values - tau, (a["last_published_stress"].values > tau).astype(int))
    add("Regional-only rule", a["sws_hunger"].values - tau, (a["sws_hunger"].values > tau).astype(int))
    add("Always-HIGH", np.full(len(a), np.nan), np.ones(len(a), int))
    add("Always-LOW", np.full(len(a), np.nan), np.zeros(len(a), int))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- metrics
def metrics(g: pd.DataFrame, probabilistic: bool) -> dict:
    from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
    ins = int((g["pred"] < 0).sum())
    s = g[g["pred"] >= 0]
    y, pr = s["y"].values, s["pred"].values
    tp, tn = int(((y == 1) & (pr == 1)).sum()), int(((y == 0) & (pr == 0)).sum())
    fp, fn = int(((y == 0) & (pr == 1)).sum()), int(((y == 1) & (pr == 0)).sum())
    both = len(set(y)) == 2
    hr = tp / (tp + fn) if tp + fn else None
    lr = tn / (tn + fp) if tn + fp else None
    out = {"rows_scored": len(s), "insufficient_predictions": ins, "quarters": int(s["target_quarter"].nunique()),
           "reference_HIGH": int(y.sum()), "reference_LOW": int(len(y) - y.sum()),
           "pred_HIGH": int(pr.sum()), "pred_LOW": int(len(pr) - pr.sum()),
           "accuracy": round((tp + tn) / len(s), 4) if len(s) else None,
           "balanced_accuracy": round((hr + lr) / 2, 4) if hr is not None and lr is not None else None,
           "HIGH_precision": round(tp / (tp + fp), 4) if tp + fp else None,
           "HIGH_recall": None if hr is None else round(hr, 4), "LOW_recall": None if lr is None else round(lr, 4),
           "false_HIGH": fp, "false_LOW": fn, "confusion_[[TN,FP],[FN,TP]]": [[tn, fp], [fn, tp]],
           "per_quarter": {q: {"correct": int((x["y"] == x["pred"]).sum()), "pred_HIGH": int(x["pred"].sum()),
                               "ref_HIGH": int(x["y"].sum())} for q, x in s.groupby("target_quarter")}}
    sc = s["score"].values
    if both and not np.isnan(sc).any() and np.ptp(sc) > 0:
        out["ROC_AUC"] = round(float(roc_auc_score(y, sc)), 4)
        out["PR_AUC_HIGH"] = round(float(average_precision_score(y, sc)), 4)
    else:
        out["ROC_AUC"] = out["PR_AUC_HIGH"] = None
    if probabilistic and not np.isnan(sc).any():
        out["brier"] = round(float(np.mean((sc - y) ** 2)), 4)
        out["log_loss"] = round(float(log_loss(y, np.clip(sc, 1e-6, 1 - 1e-6), labels=[0, 1])), 4)
        bins = pd.cut(sc, [0, 0.5, 0.8, 0.95, 1.0], include_lowest=True)
        out["reliability"] = {str(b): {"n": int(len(x)), "mean_p": round(float(x["p"].mean()), 3),
                                       "observed_HIGH": round(float(x["y"].mean()), 3)}
                              for b, x in pd.DataFrame({"p": sc, "y": y, "b": bins}).groupby("b", observed=True)}
    return out


def evaluate(scored: pd.DataFrame) -> dict:
    res = {m: metrics(g, probabilistic=(m == "Revised LightGBM")) for m, g in scored.groupby("model")}
    lg = scored[(scored["model"] == "Revised LightGBM") & (scored["pred"] >= 0)]
    boots = {}
    for b in ("Carry-forward", "Equation 3 rule", "Regional-only rule"):
        other = scored[scored["model"] == b]
        boots[b] = E3.paired_ba_bootstrap(lg, other)
    res["paired_BA_bootstrap_revised_minus"] = boots
    ba = {b: res[b]["balanced_accuracy"] for b in ("Carry-forward", "Equation 3 rule", "Regional-only rule")}
    defined = {k: v for k, v in ba.items() if v is not None}
    best = max(defined, key=defined.get) if defined else None
    me = res["Revised LightGBM"]["balanced_accuracy"]
    if best is None or me is None:
        verdict = "not evaluable (a class is absent)"
    else:
        gain, ci = me - defined[best], boots[best]["ci95"]
        verdict = ("improvement" if gain >= 0.10 and ci[0] > 0 else
                   "non-inferiority" if gain >= -0.05 else "no demonstrated improvement")
    res["decision"] = {"better_baseline": best, "gain": None if best is None or me is None else round(me - defined[best], 4),
                       "verdict": verdict}
    return res


def old_model_in_sample(rows: pd.DataFrame) -> pd.DataFrame:
    """Old served model (models/lgbm_best.pkl) on its own feature matrix: IN-SAMPLE, descriptive only."""
    import joblib
    b = joblib.load("models/lgbm_best.pkl")
    f = pd.read_parquet("data/processed/features_fused.parquet")
    f = f[(f["quarter"] >= "2021-Q1") & (f["quarter"] <= "2025-Q4")]
    f = f.assign(p_old=b["model"].predict_proba(f[b["feature_cols"]])[:, 1])
    return f[["province_code", "quarter", "p_old"]]


def describe(p: pd.Series) -> dict:
    p = p.dropna()
    return {"n": int(len(p)), "min": round(float(p.min()), 3), "median": round(float(p.median()), 3),
            "max": round(float(p.max()), 3), "share_ge_0.9": round(float((p >= 0.9).mean()), 3),
            "HIGH(>=0.5)": int((p >= 0.5).sum()), "LOW(<0.5)": int((p < 0.5).sum())}


def execute(authorized_by: str) -> Path:
    assert_isolated()
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    meta_path = SERVED.with_name(SERVED.stem + "_meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if E1.sha256(SERVED) != meta["sha256"]["artifact"]:
        raise RuntimeError("served artifact does not match its recorded hash")
    run = E1.RunDir(RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E6"))
    import scripts.build_revised_forecasts as B                    # builds the evaluation-only artifact
    approved_path = B.build("approved", run.path)
    arts = {"retrospective_tau0 (served)": pd.read_parquet(SERVED), "approved_14.345 (leakage-affected)": pd.read_parquet(approved_path)}
    vault = E1.LabelVault.from_project()
    for name, a in arts.items():                                   # predictions exist before labels are read
        vault.register_predictions(name, SERVED if "served" in name else approved_path)
    results, scored_all = {}, []
    for name, a in arts.items():
        pred = predictors(a)
        labs = []
        for q in TEST:
            lab = vault.reveal(name, q)
            labs.append(lab.assign(y=(lab["stress_score"] > a["tau"].iloc[0]).astype(int))[["quarter", "province_code", "y"]])
        lab = pd.concat(labs)
        s = pred.merge(lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"])
        s["reference"] = name
        scored_all.append(s)
        results[name] = evaluate(s)
        un = a[a["target_quarter"].isin(UNEVALUABLE)]
        results[name]["unevaluable_2025Q2_Q3"] = un["classification"].value_counts().to_dict()
    run.write_csv("scored_rows.csv", pd.concat(scored_all, ignore_index=True))

    # before/after on permitted data (2021-2025)
    labels_all = pd.read_parquet("data/processed/labels.parquet")
    labels_all = labels_all[(labels_all["quarter"] >= "2021-Q1") & (labels_all["quarter"] <= "2025-Q4")]
    old = old_model_in_sample(labels_all)
    served = arts["retrospective_tau0 (served)"]
    test_rows = served[served["target_quarter"].isin(TEST)][["province_code", "target_quarter", "probability"]]
    test_old = test_rows.merge(old, left_on=["province_code", "target_quarter"], right_on=["province_code", "quarter"])
    by_year = lambda df, qc, col: {y: describe(g[col]) for y, g in df.groupby(df[qc].str[:4])}
    before_after = {
        "labels_2021_2025": {
            "old_label_stress_14.6 (labels.parquet; 2020-2025 median)": int(labels_all["label_stress"].sum()),
            "S1_retrospective_tau0_10.843": int((labels_all["stress_score"] > meta["tau"]).sum()),
            "S1_approved_14.345": int((labels_all["stress_score"] > 14.345).sum()), "rows": len(labels_all)},
        "old_served_probabilities_in_sample_2021_2025": describe(old["p_old"]),
        "old_served_by_year": by_year(old, "quarter", "p_old"),
        "revised_served_probabilities_2021_2025": describe(served["probability"]),
        "revised_classifications_by_year": {y: g["classification"].value_counts().to_dict()
                                            for y, g in served.groupby(served["target_quarter"].str[:4])},
        "same_35_test_rows": {"old_in_sample": describe(test_old["p_old"]), "revised_out_of_sample": describe(test_old["probability"])},
    }
    e4 = json.loads((RUNS / "20261011T120714Z_E4" / "metrics.json").read_text(encoding="utf-8"))["results"]
    e3_ref = {k: {x: e4[k]["E3-LightGBM"].get(x) for x in ("mean_quarter_accuracy", "balanced_accuracy", "roc_auc", "brier",
                                                        "confusion_[[TN,FP],[FN,TP]]")} for k in ("D-C", "D-A")}
    run.write_json("metrics.json", {
        "label": "E6 EXPLORATORY final evaluation (6th analysis on 7 reused quarters; n_eff ~ 7). 0.50 rule fixed.",
        "served_meta": {k: meta[k] for k in ("tau", "tau_as_of", "model", "calibration_by_quarter")},
        "results": results, "before_after": before_after,
        "E3_class_weighted_reference_not_rerun": e3_ref})
    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    assert_isolated()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(), "authorized_by": authorized_by,
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed,
                                     "prediction_artifacts_sha256": {"served": E1.sha256(SERVED),
                                                                     "approved_eval_only": E1.sha256(approved_path)},
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not a.execute or not a.authorized_by.strip():
        ap.error("this one-time evaluation requires --execute --authorized-by")
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
