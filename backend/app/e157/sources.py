"""
Which downloaded data source contributes most? Each source added on its own to the E151 required model, same Lead-1 rows, nothing tuned. Retrospective; a ranking, not a model selection.

Sources: PSA farmgate palay (E152), PSA wholesale rice (E152), NASA POWER rainfall (E152), PSA regional household consumption (E154), SunStar headlines (E155).

    python -m app.e157.sources -> data/e156/out/source_ranking.json
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import SUNCOLS
from app.e155.test import panel as sun_panel
from app.e156.audit import setup
from app.e156.leads import OUT

warnings.filterwarnings("ignore")
SOURCES = {"farmgate_palay": ["l_fg_yoy", "l_fg_rel", "r_fg_yoy"], "wholesale_rice": ["l_rice_yoy", "l_rice_rel", "r_rice_yoy", "l_terms"], "nasa_rainfall": ["l_rain3", "l_rain6", "r_rain3"], "regional_consumption": ["income_growth", "income_rel"], "sunstar_headlines": SUNCOLS}


def run(survey, L, H, S_P):
    S, P, tr, te, base = setup(survey)
    def add(d):
        d = d.merge(L, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_l")).drop(columns=["qi_l"], errors="ignore")
        d = E154.add_income(d, H)
        return d.merge(S_P, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_s")).drop(columns=["qi_s"], errors="ignore")
    tr, te = add(tr), add(te)
    out = te[["key", "survey"]].copy()
    for name, extra in [("E151", [])] + list(SOURCES.items()):
        m = Pv.Res2(Pv.GNT_COLS + extra).fit(tr)
        mu = base + m.predict(te)
        sd, _, _ = m.scale(te["gap_q"].values)
        out[name] = norm.cdf(mu / sd)
        out["cov_" + name] = te[extra].notna().any(axis=1).mean() if extra else 1.0
    return out


def main():
    L = pd.read_parquet(O152 / "local_panel.parquet")
    H, S_P = E154.income(), sun_panel()
    R = pd.concat(Parallel(n_jobs=3)(delayed(run)(s, L, H, S_P) for s in ("ENNS2018", "ENNS2019", "ENNS2021")))
    F = pd.read_csv(O51 / "prov_oof.csv")
    x = F[F["lead"] == 1][["key", "survey", "y_high", "q_true", "region"]]
    R = R.merge(x, on=["key", "survey"]).reset_index(drop=True)
    rng = np.random.default_rng(157)
    res = {}
    for name in ["E151"] + list(SOURCES):
        ok = (R[name] >= .5) == (R["y_high"] == 1)
        r = {"correct": int(ok.sum()), "accuracy": round(float(ok.mean()), 3), "brier_soft": round(float(np.mean((R[name] - R["q_true"]) ** 2)), 4), "test_rows_with_data": round(float(R["cov_" + name].mean()), 3)}
        if name != "E151":
            d = E7.diff_ci(R, name, "E151", "q_true", rng, n=2000)
            r["brier_change_vs_e151"], r["ci95"] = round(d["diff"], 4), [round(v, 4) for v in d["ci95"]]
        res[name] = r
    (OUT / "source_ranking.json").write_text(json.dumps(res, indent=1), newline="\n")
    for k, v in sorted(res.items(), key=lambda t: t[1].get("brier_change_vs_e151", 0)):
        print(k, v)


if __name__ == "__main__":
    main()
