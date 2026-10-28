"""LEAD2_FIVE_TRIGGER library: the served unified LightGBM price part (UNI-FINAL U2 recipe = P0), refitted at every
origin from the FORECAST_RESEARCH snapshot, with optional extra columns and column removals for the five trigger
groups. Reuses FORECAST_RESEARCH fr_lib (stack, pi_H, schedules, R1-R7) and metrics."""
from __future__ import annotations

import functools
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LT = HERE.parent
EXP = LT.parent
sys.path.insert(0, str(EXP / "FORECAST_RESEARCH" / "runner"))
import fr_lib as F  # noqa: E402
import metrics as M  # noqa: E402

OUT, DATA = LT / "out", LT / "data"
KEY = ["t", "lead", "province_code"]
SEED_UNI = 2027
WORLD = ["W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy", "W_urea_yoy"]
E107_COLS = ["A1_food", "A1_gap", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"]
U2 = E107_COLS + ["A_mom", "G_pri_yoy", "NG_gap_price", "lead"] + WORLD          # = uni_lib.cols("U2")
MONO_UP = ["A1_food", "A1_gap", "A_mom"]
GRID = [dict(id=i, depth=d, leaves=2 ** d, trees=n, cw=w)
        for i, (d, n, w) in enumerate(itertools.product((1, 2), (50, 150), (None, "balanced")))]
MIN_Q, MIN_HIGH, MIN_LOW = 6, 5, 5
# the user's five trigger groups (2026-10-28); H1 (regional SWS hunger outlook) is the hunger condition of the
# Chapter I target, kept in the model but not a trigger; `lead` is the horizon
GROUPS = {"market": ["A1_food", "A1_gap", "A_mom", "A2", "A3", "W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy"],
          "climate": ["C1", "C2", "C3", "C4", "W_urea_yoy"],
          "employment_remittances": ["E1", "E2"],
          "news_nlp": ["N1", "G_pri_yoy", "NG_gap_price"],
          "poverty_vulnerability": ["V1"]}
INDICATOR_GROUP = {"A1": "market", "A2": "market", "A3": "market", "C1": "climate", "C2": "climate", "C3": "climate",
                   "C4": "climate", "E1": "employment_remittances", "E2": "employment_remittances", "N1": "news_nlp",
                   "V1": "poverty_vulnerability", "H1": "hunger_condition (target component, not a trigger)"}


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_protocol():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert sha256(LT / "PROTOCOL_LEAD2_FIVE_TRIGGER.md") == want, "protocol changed after freezing"


@functools.lru_cache(maxsize=1)
def stack() -> pd.DataFrame:
    """The served model's own stack (snapshot_l2.py): every lead 1..K. The unified model trains on all of them."""
    return pd.read_csv(DATA / "stack_l2.csv", dtype={"province_code": str})


@functools.lru_cache(maxsize=1)
def known_price() -> pd.DataFrame:
    k = pd.read_csv(DATA / "known_price_l2.csv", dtype={"province_code": str})
    return k.rename(columns={"y": "y_price"})


def train_rows(S: pd.DataFrame, t: int) -> pd.DataFrame:
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1)].rename(columns={"target_q": "q"})
    kp = known_price()
    kp = kp[kp["t"] == t][["province_code", "q", "y_price"]].rename(columns={"y_price": "y"})
    return tr.merge(kp, on=["province_code", "q"], how="inner")


def eligible(tr) -> bool:
    return tr["q"].nunique() >= MIN_Q and int(tr["y"].sum()) >= MIN_HIGH and int((1 - tr["y"]).sum()) >= MIN_LOW


class Uni:
    def __init__(self, cfg, cols, mono=True, min_child=15):
        self.cfg, self.cols, self.mono, self.min_child = cfg, cols, mono, min_child
        self.m = self.const = None

    def fit(self, tr):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        kw = {}
        if self.mono and any(c in MONO_UP for c in self.cols):
            kw["monotone_constraints"] = [1 if c in MONO_UP else 0 for c in self.cols]
            kw["monotone_constraints_method"] = "basic"
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=SEED_UNI, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"],
                                    min_child_samples=self.min_child, **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te):
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]

    def shap(self, te):
        return None if self.m is None else self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)


def select(tr, cols, mono=True, grid=GRID):
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    folds = [(f, h) for f, h in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    if not folds:
        return grid[0], {}
    sc = {}
    for c in grid:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
        ps = np.concatenate([Uni(c, cols, mono).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(grid, key=lambda c: (round(sc[c["id"]], 9), c["id"])), sc


def run(cols, origins, S=None, explain=False, mono=True, models=None) -> pd.DataFrame:
    S = stack() if S is None else S
    out = []
    for t in origins:
        tr = train_rows(S, int(t))
        te = S[S["t"] == t]
        if not eligible(tr) or not len(te):
            continue
        cfg, _ = select(tr, cols, mono)
        mdl = Uni(cfg, cols, mono).fit(tr)
        if models is not None:
            models[int(t)] = mdl
        o = te[KEY].copy()
        o["pi_P"], o["cfg"] = mdl.predict(te), cfg["id"]
        if explain:
            sv = mdl.shap(te)
            if sv is not None:
                for j, c in enumerate(cols):
                    o[f"shap_{c}"] = sv[:, j]
        out.append(o)
    return pd.concat(out, ignore_index=True)
