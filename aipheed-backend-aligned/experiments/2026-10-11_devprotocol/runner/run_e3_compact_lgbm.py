"""
E3: compact, constrained LightGBM classifier on the approved Eq. 3 target (protocol ../E3_PROTOCOL.md).

DRY RUN BY DEFAULT (prints fold plan, input availability and constraint mapping; writes nothing).
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e3_compact_lgbm.py
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e3_compact_lgbm.py --execute --authorized-by "<name>"

Reuses the E1 runner's label vault, fold plan, thresholds and safety helpers.
Tests: tests/unit/test_e3_compact_lgbm.py
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

import scripts.supplementary.devprotocol_rule_l as D

_spec = importlib.util.spec_from_file_location("run_exploratory", Path(__file__).with_name("run_exploratory.py"))
E1 = sys.modules.get("run_exploratory") or importlib.util.module_from_spec(_spec)
if "run_exploratory" not in sys.modules:
    sys.modules["run_exploratory"] = E1
    _spec.loader.exec_module(E1)

EXP = Path("experiments/2026-10-11_devprotocol")
RUNS = EXP / "runs"
PROTOCOL = EXP / "E3_PROTOCOL.md"
RUNNER = Path(__file__)
E1_METRICS = RUNS / "20261011T111651Z" / "metrics.json"

SEED = 42
CUT = 0.50
INPUTS = ["last_published_stress", "sws_hunger", "sws_change", "cpi_rel", "food_cpi_yoy",
          "rice_price_regular_accel", "unemployment_rate"]
MONOTONE = [1, 1, 0, 0, 0, 0, 0]                      # aligned with INPUTS order
SENSITIVITY_EXTRA = "FSSI"
LGBM_PARAMS = {"objective": "binary", "num_leaves": 4, "min_child_samples": 5, "n_estimators": 100,
               "learning_rate": 0.05, "random_state": SEED, "verbosity": -1}
ANALYSES = ("A-origin", "A-global")
VARIANTS = {"base": (INPUTS, MONOTONE), "+FSSI": (INPUTS + [SENSITIVITY_EXTRA], MONOTONE + [0])}
TEST_QUARTERS = E1.TEST_PRIMARY
BOOTSTRAP_DRAWS = 10_000
PROTECTED_GLOBS = E1.PROTECTED_GLOBS + (
    "experiments/2026-10-11_devprotocol/runs/20261011T111651Z/*",
    "experiments/2026-10-11_devprotocol/runs/20261011T113409Z_E2/*",
    "experiments/2026-10-11_devprotocol/diagnosis_20261011T111651Z/*",
    "experiments/2026-10-11_devprotocol/runner/*.py",
)


# ---------------------------------------------------------------- inputs
def anchor_quarter(q: str) -> str | None:
    """Latest Eq. 3 label published before q's own origin (Rule L, development protocol)."""
    e = D.eligible_training_quarters(q, "development")
    return max(e) if e else None


def add_last_published_stress(rows: pd.DataFrame, vault, target: str) -> pd.DataFrame:
    """Attach last_published_stress via the vault: every anchor is < target, so access is legal."""
    rows = rows.copy()
    anchors = rows["target_quarter"].map(anchor_quarter)
    need = sorted({a for a in anchors.dropna()})
    lab = vault.training(need, target).set_index(["quarter", "province_code"])["stress_score"] if need else None
    rows["anchor_quarter"] = anchors
    rows["last_published_stress"] = [
        lab.get((a, p), np.nan) if isinstance(a, str) else np.nan
        for a, p in zip(anchors, rows["province_code"])]
    return rows


# ---------------------------------------------------------------- model
def fit_lgbm(X: pd.DataFrame, y: np.ndarray, monotone: list[int]):
    from lightgbm import LGBMClassifier
    if list(X.columns)[:len(INPUTS)] != INPUTS or len(monotone) != X.shape[1]:
        raise RuntimeError("feature order / monotone vector misaligned")
    pos = float(np.mean(y))
    return LGBMClassifier(**LGBM_PARAMS, scale_pos_weight=(1 - pos) / pos,
                          monotone_constraints=list(monotone)).fit(X, y)


def predict_fold(frame, vault, fold, analysis, cols, monotone, fitter=fit_lgbm, check_determinism=True):
    tr = E1.training_matrix(frame, vault, fold)
    te = E1.test_matrix(frame, fold.target)
    tr = add_last_published_stress(tr, vault, fold.target)
    te = add_last_published_stress(te, vault, fold.target)
    if te["last_published_stress"].isna().any():
        raise RuntimeError(f"{fold.target}: a test row lacks last_published_stress")
    tau = E1.fold_threshold(analysis, tr, vault)
    y = (tr["stress_score"] > tau).astype(int).values
    share = float(y.mean())
    out = []

    def add(model, score, pred, note=""):
        out.append(pd.DataFrame({"target_quarter": fold.target, "province_code": te["province_code"].values,
                                 "model": model, "score": score, "pred": np.asarray(pred).astype(int), "tau": tau,
                                 "n_train_quarters": len(fold.train_quarters), "train_high_share": share,
                                 "note": note}))

    if share in (0.0, 1.0):
        add("E3-LightGBM", np.full(5, np.nan), np.full(5, -1), "degenerate fold: not fitted")
    else:
        m = fitter(tr[cols], y, monotone)
        p = m.predict_proba(te[cols])[:, 1]
        if check_determinism and not np.array_equal(p, fitter(tr[cols], y, monotone).predict_proba(te[cols])[:, 1]):
            raise RuntimeError(f"{fold.target}: E3 not reproducible")
        add("E3-LightGBM", p, (p >= CUT).astype(int))

    s = te["sws_hunger"].values + 2 * te["cpi_rel"].values
    fb = int(share >= 0.5)
    add("Eq3-rule", s - tau, np.where(np.isnan(s), fb, s > tau),
        f"{int(np.isnan(s).sum())} rows used the training-majority fallback")
    cf = te["last_published_stress"].values
    add("carry-forward", cf - tau, cf > tau, f"anchor {te['anchor_quarter'].iloc[0]}")
    add("always-HIGH (reference)", np.full(5, np.nan), np.ones(5), "constant: AUC undefined")
    add("always-LOW (reference)", np.full(5, np.nan), np.zeros(5), "constant: AUC undefined")
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- metrics
def balanced_accuracy(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    if len(set(y)) < 2:
        return np.nan
    return float(np.mean([(pred[y == c] == c).mean() for c in (0, 1)]))


def metrics(r: pd.DataFrame, brier: bool) -> dict:
    from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score
    r = r[r["pred"] >= 0]
    y, pr = r["y"].values, r["pred"].values
    k, n = int((y == pr).sum()), len(r)
    pw, rw, fw, _ = precision_recall_fscore_support(y, pr, average="weighted", zero_division=0)
    score_ok = r["score"].notna().all() and r["score"].nunique() > 1 and len(set(y)) == 2
    out = {"rows": n, "correct": k, "mean_quarter_accuracy": round(E1.qacc(r), 4),
           "accuracy_clopper_pearson_95_OPTIMISTIC": E1.clopper_pearson(k, n),
           "balanced_accuracy": None if np.isnan(balanced_accuracy(y, pr)) else round(balanced_accuracy(y, pr), 4),
           "weighted_precision": round(float(pw), 4), "weighted_recall": round(float(rw), 4),
           "weighted_f1": round(float(fw), 4),
           "high_recall": round(float((pr[y == 1] == 1).mean()), 4) if (y == 1).any() else None,
           "low_recall": round(float((pr[y == 0] == 0).mean()), 4) if (y == 0).any() else None,
           "roc_auc": round(float(roc_auc_score(y, r["score"])), 4) if score_ok else None,
           "test_class_counts": {"HIGH": int(y.sum()), "LOW": int(n - y.sum())},
           "confusion_[[TN,FP],[FN,TP]]": confusion_matrix(y, pr, labels=[0, 1]).tolist(),
           "per_quarter": {q: {"correct": int((g["y"] == g["pred"]).sum()), "pred_high": int(g["pred"].sum()),
                               "actual_high": int(g["y"].sum())} for q, g in r.groupby("target_quarter")}}
    if not score_ok:
        out["roc_auc_note"] = "undefined: constant or missing score, or one class absent"
    if brier and r["score"].notna().all():
        out["brier"] = round(float(brier_score_loss(y, r["score"])), 4)
    return out


def paired_ba_bootstrap(a: pd.DataFrame, b: pd.DataFrame, draws: int = BOOTSTRAP_DRAWS) -> dict:
    m = a.merge(b, on=["target_quarter", "province_code"], suffixes=("", "_b"))
    qs = sorted(m["target_quarter"].unique())
    groups = {q: m[m["target_quarter"] == q] for q in qs}
    rng = np.random.default_rng(SEED)
    diffs, skipped = [], 0
    for _ in range(draws):
        s = pd.concat([groups[qs[i]] for i in rng.integers(0, len(qs), len(qs))])
        d = balanced_accuracy(s["y"], s["pred"]) - balanced_accuracy(s["y"], s["pred_b"])
        if np.isnan(d):
            skipped += 1
        else:
            diffs.append(d)
    point = balanced_accuracy(m["y"], m["pred"]) - balanced_accuracy(m["y"], m["pred_b"])
    lo, hi = np.percentile(diffs, [2.5, 97.5]) if diffs else (np.nan, np.nan)
    return {"point_diff": round(float(point), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "draws_used": len(diffs), "draws_skipped_one_class": skipped}


def decision(block: dict, boots: dict) -> dict:
    ba = {k: block[k]["balanced_accuracy"] for k in ("E3-LightGBM", "carry-forward", "Eq3-rule")}
    best = max(("carry-forward", "Eq3-rule"), key=lambda k: -1 if ba[k] is None else ba[k])
    gain = None if ba["E3-LightGBM"] is None or ba[best] is None else ba["E3-LightGBM"] - ba[best]
    ci = boots[best]["ci95"]
    acc_ok = block["E3-LightGBM"]["mean_quarter_accuracy"] >= block["carry-forward"]["mean_quarter_accuracy"]
    improvement = gain is not None and gain >= 0.10 and ci[0] > 0 and acc_ok
    noninferior = (not improvement) and gain is not None and gain >= -0.05
    return {"better_baseline": best, "ba_gain_vs_better_baseline": None if gain is None else round(gain, 4),
            "ci95_of_gain": ci, "accuracy_not_below_carry_forward": bool(acc_ok),
            "verdict": "improvement" if improvement else ("non-inferiority" if noninferior
                                                          else "no demonstrated improvement"),
            "interpretation": "exploratory criterion on 7 reused quarters (3 LOW rows under A-origin); "
                              "not proof of generalization; does not freeze a 2026 candidate"}


# ---------------------------------------------------------------- run
def input_availability(frame, vault) -> dict:
    out = {}
    for f in E1.fold_plan(TEST_QUARTERS):
        te = add_last_published_stress(E1.test_matrix(frame, f.target), vault, f.target)
        tr = add_last_published_stress(E1.training_matrix(frame, vault, f), vault, f.target)
        out[f.target] = {"test_nan": te[INPUTS + [SENSITIVITY_EXTRA]].isna().mean().round(2).to_dict(),
                         "train_nan": tr[INPUTS + [SENSITIVITY_EXTRA]].isna().mean().round(2).to_dict(),
                         "test_anchor": te["anchor_quarter"].iloc[0], "n_train_quarters": len(f.train_quarters)}
    return out


def execute(authorized_by: str, runs_root: Path = RUNS) -> Path:
    E1.assert_no_forbidden_modules()
    if not PROTOCOL.exists():
        raise FileNotFoundError(PROTOCOL)
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    vault = E1.LabelVault.from_project()
    if abs(vault.global_threshold() - E1.THR_GLOBAL_EXPECTED) > 1e-3:
        raise RuntimeError("global median changed")
    frame, usable = D.development_frame()
    missing = [c for c in INPUTS[1:] + [SENSITIVITY_EXTRA] if c not in usable]
    if missing:
        raise RuntimeError(f"inputs not available under the development protocol: {missing}")
    folds = E1.fold_plan(TEST_QUARTERS)
    avail = input_availability(frame, vault)

    run = E1.RunDir(runs_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E3"))
    import lightgbm, sklearn, scipy
    run.write_json("config.json", {
        "experiment": "E3 compact constrained LightGBM on the approved Eq. 3 target (exploratory; 3rd design on reused quarters)",
        "authorized_by": authorized_by, "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": PROTOCOL.as_posix(), "sha256": E1.sha256(PROTOCOL)},
        "runner_sha256": E1.sha256(RUNNER), "e1_helpers_sha256": E1.sha256(Path(E1.__file__)),
        "devprotocol_sha256": E1.sha256(Path(D.__file__)),
        "lgbm_params": LGBM_PARAMS, "class_weight": "scale_pos_weight=(1-p)/p from fold training labels",
        "variants": {k: {"inputs": v[0], "monotone_constraints": v[1]} for k, v in VARIANTS.items()},
        "cutoff": CUT, "analyses": ANALYSES, "primary": "A-origin | base",
        "test_quarters": TEST_QUARTERS,
        "eligible_training_quarters": {f.target: f.train_quarters for f in folds},
        "input_availability": avail, "tau_A_global": vault.global_threshold(),
        "versions": {"numpy": np.__version__, "pandas": pd.__version__, "lightgbm": lightgbm.__version__,
                     "sklearn": sklearn.__version__, "scipy": scipy.__version__},
        "input_provenance_sha256": {k: v for k, v in before.items()
                                    if k.startswith(("data/processed", "data/supplementary", "evidence/2026-10"))},
    })

    scored = []
    for analysis in ANALYSES:
        for vname, (cols, mono) in VARIANTS.items():
            for f in folds:
                key = f"{analysis}__{vname}__{f.target}"
                preds = predict_fold(frame, vault, f, analysis, cols, mono)
                path = run.write_csv(f"pred_{key.replace('+', 'plus')}.csv", preds)     # label-free, first
                vault.register_predictions(key, path)
                lab = vault.reveal(key, f.target)
                lab["y"] = (lab["stress_score"] > preds["tau"].iloc[0]).astype(int)
                s = preds.merge(lab[["province_code", "y"]], on="province_code")
                s["analysis"], s["variant"] = analysis, vname
                scored.append(s)
    allr = pd.concat(scored, ignore_index=True)
    run.write_csv("scored_rows.csv", allr)

    results = {}
    for (analysis, vname), g in allr.groupby(["analysis", "variant"]):
        block = {m: metrics(mg, brier=(m == "E3-LightGBM")) for m, mg in g.groupby("model")}
        e3 = g[g["model"] == "E3-LightGBM"]
        boots = {b: paired_ba_bootstrap(e3, g[g["model"] == b]) for b in ("carry-forward", "Eq3-rule")}
        for m, mg in g.groupby("model"):
            block[m]["quarter_bootstrap_accuracy_95"] = E1.quarter_bootstrap(mg[mg["pred"] >= 0])
        block["paired_balanced_accuracy_bootstrap_E3_minus"] = boots
        block["decision_rule"] = decision(block, boots)
        block["tau_by_fold"] = g.groupby("target_quarter")["tau"].first().round(4).to_dict()
        results[f"{analysis} | {vname}"] = block
    e1 = json.loads(E1_METRICS.read_text(encoding="utf-8"))["results"]
    e1_ref = {k: {m: {x: e1[k][m].get(x) for x in ("mean_quarter_accuracy", "balanced_accuracy", "roc_auc",
                                                   "high_recall", "confusion_matrix_[[TN,FP],[FN,TP]]")}
                  for m in ("MODEL-B2", "carry-forward", "Eq3-rule")}
              for k in ("A-origin | base | primary", "A-global | base | primary")}
    run.write_json("metrics.json", {
        "label": "E3 EXPLORATORY: third design on 7 reused quarters; design informed by E1/E2; not a blind or "
                 "independent validation; cannot establish the >75% requirement.",
        "primary": "A-origin | base (fold-specific threshold; pending adviser approval)",
        "secondary": "A-global | base (14.345; LEAKAGE-AFFECTED)",
        "results": results, "e1_reference_not_refitted": e1_ref})

    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    E1.assert_no_forbidden_modules()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed,
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E3 compact constrained LightGBM experiment")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not Path("app/ml").is_dir():
        ap.error("run from aipheed-backend-aligned/ with PYTHONPATH=.")
    if a.execute and not a.authorized_by.strip():
        ap.error("--execute requires --authorized-by")
    E1.assert_no_forbidden_modules()
    if not a.execute:
        frame, _ = D.development_frame()
        print(json.dumps({"inputs": INPUTS, "monotone": dict(zip(INPUTS, MONOTONE)),
                          "availability": input_availability(frame, E1.LabelVault.from_project())},
                         indent=1, default=str))
        print("DRY RUN: nothing fitted, nothing written.")
        return 0
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
