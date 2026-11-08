"""
v6 LightGBM candidates (docs/aipheed/v6/PREREGISTRATION.md section 2): predicted CHANGE from the latest reading,
pooled over the 4 SWS areas, one model per lead, fixed over-fitting controls from the LightGBM documentation,
early stopping on the chronologically last 25 % of training issues only, deterministic. LGBM-D-S additionally shrinks
the change toward persistence with w chosen on that inner fold. Explanations use LightGBM's native TreeSHAP.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.forecasting.v4 import models as DX
from app.forecasting.v4.features import FEATURES, GROUP

PARAMS = {"objective": "regression", "num_leaves": 4, "max_depth": 2, "min_data_in_leaf": 10, "learning_rate": 0.05,
          "lambda_l1": 1.0, "lambda_l2": 5.0, "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1,
          "max_bin": 63, "min_gain_to_split": 0.0, "deterministic": True, "force_row_wise": True, "seed": 2026,
          "verbose": -1, "num_threads": 1}
MAX_ROUNDS, STOP = 200, 20
MIN_ROWS = 30
W_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
HIST = ["last_change", "dev_mean", "h", "area_mm", "area_vis", "area_min"]
EXPLAIN_GROUP = {**GROUP, "last_change": "history", "dev_mean": "history", "h": "history",
                 "area_mm": "area", "area_vis": "area", "area_min": "area"}


@dataclass
class LgbmFit:
    model: str | None = None            # LightGBM model string (deterministic text), None = predict no change
    features: list = field(default_factory=list)
    exog: list = field(default_factory=list)
    best_iter: int = 0
    w: float = 0.0
    n_train: int = 0
    train_mae: float = float("nan")      # in-sample MAE of the change, w = 1
    train_mae_s: float = float("nan")    # in-sample MAE of the change, learned w


def design(df: pd.DataFrame) -> pd.DataFrame:
    """Add the area dummies (Balance Luzon is the reference) to a frame holding area + history + exogenous columns."""
    d = df.copy()
    d["area_mm"] = (d.area == "metro_manila").astype(float)
    d["area_vis"] = (d.area == "visayas").astype(float)
    d["area_min"] = (d.area == "mindanao").astype(float)
    return d


def fit(train: pd.DataFrame) -> LgbmFit:
    """train: rows with issue, area, change and the HIST/FEATURES columns (history already point-in-time)."""
    out = LgbmFit(n_train=len(train))
    if train.empty:
        return out
    out.exog = [f for f in FEATURES if DX.stable(train, f)[-1]]
    out.features = HIST + out.exog
    if len(train) < MIN_ROWS:
        return out
    t = design(train)
    iss = sorted(t.issue.unique())
    n_in = max(2, math.ceil(0.25 * len(iss)))
    inner = t[t.issue.isin(iss[-n_in:])]
    early = t[~t.issue.isin(iss[-n_in:])]
    if len(early) < 10 or inner.empty:
        return out
    dtr = lgb.Dataset(early[out.features].astype(float), early.change.astype(float), free_raw_data=False)
    dva = lgb.Dataset(inner[out.features].astype(float), inner.change.astype(float), reference=dtr)
    b = lgb.train(PARAMS, dtr, num_boost_round=MAX_ROUNDS, valid_sets=[dva],
                  callbacks=[lgb.early_stopping(STOP, verbose=False)])
    best = int(b.best_iteration or 0)
    if best <= 0:
        return out
    pin = b.predict(inner[out.features].astype(float), num_iteration=best)
    maes = [(float(np.mean(np.abs(w * pin - inner.change.to_numpy()))), w) for w in W_GRID]
    out.w = min(maes)[1]                                   # ties -> smaller w (tuple order)
    full = lgb.train(PARAMS, lgb.Dataset(t[out.features].astype(float), t.change.astype(float)), num_boost_round=best)
    out.model, out.best_iter = full.model_to_string(), best
    ptr = full.predict(t[out.features].astype(float))
    out.train_mae = float(np.mean(np.abs(ptr - t.change.to_numpy())))
    out.train_mae_s = float(np.mean(np.abs(out.w * ptr - t.change.to_numpy())))
    return out


def predict(f: LgbmFit, rows: pd.DataFrame) -> tuple[np.ndarray, list[dict]]:
    """Predicted change per row and its exact TreeSHAP decomposition (feature contributions + expected value)."""
    if f.model is None:
        return np.zeros(len(rows)), [{"expected_value": 0.0} for _ in range(len(rows))]
    b = lgb.Booster(model_str=f.model)
    X = design(rows)[f.features].astype(float)
    pred = b.predict(X)
    contrib = b.predict(X, pred_contrib=True)
    out = []
    for c in contrib:
        d = {"expected_value": float(c[-1])}
        for name, v in zip(f.features, c[:-1]):
            g = EXPLAIN_GROUP[name]
            d[g] = d.get(g, 0.0) + float(v)
        out.append(d)
    return pred, out
