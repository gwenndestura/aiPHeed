"""
E179: broad LightGBM optimisation of SIMPLE (EXPLORATORY; test-informed comparison disclosed). Writes only this folder.

Every configuration in GRID is run at every issue (ENNS 2018/2019/2021 x Leads 1-3) with E168's anchors, temperature shrink and
HIGH line; its training-only score and its forecasts are saved. Two selections are reported separately:
  TS      = per issue, the lowest training-only score (survey-round-aware, app.e171.candidates.score_all), plus a training-only
            decision threshold variant (TS_THR);
  BEST72  = the configuration with the most correct Lead-2 forecasts on the 72 rows (test-informed; disclosed, not validation).

    cd backend && PYTHONPATH=. python ../experiments/E179_AGGRESSIVE_SIMPLE_OPTIMIZATION/run.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
LEADS = (1, 2, 3)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
INTER = [("cpi_food_yoy", "c_rain_anom_6m"), ("cpi_since", "agri_since"), ("cpi_food_yoy", "c_soil_anom_3m")]


def settings():
    from app.e150 import model as M
    P = dict(M.PARAMS)
    return {"R0": dict(P), "R1": dict(P, num_leaves=2, max_depth=1, min_child_samples=20, reg_lambda=10.0),
            "R2": dict(P, num_leaves=3, max_depth=2, min_child_samples=20, reg_lambda=10.0), "R3": dict(P, min_child_samples=30, reg_lambda=20.0),
            "R4": dict(P, num_leaves=2, max_depth=1, min_child_samples=40, reg_lambda=20.0, colsample_bytree=0.5),
            "R5": dict(P, num_leaves=2, max_depth=1, min_child_samples=20, reg_lambda=10.0, learning_rate=0.05),
            "R6": dict(P, num_leaves=4, max_depth=2, min_child_samples=50, reg_lambda=50.0),
            "R7": dict(P, num_leaves=3, max_depth=2, min_child_samples=20, reg_lambda=10.0, extra_trees=True)}


INPUTS = ("GOV", "FULL", "GOV_S", "GOV_A", "GOV_AX")
SINGLE = [(r, f, 1) for r in ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7") for f in INPUTS]
ENS = [(r, f, 5) for r in ("R0", "R2") for f in ("GOV", "GOV_A")]
GRID = SINGLE + ENS                                         # 44 configurations


def install():
    """Register inputs and learners in this process (called inside every worker job)."""
    from app.e164 import auto as U
    from app.e171 import candidates as C171
    from app.e172 import lgbm_only as E
    E._install()
    gov = U.FS["GOV"]
    U.FS["GOV_A"] = gov + ["anc_lvl"]
    U.FS["GOV_AX"] = gov + ["anc_lvl"] + [f"{a}_x_{b}" for a, b in INTER]
    S = settings()
    for r, p in S.items():
        for seeds in (1, 5):
            name = f"X{r}S{seeds}"
            U.LEARNERS[name] = type(name, (E.LGB,), {"P": p, "SEEDS": tuple(range(151, 151 + seeds))})
    return U, C171, E


def cfgname(r, f, s):
    return f"{r}|{f}|seeds{s}"


def task(survey, lead, mode="main"):
    from app.e144 import data as SWSD
    from app.e147 import features as Fe
    from app.e148 import model as M8
    from app.e148 import panel as Pn
    from app.e150 import evaluate as Ev
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e154 import model as E154
    from app.e166 import temperature as T
    from app.e168 import lgbm as L
    U, C171, E = install()
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    C171.LEAD_NOW["v"] = lead
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    cut = Pn.q_start(i)
    sw = SWSD.sws_quarterly()
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
        sw = T.corrupt_sws(sw, cut)
    SW = L.sws_forecasts(sw, i)
    H = E154.income()
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = C171.add_sws(E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H), sw).reset_index(drop=True)
    tr = C171.add_sws(E154.add_income(Pv.add_inputs(S, P.tr), H), sw).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    scheme, msk, r1 = E.score(tr, AN, E.STAGE1)
    anchor = min(E.STAGE1, key=lambda c: r1[c]["sse"])[0]
    for d, a in ((tr, AN[anchor][0]), (te, AN[anchor][1])):
        d["anc_lvl"] = a
        for x, y in INTER:
            d[f"{x}_x_{y}"] = d[x] * d[y]
    menu = [(anchor, f"X{r}S{s}", f) for r, f, s in GRID]
    _, _, res = E.score(tr, AN, menu)
    o = te[KEY].copy()
    o["mode"], o["anchor"], o["scheme"], o["train_rounds"] = mode, anchor, scheme, int(tr["survey"].nunique())
    ts = min(menu, key=lambda c: res[c]["sse"])
    todo = menu if mode == "main" else [ts]
    imp = {}
    for c in todo:
        r = C171.finalize(tr, te, AN, SW, cut, lead, scheme, msk, res, [c])
        n = cfgname(c[1][1:3], c[2], c[1][-1])
        o[f"mu::{n}"], o[f"p::{n}"], o[f"half::{n}"] = r["mu"], r["p"], r["half"]
        o[f"train::{n}"] = res[c]["sse"]
        if c == ts:
            o["TS_cfg"] = n
            o["mu::TS"], o["p::TS"], o["half::TS"], o["lam::TS"] = r["mu"], r["p"], r["half"], r["lam"]
            # training-only decision threshold on the score scale: maximise training out-of-fold accuracy over a grid
            oof = res[c]["oof_id"]
            ok = np.isfinite(oof)
            yt = tr["y_true"].values >= 0
            grid = np.round(np.arange(-0.5, 0.51, 0.05), 2)
            accs = [float(((oof[ok] >= t) == yt[ok]).mean()) for t in grid]
            t_best = float(grid[int(np.argmax(accs))]) if max(accs) > accs[int(np.where(grid == 0)[0][0])] else 0.0
            o["thr::TS"] = t_best
            o["p::TS_THR"] = np.where(np.asarray(r["mu"]) >= t_best * r["lam"], np.maximum(r["p"], 0.5 + 1e-9), np.minimum(r["p"], 0.5 - 1e-9))
            m = U.LEARNERS[c[1]](U.FS[c[2]]).fit(tr.assign(e=tr["y_true"].values - AN[anchor][0]))
            g = pd.Series(np.mean([b.booster_.feature_importance("gain") for b in m.ms_], axis=0), index=m.use_)
            imp = (g / g.sum()).sort_values(ascending=False).head(12).round(4).to_dict()
    o["TS_importance"] = json.dumps(imp)
    return o


def main():
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, h, "corrupt") for s in SURVEYS for h in (1, 2)]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, m) for s, h, m in jobs) if x is not None]
    A = pd.concat(R, ignore_index=True)
    A.to_csv(HERE / "all_rows.csv", index=False, lineterminator="\n")
    print("written", A.shape)


if __name__ == "__main__":
    if sys.argv[1:] == ["registry"]:
        S = settings()
        rows = [{"candidate_id": cfgname(r, f, s), "lightgbm": "yes", "settings": json.dumps({k: v for k, v in S[r].items() if k in
                 ("num_leaves", "max_depth", "min_child_samples", "reg_lambda", "learning_rate", "colsample_bytree", "subsample", "extra_trees")}),
                 "inputs": f, "seeds": s, "training_data": "all released rounds before each issue (E168 rule)",
                 "validation": "survey-round-aware training score (forward over rounds if 2+, else region folds)",
                 "anchor": "E168 stage-1 rule (training-only)"} for r, f, s in GRID]
        rows += [{"candidate_id": "TS", "lightgbm": "yes", "settings": "per issue: lowest training score among the 44", "inputs": "selected",
                  "seeds": "selected", "training_data": "same", "validation": "training-only selection", "anchor": "same"},
                 {"candidate_id": "TS_THR", "lightgbm": "yes", "settings": "TS + decision threshold on the score chosen to maximise training out-of-fold accuracy",
                  "inputs": "selected", "seeds": "selected", "training_data": "same", "validation": "training-only", "anchor": "same"},
                 {"candidate_id": "BEST72", "lightgbm": "yes", "settings": "the configuration with most correct Lead-2 rows (test-informed, disclosed)",
                  "inputs": "selected on the 72 rows", "seeds": "-", "training_data": "same", "validation": "TEST-INFORMED (not validation)", "anchor": "same"}]
        pd.DataFrame(rows).to_csv(HERE / "candidate_registry.csv", index=False, lineterminator="\n")
        print(len(rows), "registered")
    else:
        main()
