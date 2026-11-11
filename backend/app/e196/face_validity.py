"""
Objective 5 face-validity check of E196 against DOST-FNRI CALABARZON figures (local only; E196 is not changed).

Part A (same instrument, HFIAS moderate+severe): E196's back-test forecasts for every CALABARZON province survey result
         in the validation rounds (Laguna ENNS 2018; Quezon, Rizal ENNS 2019 = the "NNS 2019" figures; Batangas, Cavite
         ENNS 2021), Leads 1-3: forecast level and 90 % range against the published estimate.
Part B (NNS 2023, published on FIES, a different scale): E196 run as of 2023-Q2 (Lead 1, with the Lead-2 forecast issued
         at 2023-Q1, same target 2023-Q3), using only data available then; CALABARZON's population-weighted level and
         risk class, compared with the published direction (CALABARZON the lowest of 17 regions in 2023).

    python -m app.e196.face_validity
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold

from app.e178 import common as K
from app.e178 import retrain as RT

warnings.filterwarnings("ignore")
OUT = K.D / "e196" / "out"
CAL = ("batangas", "cavite", "laguna", "quezon", "rizal")
SEEDS = tuple(range(17901, 17921))
pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
# PSA 2020 Census of Population (provincial totals, persons), used only to weight the regional average in Part B
POP2020 = {"Batangas": 2908494, "Cavite": 4344829, "Laguna": 3382193, "Quezon": 1950459, "Rizal": 3330143}


def backtest_job(survey, lead):
    from app.e191 import run as R
    from app.e194 import run as E194
    tr, te, AN = R.load(R.FR / f"{survey}_L{lead}_main.pkl")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    ranked = E194.stage_a_ranked(tr, AN, folds)[:5]
    stream = RT.job_id(survey, lead, "main")
    keep = te["key"].isin(CAL).values
    acc = []
    for _, _, cfg in ranked:
        for s in SEEDS:
            mu, p, half = R.run_cfg(tr, te, AN, folds, cfg, R.spec_of("e184"), s, stream)[0]
            acc.append((np.asarray(mu)[keep], np.asarray(p)[keep], np.asarray(half)[keep]))
    o = te.loc[keep, ["key", "survey", "lead"]].copy()
    o["mu"], o["p"], o["half"] = (np.mean([a[k] for a in acc], axis=0) for k in range(3))
    return o


def part_a():
    jobs = [(s, l) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for l in (1, 2, 3)]
    B = pd.concat(Parallel(n_jobs=7, verbose=5)(delayed(backtest_job)(s, l) for s, l in jobs), ignore_index=True)
    W = {nm: B.pivot_table(index=["key", "survey"], columns="lead", values=nm) for nm in ("mu", "p", "half")}
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    rows = []
    for (k, s), _ in W["mu"].iterrows():
        g = G[(G["key"] == k) & (G["survey"] == s) & (G["lead"] == 1)].iloc[0]
        for L in (1, 2, 3):
            ls = [1, 2] if L == 1 else [L]                      # E196's rule: Lead 1 = mean(Lead 1, Lead 2)
            mu, p, half = (float(np.mean([W[nm].at[(k, s), l] for l in ls])) for nm in ("mu", "p", "half"))
            lo, hi, f = float(pct(mu - half)), float(pct(mu + half)), float(pct(mu))
            actual = float(pct(g["y_true"]))
            rows.append({"province": g["province"], "survey": s, "lead": L, "last_survey_pct": round(float(pct(g["y_anchor"])), 1),
                         "actual_pct": round(actual, 1), "forecast_pct": round(f, 1), "range90": [round(lo, 1), round(hi, 1)],
                         "inside_range90": bool(lo <= actual <= hi), "abs_error_pts": round(abs(f - actual), 1),
                         "p_high": round(p, 3), "forecast_class": "HIGH" if p >= .5 else "LOW", "actual_class": "HIGH" if actual >= 50 else "LOW"})
    return pd.DataFrame(rows)


def part_b():
    from app.e196 import serve as S96
    jobs = [(1, "2023-Q2"), (2, "2023-Q1")]
    preps = {(p["lead"], p["issue"]): p for p in Parallel(n_jobs=2)(delayed(S96._prep)(l, i) for l, i in jobs)}
    fits = Parallel(n_jobs=7, verbose=5)(delayed(S96._fit)(preps[j], r) for j in jobs for r in range(5))
    v = {nm: np.mean([f[nm] for f in fits], axis=0) for nm in ("mu", "p", "half")}       # mean of the 10 fits = E196 Lead 1
    te = preps[(1, "2023-Q2")]["te"]
    assert list(te["province"]) == list(preps[(2, "2023-Q1")]["te"]["province"])
    rows = [{"province": te["province"].iloc[k], "target": "2023-Q3", "forecast_pct": round(float(pct(v["mu"][k])), 1),
             "range90": [round(float(pct(v["mu"][k] - v["half"][k])), 1), round(float(pct(v["mu"][k] + v["half"][k])), 1)],
             "p_high": round(float(v["p"][k]), 3), "class": "HIGH" if v["p"][k] >= .5 else "LOW"} for k in range(len(te))]
    F = pd.DataFrame(rows)
    w = F["province"].map(POP2020).astype(float)
    region = float(np.sum(w * F["forecast_pct"]) / w.sum())
    return F, round(region, 1)


def main():
    prod = K.production_issue()
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e196.face_validity", [], prod))
    A = part_a()
    F, region23 = part_b()
    res = {"part_a_hfias_backtest": A.to_dict("records"),
           "part_a_summary": {"rows": int(len(A)), "inside_range90": int(A["inside_range90"].sum()), "class_agreement": int((A["forecast_class"] == A["actual_class"]).sum()),
                              "mean_abs_error_pts": round(float(A["abs_error_pts"].mean()), 1)},
           "part_b_2023": {"provinces": F.to_dict("records"), "calabarzon_population_weighted_forecast_pct": region23,
                           "published": "NNS 2023 (FIES scale): CALABARZON lowest of 17 regions; national 31.4 %. Regional value not verified here.",
                           "instrument_note": "E196 forecasts the HFIAS moderate+severe share; NNS 2023 reports FIES. Levels are not directly comparable."}}
    K.dump_json(res, OUT / "face_validity.json")
    pd.set_option("display.width", 200)
    print(A.to_string(index=False))
    print(res["part_a_summary"])
    print(F.to_string(index=False))
    print("CALABARZON 2023-Q3 population-weighted E196 forecast (HFIAS scale):", region23)


if __name__ == "__main__":
    main()
