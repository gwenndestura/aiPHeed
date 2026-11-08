"""
E153: optimisation under overfitting control, requested by the owner (docs/e153/PROTOCOL.md). One locked run.

Inputs always include all five groups. Settings are tuned only inside each round's training rows, by leaving out whole earlier rounds when there are at least two, else regions. The final model averages 10 seeds. Overfitting is measured three ways: train vs held-out error, seed stability, and a shuffled-label null.

    python -m app.e153.model lock | run
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT as OUT51
from app.e151 import prov as Pv
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e153" / "out"
SETS = {"five_groups": Pv.GOV_COLS, "five_groups_news": Pv.GNT_COLS}
GRID = [dict(num_leaves=l, min_child_samples=c, reg_lambda=r, colsample_bytree=s, n_estimators=n) for l, c, r, s, n in product([3, 4, 7], [10, 30], [5.0, 20.0], [0.5, 0.8], [100, 300])]
WEIGHT = [0.25, 0.5, 0.75, 1.0]
SEEDS = 10
SHUFFLES = 40
FILES = [BACKEND_DIR / "app" / "e153" / "model.py", BACKEND_DIR.parent / "docs" / "e153" / "PROTOCOL.md"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {p.name: _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def params(use, g, seed):
    return dict(objective="regression", learning_rate=0.02, max_depth=3, subsample=0.8, subsample_freq=1, n_jobs=1, verbose=-1, monotone_constraints=[Pv.SIGN.get(c, 0) for c in use], monotone_constraints_method="basic", random_state=seed, **g)


def folds(d):
    s = d["survey"].values
    if pd.Series(s).nunique() >= 2:
        return [(np.where(s != u)[0], np.where(s == u)[0]) for u in pd.unique(s)]
    return list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))


def select(tr, cols_by):
    d = tr.reset_index(drop=True)
    w = 1.0 / (d["se_true"] ** 2 + 0.05)
    fs = folds(d)
    best = None
    for name, cols in cols_by.items():
        use = [c for c in cols if d[c].notna().any() and d[c].nunique() > 1]
        for g in GRID:
            pred = np.zeros(len(d))
            for a, b in fs:
                pred[b] = lgb.LGBMRegressor(**params(use, g, Pv.SEED)).fit(d.iloc[a][use], d.iloc[a]["e"], sample_weight=w.iloc[a]).predict(d.iloc[b][use])
            for wt in WEIGHT:
                res = d["e"].values - wt * pred
                p = norm.cdf((d["base"].values + wt * pred) / max(1e-3, np.std(res)))
                sc = float(np.mean((p - d["q_true"].values) ** 2))
                if best is None or sc < best["score"] - 1e-6:
                    best = {"score": sc, "set": name, "grid": g, "weight": wt, "use": use, "cv_rmse": float(np.sqrt(np.mean(res ** 2))), "sd": float(np.std(res)), "half": float(np.quantile(np.abs(res), 0.9)), "oof_mse_raw": float(np.mean((d["e"].values - pred) ** 2))}
    return best


def predict(tr, te, sel, seeds=SEEDS, y=None):
    d = tr.reset_index(drop=True)
    w = 1.0 / (d["se_true"] ** 2 + 0.05)
    t = d["e"] if y is None else pd.Series(y)
    ms = [lgb.LGBMRegressor(**params(sel["use"], sel["grid"], Pv.SEED + s)).fit(d[sel["use"]], t, sample_weight=w) for s in range(seeds)]
    return np.array([m.predict(te[sel["use"]]) for m in ms]), np.array([m.predict(d[sel["use"]]) for m in ms])


def task(survey):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    P = M.Pipeline(S, M8.RQ[survey] - 1, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr).reset_index(drop=True)
    base, _ = P.hier.predict(te, te["T"].values)
    sel = select(tr, SETS)
    pte, ptr = predict(tr, te, sel)
    mu = base + sel["weight"] * pte.mean(axis=0)
    o = te[["key", "province", "region", "island", "sws_area", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["mu_A"], o["A"], o["half_A"] = mu, norm.cdf(mu / sel["sd"]), sel["half"]
    # seed stability: how many rows change class across single-seed forecasts
    cls = (base + sel["weight"] * pte) >= 0
    flip = int(np.sum(cls.any(axis=0) & ~cls.all(axis=0)))
    # overfitting: in-sample against held-out error of the same settings
    in_mse = float(np.mean((tr["e"].values - ptr.mean(axis=0)) ** 2))
    # shuffled-label null: the same settings fitted to training errors shuffled within round; what would accuracy be with no signal in the inputs
    r = np.random.default_rng(153)
    null_mu = []
    for _ in range(SHUFFLES):
        y = tr["e"].copy()
        for _, g in tr.groupby(["survey", "lead"]):
            y.loc[g.index] = r.permutation(g["e"].values)
        pn, _x = predict(tr, te, sel, seeds=1, y=y.values)
        null_mu.append(base + sel["weight"] * pn[0])
    meta = {"survey": survey, "train_rows": int(len(tr)), "set": sel["set"], "grid": sel["grid"], "weight": sel["weight"], "cv_soft_brier": sel["score"], "in_sample_mse": in_mse, "held_out_mse": sel["oof_mse_raw"], "overfit_ratio": sel["oof_mse_raw"] / in_mse, "rows_flipping_across_seeds": flip, "n_rows": int(len(te))}
    return o, meta, np.array(null_mu)


def main_run():
    lk = json.loads((OUT / "lock.json").read_text())
    bad = [p.name for p in FILES if _sha(p) != lk["hashes"][p.name]]
    if bad:
        raise RuntimeError(f"lock mismatch {bad}")
    if (OUT / "results.json").exists():
        raise SystemExit("this experiment has already run; the protocol allows one")
    out = Parallel(n_jobs=3)(delayed(task)(s) for s in ("ENNS2018", "ENNS2019", "ENNS2021"))
    F = Pv.label_2021(pd.concat([a for a, _, _ in out], ignore_index=True))
    G = pd.read_csv(OUT51 / "prov_oof.csv")
    G = G[G["lead"] == 1][["key", "survey", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT"]]
    F = F.merge(G, on=["key", "survey"])
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(153)
    def rep(g):
        g = g.reset_index(drop=True)
        m = Pv.met(g, "A")
        y = g["y_high"].values
        sc = Pv.scale_test(g, "A", rng, n=2000)
        return {"n": int(len(g)), "n_high": int(y.sum()), "n_correct": int(((g["A"] >= .5) == (y == 1)).sum()), "accuracy": m["accuracy"], "balanced": m["balanced_accuracy"], "high_recall": m["recall"], "low_recall": m["low_recall"], "auc": m["auc"], "brier": m["brier"], "mae_points": m["mae_points"], "coverage_90": m["coverage_90"], "confusion": m["confusion"], "majority_rule": float(max(y.mean(), 1 - y.mean())), "minus_persistence": E7.diff_ci(g, "A", "PERS", "q_true", rng, n=2000), "minus_e151": E7.diff_ci(g, "A", "GNT", "q_true", rng, n=2000), "slope_ci95": sc["slope_ci95"], "mean_error_ci95": sc["mean_error_ci95"], "may_be_called_prevalence": sc["may_be_called_prevalence"]}
    # null accuracy of the pool, pairing shuffles across rounds
    order = {x["survey"]: n for _, x, n in out}
    nulls = []
    for k in range(SHUFFLES):
        ok = 0
        for s, n in order.items():
            g = out[[m["survey"] for _, m, _ in out].index(s)][0]
            lab = F.set_index("key").loc[g["key"].values]
            lab = lab[lab["survey"] == s]
            ok += int(((n[k][:len(lab)] >= 0) == (lab["y_high"].values == 1)).sum())
        nulls.append(ok / len(F))
    res = {"status": "one locked run; all rows read before; retrospective", "meta": [m for _, m, _ in out], "pool": rep(F), "round_2021": rep(F[F["survey"] == "ENNS2021"]), "round_2018": rep(F[F["survey"] == "ENNS2018"]), "round_2019": rep(F[F["survey"] == "ENNS2019"]), "shuffled_input_null": {"mean_accuracy": float(np.mean(nulls)), "p95": float(np.percentile(nulls, 95)), "share_at_or_above_real": float(np.mean(np.array(nulls) >= ((F["A"] >= .5) == (F["y_high"] == 1)).mean()))}}
    p = res["pool"]
    res["adopt"] = bool(p["accuracy"] >= 0.75 and p["minus_e151"]["ci95"][1] < 0)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, default=float))


if __name__ == "__main__":
    {"lock": lock, "run": main_run}[sys.argv[1]]()
