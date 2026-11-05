"""
The frozen E154 specification with an added L0: the nowcast of the current quarter, issued on its first day. L1 stays next quarter, as in E151 to E154.
Nothing is tuned; inputs and settings are those locked in model.py. Rows read before: retrospective.

    python -m app.e154.current_quarter -> data/e154/out/current_quarter.json, current_quarter_oof.csv
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E

warnings.filterwarnings("ignore")
INTERNAL = [0, 1, 2, 3, 4]


def task(survey, h, H):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - h
    if not M.released(i, Pv.ROUNDS):
        return None
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [h], Pv.ORIGIN[survey])), H)
    if te.empty:
        return None
    tr = E.add_income(Pv.add_inputs(S, P.tr), H)
    base, _ = P.hier.predict(te, te["T"].values)
    pte, _, _, _ = E.fit_predict(tr, te)
    s = tr["survey"].values
    groups = [(np.where(s != u)[0], np.where(s == u)[0]) for u in pd.unique(s)] if pd.Series(s).nunique() >= 2 else [(np.where(tr["region"].values != r)[0], np.where(tr["region"].values == r)[0]) for r in pd.unique(tr["region"])]
    oof = np.zeros(len(tr))
    for a, b in groups:
        oof[b] = E.fit_predict(tr.iloc[a], tr.iloc[b], seeds=2)[0]
    r_o = tr["e"].values - oof
    lvl = float(np.mean(tr["e"]))
    o = te[["key", "province", "region", "survey", "T", "i", "y_anchor"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["owner_lead"] = h
    o["mu_E154"], o["E154"], o["half_E154"] = base + pte, norm.cdf((base + pte) / np.std(r_o)), float(np.quantile(np.abs(r_o), 0.9))
    o["mu_LEVEL"], o["LEVEL"] = base + lvl, norm.cdf((base + lvl) / float(np.std(tr["e"])))
    o["mu_PERS"], o["PERS"] = te["y_anchor"].values, norm.cdf(te["y_anchor"].values / float(np.std(tr["y_true"] - tr["y_anchor"])))
    return o


def main():
    H = E.income()
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in INTERNAL) if x is not None]
    F = Pv.label_2021(pd.concat(R, ignore_index=True))
    F.to_csv(E.OUT / "current_quarter_oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(154)
    res = {"definition": "L0 = nowcast of the current quarter, issued on its first day; L1 = next quarter (one quarter ahead); L2 to L4 further ahead", "status": "frozen E154 specification, no tuning; retrospective", "by_owner_lead": {}}
    for L, g in F.groupby("owner_lead"):
        g = g.reset_index(drop=True)
        out = {"n": int(len(g)), "n_high": int(g["y_high"].sum())}
        for a in ("E154", "LEVEL", "PERS"):
            ok = (g[a] >= .5) == (g["y_high"] == 1)
            m = {"correct": int(ok.sum()), "accuracy": float(ok.mean()), "high_recall": float(ok[g["y_high"] == 1].mean()), "low_recall": float(ok[g["y_high"] == 0].mean()), "brier_soft": float(np.mean((g[a] - g["q_true"]) ** 2)), "mae_points": float(np.mean(np.abs(100 / (1 + np.exp(-g[f"mu_{a}"])) - 100 / (1 + np.exp(-g["y_true"])))))}
            m["by_round"] = {s: int(((x[a] >= .5) == (x["y_high"] == 1)).sum()) for s, x in g.groupby("survey")}
            out[a] = m
        out["E154_minus_PERS"] = E7.diff_ci(g, "E154", "PERS", "q_true", rng, n=2000)
        res["by_owner_lead"][f"L{int(L)}"] = out
    (E.OUT / "current_quarter.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for L, v in res["by_owner_lead"].items():
        print(L, "n", v["n"], {a: (v[a]["correct"], round(v[a]["accuracy"], 3), round(v[a]["high_recall"], 2), round(v[a]["low_recall"], 2), round(v[a]["mae_points"], 2), v[a]["by_round"]) for a in ("E154", "LEVEL", "PERS")}, "vsPERS", round(v["E154_minus_PERS"]["diff"], 3), [round(x, 3) for x in v["E154_minus_PERS"]["ci95"]])


if __name__ == "__main__":
    main()
