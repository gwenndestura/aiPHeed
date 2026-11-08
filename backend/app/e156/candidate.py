"""
E156 candidate (docs/e156/CANDIDATE_PROTOCOL.md): E151 plus a slope correction fitted only on each round's training rows. One run.

    python -m app.e156.candidate -> data/e156/out/candidate_oof.csv, candidate_results.json
"""
from __future__ import annotations

import json
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.e156 import leads as LD

warnings.filterwarnings("ignore")
OUT = LD.OUT


def task(survey, lead):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    if not M.released(i, Pv.ROUNDS):
        return None
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])).reset_index(drop=True)
    if te.empty:
        return None
    tr = Pv.add_inputs(S, P.tr).reset_index(drop=True)
    base, _ = P.hier.predict(te, te["T"].values)
    m = Pv.Res2(Pv.GNT_COLS).fit(tr)
    mu = base + m.predict(te)
    # training-internal calibration: out-of-fold forecasts of the training rows against their survey values
    oof_mu = tr["base"].values + (tr["e"].values - m.oof_)
    w = 1.0 / (tr["se_true"].values ** 2 + 0.05)
    X = np.column_stack([np.ones(len(tr)), oof_mu])
    a, b = np.linalg.lstsq(X * np.sqrt(w)[:, None], tr["y_true"].values * np.sqrt(w), rcond=None)[0]
    mu_c = a + b * mu
    res = tr["y_true"].values - (a + b * oof_mu)
    sd = float(np.std(res))
    o = te[["key", "province", "region", "island", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["mu_CAL"], o["CAL"], o["half_CAL"] = mu_c, norm.cdf(mu_c / sd), float(np.quantile(np.abs(res), 0.9))
    o["cal_a"], o["cal_b"] = float(a), float(b)
    return o


def main():
    if (OUT / "candidate_results.json").exists():
        raise SystemExit("this candidate has already run; the protocol allows one")
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)) if x is not None]
    F = Pv.label_2021(pd.concat(R, ignore_index=True))
    G = pd.read_csv(O51 / "prov_oof.csv")[["key", "survey", "lead", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT"]]
    F = F.merge(G, on=["key", "survey", "lead"])
    F.to_csv(OUT / "candidate_oof.csv", index=False, lineterminator="\n")
    cand = LD.evaluate(F, "CAL", "E156 calibrated")
    base = LD.evaluate(F, "GNT", "E151")
    l1c, l1b = cand["leads"][0], base["leads"][0]
    adopt = bool(sum(l1c["criteria"].values()) >= sum(l1b["criteria"].values()) and l1c["brier_soft"] <= l1b["brier_soft"])
    res = {"candidate": cand, "e151": base, "slopes_by_round_lead1": F[F["lead"] == 1].groupby("survey")["cal_b"].first().round(3).to_dict(), "adopt": adopt}
    (OUT / "candidate_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for r in cand["leads"]:
        print("CAL", r["lead"], r["accuracy"], r["f1"], r["auc"], r["brier_soft"], r["brier_minus_persistence_ci95"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()}, r["high_recall"], r["low_recall"])
    print("max reliable", cand["maximum_reliable_lead"], "slopes", res["slopes_by_round_lead1"], "adopt", adopt)


if __name__ == "__main__":
    main()
