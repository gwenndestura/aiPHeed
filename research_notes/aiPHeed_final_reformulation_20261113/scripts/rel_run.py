r"""PROTOCOL_REL (sha 4b740e48, locked before this script ran). Fits REL-LGBM (FINAL engine, relative target/anchors), REL-HB, REL-P on FINAL's
cached Lead-1 tables. No test outcome is read (test tables carry no y). Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.
Usage: python rel_run.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; PARTS = HERE / "parts"; EV = HERE / "evidence"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
for p in PATHS:
    if p not in sys.path:
        sys.path.insert(0, p)
SEEDS = (168, 1, 2, 3, 4); SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
lg = lambda p: float(np.log(p / (1 - p)))
NAT_PCT = {"FNRI2015": 53.8, "ENNS2018": 41.6, "ENNS2019": 46.9, "ENNS2021": 41.0}


def national(l13_mode="est"):
    import run_qs
    tr, _, _ = run_qs.load("ENNS2021", 1)
    b = tr[tr.survey == "FNRI2015"].drop_duplicates("key")
    N = {k: lg(v / 100) for k, v in NAT_PCT.items()}
    N["NNS2013"] = float(b.y_anchor.mean() - (b.y_true.mean() - N["FNRI2015"])) if l13_mode == "est" else N["FNRI2015"]
    return N


def cross_sections(tr, N):
    """Anchor-round cross-sections (all 78 provinces of 2013 and 2015; both released before every origin)."""
    b = tr[tr.survey == "FNRI2015"].drop_duplicates("key")
    cs = {"FNRI2015": pd.DataFrame({"key": b.key, "region": b.region, "z": b.y_true - N["FNRI2015"], "se": b.se_true}),
          "NNS2013": pd.DataFrame({"key": b.key, "region": b.region, "z": b.y_anchor - N["NNS2013"], "se": b.se_anchor})}
    out = {}
    for r, c in cs.items():
        tau2 = max(float(c.z.var() - (c.se ** 2).mean()), 0.01)
        out[r] = (c.groupby("region").z.mean().to_dict(), float(c.z.mean()), tau2)
    return out


def rel_anchors(d, N, CS):
    from app.e148 import model as M8
    inv = {v: k for k, v in M8.RQ.items()}
    rnd = d.rq_anchor.map(inv)
    za = d.y_anchor.values - rnd.map(N).values
    mreg = np.array([CS[r][0].get(g, CS[r][1]) for r, g in zip(rnd, d.region)])
    tau2 = rnd.map(lambda r: CS[r][2]).values
    lam = tau2 / (tau2 + d.se_anchor.values ** 2)
    return za, mreg + lam * (za - mreg), mreg, rnd


def tables(survey, N, drop=None):
    import run_qs
    tr, te, _ = run_qs.load(survey, 1)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    if drop:
        tr = tr[tr.survey != drop].reset_index(drop=True)
    full_tr, _, _ = run_qs.load("ENNS2021", 1)          # anchor-round cross-sections only (2013/2015 values; released at every origin)
    CS = cross_sections(full_tr, N)
    tr = tr.assign(y_true=tr.y_true.values - tr.survey.map(N).values)
    tr = tr.assign(q_true=norm.cdf(tr.y_true / tr.se_true.clip(lower=1e-3)))
    a_tr, a_te = rel_anchors(tr, N, CS), rel_anchors(te, N, CS)
    AN = {"H": (a_tr[0], a_te[0]), "OH": (a_tr[1], a_te[1]), "RSS": (a_tr[2], a_te[2])}
    return tr, te, AN, a_tr[3], a_te[3]


def stat_models(survey, N, drop=None):
    from app.e164 import auto as A4
    tr, te, AN, _, _ = tables(survey, N, drop)
    y, w, g_tr, g_te = tr.y_true.values, 1.0 / (tr.se_true.values ** 2 + 0.05), tr.gap_q.values.astype(float), te.gap_q.values.astype(float)
    out = []
    zP_tr, zP_te = AN["H"]
    sd, _ = A4.scale(y - zP_tr, g_tr, g_te)
    out.append(te[["key", "survey", "lead"]].assign(model="REL_P", mu=zP_te, p=norm.cdf(zP_te / sd)))
    zE_tr, zE_te = AN["OH"]
    X = np.column_stack([np.ones(len(y)), zE_tr]) * np.sqrt(w)[:, None]
    ab = np.linalg.lstsq(X, y * np.sqrt(w), rcond=None)[0]
    sd, _ = A4.scale(y - (ab[0] + ab[1] * zE_tr), g_tr, g_te)
    mu = ab[0] + ab[1] * zE_te
    out.append(te[["key", "survey", "lead"]].assign(model="REL_HB", mu=mu, p=norm.cdf(mu / sd), hb_a=ab[0], hb_b=ab[1]))
    return pd.concat(out)


def lgbm(tag, survey, seed, l13="est", drop=None):
    f = PARTS / f"{tag}__{survey}__{seed}.csv"
    if f.exists():
        return str(f)
    import engine_final as EF
    N = national(l13)
    tr, te, AN, _, _ = tables(survey, N, drop)
    r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    te[["key", "survey", "lead"]].assign(model=tag, seed=seed, mu=r["mu"], p=r["p"], cfg=r["cfg"], selected=";".join(r["model"].use_),
                                         n_train=len(tr), train_high_share=float((tr.y_true >= 0).mean())).to_csv(f, index=False, lineterminator="\n")
    return str(f)


def safe(*a):
    try:
        return lgbm(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    from joblib import Parallel, delayed
    PARTS.mkdir(exist_ok=True)
    N = national(); N13 = national("2015")
    json.dump({"national_logit": N, "national_pct": {k: round(100 / (1 + np.exp(-v)), 3) for k, v in N.items()},
               "nns2013_sensitivity_logit": N13["NNS2013"]}, open(EV / "REL_national_reference.json", "w"), indent=1)
    S = []
    for sv in SURVEYS:
        S.append(stat_models(sv, N).assign(variant="main"))
        S.append(stat_models(sv, N13).assign(variant="l13_2015"))
    for d in ("FNRI2015", "ENNS2018", "ENNS2019"):
        S.append(stat_models("ENNS2021", N, drop=d).assign(variant=f"drop_{d}"))
    pd.concat(S).to_csv(PARTS / "REL_STAT_all.csv", index=False, lineterminator="\n")
    J = [("REL_LGBM", sv, s) for sv in SURVEYS for s in SEEDS] + [("REL_LGBM_L13", sv, 168, "2015") for sv in SURVEYS] + \
        [(f"REL_LGBM_DROP_{d}", "ENNS2021", 168, "est", d) for d in ("FNRI2015", "ENNS2018", "ENNS2019")]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=18, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:4], sep="\n", flush=True)
