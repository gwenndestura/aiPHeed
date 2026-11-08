"""
POST-HOC, after the E150 lock and after all E150 scoring: the structural level used absolute poverty, which double-counts the national decline already in the shared level.
Candidate correction: structural inputs relative to the all-province mean at the same issue quarter. It changes no E150 result. All rows it is scored on have been read, so it is not validation.

    python -m app.e150.posthoc_relative -> data/e150/out/posthoc_relative.json, issue/posthoc_five_province.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import model as M8
from app.e150 import OUT
from app.e150 import evaluate as Ev
from app.e150 import issue as Is
from app.e150 import model as M
from app.fi5.target import qindex, qlabel

COLS = ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density", "m_food_threshold_rel"]
_Base = M.Store


class RelStore(_Base):
    def __init__(self, base=None):
        super().__init__(base)
        g = self.s8.gov.copy()
        g[COLS] = g[COLS] - g[COLS].groupby(level="qi").transform("mean")
        self.s8.gov = g


def task(survey, lead):
    M.Store = RelStore
    Fe.LT = 0.0
    return Ev.task(survey, lead)


def main():
    rng = np.random.default_rng(1500)
    L = pd.read_csv(Lb.SEALED)
    w = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]
    R = [x for x in Parallel(n_jobs=14)(delayed(task)(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in Ev.LEADS) if x is not None]
    X = pd.concat(R, ignore_index=True).merge(w, on="key", how="left")
    d21 = X["survey"] == "ENNS2021"
    X = X[~d21 | X["pct"].notna()].copy()
    X.loc[d21, "y_true"] = Fe._logit(X.loc[d21, "pct"])
    X.loc[d21, "q_true"] = norm.cdf(X.loc[d21, "y_true"] / (0.03 / (X.loc[d21, "pct"] / 100 * (1 - X.loc[d21, "pct"] / 100))))
    X["y_high"] = (X["y_true"] >= 0).astype(int)
    X.to_csv(OUT / "posthoc_relative_oof.csv", index=False, lineterminator="\n")
    res = {"status": "post hoc; every row already read; not validation", "by_set": {}}
    for lab, s in (("development", X[X["survey"] != "ENNS2021"]), ("2021", X[X["survey"] == "ENNS2021"]), ("pool", X)):
        res["by_set"][lab] = {}
        for h, g in s.groupby("lead"):
            g = g.reset_index(drop=True)
            e = {"n": int(len(g)), "n_high": int(g["y_high"].sum()), "always_high": float(g["y_high"].mean())}
            for a in ("A-H", "A-Hh", "A-G", "PERS"):
                e[a] = Ev.met(g, a)
                e[a]["continuous"] = Ev.continuous(g, a)
            e["coverage_A-H"] = float(np.mean(np.abs(g["y_true"].values - g["mu_A-H"].values) <= 1.645 * g["sigma_base"].values))
            e["A-H_minus_PERS"] = E7.diff_ci(g, "A-H", "PERS", "q_true", rng)
            res["by_set"][lab][f"L{h}"] = e
    # live
    M.Store = RelStore
    S = M.Store(Is.extended_base())
    P = M.Pipeline(S, Is.ISSUE, Is.ROUNDS, "F")
    five = S.base.drop_duplicates("key")
    five = five[five["province"].isin(Is.CAL)]
    rows = []
    for h in (1, 2, 3, 4):
        te = M.rows_for(S, five.assign(T=Is.ISSUE + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [h], "F").reset_index(drop=True)
        o = M.predict_all(P, te, None, news=False)
        q = M.q90(P.tr["e"].values)
        for k in range(len(te)):
            mu = float(o["mu_A-H"][k])
            rows.append({"province": te["province"].iloc[k], "target_quarter": qlabel(Is.ISSUE + h), "lead": h, "measured": round(float(Is.expit100(te["y_anchor"].iloc[k])), 1), "forecast_pct": round(float(Is.expit100(mu)), 1), "low90": round(float(Is.expit100(mu - q)), 1), "high90": round(float(Is.expit100(mu + q)), 1), "p_high_ge50": round(float(norm.cdf(mu / P.sigma_base)), 3),
                         "level": round(float(o["part_level"][k]), 3), "shared": round(float(o["part_shared"][k]), 3), "adj": round(float(o["part_adj"][k]), 3), "pct_A-Hh": round(float(Is.expit100(o["mu_A-Hh"][k])), 1), "pct_A-G": round(float(Is.expit100(o["mu_A-G"][k])), 1)})
    Lv = pd.DataFrame(rows)
    Lv.to_csv(OUT / "issue" / "posthoc_five_province.csv", index=False, lineterminator="\n")
    res["loading"] = P.loading
    (OUT / "posthoc_relative.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    f = lambda m: {k: (round(m[k], 3) if isinstance(m.get(k), float) else m.get(k)) for k in ("accuracy", "balanced_accuracy", "recall", "low_recall", "auc", "brier", "ece")}
    for lab in res["by_set"]:
        for L_ in ("L1", "L3", "L5"):
            e = res["by_set"][lab][L_]
            print(lab, L_, e["n"], e["n_high"], round(e["always_high"], 3), "A-H", f(e["A-H"]), "mae", round(e["A-H"]["continuous"]["mae_points"], 2), "slope", round(e["A-H"]["continuous"]["calibration_slope"], 2), "cov", round(e["coverage_A-H"], 2), "-PERS", round(e["A-H_minus_PERS"]["diff"], 4), [round(v, 4) for v in e["A-H_minus_PERS"]["ci95"]])
    print("loading", P.loading)
    print(Lv[Lv["lead"] == 1].to_string(index=False))


if __name__ == "__main__":
    main()
