"""
Owner decision (2026-11-06): remove employment and remittances, which contribute nothing (E156, E157). E151 otherwise unchanged: market, climate, poverty and news. One run, Leads 1 to 8, judged by docs/e156/LEAD_RELIABILITY_CRITERIA.md. Retrospective.

    python -m app.e157.three_groups -> data/e156/out/three_groups_oof.csv, three_groups_results.json
"""
from __future__ import annotations

import json
import warnings

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
DROP = set(M.GROUPS["employment"]) | set(M.GROUPS["remittance"]) | {c for c in Pv.NEWS_ALL if "employment" in c or "remittance" in c}
COLS = [c for c in Pv.GNT_COLS if c not in DROP]


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
    m = Pv.Res2(COLS).fit(tr)
    mu = base + m.predict(te)
    sd, half, _ = m.scale(te["gap_q"].values)
    o = te[["key", "province", "region", "island", "survey", "T", "lead", "y_anchor", "gap_q"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["mu_G3"], o["G3"], o["half_G3"] = mu, norm.cdf(mu / sd), half
    return o


def main():
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(1, 9)) if x is not None]
    F = Pv.label_2021(pd.concat(R, ignore_index=True))
    G = pd.read_csv(O51 / "prov_oof.csv")[["key", "survey", "lead", "PERS", "mu_PERS", "half_PERS", "GNT", "mu_GNT", "half_GNT"]]
    F = F.merge(G, on=["key", "survey", "lead"])
    F.to_csv(LD.OUT / "three_groups_oof.csv", index=False, lineterminator="\n")
    new, old = LD.evaluate(F, "G3", "E151 without employment and remittances"), LD.evaluate(F, "GNT", "E151")
    from app.e147 import evaluate as E7
    x = F[F["lead"] == 1].reset_index(drop=True)
    res = {"removed": sorted(DROP), "inputs_left": len(COLS), "new": new, "e151": old, "lead1_brier_new_minus_e151": E7.diff_ci(x, "G3", "GNT", "q_true", np.random.default_rng(157), n=2000)}
    (LD.OUT / "three_groups_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for r in new["leads"]:
        print("G3", r["lead"], r["accuracy"], r["f1"], r["auc"], r["brier_soft"], r["brier_minus_persistence_ci95"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()}, r["confusion"])
    print("max reliable", new["maximum_reliable_lead"], "| lead1 vs E151", res["lead1_brier_new_minus_e151"]["diff"], res["lead1_brier_new_minus_e151"]["ci95"], "| removed", len(DROP))


if __name__ == "__main__":
    main()
