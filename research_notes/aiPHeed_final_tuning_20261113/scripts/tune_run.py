r"""PROTOCOL_TUNE (sha 1f59459a, locked before this script ran): fits arms A1-A5 (+ training-round drops). Engine unchanged; all choices inside
training data. No test outcome is read. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.   Usage: python tune_run.py [jobs]"""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; PARTS = HERE / "parts"; EV = HERE / "evidence"
for p in [str(RN / "aiPHeed_final_model_optimization_20261113" / "scripts"), str(RN / "aiPHeed_study_20261110" / "evidence" / "scripts"),
          str(RN / "aiPHeed_complete_validation" / "tests"), str(RN / "aiPHeed_objective_completion_20261111" / "scripts"),
          str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"), str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"),
          str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]:
    if p not in sys.path:
        sys.path.append(p)
lg = lambda p: np.log(p / (1 - p))
NAT = {"NNS2013": 0.2432467540453589, "FNRI2015": lg(.538), "ENNS2018": lg(.416), "ENNS2019": lg(.469), "ENNS2021": lg(.410)}
RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}; INV = {v: k for k, v in RQ.items()}
S = ["income_rel", "p_poverty", "p_poverty_gap", "hh_grdp_rel", "p_subsistence"]
SEEDS = (168, 1, 2, 3, 4); CWS = ("none", "sqrt", "balanced")


def load_fold(survey, drop=None):
    if survey == "ENNS2021":
        import build_lg as B
        tr, te, AN = B.load(pickle.load(open(RN / "aiPHeed_final_model_optimization_20261113" / "cache_lg" / "LG_ENNS2021_1.pkl", "rb")))
    else:
        import run_qs
        tr, te, AN = run_qs.load(survey, 1)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    if drop:
        keep = (tr.survey != drop).values
        tr = tr[keep].reset_index(drop=True); AN = {a: (np.asarray(v[0])[keep], v[1]) for a, v in AN.items()}
    return tr, te, AN


def latest_nat(i):
    rel = [r for r, q in RQ.items() if q + 6 <= int(i)]
    return NAT[max(rel, key=RQ.get)]


def sanc(tr, te):
    """Structural-attractor anchor (ATTR, PROTOCOL_ATTR inputs) on the absolute logit scale; training rows cross-fitted by region."""
    from sklearn.linear_model import BayesianRidge
    from sklearn.model_selection import GroupKFold
    for d in (tr, te):
        d["z_a"] = d.y_anchor.values - d.rq_anchor.map(INV).map(NAT).values
    base = tr[(tr.lead == 1) & (tr.get("lg_pair", pd.Series(0, index=tr.index)).fillna(0) == 0)]
    def fit(rows):
        zT = rows.y_true - rows.survey.map(NAT)
        med = rows[S].median(); X = rows[["z_a"] + S].fillna(med); mu_, sd_ = X.mean(), X.std().replace(0, 1)
        br = BayesianRidge().fit(((X - mu_) / sd_).values, zT.values, sample_weight=(1 / (rows.se_true ** 2 + 0.05)).values)
        return lambda d: br.predict(((d[["z_a"] + S].fillna(med) - mu_) / sd_).values), br.coef_
    a_tr = np.full(len(tr), np.nan)
    regs = base.region.unique(); gk = GroupKFold(min(5, len(regs)))
    for _, hold in gk.split(base, groups=base.region):
        hr = set(base.region.iloc[hold]); f, _ = fit(base[~base.region.isin(hr)])
        m = tr.region.isin(hr).values; a_tr[m] = f(tr[m])
    f_all, coef = fit(base)
    a_te = f_all(te)
    L_tr = np.array([latest_nat(i) for i in tr.i]); L_te = np.array([latest_nat(i) for i in te.i])
    return a_tr + L_tr, a_te + L_te, {"coef": np.round(coef, 4).tolist(), "n_attr_train": len(base), "nan_train_anchor": int(np.isnan(a_tr).sum())}


def job(arm, survey, seed, cw, drop=None):
    tag = f"{arm}__{survey}__{seed}__{cw}" + (f"__drop_{drop}" if drop else "")
    f = PARTS / f"{tag}.csv"
    if f.exists():
        return str(f)
    import engine_final as EF
    from app.hcw import engine as H
    tr, te, AN = load_fold(survey, drop)
    info = {}
    kw = dict(rate="lin", miss="mind", cw=cw, hpw=arm in ("A1", "A5"))
    old = H.ANC
    try:
        if arm in ("A4", "A5"):
            a_tr, a_te, info = sanc(tr, te)
            a_tr = np.where(np.isnan(a_tr), np.asarray(AN["H"][0]), a_tr)
            AN = dict(AN); AN["SANC"] = (a_tr, a_te); H.ANC = tuple(old) + ("SANC",)
        r = EF.fit_predict(tr, te, AN, seed, **kw)
    finally:
        H.ANC = old
    te[["key", "survey", "lead"]].assign(arm=arm, seed=seed, cw=cw, drop=drop or "", p=r["p"], mu=r["mu"], thr=r["thr"], inner_brier=r["inner_brier"],
                                         cal=r["cal"], cfg=r["cfg"], selected=";".join(r["model"].use_), n_train=len(tr),
                                         sanc_info=json.dumps(info)).to_csv(f, index=False, lineterminator="\n")
    return str(f)


def safe(*a):
    try:
        return job(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    PARTS.mkdir(exist_ok=True)
    SV = ("ENNS2018", "ENNS2019", "ENNS2021")
    J = [("A1", s, sd, "balanced") for s in SV for sd in SEEDS] + [("A2", s, sd, c) for s in SV for sd in SEEDS for c in CWS] + \
        [("A4", s, sd, "balanced") for s in SV for sd in SEEDS] + [("A5", s, sd, c) for s in SV for sd in SEEDS for c in CWS] + \
        [("A5", "ENNS2021", 168, c, d) for c in CWS for d in ("FNRI2015", "ENNS2018", "ENNS2019")] + \
        [("A2", "ENNS2021", 168, "balanced", d) for d in ("FNRI2015", "ENNS2018", "ENNS2019")]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=int(sys.argv[1]) if len(sys.argv) > 1 else 16, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:4], sep="\n", flush=True)
