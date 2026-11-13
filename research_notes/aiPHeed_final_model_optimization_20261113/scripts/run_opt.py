r"""PROTOCOL_OPT new arms (DELTA, TRAJ, DELTA+TRAJ): FINAL's engine unchanged (engine_final.fit_predict rate='lin', miss='mind', cw='balanced'),
extra candidate inputs only. Lead 1, 3 folds x 5 seeds. No outcome is read. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=."""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
SEEDS = (168, 1, 2, 3, 4)
GOV_D = ["p_poverty", "p_subsistence", "p_poverty_gap", "unemp_region"]; CAND_D = ["hh_grdp_rel", "hh_grdp_g", "ag_pc"]
TRAJ = ["x_sv_prov_chg", "x_sv_reg_chg", "x_sv_nat_chg", "x_sv_prov_dev_reg", "x_sv_vol"]
ARMS = {"DELTA": ("d",), "TRAJ": ("t",), "DELTA_TRAJ": ("d", "t")}


def add_delta(d):
    G = pd.read_parquet("data/e148/out/gov_panel.parquet")[["key", "qi"] + GOV_D]
    C = pd.read_parquet(CACHE / "cand_panel.parquet")[["key", "qi"] + CAND_D]
    P = G.merge(C, on=["key", "qi"], how="outer")
    now = d[["key", "i"]].merge(P.rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    then = d[["key", "rq_anchor"]].merge(P.rename(columns={"qi": "rq_anchor"}), on=["key", "rq_anchor"], how="left")
    d = d.copy()
    for c in GOV_D + CAND_D:
        d["d_" + c] = now[c].values - then[c].values
    return d


def job(arm, survey, seed):
    f = HERE / "parts" / f"{arm}__{survey}__1__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    from app.hcw import engine as H
    tr, te, AN = run_qs.load(survey, 1)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    extra = []
    if "d" in ARMS[arm]:
        tr, te = add_delta(tr), add_delta(te); extra += ["d_" + c for c in GOV_D + CAND_D]
    if "t" in ARMS[arm]:
        extra += TRAJ
    extra = [c for c in extra if c in tr.columns]
    orig = H.feature_sets
    H.feature_sets = lambda: {k: list(v) + [c for c in extra if c not in v] for k, v in orig().items()}
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        H.feature_sets = orig
    m = r["model"]
    out = te[["key", "survey", "lead"]].assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cfg=r["cfg"], selected=";".join(m.use_),
                                               extra_selected=";".join(c for c in m.use_ if (c[3:] if c.startswith("mi_") else c) in extra),
                                               extra_test_missing=int(te[extra].isna().sum().sum()), extra_train_missing_share=float(tr[extra].isna().mean().mean()))
    out.to_csv(f.with_suffix(".tmp"), index=False, lineterminator="\n"); f.with_suffix(".tmp").replace(f)
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=18); a = ap.parse_args()
    J = [(arm, sv, s) for arm in ARMS for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
