r"""PROTOCOL_DRM addendum 1 (sha 85cc295f, locked before this script ran): LG-D = FINAL-LG + drm_disp (D3 at each row's issue quarter).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.   Usage: python lgd_run.py fit|score"""
import glob, json, pickle, re, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"; PARTS = HERE / "parts"
for p in [str(RN / "aiPHeed_final_model_optimization_20261113" / "scripts"), str(RN / "aiPHeed_study_20261110" / "evidence" / "scripts"),
          str(RN / "aiPHeed_complete_validation" / "tests"), str(RN / "aiPHeed_objective_completion_20261111" / "scripts"),
          str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"), str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"),
          str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]:
    if p not in sys.path:
        sys.path.append(p)
nk = lambda s: re.sub(r"[^a-z]", "", str(s).lower().replace("province", "").replace("city of ", ""))
SEEDS = (168, 1, 2, 3, 4)


def d3_table():
    V = pd.read_csv(EV / "DROMIC_LEADQ_province_values.csv")
    V = V[(V.family == "hydromet") & V.measure.isin(["disp_in", "disp_out"])]
    s = V.groupby(["window", "province"]).value.sum()
    pop = pd.read_csv("C:/Users/admin/aipheed_hcw/backend/data/e137/raw/psa/population_2010_2024.csv", dtype=str, encoding="latin-1")
    pop = pop[pop.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    pop = pd.DataFrame({"k": pop.iloc[:, 0].str.replace("*", "", regex=False).map(nk), "p": pd.to_numeric(pop.filter(like="2015)").iloc[:, 0], errors="coerce")})
    pop = pop.drop_duplicates("k").set_index("k").p
    pop["maguindanao"] = pop.get("maguindanaodelnorte", np.nan) + pop.get("maguindanaodelsur", np.nan) - 299438.0
    alias = {"northcotabato": "cotabato", "compostelavalley": "davaodeoro", "westernsamar": "samar"}
    P = lambda k: pop.get(nk(k), pop.get(alias.get(nk(k), ""), np.nan))
    return s, P


def add_d3(d, s, P, has):
    vals = []
    for k, i, h in zip(d.key, d.i, has):
        if not h:
            vals.append(np.nan); continue
        v = float(s.get((f"Q{int(i)}", k), 0.0))
        vals.append(float(np.log1p(v / (P(k) / 1000.0))))
    return d.assign(drm_disp=vals)


def load(survey):
    import build_lg as B
    if survey == "ENNS2021":
        tr, te, AN = B.load(pickle.load(open(RN / "aiPHeed_final_model_optimization_20261113" / "cache_lg" / "LG_ENNS2021_1.pkl", "rb")))
    else:
        import run_qs
        tr, te, AN = run_qs.load(survey, 1)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    s, P = d3_table()
    pair = tr.get("lg_pair", pd.Series(0, index=tr.index)).fillna(0).values == 1
    has_tr = tr.survey.isin(["ENNS2018", "ENNS2019"]).values & ~pair & tr.i.between(8066, 8077).values
    tr, te = add_d3(tr, s, P, has_tr), add_d3(te, s, P, np.ones(len(te), bool))
    return tr, te, AN


def job(survey, seed, drop=None):
    f = PARTS / (f"LGD__{survey}__{seed}" + (f"__drop_{drop}" if drop else "") + ".csv")
    if f.exists():
        return str(f)
    import engine_final as EF
    from app.hcw import engine as H
    tr, te, AN = load(survey)
    if drop:
        keep = (tr.survey != drop).values
        tr = tr[keep].reset_index(drop=True); AN = {a: (np.asarray(v[0])[keep], v[1]) for a, v in AN.items()}
    orig, osign = H.feature_sets, dict(H.NEW_SIGN)
    H.feature_sets = lambda: {k: list(v) + ["drm_disp"] for k, v in orig().items()}
    H.NEW_SIGN["drm_disp"] = 1
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        H.feature_sets = orig; H.NEW_SIGN.clear(); H.NEW_SIGN.update(osign)
    use = r["model"].use_
    te[["key", "survey", "lead", "drm_disp"]].assign(seed=seed, drop=drop or "", p=r["p"], mu=r["mu"], cfg=r["cfg"], selected=";".join(use),
                                                     drm_selected=int(any(c in ("drm_disp", "mi_drm_disp") for c in use)),
                                                     train_d3_nonmissing=int(tr.drm_disp.notna().sum())).to_csv(f, index=False, lineterminator="\n")
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1200:]}"


if __name__ == "__main__":
    PARTS.mkdir(exist_ok=True)
    if sys.argv[1] == "fit":
        from joblib import Parallel, delayed
        J = [("ENNS2021", s) for s in SEEDS] + [("ENNS2021", 168, d) for d in ("FNRI2015", "ENNS2018", "ENNS2019")] + [("ENNS2018", 168), ("ENNS2019", 168)]
        R = Parallel(n_jobs=10, verbose=5)(delayed(safe)(*j) for j in J)
        print("FAILED", [x for x in R if x.startswith("FAIL")])
    else:
        tr, te, _ = load("ENNS2021")
        print("train D3 non-missing", int(tr.drm_disp.notna().sum()), "of", len(tr), "; test D3", te[["key", "drm_disp"]].round(3).to_dict("records")[:5])
