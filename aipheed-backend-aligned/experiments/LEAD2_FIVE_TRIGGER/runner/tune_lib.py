"""LEAD2_TUNING library: a wider, reproducible LightGBM search for the unified price model of P0H4-U.

- STRUCT: 72 structural configurations (depth/leaves x min_child x feature/bagging fraction x regularisation x class
  weight) at learning rate 0.05; each is fitted once to 300 rounds and read at CKPT rounds (staged prediction = early
  stopping chosen on chronological validation). The 8 P0H4-U configurations are a subset (depth 1/2, min_child 15,
  no sampling, L2 5, rounds 50/150).
- nested(): at every origin the configuration is chosen on the inner chronological folds of that origin's training
  rows only (last 4 training origins, price-label log loss), exactly as lt_lib.select does for P0H4-U.
- all_configs(): walk-forward predictions of every configuration, for the development-only global selection.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import lt_lib as T

KEY = T.KEY
CKPT = (25, 50, 100, 150, 300)
STRUCT = [dict(sid=i, depth=d, leaves=l, min_child=mc, ff=ff, bag=bg, l1=l1, l2=l2, gain=gn, cw=cw)
          for i, ((d, l), mc, (ff, bg), (l1, l2, gn), cw) in enumerate(itertools.product(
              ((1, 2), (2, 4), (3, 8)), (15, 5, 40), ((1.0, 1.0), (0.7, 0.8)), ((0.0, 5.0, 0.0), (1.0, 20.0, 0.05)),
              (None, "balanced")))]
B0_SIDS = [s["sid"] for s in STRUCT if s["depth"] <= 2 and s["min_child"] == 15 and s["ff"] == 1.0 and s["l2"] == 5.0]


def cfg_id(s: dict, k: int) -> str:
    return f"s{s['sid']}|k{k}"


def b0_order(s: dict, k: int) -> tuple:
    """Tie-break order that reproduces lt_lib.GRID for the B0 subset (depth, trees, class weight)."""
    return (s["depth"], k, s["cw"] is not None, s["sid"])


class Staged:
    def __init__(self, s: dict, cols, dirs: dict):
        self.s, self.cols, self.dirs = s, cols, dirs
        self.m = self.const = None

    def fit(self, tr):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        s = self.s
        kw = dict(subsample=s["bag"], subsample_freq=1, colsample_bytree=s["ff"]) if s["bag"] < 1 else {}
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, deterministic=True, force_row_wise=True,
                                    feature_pre_filter=False, random_state=T.SEED_UNI, n_jobs=1, verbose=-1,
                                    max_depth=s["depth"], num_leaves=s["leaves"], n_estimators=max(CKPT),
                                    min_child_samples=s["min_child"], reg_alpha=s["l1"], reg_lambda=s["l2"],
                                    min_split_gain=s["gain"], class_weight=s["cw"],
                                    monotone_constraints=[self.dirs.get(c, 0) for c in self.cols],
                                    monotone_constraints_method="basic", **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te, k: int):
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float), num_iteration=k)[:, 1]


def _folds(tr):
    origins = sorted(tr["t"].unique())[-4:]
    f = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    return [(a, b) for a, b in f if a["q"].nunique() >= 3 and a["y"].nunique() == 2 and len(b)]


def _logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def nested(S, cols, dirs, origins, sids=None, ckpts=CKPT, log=None) -> pd.DataFrame:
    grid = [s for s in STRUCT if sids is None or s["sid"] in sids]
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        folds = _folds(tr)
        if folds:
            ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
            sc = {}
            for s in grid:
                ms = [Staged(s, cols, dirs).fit(f) for f, _ in folds]
                for k in ckpts:
                    sc[(s["sid"], k)] = _logloss(ys, np.concatenate([m.predict(h, k) for m, (_, h) in zip(ms, folds)]))
            best = min(((s, k) for s in grid for k in ckpts), key=lambda o: (round(sc[(o[0]["sid"], o[1])], 9), b0_order(*o)))
        else:
            best = min(((s, k) for s in grid for k in (50, 150)), key=lambda o: b0_order(*o))
        s, k = best
        p = Staged(s, cols, dirs).fit(tr).predict(te, k)
        out.append(te[KEY].assign(pi_P=p, cfg=cfg_id(s, k)))
        if log:
            log(f"origin {t} -> {cfg_id(s, k)}")
    return pd.concat(out, ignore_index=True)


def all_configs(S, cols, dirs, origins) -> pd.DataFrame:
    """Walk-forward price probabilities of every (structure, rounds) configuration: columns s{sid}|k{k}."""
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        o = te[KEY].copy()
        for s in STRUCT:
            m = Staged(s, cols, dirs).fit(tr)
            for k in CKPT:
                o[cfg_id(s, k)] = m.predict(te, k)
        out.append(o)
    return pd.concat(out, ignore_index=True)
