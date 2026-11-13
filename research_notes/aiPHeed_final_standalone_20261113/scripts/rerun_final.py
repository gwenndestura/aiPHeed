r"""Re-runs FINAL exactly as stored (engine_final.fit_predict, rate='lin', miss='mind', cw='balanced'; the CW_BAL arm of
run_cw.py) for all 45 forward fits, recording what the stored parts lack: the training-chosen balanced-accuracy threshold
(engine_opt._thr on the inner out-of-fold probabilities) and the chosen calibration. Used for PROTOCOL_SA Rule 7a
(reproduction of all 45 stored fits) and 7e (Lead 1, seed 168: the same fitted model predicts copies of the test rows with one
input group set to missing). No outcome of the test rows is read here.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python rerun_final.py [--jobs N]"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
OUT = HERE / "parts_rerun"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
SEEDS = (168, 1, 2, 3, 4)


def group_of(c: str) -> str:
    """FINAL's inputs mapped onto the dashboard groups (news counted inside its topic's group); documented in the report."""
    if c in ("gap_q", "lead"):
        return "timing"
    for topic, g in (("market", "market"), ("climate", "climate"), ("employment", "employment"), ("poverty", "poverty"), ("hunger", "poverty")):
        if c.endswith("_" + topic):
            return g
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")):
        return "market"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni":
        return "climate"
    if c.startswith(("unemp", "income_growth", "hh_grdp_g")):
        return "employment"
    if c.startswith("remit"):
        return "ofw_remittance"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density", "income_rel", "hh_grdp_rel", "h2"):
        return "poverty"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")):
        return "agri_fish"
    return "news_aggregate"


def job(survey, lead, seed):
    f = OUT / f"FINALR__{survey}__{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import engine_opt as EO
    import run_qs
    from app.hcw import engine as H
    tr, te, AN = run_qs.load(survey, lead)
    te = te.reset_index(drop=True)
    blocks, AN2 = [te.assign(variant="none")], {a: (AN[a][0], AN[a][1]) for a in AN}
    if lead == 1 and seed == 168:
        allc = sorted({c for v in H.feature_sets().values() for c in v if c in te.columns})
        for g in ("market", "climate", "employment", "poverty", "agri_fish", "news_aggregate"):
            cols = [c for c in allc if group_of(c) == g]
            blocks.append(te.assign(**{c: np.nan for c in cols}, variant=f"missing_{g}"))
        AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), len(blocks))) for a in AN}
    T = pd.concat(blocks, ignore_index=True)
    r = EF.fit_predict(tr, T, AN2, seed, rate="lin", miss="mind", cw="balanced")
    out = T[["key", "survey", "lead", "T", "i", "variant"]].assign(arm="FINALR", seed=seed, p=r["p"], mu=r["mu"], cal=r["cal"], thr=r["thr"],
                                                                     inner_brier=r["inner_brier"], cfg=r["cfg"])
    OUT.mkdir(exist_ok=True)
    out.to_csv(f.with_suffix(".tmp"), index=False, lineterminator="\n")
    f.with_suffix(".tmp").replace(f)
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    J = [(sv, l, s) for l in (1, 2, 3) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS]
    J.sort(key=lambda j: (j[1] != 1 or j[2] != 168))           # perturbation fits first
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
