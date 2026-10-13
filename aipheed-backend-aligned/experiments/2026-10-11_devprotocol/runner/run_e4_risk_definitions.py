"""
E4: comparison of HIGH/LOW risk definitions on the approved Eq. 3 stress score
(protocol ../E4_RISK_DEFINITION_PROTOCOL.md). Isolated experiment; nothing here touches production.

Definitions (all keep stress = SWS + 2 x (provincial food CPI YoY - five-province mean)):
  D-A  stress > 14.345                (approved global median; leaky on 2021-2025 test quarters)
  D-B  stress > tau_T                 (fold training median; drifts)
  D-C  stress > tau0                  (median of labels published before 2023-10-01, frozen)
  D-D  stress > max(tau0, SWS_t)      (frozen reference AND above the regional food-price mean)

DRY RUN BY DEFAULT.
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e4_risk_definitions.py
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e4_risk_definitions.py --execute --authorized-by "<name>"
Tests: tests/unit/test_e4_risk_definitions.py
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
import scripts.supplementary.window2021_study as W

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
PROTOCOL = EXP / "E4_RISK_DEFINITION_PROTOCOL.md"
RUNNER = Path(__file__)
DEFINITIONS = ("D-A", "D-B", "D-C", "D-D")
FIRST_ORIGIN_TARGET = "2023-Q4"
TEST_QUARTERS = E1.TEST_PRIMARY
MODEL = "E3-LightGBM"                       # E3 configuration, unchanged
PROTECTED_GLOBS = E3.PROTECTED_GLOBS + (
    "experiments/2026-10-11_devprotocol/runs/20261011T114801Z_E3/*",
)


# ---------------------------------------------------------------- thresholds and labels
def tau0(vault) -> float:
    """Median stress of labels published before the first evaluation origin; frozen thereafter."""
    first = E1.fold_plan([FIRST_ORIGIN_TARGET])[0]
    return float(vault.training(first.train_quarters, FIRST_ORIGIN_TARGET)["stress_score"].median())


def threshold(defn: str, train: pd.DataFrame, vault, t0: float) -> float:
    if defn == "D-A":
        return vault.global_threshold()
    if defn == "D-B":
        return float(train["stress_score"].median())
    return t0                                   # D-C and D-D


def label(defn: str, rows: pd.DataFrame, tau: float, quarter_col: str) -> np.ndarray:
    """rows must hold all five provinces of every quarter it contains (needed for D-D)."""
    s = rows["stress_score"].values
    if defn != "D-D":
        return (s > tau).astype(int)
    if not (rows.groupby(quarter_col).size() == 5).all():
        raise RuntimeError("D-D needs all five provinces of each quarter")
    qmean = rows.groupby(quarter_col)["stress_score"].transform("mean").values
    return ((s > tau) & (s > qmean)).astype(int)


# ---------------------------------------------------------------- prediction (label-free)
def predict_fold(frame, vault, fold, defn, t0, fitter=E3.fit_lgbm, check_determinism=True):
    tr = E3.add_last_published_stress(E1.training_matrix(frame, vault, fold), vault, fold.target)
    te = E3.add_last_published_stress(E1.test_matrix(frame, fold.target), vault, fold.target)
    tau = threshold(defn, tr, vault, t0)
    y = label(defn, tr, tau, "target_quarter")
    share = float(y.mean())
    out = []

    def add(model, score, pred, note=""):
        out.append(pd.DataFrame({"target_quarter": fold.target, "province_code": te["province_code"].values,
                                 "model": model, "score": score, "pred": np.asarray(pred).astype(int),
                                 "tau": tau, "definition": defn, "n_train_quarters": len(fold.train_quarters),
                                 "train_high_share": share, "note": note}))

    if share in (0.0, 1.0):
        add(MODEL, np.full(5, np.nan), np.full(5, -1), "degenerate fold: not fitted")
    else:
        m = fitter(tr[E3.INPUTS], y, E3.MONOTONE)
        p = m.predict_proba(te[E3.INPUTS])[:, 1]
        if check_determinism and not np.array_equal(
                p, fitter(tr[E3.INPUTS], y, E3.MONOTONE).predict_proba(te[E3.INPUTS])[:, 1]):
            raise RuntimeError(f"{fold.target}: not reproducible")
        add(MODEL, p, (p >= E3.CUT).astype(int))

    s = (te["sws_hunger"] + 2 * te["cpi_rel"]).values
    lps = te["last_published_stress"].values
    fb = int(share >= 0.5)
    if defn == "D-D":
        eq = np.where(np.isnan(s), fb, (s > tau) & (te["cpi_rel"].values > 0))
        add("Eq3-rule", np.full(5, np.nan), eq, "two-condition rule: AUC not computed")
        cf = (lps > tau) & (lps > lps.mean())     # anchor quarter's own regional mean
        add("carry-forward", np.full(5, np.nan), cf, "two-condition rule: AUC not computed")
    else:
        add("Eq3-rule", s - tau, np.where(np.isnan(s), fb, s > tau),
            f"{int(np.isnan(s).sum())} rows used the training-majority fallback")
        add("carry-forward", lps - tau, lps > tau)
    add("always-HIGH (reference)", np.full(5, np.nan), np.ones(5), "constant: AUC undefined")
    add("always-LOW (reference)", np.full(5, np.nan), np.zeros(5), "constant: AUC undefined")
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- metrics
def extra_metrics(g: pd.DataFrame) -> dict:
    g = g[g["pred"] >= 0]
    y, p = g["y"].values, g["pred"].values
    tp = int(((y == 1) & (p == 1)).sum())
    return {"high_precision": round(tp / int(p.sum()), 4) if p.sum() else None,
            "quarters_with_mixed_actual": int(g.groupby("target_quarter")["y"].nunique().gt(1).sum()),
            "quarters_with_mixed_predicted": int(g.groupby("target_quarter")["pred"].nunique().gt(1).sum()),
            "per_province": {pc: {"actual_high": int(x["y"].sum()), "pred_high": int(x["pred"].sum()),
                                  "correct": int((x["y"] == x["pred"]).sum())}
                             for pc, x in g.groupby("province_code")}}


def describe_labels(t0: float) -> dict:
    """Post-run descriptive label counts over all labelled rows (read after every reveal)."""
    lab = W.window_labels(E1.THR_GLOBAL_EXPECTED)
    lab = lab[lab["quarter"] <= E1.LAST_LABEL][["quarter", "province_code", "stress_score"]]
    out = {}
    for defn, tau in (("D-A", E1.THR_GLOBAL_EXPECTED), ("D-C", t0), ("D-D", t0)):
        y = label(defn, lab, tau, "quarter")
        q = pd.Series(y).groupby(lab["quarter"].values).sum()
        out[defn] = {"threshold": round(tau, 4), "all_80_rows": {"HIGH": int(y.sum()), "LOW": int(len(y) - y.sum())},
                     "high_by_quarter": {k: int(v) for k, v in q.items()},
                     "quarters_mixed": int(((q > 0) & (q < 5)).sum()), "quarters_all_high": int((q == 5).sum()),
                     "quarters_all_low": int((q == 0).sum())}
    return out


# ---------------------------------------------------------------- run
def execute(authorized_by: str, runs_root: Path = RUNS) -> Path:
    E1.assert_no_forbidden_modules()
    if not PROTOCOL.exists():
        raise FileNotFoundError(PROTOCOL)
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    vault = E1.LabelVault.from_project()
    t0 = tau0(vault)
    frame, _ = D.development_frame()
    folds = E1.fold_plan(TEST_QUARTERS)

    run = E1.RunDir(runs_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E4"))
    import lightgbm, sklearn
    run.write_json("config.json", {
        "experiment": "E4 risk-definition comparison (isolated; exploratory; 4th analysis on reused quarters)",
        "authorized_by": authorized_by, "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": PROTOCOL.as_posix(), "sha256": E1.sha256(PROTOCOL)},
        "runner_sha256": E1.sha256(RUNNER), "e3_runner_sha256": E1.sha256(Path(E3.__file__)),
        "definitions": {"D-A": "stress > 14.345 (approved global median; leaky on these quarters)",
                        "D-B": "stress > tau_T (fold training median)",
                        "D-C": f"stress > tau0 = {t0:.4f} (median of labels published before 2023-10-01; frozen)",
                        "D-D": f"stress > max(tau0, SWS_t), i.e. stress > {t0:.4f} AND deviation > 0"},
        "tau0": t0, "tau0_source_quarters": E1.fold_plan([FIRST_ORIGIN_TARGET])[0].train_quarters,
        "model": {"lgbm_params": E3.LGBM_PARAMS, "inputs": E3.INPUTS, "monotone": E3.MONOTONE,
                  "class_weight": "scale_pos_weight from fold training labels"},
        "test_quarters": TEST_QUARTERS, "eligible_training_quarters": {f.target: f.train_quarters for f in folds},
        "versions": {"numpy": np.__version__, "pandas": pd.__version__,
                     "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__},
        "input_provenance_sha256": {k: v for k, v in before.items()
                                    if k.startswith(("data/processed", "data/supplementary", "evidence/2026-10"))},
    })

    scored = []
    for defn in DEFINITIONS:
        for f in folds:
            key = f"{defn}__{f.target}"
            preds = predict_fold(frame, vault, f, defn, t0)
            path = run.write_csv(f"pred_{key}.csv", preds)            # label-free, written first
            vault.register_predictions(key, path)
            lab = vault.reveal(key, f.target)
            lab["y"] = label(defn, lab, preds["tau"].iloc[0], "quarter")
            scored.append(preds.merge(lab[["province_code", "y"]], on="province_code"))
    allr = pd.concat(scored, ignore_index=True)
    run.write_csv("scored_rows.csv", allr)

    results = {}
    for defn, g in allr.groupby("definition"):
        block = {}
        for m, mg in g.groupby("model"):
            block[m] = {**E3.metrics(mg, brier=(m == MODEL)), **extra_metrics(mg)}
            block[m]["quarter_bootstrap_accuracy_95"] = E1.quarter_bootstrap(mg[mg["pred"] >= 0])
        lg = g[g["model"] == MODEL]
        boots = {b: E3.paired_ba_bootstrap(lg, g[g["model"] == b]) for b in ("carry-forward", "Eq3-rule")}
        block["paired_balanced_accuracy_bootstrap_LightGBM_minus"] = boots
        block["decision_rule"] = E3.decision(block, boots)
        block["tau_by_fold"] = g.groupby("target_quarter")["tau"].first().round(4).to_dict()
        results[defn] = block
    run.write_json("metrics.json", {
        "label": "E4 EXPLORATORY: risk-definition comparison on 7 reused quarters (n_eff ~ 7). Definitions are "
                 "empirical, not an official DA/government classification. D-A is leakage-affected.",
        "results": results, "label_counts_all_labelled_rows": describe_labels(t0)})

    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    E1.assert_no_forbidden_modules()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed,
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E4 risk-definition comparison")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not Path("app/ml").is_dir():
        ap.error("run from aipheed-backend-aligned/ with PYTHONPATH=.")
    if a.execute and not a.authorized_by.strip():
        ap.error("--execute requires --authorized-by")
    E1.assert_no_forbidden_modules()
    if not a.execute:
        v = E1.LabelVault.from_project()
        print(json.dumps({"tau0": tau0(v), "definitions": DEFINITIONS, "test_quarters": TEST_QUARTERS}, indent=1))
        print("DRY RUN: nothing fitted, nothing written.")
        return 0
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
