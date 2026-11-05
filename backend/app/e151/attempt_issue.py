"""
Live forecast from the D5 attempt's rule, with all released rounds. Research output; sealed once.

    python -m app.e151.attempt_issue -> data/e151/out/issue/attempt_forecast.json, sealed_attempt_2027-Q1.json
"""
from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e147 import features as Fe
from app.e150 import model as M
from app.e150.issue import expit100
from app.e151 import OUT
from app.e151 import attempt as A
from app.e151 import prov as Pv
from app.fi5.target import qindex, qlabel

warnings.filterwarnings("ignore")
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
ISSUE = qindex("2026-Q4")


def main():
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, ISSUE, Pv.ROUNDS, "F")
    tr = Pv.add_inputs(S, P.tr).reset_index(drop=True)
    y, q, tb = tr["e"].values, tr["q_true"].values, tr["base"].values
    fits, rank = {}, []
    for name, cols in A.SETS.items():
        fits[name] = A._cv(tr, cols)
        _, _, _, pred, fid = fits[name]
        for wt, bias in product(A.WEIGHT, A.BIAS):
            adj = np.array([np.mean((y - wt * pred)[fid != f]) if bias else 0.0 for f in fid])
            res = y - wt * pred - adj
            p = norm.cdf((tb + wt * pred + adj) / max(1e-3, np.std(res)))
            rank.append({"set": name, "weight": wt, "bias": bias, "cv_soft_brier": float(np.mean((p - q) ** 2))})
    R = pd.DataFrame(rank)
    pick = R.loc[R["cv_soft_brier"].round(6).idxmin()].to_dict()
    use, par, n, pred, _ = fits[pick["set"]]
    m = lgb.LGBMRegressor(n_estimators=n, **par).fit(tr[use], tr["e"], sample_weight=1.0 / (tr["se_true"] ** 2 + 0.05))
    c = float(np.mean(y - pick["weight"] * pred)) if pick["bias"] else 0.0
    res = y - pick["weight"] * pred - c
    sd, half = float(np.std(res)), float(np.quantile(np.abs(res), 0.9))
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    te = Pv.add_inputs(S, M.rows_for(S, five.assign(T=ISSUE + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")).reset_index(drop=True)
    base, _ = P.hier.predict(te, te["T"].values)
    mu = base + pick["weight"] * m.predict(te[use]) + c
    rows = [{"province": te["province"].iloc[k], "target_quarter": qlabel(ISSUE + 1), "latest_survey": round(float(expit100(te["y_anchor"].iloc[k])), 1), "score": round(float(expit100(mu[k])), 1), "low90": round(float(expit100(mu[k] - half)), 1), "high90": round(float(expit100(mu[k] + half)), 1), "p_high": round(float(norm.cdf(mu[k] / sd)), 3), "class": "HIGH" if mu[k] >= 0 else "LOW"} for k in range(len(te))]
    C = np.abs(m.booster_.predict(tr[use], pred_contrib=True)[:, :-1]).mean(axis=0)
    gs = {}
    from app.e151.issue import group_of
    for nm, v in zip(use, C):
        gs[group_of(nm)] = gs.get(group_of(nm), 0.0) + float(v)
    tot = sum(gs.values()) or 1.0
    out = {"pick": pick, "bias_logit": c, "forecasts": rows, "shap_share": {k: round(v / tot, 4) for k, v in sorted(gs.items(), key=lambda t: -t[1])}}
    (OUT / "issue" / "attempt_forecast.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    f = OUT / "issue" / "sealed_attempt_2027-Q1.json"
    if not f.exists():
        f.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(f.read_bytes()).hexdigest())
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
