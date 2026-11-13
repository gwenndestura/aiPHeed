r"""PROTOCOL_POVVULN (sha bb63c891, locked before this script ran): arms P0, P1-P3, P1F-P3F on FINAL's folds.
Same engine and folds as inputs_run.py. Poverty rounds from backend/data/hcw_official/raw/psa_poverty_by_province.csv (branch).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.   Usage: python povvuln_run.py [jobs] [leads]   |   python povvuln_run.py check"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inputs_run as B                                                        # noqa: E402

POV_FILE = Path(r"C:\Users\admin\aipheed_fmc\backend\data\hcw_official\raw\psa_poverty_by_province.csv")
ROUNDS = (2006, 2009, 2012, 2015, 2018, 2021, 2023)
POV = ["pv_fam", "pv_pop", "sb_fam", "sb_pop", "d_pv_pop", "d_pv_fam", "p_poverty_gap"]
VUL = ["p_density_c", "p_popgrowth"]
OLD = ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density"]           # FINAL's own poverty/vulnerability columns
SIGNS = {"pv_fam": 1, "pv_pop": 1, "sb_fam": 1, "sb_pop": 1, "d_pv_pop": 1, "d_pv_fam": 1, "p_density_c": 0, "p_popgrowth": 0}
ARMS = {"P0": ([], []), "P1": (POV, []), "P2": (VUL, []), "P3": (POV + VUL, []),
        "P1F": (POV, POV), "P2F": (VUL, VUL), "P3F": (POV + VUL, POV + VUL)}


def _logit(pct):
    p = min(max(float(pct) / 100.0, 0.0005), 0.9995)
    return float(np.log(p / (1 - p)))


@lru_cache(maxsize=None)
def table():
    from app.e137 import features as F
    d = pd.read_csv(POV_FILE)
    d = d[d.level == "province_or_district"].copy()
    d["k"] = d["name"].map(F.nospace)
    return {(r.indicator, r.k, int(r.year)): r.value_pct for r in d.itertuples() if pd.notna(r.value_pct)}


def pov_row(key, i):
    from app.e137 import features as F
    T, k, d = table(), F.nospace(key), B.issue_date(i)
    rel = [y for y in ROUNDS if pd.Timestamp(year=y + 2, month=1, day=1) <= d]
    out = {c: np.nan for c in POV if c != "p_poverty_gap"}
    for ind, col in (("pov_fam", "pv_fam"), ("pov_pop", "pv_pop"), ("sub_fam", "sb_fam"), ("sub_pop", "sb_pop")):
        have = [y for y in rel if (ind, k, y) in T]
        if have:
            out[col] = _logit(T[(ind, k, have[-1])])
            if col in ("pv_fam", "pv_pop") and len(have) >= 2:
                out["d_" + col] = _logit(T[(ind, k, have[-1])]) - _logit(T[(ind, k, have[-2])])
    return out


def add_pov(df):
    rows = {(k, i): pov_row(k, i) for k, i in df[["key", "i"]].drop_duplicates().itertuples(index=False)}
    add = pd.DataFrame([rows[(k, i)] for k, i in df[["key", "i"]].itertuples(index=False)], index=df.index)
    return pd.concat([df.drop(columns=[c for c in add.columns if c in df]), add], axis=1)


def job(arm, survey, lead, seed):
    tag = f"{arm}__{survey}__L{lead}__{seed}"
    f = B.PARTS / f"{tag}.csv"
    if f.exists():
        return str(f)
    import engine_final as EF
    import engine_opt as EO
    import run_qs
    from app.hcw import engine as H
    new, force = ARMS[arm]
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    tr, te = add_pov(B.add_official(tr)), add_pov(B.add_official(te))        # p_density_c, p_popgrowth from inputs_run (latest released census)
    H.NEW_SIGN.update(SIGNS)
    drop = set(OLD) - set(new)                                              # p_poverty_gap stays when POVERTY is added
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


def check():
    """Coverage and redundancy (Spearman) of the poverty/vulnerability features on each fold's training rows."""
    import run_qs
    out = []
    for s in B.SURVEYS:
        tr, te, _ = run_qs.load(s, 1)
        a = add_pov(B.add_official(tr)); b = add_pov(B.add_official(te))
        cols = [c for c in POV + VUL + ["p_poverty", "p_subsistence", "p_density"] if c in a]
        print(s, "train coverage", {c: round(float(a[c].notna().mean()), 2) for c in cols})
        print(s, "test  coverage", {c: round(float(b[c].notna().mean()), 2) for c in cols})
        print(s, "distinct", {c: int(a[c].nunique()) for c in cols})
        R = a[cols].corr(method="spearman").round(3)
        R.insert(0, "fold", s); out.append(R)
        chk = a[["p_poverty", "pv_pop"]].dropna()
        print(s, "p_poverty vs pv_pop (same base) max |diff|", float((chk.p_poverty - chk.pv_pop).abs().max()) if len(chk) else None)
    pd.concat(out).to_csv(B.HERE / "evidence" / "POVVULN_spearman.csv", lineterminator="\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check(); sys.exit(0)
    leads = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1,2").split(",")]
    J = [(a, s, L, sd) for L in leads for a in ARMS for s in B.SURVEYS for sd in B.SEEDS]
    print(len(J), "jobs", flush=True)
    import povvuln_run as M
    R = Parallel(n_jobs=int(sys.argv[1]) if len(sys.argv) > 1 else 18, verbose=5)(delayed(M.safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:4], sep="\n", flush=True)
