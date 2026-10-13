"""
compare.py
----------
The controlled experiment behind this folder's claim.

One frame, one model, one set of folds. The only thing that varies between
arms is which columns the classifier is allowed to see. Every arm is scored on
exactly the same rows, so a difference between two lines is a difference
between two feature sets and nothing else.

The frame comes from the ORIGINAL pipeline's own loader
(backend/scripts/train_food_availability.py:load), not from features.py, so
the lean arm is not being handed a quietly friendlier version of the data. The
lean columns are the twelve that loader already computes; the full arm is every
column the deployed model uses.

What each arm costs to keep running is listed alongside what it scores, because
that is the trade the folder exists to measure.

Run from anywhere:
    aipheed-lean> ../backend/venv/Scripts/python.exe compare.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"

# The backend loader resolves data/... relative to the working directory.
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from scripts.train_food_availability import (  # noqa: E402
    DEEP, GOV, MATCHED, NLP, SEASONAL, SERIES, load)

sys.path.insert(0, str(HERE))
from train import report, walk_forward  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("compare")

LEAN = SERIES + SEASONAL          # the twelve in features.py, same names

# What has to keep working for an arm to produce a number next quarter.
# "sources" counts distinct external feeds; "moving parts" counts the fetchers,
# scrapers, models and join steps between the source and the feature column.
COST = {
    "seasonal only":            (1, 1,  "PSA production table"),
    "LEAN (12)":                (1, 1,  "PSA production table"),
    "LEAN + government (26)":   (9, 14, "+ CPI, rice, fuel, FX, remittance, unemployment, poverty, rainfall, ENSO/cyclone"),
    "LEAN + NLP (17)":          (3, 12, "+ news corpus, geocoder, XLM-RoBERTa relevance, FSSI, trigger classifier"),
    "LEAN + matched news (15)": (3, 10, "+ news corpus, geocoder, event-type tagging"),
    "LEAN + deep (18)":         (1, 1,  "PSA production table"),
    "FULL (38)":                (12, 40, "everything above at once"),
}

ARMS: dict[str, list[str]] = {
    "seasonal only":            SEASONAL,
    "LEAN (12)":                LEAN,
    "LEAN + government (26)":   LEAN + GOV,
    "LEAN + NLP (17)":          LEAN + NLP,
    "LEAN + matched news (15)": LEAN + MATCHED,
    "LEAN + deep (18)":         LEAN + DEEP,
    "FULL (38)":                LEAN + GOV + NLP + MATCHED + DEEP,
}


def main() -> None:
    df = load()

    missing = {k: [c for c in cols if c not in df.columns] for k, cols in ARMS.items()}
    missing = {k: v for k, v in missing.items() if v}
    if missing:
        raise SystemExit(f"columns absent from the loader's frame: {missing}")

    results: dict[str, dict] = {}
    for name, cols in ARMS.items():
        cols = list(dict.fromkeys(cols))          # de-duplicate, preserve order
        log.info("running %s (%d features)", name, len(cols))
        preds = walk_forward(df, cols)
        r = report(preds)
        r["n_features"] = len(cols)
        r["mature"] = report(preds[preds["fold"] >= 4])
        results[name] = r

    base = results["FULL (38)"]

    print("\n" + "=" * 112)
    print("FEATURE-SET HEAD TO HEAD -- identical rows, folds, model and hyperparameters")
    print("Walk-forward by quarter, 12 folds, 3,862 scored observations, threshold 0.50")
    print("=" * 112)
    hdr = (f"{'arm':26s} {'nfeat':>5s} {'acc':>8s} {'d.FULL':>8s} "
           f"{'prec':>7s} {'rec':>7s} {'F1':>7s} {'AUC':>8s} {'d.FULL':>8s} {'srcs':>5s} {'parts':>6s}")
    print(hdr)
    print("-" * 112)
    for name, r in results.items():
        srcs, parts, _ = COST[name]
        print(f"{name:26s} {r['n_features']:5d} {r['accuracy']:8.4f} "
              f"{r['accuracy'] - base['accuracy']:+8.4f} "
              f"{r['shock']['precision']:7.4f} {r['shock']['recall']:7.4f} "
              f"{r['shock']['f1']:7.4f} {r['roc_auc']:8.4f} "
              f"{r['roc_auc'] - base['roc_auc']:+8.4f} {srcs:5d} {parts:6d}")
    print("-" * 112)
    b = base["baselines"]
    print(f"{'majority baseline':26s} {'':5s} {b['majority']:8.4f}")
    print(f"{'seasonal persistence':26s} {'':5s} {b['seasonal_persistence']:8.4f}"
          f"   <- the baseline that matters on an annual production cycle")
    print("=" * 112)
    print("precision / recall / F1 are for the SHOCK class. srcs = external data feeds")
    print("required; parts = fetchers, models and join steps between source and feature.")

    print("\n  mature folds only (>= 4 folds of history)")
    print(f"  {'arm':26s} {'acc':>8s} {'rec':>8s} {'F1':>8s} {'AUC':>8s}")
    for name, r in results.items():
        m = r["mature"]
        print(f"  {name:26s} {m['accuracy']:8.4f} {m['shock']['recall']:8.4f} "
              f"{m['shock']['f1']:8.4f} {m['roc_auc']:8.4f}")

    out = HERE / "outputs" / "comparison.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {k: {kk: vv for kk, vv in v.items()} for k, v in results.items()},
        indent=2), encoding="utf-8")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
