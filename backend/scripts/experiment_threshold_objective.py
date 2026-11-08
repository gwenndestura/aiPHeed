"""
scripts/experiment_threshold_objective.py
------------------------------------------
Should the decision threshold be chosen to maximise accuracy, or recall?

BACKGROUND
----------
scripts/experiment_threshold.py already tested WHERE the threshold is chosen
(in-sample vs. out-of-sample predictions) and found in-sample wins -- that
question is settled, don't re-open it.

This tests a different question: WHAT the threshold search is optimising for.
train_food_availability_v2.pick_threshold() scans 71 cut-offs from 0.15 to
0.85 and keeps whichever maximises raw accuracy:

    return float(grid[int(np.argmax([accuracy_score(y, (p >= t).astype(int))
                                     for t in grid]))])

"no shock" is the majority class in every group (fisheries ~56% shock,
crops 24-30%), so an accuracy-maximising cut-off is pulled toward under-calling
shocks -- consistent with the measured shock recall of 0.62 (nowcast) against
precision of 0.70. For an early-warning tool, missing a real shortfall (a false
negative) plausibly costs more than a false alarm an analyst reviews and
dismisses. If so, optimising the threshold for F1 or F2 (recall-weighted)
instead of accuracy is a legitimate operational choice, not a way to inflate a
number -- the model and its ranking (AUC) do not change, only where the cut-off
sits on the ROC curve.

CANDIDATES
----------
  accuracy   current behaviour (baseline) -- maximise accuracy_score
  f1         maximise F1 (equal weight on precision and recall)
  f2         maximise F-beta, beta=2 (recall weighted twice precision)
  f0.5       maximise F-beta, beta=0.5 (precision weighted twice recall) --
             included for contrast, not because it's expected to win

Everything else is held fixed: same features, same ensemble, same in-sample
threshold-placement approach experiment_threshold.py already confirmed is the
better of the two placements tested. Only the objective the grid search
maximises changes.

FOLD DISCIPLINE
----------------
SELECT / CONFIRM exactly as in experiment_accuracy.py and experiment_threshold.py.
A candidate is only worth adopting if CONFIRM recall improves without CONFIRM
accuracy collapsing -- report the honest trade-off either way.

USAGE
-----
    python scripts/experiment_threshold_objective.py
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import fbeta_score

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.experiment_accuracy import operating, score  # noqa: E402
from scripts.train_food_availability import (  # noqa: E402
    GOV, MATCHED, NLP, SEASONAL, SERIES, load,
)
from scripts.train_food_availability_v2 import (  # noqa: E402
    MIN_TRAIN, best_params, fit_predict, target_encode,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("thr_obj")

OUT = Path("data/processed/experiment_threshold_objective.json")
VARIANT = "ens_tenc"
MATURITY_FOLDS = 4
GRID = np.linspace(0.15, 0.85, 71)

OBJECTIVES = {
    "accuracy": None,   # None = accuracy, handled specially (matches the incumbent exactly)
    "f1": 1.0,
    "f2": 2.0,
    "f0.5": 0.5,
}


def pick_threshold_objective(y: pd.Series, p: np.ndarray, beta: float | None) -> float:
    """Same 71-point grid as the incumbent pick_threshold(); different score."""
    if beta is None:
        from sklearn.metrics import accuracy_score
        vals = [accuracy_score(y, (p >= t).astype(int)) for t in GRID]
    else:
        vals = [fbeta_score(y, (p >= t).astype(int), beta=beta, zero_division=0)
                for t in GRID]
    return float(GRID[int(np.argmax(vals))])


def walk_forward(df: pd.DataFrame, cols: list[str], params: dict,
                 beta: float | None) -> pd.DataFrame:
    seen: set[str] = set()
    cols = [c for c in cols if c in df.columns and not (c in seen or seen.add(c))]
    quarters = sorted(df["quarter"].unique())
    rows = []
    for i in range(MIN_TRAIN, len(quarters)):
        tr = df[df["quarter"].isin(quarters[:i])].copy()
        te = df[df["quarter"] == quarters[i]].copy()
        if len(te) < 10 or tr["label_shock"].nunique() < 2:
            continue
        tr["commodity_te"], te["commodity_te"] = target_encode(tr, te, "commodity")
        use = cols + ["commodity_te"]

        prob = np.zeros(len(te))
        thr = np.zeros(len(te))
        for grp in te["group"].unique():
            mask = (te["group"] == grp).to_numpy()
            sub = tr[tr["group"] == grp]
            if len(sub) < 50 or sub["label_shock"].nunique() < 2:
                sub = tr
            # In-sample threshold placement -- experiment_threshold.py already
            # confirmed this beats out-of-sample holdout placement. Only the
            # objective the grid search maximises varies here.
            p_tr_g, p_te = fit_predict(sub, te[mask], use, VARIANT, params)
            prob[mask] = p_te
            thr[mask] = pick_threshold_objective(sub["label_shock"], p_tr_g, beta)

        rows.append(te.assign(prob=prob, pred=(prob >= thr).astype(int),
                              threshold=thr, fold=i))
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    df = load()
    cols = [c for c in SERIES + SEASONAL + GOV + NLP + MATCHED if c in df.columns]
    params = best_params()

    quarters = sorted(df["quarter"].unique())
    mature_q = quarters[MIN_TRAIN:][MATURITY_FOLDS:]
    split_at = mature_q[len(mature_q) // 2 - 1]
    log.info("SELECT <= %s | CONFIRM > %s", split_at, split_at)

    results = {}
    thresholds_seen = {}
    for name, beta in OBJECTIVES.items():
        log.info("running objective=%s", name)
        preds = walk_forward(df, cols, params, beta)
        results[name] = score(preds, split_at)
        op = operating(preds)
        thresholds_seen[name] = {
            g: round(float(s["threshold"].mean()), 3)
            for g, s in op.groupby("group")
        }

    print("\n" + "=" * 108)
    print("THRESHOLD OBJECTIVE — same model, same features, same in-sample placement")
    print(f"SELECT <= {split_at}   |   CONFIRM > {split_at} (never used to choose)")
    print("=" * 108)
    base = results["accuracy"]
    print(f"{'objective':14s} {'sel acc':>9s} {'con acc':>9s} {'d.acc':>8s} "
          f"{'con prec':>9s} {'con rec':>9s} {'d.rec':>8s} {'con f1':>9s} {'con AUC':>9s}")
    print("-" * 108)
    for name, r in results.items():
        c, s = r.get("confirm", {}), r.get("select", {})
        b = base.get("confirm", {})
        d_acc = c.get("accuracy", float("nan")) - b.get("accuracy", float("nan"))
        d_rec = c.get("recall_shock", float("nan")) - b.get("recall_shock", float("nan"))
        print(f"{name:14s} {s.get('accuracy', float('nan')):9.4f} "
              f"{c.get('accuracy', float('nan')):9.4f} {d_acc:+8.4f} "
              f"{c.get('precision_shock', float('nan')):9.4f} "
              f"{c.get('recall_shock', float('nan')):9.4f} {d_rec:+8.4f} "
              f"{c.get('f1_shock', float('nan')):9.4f} "
              f"{c.get('roc_auc', float('nan')):9.4f}")
    print("=" * 108)
    print("Adopt only if CONFIRM recall rises without CONFIRM accuracy collapsing.")
    print("\nmean threshold by group:")
    for name, t in thresholds_seen.items():
        print(f"  {name:14s} {t}")

    OUT.write_text(json.dumps({"split_at": split_at, "results": results,
                               "mean_thresholds": thresholds_seen}, indent=2))
    log.info("saved -> %s", OUT)


if __name__ == "__main__":
    main()
