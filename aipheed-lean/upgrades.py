"""
upgrades.py
-----------
How far the lean core can be pushed, and where pushing stops paying.

compare.py answers "which features". This answers "which machinery". Each row
adds one mechanism to the row above it and is scored on the same folds, so the
marginal value of every mechanism is visible on its own line rather than
bundled into a single headline number.

Everything here still reads one data source. None of these add a fetcher, a
corpus or a model of the outside world -- they only change how the classifier
is fit and how its probability is turned into a decision.

Every threshold and every model is fit inside the training window. A threshold
chosen on the test fold would be reading the answer, and would raise accuracy
while meaning nothing.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler

from features import LEAN_FEATURES, build_features
from panel import load_panel
from train import MIN_TRAIN_QUARTERS, PARAMS, RANDOM_SEED, report

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent


def pick_threshold(y_true: np.ndarray, prob: np.ndarray,
                   objective: str = "accuracy") -> float:
    """
    The probability cut that maximises `objective` on the rows given.

    Only ever called with training-fold rows. The grid is coarse on purpose: a
    finer one fits the training fold's noise and transfers worse.

    objective='f1' is not the same choice as 'accuracy'. Accuracy is maximised
    by predicting the majority class more often, which on a 29% positive rate
    means predicting fewer shocks and missing more of them. F1 balances the two
    error types, so it lands on a lower cut and keeps recall. For an
    early-warning indicator a missed shortfall costs more than a false alarm,
    which is the argument for optimising F1 here.
    """
    grid = np.arange(0.30, 0.71, 0.01)
    if objective == "f1":
        scores = [f1_score(y_true, (prob >= t).astype(int), zero_division=0) for t in grid]
    else:
        scores = [((prob >= t).astype(int) == y_true).mean() for t in grid]
    return float(grid[int(np.argmax(scores))])


def members(seed: int = RANDOM_SEED) -> dict:
    """
    Four learners that make different mistakes.

    The two tree ensembles and the linear model disagree on different rows than
    the boosted trees do, which is the only reason averaging them helps. The
    linear model needs its inputs scaled and cannot take NaN, so it gets a
    median-filled copy inside its own pipeline.
    """
    return {
        "lgbm": LGBMClassifier(**PARAMS),
        "rf": RandomForestClassifier(n_estimators=300, max_depth=10,
                                     min_samples_leaf=5, class_weight="balanced",
                                     random_state=seed, n_jobs=-1),
        "et": ExtraTreesClassifier(n_estimators=300, max_depth=12,
                                   min_samples_leaf=3, class_weight="balanced",
                                   random_state=seed, n_jobs=-1),
        "lr": make_pipeline(StandardScaler(),
                            LogisticRegression(max_iter=2000, class_weight="balanced",
                                               random_state=seed)),
    }


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, cols: list[str],
                 ensemble: bool) -> tuple[np.ndarray, np.ndarray]:
    """Return (train-fold probabilities, test-fold probabilities)."""
    if not ensemble:
        m = LGBMClassifier(**PARAMS).fit(train[cols], train["label_shock"])
        return m.predict_proba(train[cols])[:, 1], m.predict_proba(test[cols])[:, 1]

    tr_x = train[cols]
    te_x = test[cols]
    tr_x_f = tr_x.fillna(tr_x.median())
    te_x_f = te_x.fillna(tr_x.median())

    p_tr, p_te = [], []
    for name, m in members().items():
        a, b = (tr_x, te_x) if name in ("lgbm",) else (tr_x_f, te_x_f)
        m.fit(a, train["label_shock"])
        p_tr.append(m.predict_proba(a)[:, 1])
        p_te.append(m.predict_proba(b)[:, 1])
    return np.mean(p_tr, axis=0), np.mean(p_te, axis=0)


def run(df: pd.DataFrame, cols: list[str], *, threshold: str = "fixed",
        objective: str = "accuracy", per_group_model: bool = False,
        ensemble: bool = False) -> pd.DataFrame:
    """
    threshold: 'fixed'     -- 0.50
               'global'    -- one cut picked on the training fold
               'per_group' -- one cut per commodity group, picked on the training fold
    objective: what the picked cut maximises on that training fold
    """
    quarters = sorted(df["quarter"].unique())
    frames = []

    for i, q in enumerate(quarters):
        if i < MIN_TRAIN_QUARTERS:
            continue
        train = df[df["quarter"] < q]
        test = df[df["quarter"] == q].copy()
        if test.empty or train["label_shock"].nunique() < 2:
            continue

        test["prob"] = np.nan
        test["thr"] = 0.5

        # Fitting per group means each group gets its own model; otherwise one
        # model is fit on everything and the group is just a feature.
        splits = ([(g, train[train["group"] == g], test[test["group"] == g])
                   for g in test["group"].unique()]
                  if per_group_model else [(None, train, test)])

        for g, tr, te in splits:
            if te.empty:
                continue
            if len(tr) < 50 or tr["label_shock"].nunique() < 2:
                tr = train                      # too thin to fit alone; pool
            p_tr, p_te = _fit_predict(tr, te, cols, ensemble)
            test.loc[te.index, "prob"] = p_te

            if threshold == "global":
                test.loc[te.index, "thr"] = pick_threshold(
                    tr["label_shock"].to_numpy(), p_tr, objective)
            elif threshold == "per_group":
                for gg in te["group"].unique():
                    mask = tr["group"] == gg
                    t = (pick_threshold(tr.loc[mask, "label_shock"].to_numpy(),
                                        p_tr[mask.to_numpy()], objective)
                         if mask.sum() >= 50 else
                         pick_threshold(tr["label_shock"].to_numpy(), p_tr, objective))
                    test.loc[te.index[te["group"] == gg], "thr"] = t

        test = test[test["prob"].notna()]
        frames.append(pd.DataFrame({
            "quarter": test["quarter"].values,
            "group": test["group"].values,
            "province_name": test["province_name"].values,
            "label_shock": test["label_shock"].astype(int).values,
            "shock_lag4": test["shock_lag4"].values,
            "prob": test["prob"].values,
            "pred": (test["prob"] >= test["thr"]).astype(int).values,
            "fold": i - MIN_TRAIN_QUARTERS,
        }))

    return pd.concat(frames, ignore_index=True)


CONFIGS = [
    ("1. LEAN, threshold 0.50",        dict()),
    ("2. + threshold on train fold",   dict(threshold="global")),
    ("2b.  same, tuned for F1",        dict(threshold="global", objective="f1")),
    ("3. + per-group thresholds",      dict(threshold="per_group")),
    ("4. + per-group models",          dict(threshold="per_group", per_group_model=True)),
    ("5. + 4-model ensemble",          dict(threshold="per_group", per_group_model=True,
                                            ensemble=True)),
]


def main() -> None:
    df = build_features(load_panel())
    results: dict[str, dict] = {}

    for name, kw in CONFIGS:
        print(f"running {name} ...", flush=True)
        preds = run(df, LEAN_FEATURES, **kw)
        r = report(preds)
        r["mature"] = report(preds[preds["fold"] >= 4])

        # Abstention: answer only the most confident share, refer the rest.
        conf = (preds["prob"] - 0.5).abs()
        mature = preds[preds["fold"] >= 4].copy()
        mature["confidence"] = (mature["prob"] - 0.5).abs()
        k = int(len(mature) * 0.90)
        r["operating"] = report(mature.nlargest(k, "confidence"))
        results[name] = r

    seas = results[CONFIGS[0][0]]["baselines"]["seasonal_persistence"]
    maj = results[CONFIGS[0][0]]["baselines"]["majority"]

    print("\n" + "=" * 104)
    print("WHAT THE MACHINERY BUYS -- all rows use the same 12 features and one data source")
    print("=" * 104)
    print(f"{'configuration':32s} {'acc':>8s} {'step':>8s} {'rec':>8s} {'F1':>8s} "
          f"{'AUC':>8s} {'vs seas':>9s}")
    print("-" * 104)
    prev = None
    for name, _ in CONFIGS:
        r = results[name]
        step = "" if prev is None else f"{r['accuracy'] - prev:+8.4f}"
        print(f"{name:32s} {r['accuracy']:8.4f} {step:>8s} {r['shock']['recall']:8.4f} "
              f"{r['shock']['f1']:8.4f} {r['roc_auc']:8.4f} "
              f"{r['accuracy'] - seas:+9.4f}")
        prev = r["accuracy"]
    print("-" * 104)
    print(f"{'majority baseline':32s} {maj:8.4f}")
    print(f"{'seasonal persistence':32s} {seas:8.4f}")
    print("=" * 104)
    print("all folds, full coverage. 'vs seas' is the margin over seasonal persistence --")
    print("the number that decides whether the model is doing anything a lookup table cannot.")

    print(f"\n  mature folds (>= 4) and operating set (mature, 90% coverage)")
    print(f"  {'configuration':32s} {'mature acc':>11s} {'mature rec':>11s} "
          f"{'oper acc':>10s} {'oper rec':>10s}")
    for name, _ in CONFIGS:
        r = results[name]
        print(f"  {name:32s} {r['mature']['accuracy']:11.4f} "
              f"{r['mature']['shock']['recall']:11.4f} "
              f"{r['operating']['accuracy']:10.4f} {r['operating']['shock']['recall']:10.4f}")

    out = HERE / "outputs" / "upgrades.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
