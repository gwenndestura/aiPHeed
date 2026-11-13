r"""PROTOCOL_INPUTS addendum 1 (sha 56e6c928): arms N-AFF, N-ALL, N-ALL-F. Same engine and folds as inputs_run.py; the AFF columns
are read from the branch's backend/data/hcw_official/raw/psa_grdp_aff_by_region.csv (REGIONAL values).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.   Usage: python inputs_run2.py [jobs] [leads]"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inputs_run as B                                                        # noqa: E402

AFF_FILE = Path(r"C:\Users\admin\aipheed_fmc\backend\data\hcw_official\raw\psa_grdp_aff_by_region.csv")
AFF = ["aff_g", "aff_share"]
AFF_SIGNS = {"aff_g": -1, "aff_share": 0}
ARMS = {"N-AFF": dict(new=AFF, drop=[], force=[]),
        "N-ALL": dict(new=B.NEW + AFF, drop=["p_density"], force=[]),
        "N-ALL-F": dict(new=B.NEW + AFF, drop=["p_density"], force=B.FORCE["N-OFF-F"] + AFF)}


def add_aff(df):
    from app.e154 import model as E154
    A = pd.read_csv(AFF_FILE).set_index(["region", "year"])
    def one(reg, i):
        y = E154.available_year(int(i))
        if (reg, y) in A.index:
            r = A.loc[(reg, y)]
            return float(r.aff_growth_pct), float(r.aff_share_pct)
        return np.nan, np.nan
    v = [one(r, i) for r, i in df[["region", "i"]].itertuples(index=False)]
    df = df.copy()
    df["aff_g"], df["aff_share"] = [a for a, _ in v], [b for _, b in v]
    return df


def job(arm, survey, lead, seed):
    tag = f"{arm}__{survey}__L{lead}__{seed}"
    f = B.PARTS / f"{tag}.csv"
    if f.exists():
        return str(f)
    import engine_final as EF
    import engine_opt as EO
    import run_qs
    from app.hcw import engine as H
    cfg = ARMS[arm]
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    if any(c in B.NEW for c in cfg["new"]):
        tr, te = B.add_official(tr), B.add_official(te)
    tr, te = add_aff(tr), add_aff(te)
    H.NEW_SIGN.update(B.NEW_SIGNS); H.NEW_SIGN.update(AFF_SIGNS)
    drop, new, force = set(cfg["drop"]), cfg["new"], cfg["force"]
    fs0, sel0 = H.feature_sets, EO.M2._select
    def fs():
        return {k: [c for c in v if c not in drop] + [c for c in new if c not in v] for k, v in fs0().items()}
    def sel(self, d):
        use = list(sel0(self, d))
        for c in force:
            if c in self.cols and c in d and c not in use and d[c].notna().any() and d[c].nunique() > 1:
                use.append(c)
        return use
    H.feature_sets = fs
    if force:
        EO.M2._select = sel
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        H.feature_sets, EO.M2._select = fs0, sel0
    te[["key", "survey", "lead"]].assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cal=r["cal"], cfg=r["cfg"],
                                         selected=";".join(r["model"].use_), n_train=len(tr)).to_csv(f, index=False, lineterminator="\n")
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    leads = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1,2").split(",")]
    J = [(a, s, L, sd) for L in leads for a in ARMS for s in B.SURVEYS for sd in B.SEEDS]
    print(len(J), "jobs", flush=True)
    import inputs_run2 as M
    R = Parallel(n_jobs=int(sys.argv[1]) if len(sys.argv) > 1 else 18, verbose=5)(delayed(M.safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:4], sep="\n", flush=True)
