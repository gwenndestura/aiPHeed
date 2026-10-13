"""
scripts/verify_lean_claim.py
-----------------------------
Independent check of the claim that a 12-feature random forest beats the
deployed 35-feature ensemble.

WHY THIS EXISTS
---------------
A separate line of work (kept outside this repository) reported that the
deployed system is beaten on recall, F1 and AUC by a single random forest over
twelve panel-derived features. If true, it changes what is worth building next:
there is little point wiring a persistence layer and a scheduler around an
ensemble that a simpler model outperforms.

That claim is checked here against the COMMITTED pipeline rather than by
re-reading the other codebase, so the result stands on this repository's own
data loader, its own folds and its own metric definitions.

WHAT IS COMPARED
----------------
Identical rows, identical walk-forward folds, identical metric code.

    ARM A  the deployed configuration
           35 features, four-member soft-voting ensemble (LightGBM, RandomForest,
           ExtraTrees, LogisticRegression), fitted per commodity group, with a
           per-group decision threshold and commodity target encoding.

    ARM B  the simplified configuration
           12 features, one RandomForest(n_estimators=400, max_depth=10,
           min_samples_leaf=5, class_weight="balanced") behind a median imputer,
           one pooled threshold, no per-group models, no target encoding.

    ARM C  the zero-parameter ranker: score each row by shock_rate_qoy alone.
           It fits nothing. Anything more elaborate has to beat it.

Reported at full coverage on all folds AND at the deployed operating condition
(mature folds, 90% coverage) so neither arm is flattered by the reporting rule.

USAGE
-----
    python scripts/verify_lean_claim.py
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.experiment_accuracy import walk_forward as deployed_walk_forward  # noqa: E402
from scripts.train_food_availability import (  # noqa: E402
    GOV, MATCHED, NLP, SEASONAL, SERIES, classification_metrics, load,
)
from scripts.train_food_availability_v2 import (  # noqa: E402
    MIN_TRAIN, best_params, pick_threshold,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("verify")

OUT = Path("data/processed/verify_lean_claim.json")
MATURITY_FOLDS = 4
COVERAGE = 0.90

# The twelve features named by the simplified methodology, all present in the
# committed load().
F12 = ["shock_lag4", "shock_rate_qoy", "quarter_num",
       "dev_lag4", "dev_qoy_mean", "dev_lag1",
       "shock_lag1", "shock_lag2", "dev_roll4",
       "series_vol", "group_code", "province_idx"]

FOREST = dict(n_estimators=400, max_depth=10, min_samples_leaf=5,
              class_weight="balanced", random_state=42, n_jobs=-1)


def forest_walk_forward(df: pd.DataFrame, cols: list[str], seed: int) -> pd.DataFrame:
    """One pooled forest, one pooled threshold, same folds as the deployed arm."""
    quarters = sorted(df["quarter"].unique())
    rows = []
    for i in range(MIN_TRAIN, len(quarters)):
        tr = df[df["quarter"].isin(quarters[:i])]
        te = df[df["quarter"] == quarters[i]]
        if len(te) < 10 or tr["label_shock"].nunique() < 2:
            continue
        m = make_pipeline(SimpleImputer(strategy="median"),
                          RandomForestClassifier(**dict(FOREST, random_state=seed)))
        m.fit(tr[cols], tr["label_shock"])
        p_tr = m.predict_proba(tr[cols])[:, 1]
        p_te = m.predict_proba(te[cols])[:, 1]
        thr = pick_threshold(tr["label_shock"], p_tr)
        rows.append(te.assign(prob=p_te, pred=(p_te >= thr).astype(int),
                              threshold=thr, fold=i))
    return pd.concat(rows, ignore_index=True)


def lookup_walk_forward(df: pd.DataFrame) -> pd.DataFrame:
    """The zero-parameter ranker: shock_rate_qoy as the score, nothing fitted."""
    quarters = sorted(df["quarter"].unique())
    rows = []
    for i in range(MIN_TRAIN, len(quarters)):
        tr = df[df["quarter"].isin(quarters[:i])]
        te = df[df["quarter"] == quarters[i]].copy()
        if len(te) < 10 or tr["label_shock"].nunique() < 2:
            continue
        p_tr = tr["shock_rate_qoy"].fillna(tr["label_shock"].mean()).to_numpy()
        p_te = te["shock_rate_qoy"].fillna(tr["label_shock"].mean()).to_numpy()
        thr = pick_threshold(tr["label_shock"], p_tr)
        rows.append(te.assign(prob=p_te, pred=(p_te >= thr).astype(int),
                              threshold=thr, fold=i))
    return pd.concat(rows, ignore_index=True)


def operating(preds: pd.DataFrame) -> pd.DataFrame:
    folds = sorted(preds["fold"].unique())
    mature = preds[preds["fold"] >= folds[MATURITY_FOLDS]]
    conf = (mature["prob"] - mature["threshold"]).abs()
    return mature[conf >= conf.quantile(1 - COVERAGE)]


def summarise(preds: pd.DataFrame, name: str) -> dict:
    out = {}
    for label, d in (("all_folds", preds), ("operating", operating(preds))):
        m = classification_metrics(d["label_shock"], d["pred"], d["prob"])
        m["n"] = len(d)
        m["majority"] = float(max(d.label_shock.mean(), 1 - d.label_shock.mean()))
        out[label] = m
    log.info("%s done", name)
    return out


def paired_quarter_bootstrap(a: pd.DataFrame, b: pd.DataFrame,
                             metric: str, n: int = 2000) -> tuple[float, float, float]:
    """
    Resample QUARTERS, not rows: every row inside a quarter shares a fold and an
    external feature vector, so a row-level bootstrap would badly overstate the
    evidence.
    """
    rng = np.random.default_rng(42)
    quarters = sorted(set(a["quarter"]) & set(b["quarter"]))
    diffs = []
    for _ in range(n):
        pick = rng.choice(quarters, size=len(quarters), replace=True)
        sa = pd.concat([a[a["quarter"] == q] for q in pick])
        sb = pd.concat([b[b["quarter"] == q] for q in pick])
        try:
            diffs.append(classification_metrics(sb.label_shock, sb.pred, sb.prob)[metric]
                         - classification_metrics(sa.label_shock, sa.pred, sa.prob)[metric])
        except Exception:
            continue
    d = np.array(diffs)
    return float(d.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> None:
    df = load()
    deployed_cols = [c for c in SERIES + SEASONAL + GOV + NLP + MATCHED if c in df.columns]
    missing = [c for c in F12 if c not in df.columns]
    if missing:
        raise SystemExit(f"F12 features absent from the committed loader: {missing}")

    log.info("ARM A: deployed, %d features, ensemble + per-group", len(deployed_cols))
    a = deployed_walk_forward(df, deployed_cols, best_params())
    log.info("ARM B: simplified, 12 features, one forest, one threshold")
    b = forest_walk_forward(df, F12, seed=42)
    log.info("ARM C: zero-parameter shock_rate_qoy lookup")
    c = lookup_walk_forward(df)

    res = {"A_deployed": summarise(a, "A"), "B_simplified": summarise(b, "B"),
           "C_lookup": summarise(c, "C")}

    print("\n" + "=" * 104)
    print("VERIFYING: does a 12-feature random forest beat the deployed 35-feature ensemble?")
    print("Identical rows, identical folds, identical metric code.")
    print("=" * 104)
    for slice_name in ("all_folds", "operating"):
        print(f"\n[{slice_name}]")
        print(f"  {'arm':34s} {'n':>5s} {'acc':>8s} {'prec':>8s} {'rec':>8s} "
              f"{'F1':>8s} {'AUC':>8s}")
        print("  " + "-" * 82)
        for key, label in (("A_deployed", "A  deployed (35 feat, ensemble)"),
                           ("B_simplified", "B  simplified (12 feat, forest)"),
                           ("C_lookup", "C  lookup (shock_rate_qoy only)")):
            m = res[key][slice_name]
            print(f"  {label:34s} {m['n']:5d} {m['accuracy']:8.4f} "
                  f"{m['precision_shock']:8.4f} {m['recall_shock']:8.4f} "
                  f"{m['f1_shock']:8.4f} {m['roc_auc']:8.4f}")
        print(f"  {'majority baseline':34s} {'':5s} "
              f"{res['A_deployed'][slice_name]['majority']:8.4f}")

    print("\n" + "-" * 104)
    print("B minus A, paired bootstrap over QUARTERS (2000 draws, 95% CI):")
    for metric in ("accuracy", "recall_shock", "f1_shock", "roc_auc"):
        mean, lo, hi = paired_quarter_bootstrap(a, b, metric)
        verdict = "B better" if lo > 0 else ("A better" if hi < 0 else "indistinguishable")
        print(f"  {metric:14s} {mean:+.4f}  CI [{lo:+.4f}, {hi:+.4f}]   {verdict}")
    print("=" * 104)

    OUT.write_text(json.dumps(res, indent=2, default=float))
    log.info("saved -> %s", OUT)


if __name__ == "__main__":
    main()
