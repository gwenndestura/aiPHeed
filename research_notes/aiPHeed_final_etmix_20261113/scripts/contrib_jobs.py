r"""FINAL-ETMIX contributor evidence (Part 4 of the 11-13 ETMIX brief). The model is NOT changed: every fit is FINAL's locked procedure
(engine_final.fit_predict, rate='lin', miss='mind', cw='balanced'), predicted at the two elapsed-time hypotheses g (own-survey gap) and
s (quarters since the latest released round); ETMIX = (p_g + p_s) / 2, exactly as sealed (protocol a365da1f).

kind 'fold'   (22 fold-leads x 5 seeds = 110 fits; the fitted model is identical to the stored FINAL fit):
    - exact TreeSHAP contributions (LightGBM pred_contrib) on the forecast-logit scale, for the g and s test rows
    - WITHHOLD: one meaning-based group, or one selected input, set to missing (MIND fills the training median + flag)
    - PERMUTE : one group (jointly) or one selected input shuffled across the test provinces, 10 repeats
kind 'retrain' (Lead 1 x 3 rounds x 7 groups x 5 seeds = 105 fits): refit with one group removed from the candidate inputs
kind 'retrain_feat' (Lead 1 x 3 rounds x named inputs x seed 168): refit with one input (and its missing flag) removed

No test outcome is read here; outcomes are joined only in contrib_eval.py, on held-out test rows.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python contrib_jobs.py fold|retrain|retrain_feat [--jobs N]"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
ST = RN / "aiPHeed_final_stability_lead_20261113"
sys.path.insert(0, str(RN / "aiPHeed_final_7of7_20261113" / "scripts"))
from ablation import GROUPS, PATHS, group          # noqa: E402  (meaning-based groups of the 7-of-7 study, unchanged)

FOLDS = [(sv, L) for sv, n in (("ENNS2018", 6), ("ENNS2019", 8), ("ENNS2021", 8)) for L in range(1, n + 1)]
SEEDS = (168, 1, 2, 3, 4)
RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}
LAG = 6
NPERM = 10
OUT = HERE / "parts"
base_of = lambda c: c[3:] if c.startswith("mi_") else c


def stale(i, T):
    """s: target quarter minus the reference quarter of the latest round released at the origin (6-quarter release lag)."""
    return T - max(q for q in RQ.values() if q + LAG <= i)


def _setup():
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    from app.hcw import engine as H
    return EF, run_qs, H


def _contrib(model, X):
    """Exact additive contributions of FINAL's rate model on the forecast-logit scale (rate contributions x g/g0); last column = bias."""
    Xu = X[model.use_]
    Xu = Xu.fillna(model.med_) if getattr(model, "impute", False) else Xu
    g = X["gap_q"].values.astype(float) / model.g0_
    return g[:, None] * model.m_.predict(Xu, pred_contrib=True), list(model.use_)


def fold_job(survey, lead, seed):
    f = OUT / f"FOLD__{survey}__{lead}__{seed}.parquet"
    if f.exists():
        return str(f)
    EF, run_qs, H = _setup()
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    s = np.array([stale(i, T) for i, T in zip(te["i"], te["T"])])
    te_s = te.assign(gap_q=s.astype(te["gap_q"].dtype))
    two = bool((s != te["gap_q"].values).any())
    hyps = [("g", te), ("s", te_s)] if two else [("g", te)]
    allc = sorted({c for v in H.feature_sets().values() for c in v if c in te.columns})
    sel = json.load(open(ST / "features_lead" / f"FINALL__{survey}__{lead}__{seed}.json"))["selected"]
    # timing inputs (gap_q, lead) are structural: withholding gap_q would make the RATE multiplier undefined, so they are not perturbed
    sel_base = sorted({base_of(c) for c in sel if base_of(c) in te.columns and group(base_of(c)) != "timing"})
    rng = np.random.default_rng(1000 * lead + seed)
    blocks = []
    for h, d in hyps:
        blocks.append(d.assign(hyp=h, kind="base", what="none", rep=0))
        for g_ in GROUPS:
            cols = [c for c in allc if group(c) == g_]
            blocks.append(d.assign(**{c: np.nan for c in cols}, hyp=h, kind="withhold_group", what=g_, rep=0))
        for c in sel_base:
            blocks.append(d.assign(**{c: np.nan}, hyp=h, kind="withhold_input", what=c, rep=0))
    for rep in range(NPERM):
        perm = rng.permutation(len(te))
        for h, d in hyps:
            for g_ in GROUPS:
                cols = [c for c in allc if group(c) == g_]
                blocks.append(d.assign(**{c: d[c].values[perm] for c in cols}, hyp=h, kind="permute_group", what=g_, rep=rep))
            for c in sel_base:
                pc = rng.permutation(len(te))
                blocks.append(d.assign(**{c: d[c].values[pc]}, hyp=h, kind="permute_input", what=c, rep=rep))
    T = pd.concat(blocks, ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), len(blocks))) for a in AN}
    r = EF.fit_predict(tr, T, AN2, seed, rate="lin", miss="mind", cw="balanced")
    res = T[["key", "survey", "lead", "hyp", "kind", "what", "rep", "gap_q"]].assign(seed=seed, p=r["p"], mu=r["mu"])
    # exact TreeSHAP on the unperturbed rows of each hypothesis (MIND flags built as the engine builds them)
    m = r["model"]
    sh = []
    for h, d in hyps:
        Xd = d.copy()
        for c in m.use_:
            if c.startswith("mi_") and c not in Xd:
                Xd[c] = Xd[base_of(c)].isna().astype(float)
        C, cols = _contrib(m, Xd)
        S = pd.DataFrame(C[:, :-1], columns=cols).assign(bias=C[:, -1], key=d["key"].values, survey=survey, lead=lead, seed=seed, hyp=h,
                                                         anchor=np.asarray(AN[r["cfg"].split("|")[0]][1], float) if r["cfg"].split("|")[0] in AN else np.nan)
        sh.append(S.melt(id_vars=["key", "survey", "lead", "seed", "hyp", "anchor"], var_name="input", value_name="contrib"))
    SH = pd.concat(sh, ignore_index=True)
    gain = dict(zip(m.use_, m.m_.booster_.feature_importance("gain")))
    split = dict(zip(m.use_, m.m_.booster_.feature_importance("split")))
    meta = {"survey": survey, "lead": lead, "seed": seed, "cfg": r["cfg"], "selected": list(m.use_), "gain": {k: float(v) for k, v in gain.items()},
            "split": {k: int(v) for k, v in split.items()}, "two_hypotheses": two, "selected_matches_stored_FINAL_fit": list(m.use_) == list(sel),
            "train_gap_equals_staleness": bool((np.array([stale(i, T_) for i, T_ in zip(tr["i"], tr["T"])]) == tr["gap_q"].values).all())}
    OUT.mkdir(exist_ok=True)
    SH.to_parquet(OUT / f"SHAP__{survey}__{lead}__{seed}.parquet", index=False)
    (OUT / f"META__{survey}__{lead}__{seed}.json").write_text(json.dumps(meta, indent=1))
    res.to_parquet(f.with_suffix(".tmp"), index=False)
    f.with_suffix(".tmp").replace(f)
    return str(f)


def retrain_job(survey, lead, seed, drop, kind):
    f = OUT / f"{kind.upper()}__{survey}__{lead}__{seed}__{drop}.csv"
    if f.exists():
        return str(f)
    EF, run_qs, H = _setup()
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    s = np.array([stale(i, T) for i, T in zip(te["i"], te["T"])])
    T = pd.concat([te.assign(hyp="g"), te.assign(gap_q=s.astype(te["gap_q"].dtype), hyp="s")], ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), 2)) for a in AN}
    orig = H.feature_sets
    keep = (lambda c: group(c) != drop) if kind == "retrain" else (lambda c: c != drop)
    H.feature_sets = lambda: {k: [c for c in v if keep(c)] for k, v in orig().items()}
    try:
        r = EF.fit_predict(tr, T, AN2, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        H.feature_sets = orig
    out = T[["key", "survey", "lead", "hyp"]].assign(seed=seed, dropped=drop, kind=kind, p=r["p"], cfg=r["cfg"], selected=";".join(r["model"].use_))
    out.to_csv(f.with_suffix(".tmp"), index=False, lineterminator="\n")
    f.with_suffix(".tmp").replace(f)
    return str(f)


def safe(fn, *a):
    try:
        return fn(*a)
    except Exception as ex:
        import traceback
        return f"FAIL {a}: {ex} {traceback.format_exc()[-1500:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["fold", "retrain", "retrain_feat"])
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--features", default="hh_grdp_rel,income_rel,cpi_food_rel_nat,p_poverty,l_rice_rel,c_agri_yoy")
    a = ap.parse_args()
    if a.kind == "fold":
        J = [(fold_job, sv, L, s) for sv, L in FOLDS for s in SEEDS]
    elif a.kind == "retrain":
        J = [(retrain_job, sv, 1, s, g, "retrain") for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for g in GROUPS for s in SEEDS]
    else:
        J = [(retrain_job, sv, 1, 168, c, "retrain_feat") for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for c in a.features.split(",")]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if str(x).startswith("FAIL")]
    print("FAILED", len(bad), *bad[:5], sep="\n", flush=True)
