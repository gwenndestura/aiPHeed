"""
E172 (docs/e172/PROTOCOL.md, blob 91d28950): the frozen E168 procedure plus the thesis decision cutoff (Chapter III
Section 3.5), chosen at each origin from the chosen calibration layer's training out-of-fold probabilities only.

    python -m app.e172.cutoff run    -> data/e172/out/rows.csv
    python -m app.e172.cutoff eval   -> data/e172/out/results.json
"""
from __future__ import annotations

import json
import sys
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from app.e164 import auto as A4
from app.e165 import final as F5
from app.e168 import lgbm_only as E
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e172" / "out"
GRID = np.round(np.arange(0.20, 0.80001, 0.025), 3)


def choose_cutoff(p_oof, high):
    acc = np.array([np.mean((p_oof >= c) == high) for c in GRID])
    best = np.flatnonzero(np.isclose(acc, acc.max()))
    return float(GRID[best[np.argmin(np.abs(GRID[best] - 0.5))]]), float(acc.max())


def run_proc(tr, te, AN):
    """E168 run_proc (app.e168.lgbm_only, lines 77-121) without ablation, plus the training-OOF cutoff."""
    tr = tr.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    best = None
    for a, f, pr, h in product(E.ANCH, E.FS, (False, True), E.HPO):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + E.LGBRes(E.FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    a, f, pr, h = best["cfg"]
    atr, ate = AN[a]
    oof = best["oof"]
    mdl = E.LGBRes(E.FS[f], *h, pr).fit(tr.assign(e=y - atr))
    mu = ate + mdl.predict(te)
    sd, _ = A4.scale(y - oof, gap, gap)
    lin, pl = np.zeros(len(tr)), np.zeros(len(tr))
    for i_tr, i_te in folds:
        Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
        ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
        lin[i_te] = ab[0] + ab[1] * oof[i_te]
        pl[i_te] = F5.soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
    sdl, _ = A4.scale(y - lin, gap, gap)
    p_oof = {"raw": norm.cdf(oof / sd), "linear": norm.cdf(lin / sdl), "platt": pl}
    inner = {k: float(np.mean((v - q) ** 2)) for k, v in p_oof.items()}
    chosen = min(inner, key=inner.get)
    sd_te, _ = A4.scale(y - oof, gap, te["gap_q"].values)
    Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w)[:, None]
    ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
    sd_lin, _ = A4.scale(y - lin, gap, te["gap_q"].values)
    P = {"raw": norm.cdf(mu / sd_te), "linear": norm.cdf((ab[0] + ab[1] * mu) / sd_lin), "platt": F5.soft_platt(oof, q).predict_proba(mu.reshape(-1, 1))[:, 1]}
    c, acc_tr = choose_cutoff(p_oof[chosen], y >= 0)
    return P[chosen], chosen, c, acc_tr, len(tr)


def task(survey, lead, H, L, S_P):
    from app.e148 import model as M8
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e147 import features as Fe
    from app.e166 import nested_source as N
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS) or M.Pipeline(Pv.Store2(None), i, Pv.ROUNDS, Pv.ORIGIN[survey]).tr.empty:
        return None
    from app.e150 import evaluate as Ev
    P_ = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), L, H, S_P)
    tr = N.add_sources(Pv.add_inputs(S, P_.tr), L, H, S_P)
    AN = A4.anchors(S, P_, tr, te)
    p, chosen, c, acc_tr, n_tr = run_proc(tr, te, AN)
    o = te[["key", "survey", "lead"]].copy()
    o["p"], o["cal"], o["cutoff"], o["train_oof_acc"], o["n_train"] = p, chosen, c, acc_tr, n_tr
    return o


def run():
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "rows.csv").exists():
        raise SystemExit("already run")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)]
    R = Parallel(n_jobs=12)(delayed(task)(s, h, H, L, S_P) for s, h in jobs)
    pd.concat([x for x in R if x is not None], ignore_index=True).to_csv(OUT / "rows.csv", index=False, lineterminator="\n")


def _m(y, pred, score):
    return {"accuracy": round(float((y == pred).mean()), 3), "precision_high": round(float(precision_score(y, pred, zero_division=0)), 3),
            "recall_high": round(float(recall_score(y, pred, zero_division=0)), 3), "f1_high": round(float(f1_score(y, pred, zero_division=0)), 3),
            "f1_weighted": round(float(f1_score(y, pred, average="weighted")), 3), "auc_roc": round(float(roc_auc_score(y, score)), 3)}


def evaluate():
    D = BACKEND_DIR / "data"
    R = pd.read_csv(OUT / "rows.csv")
    A = pd.concat([pd.read_csv(D / "e168" / "out" / "all_rows.csv"), pd.read_csv(D / "e168" / "out" / "all_rows_l3_8.csv")])
    A = A[A["mode"] == "main"][["key", "survey", "lead", "p"]].rename(columns={"p": "p_E168"})
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    res = {"protocol": "docs/e172/PROTOCOL.md blob 91d28950", "leads": {}}
    for Ld in range(1, 9):
        x = G[G["lead"] == Ld].merge(R[R["lead"] == Ld], on=["key", "survey", "lead"]).merge(A[A["lead"] == Ld], on=["key", "survey", "lead"])
        if len(x) < 10:
            continue
        same_p = float(np.max(np.abs(x["p"] - x["p_E168"])))
        y = (x["y_high"] == 1).astype(int)
        cls = {"E172": (x["p"] >= x["cutoff"]).astype(int), "E168": (x["p_E168"] >= .5).astype(int), "PERS": (x["PERS"] >= .5).astype(int)}
        sc = {"E172": x["p"], "E168": x["p_E168"], "PERS": x["PERS"]}
        folds = {a: {s: round(float((y[g.index] == cls[a][g.index]).mean()), 3) for s, g in x.groupby("survey")} for a in cls}
        res["leads"][Ld] = {"n": len(x), "max_abs_p_diff_vs_E168": same_p,
                            "cutoffs": x.groupby("survey")["cutoff"].first().to_dict(), "train_oof_acc": x.groupby("survey")["train_oof_acc"].first().round(3).to_dict(),
                            "mean_fold_accuracy": {a: round(float(np.mean(list(f.values()))), 3) for a, f in folds.items()}, "fold_accuracy": folds,
                            "metrics": {a: _m(y, cls[a], sc[a]) for a in cls}}
    def mrlt(arm):
        k = 0
        for Ld in range(1, 9):
            if Ld in res["leads"] and res["leads"][Ld]["mean_fold_accuracy"][arm] >= 0.75 and Ld == k + 1:
                k = Ld
            else:
                break
        return k
    res["MRLT_algorithm3"] = {a: mrlt(a) for a in ("E172", "E168", "PERS")}
    k = res["MRLT_algorithm3"]["E172"]
    res["decision"] = ("E172 REPLACES E168" if k >= 1 and all(res["leads"][l]["mean_fold_accuracy"]["E172"] > res["leads"][l]["mean_fold_accuracy"]["PERS"] for l in range(1, k + 1))
                       else "E168 STAYS; MRLT under Algorithm 3 = 0")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    for Ld, r in res["leads"].items():
        m = r["metrics"]["E172"]
        print(Ld, r["n"], "pdiff", round(r["max_abs_p_diff_vs_E168"], 9), "cut", r["cutoffs"], "meanfold", r["mean_fold_accuracy"], "folds172", r["fold_accuracy"]["E172"],
              "P/R/F1/F1w/AUC", m["precision_high"], m["recall_high"], m["f1_high"], m["f1_weighted"], m["auc_roc"])
    print(res["MRLT_algorithm3"], res["decision"])


if __name__ == "__main__":
    {"run": run, "eval": evaluate}[sys.argv[1]]()
