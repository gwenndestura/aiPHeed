"""
E160 deliverable 1: full calculation trace of the E158 2027-Q1 Lead 1 score for the five CALABARZON provinces.
Rebuilds exactly what app.e158.model.live() fits (same store, pipeline, columns, seed) and splits every step.

    python -m app.e160.trace
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e147 import features as Fe
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e151.issue import group_of
from app.e154 import model as E154
from app.e158 import model as E8
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
OUT = BACKEND_DIR / "data" / "e160" / "out"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def build():
    """Returns the fitted pieces live() uses, for reuse by the other E160 scripts."""
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    ISSUE = qindex("2026-Q4")
    H = E154.income()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, ISSUE, Pv.ROUNDS, "F")
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    m = Pv.Res2(E8.COLS).fit(tr)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(E8.CAL)]
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, five.assign(T=ISSUE + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")), H).reset_index(drop=True)
    return S, P, tr, m, te


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    S, P, tr, m, te = build()
    hp = P.hier
    base, parts = hp.predict(te, te["T"].values)
    res = m.predict(te)
    mu = base + res
    sd, half, _ = m.scale(te["gap_q"].values)
    C = m.m_.booster_.predict(te[m.use_], pred_contrib=True)
    rows, hist = [], []
    for k in range(len(te)):
        key, prov = te["key"].iloc[k], te["province"].iloc[k]
        own = hp.b[hp.b["key"] == key]
        for _, r in own.iterrows():
            hist.append({"province": prov, "round": r["survey"], "survey_pct": round(float(pct(r["y"])), 1), "round_national_pct": round(float(pct(hp.N[r["survey"]])), 1), "rel_logit": round(float(r["rel"]), 3), "dev_logit": round(float(r["dev"]), 3), "se_logit": round(float(r["se_y"]), 3)})
        g = {}
        for n, v in zip(m.use_, C[k, :-1]):
            gg = E8.GROUP_EXTRA.get(n) or group_of(n)
            g[gg] = g.get(gg, 0.0) + float(v)
        rows.append({
            "province": prov,
            "latest_survey_round": te["rq_anchor"].iloc[k],
            "latest_survey_pct": round(float(pct(te["y_anchor"].iloc[k])), 1),
            "quarters_since_latest": int(te["gap_q"].iloc[k]),
            "shared_level_logit": round(float(parts["shared"].iloc[k]), 3),
            "shared_level_pct": round(float(pct(parts["shared"].iloc[k])), 1),
            "structural_level_logit": round(float(parts["level"].iloc[k]), 3),
            "own_deviation_logit": round(float(parts["deviation"].iloc[k]), 3),
            "weight_own": round(float(parts["weight_own"].iloc[k]), 3),
            "own_adjustment_logit": round(float(parts["adj"].iloc[k]), 3),
            "anchor_logit": round(float(base[k]), 3),
            "anchor_pct": round(float(pct(base[k])), 1),
            "residual_logit": round(float(res[k]), 3),
            "residual_bias_logit": round(float(C[k, -1]), 3),
            "residual_by_group_logit": {a: round(v, 3) for a, v in sorted(g.items(), key=lambda t: -abs(t[1]))},
            "final_logit": round(float(mu[k]), 3),
            "final_score": round(float(pct(mu[k])), 1),
            "sd_logit": round(float(sd[k]), 3),
            "p_high": round(float(norm.cdf(mu[k] / sd[k])), 3),
            "class": "HIGH" if mu[k] >= 0 else "LOW",
        })
    meta = {"tau2_province_variance": round(hp.tau2, 4), "sig2_round_noise": round(hp.sig2, 4), "last_round": max(hp.N, key=lambda s: Pv.M8.RQ[s]), "national_by_round_pct": {s: round(float(pct(v)), 1) for s, v in hp.N.items()}, "residual_trees": m.n_, "train_rows": int(len(tr))}
    out = {"meta": meta, "provinces": rows, "survey_history": hist}
    (OUT / "trace.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(meta, indent=1))
    print(pd.DataFrame(rows).drop(columns=["residual_by_group_logit"]).T.to_string())
    for r in rows:
        print(r["province"], r["residual_by_group_logit"])
    print(pd.DataFrame(hist).to_string(index=False))


if __name__ == "__main__":
    run()
