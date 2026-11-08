"""
Freeze the E154 specification and issue forecasts. Training-free of any new choice: inputs and settings are exactly those locked in model.py. Research output; not production.

    python -m app.e154.live -> data/e154/out/{frozen_model.json, sealed_2027-Q1.json, quarterly_series.csv, trace.json, pairs.json}
"""
from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import features as Fe
from app.e150 import model as M
from app.e150.issue import expit100
from app.e151 import prov as Pv
from app.e154 import model as E
from app.fi5.target import qindex, qlabel

warnings.filterwarnings("ignore")
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
ISSUE = qindex("2026-Q4")
OUT = E.OUT


def issue(i, H, detail=False):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, i, Pv.ROUNDS, "F")
    if P.tr.empty:
        return None
    tr = E.add_income(Pv.add_inputs(S, P.tr), H)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    te = E.add_income(Pv.add_inputs(S, M.rows_for(S, five.assign(T=i + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")), H).reset_index(drop=True)
    # only rounds released by this issue date may anchor it
    base, parts = P.hier.predict(te, te["T"].values)
    pte, ptr, m, use = E.fit_predict(tr, te)
    s = tr["survey"].values
    groups = [(np.where(s != u)[0], np.where(s == u)[0]) for u in pd.unique(s)] if pd.Series(s).nunique() >= 2 else [(np.where(tr["region"].values != r)[0], np.where(tr["region"].values == r)[0]) for r in pd.unique(tr["region"])]
    oof = np.zeros(len(tr))
    for a, c in groups:
        oof[c] = E.fit_predict(tr.iloc[a], tr.iloc[c], seeds=2)[0]
    r_o = tr["e"].values - oof
    sd, half = float(np.std(r_o)), float(np.quantile(np.abs(r_o), 0.9))
    mu = base + pte
    o = pd.DataFrame({"province": te["province"], "issue_quarter": qlabel(i), "target_quarter": qlabel(i + 1), "last_survey_quarter": [qlabel(int(x)) for x in te["rq_anchor"]], "last_survey_pct": np.round(expit100(te["y_anchor"]), 1), "anchor_pct": np.round(expit100(base), 1), "score": np.round(expit100(mu), 1), "low90": np.round(expit100(mu - half), 1), "high90": np.round(expit100(mu + half), 1), "p_high": np.round(norm.cdf(mu / sd), 3), "class": np.where(mu >= 0, "HIGH", "LOW"), "n_train": len(tr)})
    if not detail:
        return o
    C = m.booster_.predict(te[use], pred_contrib=True)[:, :-1]
    trace = {te["province"].iloc[k]: {"adjustment_logit": round(float(pte[k]), 3), "by_input_logit_first_seed": {n: round(float(v), 3) for n, v in zip(use, C[k]) if abs(v) > 1e-4}, "inputs": {n: (None if pd.isna(te[n].iloc[k]) else round(float(te[n].iloc[k]), 3)) for n in E.COLS if n in te}} for k in range(len(te))}
    gs = {}
    CT = np.abs(m.booster_.predict(tr[use], pred_contrib=True)[:, :-1]).mean(axis=0)
    for n, v in zip(use, CT):
        g = next(g for g, cs in E.INPUTS.items() if n in cs)
        gs[g] = gs.get(g, 0.0) + float(v)
    tot = sum(gs.values()) or 1.0
    pp = P.hier.province(te)
    x = te.assign(mu_=(pp["level"] + pp["adj"]).values, v_=pp["var_prov"].values).set_index("province")
    pairs = {}
    for j, a in enumerate(CAL):
        for c in CAL[j + 1:]:
            d = float(x.at[a, "mu_"] - x.at[c, "mu_"])
            se = float(np.sqrt(x.at[a, "v_"] + x.at[c, "v_"]))
            pairs[f"{a}-{c}"] = {"diff_logit": round(d, 3), "se": round(se, 3), "separated_90": bool(abs(d) > 1.645 * se)}
    return o, trace, {k: round(v / tot, 4) for k, v in sorted(gs.items(), key=lambda t: -t[1])}, pairs, {"train_rows": int(len(tr)), "sd": sd, "half": half, "used": use}


def main():
    H = E.income()
    o, tr, gs, pairs, info = issue(ISSUE, H, detail=True)
    s = OUT / "sealed_2027-Q1.json"
    if not s.exists():
        s.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "model": "E154 frozen", "forecasts": o.to_dict(orient="records")}, indent=1, default=float), newline="\n")
    (OUT / "frozen_model.json").write_text(json.dumps({"frozen_utc": datetime.now(timezone.utc).isoformat(), "spec": {"inputs": E.INPUTS, "lightgbm": E.PAR, "seeds": E.SEEDS, "signs": {c: E.SIGNS.get(c, 0) for c in E.COLS}, "target": "HFIAS moderate plus severe", "classes": "HIGH at score >= 50, LOW below"}, "model_sha256": hashlib.sha256(open(E.__file__, "rb").read()).hexdigest(), "status": "frozen for future testing; not validated; not production", "shap_group_share": gs, **info}, indent=1, default=float), newline="\n")
    (OUT / "trace.json").write_text(json.dumps(tr, indent=1, default=float), newline="\n")
    (OUT / "pairs.json").write_text(json.dumps(pairs, indent=1), newline="\n")
    S = pd.concat([x for x in Parallel(n_jobs=8)(delayed(issue)(i, H) for i in range(qindex("2021-Q1"), ISSUE + 1)) if x is not None], ignore_index=True)
    S.to_csv(OUT / "quarterly_series.csv", index=False, lineterminator="\n")
    print("seal", hashlib.sha256(s.read_bytes()).hexdigest())
    print(o.drop(columns=["issue_quarter", "n_train"]).to_string(index=False))
    print("groups", gs, "pairs separated", sum(v["separated_90"] for v in pairs.values()), "of", len(pairs), info["train_rows"])
    w = S.pivot_table(index="target_quarter", columns="province", values="score")
    print(w.tail(12).to_string())
    print("mean abs quarter change", w.diff().abs().mean().round(2).to_dict(), "spread", round(float((w.max(axis=1) - w.min(axis=1)).mean()), 1), "pair corr", round(float(w.corr().values[np.triu_indices(5, 1)].mean()), 2), "HIGH share", round(float((S["class"] == "HIGH").mean()), 3))


if __name__ == "__main__":
    main()
