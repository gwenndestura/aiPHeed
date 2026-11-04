"""
Post-hoc checks on the locked E144 results (labelled post hoc: they change no E144 decision).

    python -m app.e145.posthoc_e144 -> data/e145/out/posthoc_e144.json

1. Naive class persistence and always-HIGH on E144's exact Stage A rows. E144's B1 is the training HIGH rate given the
   last class, not the naive last-class forecast the mission asks for.
2. Is the link coefficient gamma robust to the number of independent time points? It is identified from area x round
   cells, and E144's bootstrap resamples provinces within rounds, so it treats rounds and area-round shocks as fixed.
   Here: leave-one-round-out gamma, leave-one-area-out gamma, and a bootstrap of the area x round cells.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e144 import OUT as O144
from app.e144 import link as L
from app.e145 import OUT


def _acc(y, p):
    p = np.asarray(p, float)
    return float(np.mean((p >= 0.5).astype(int) == np.asarray(y).astype(int)))


def stage_a():
    W = pd.read_csv(O144 / "stage_a_oof.csv")
    out = {}
    for win, first in (("primary", "2022-Q1"), ("secondary", "2014-Q1")):
        from app.fi5.target import qindex
        Wv = W[W["issue_qi"] >= qindex(first)]
        for h, g in Wv.groupby("h"):
            last_high = (g["hunger_last_anom"] > 0).astype(float)
            lh = g.dropna(subset=["hunger_last_anom"])
            out[f"{win}|h{h}"] = {"n": int(len(g)), "base_rate_high": float(g["y"].mean()),
                                  "naive_last_class_accuracy": _acc(lh["y"], (lh["hunger_last_anom"] > 0).astype(float)),
                                  "always_high_accuracy": float(g["y"].mean()),
                                  "model_accuracy": _acc(g["y"], g["A LightGBM (full)"]),
                                  "naive_last_class_brier": float(np.mean((last_high - g["y"]) ** 2))}
    return out


def _gamma(X: pd.DataFrame) -> float:
    return float(L.fit(X, True)["beta"][2])


def link():
    X = L.rows()
    out = {"full_gamma": _gamma(X), "n_rows": int(len(X)), "n_cells": int(X.groupby(["survey", "sws_area"]).ngroups),
           "n_distinct_hunger_values": int(X["H"].round(6).nunique()), "leave_round_out": {}, "leave_area_out": {}}
    for s in X["survey"].unique():
        out["leave_round_out"][s] = _gamma(X[X["survey"] != s])
    for a in X["sws_area"].unique():
        out["leave_area_out"][a] = _gamma(X[X["sws_area"] != a])
    rng = np.random.default_rng(145)
    cells = [g for _, g in X.groupby(["survey", "sws_area"])]
    draws = []
    for _ in range(2000):
        s = pd.concat([cells[i] for i in rng.integers(0, len(cells), len(cells))])
        if s["H"].round(6).nunique() > 2:
            draws.append(_gamma(s))
    out["cell_bootstrap_ci95"] = [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]
    return out


if __name__ == "__main__":
    res = {"stage_a_naive": stage_a(), "link_robustness": link()}
    (OUT / "posthoc_e144.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))
