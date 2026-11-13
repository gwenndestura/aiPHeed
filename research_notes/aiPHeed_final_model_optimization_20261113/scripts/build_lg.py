r"""PROTOCOL_OPT2 (sha f3a6fdf7, locked before this script ran). Builds fold tables with the original cache code (opt_cache.eng, Pipeline,
A4.anchors), optionally adding genuine long-gap pair rows (FNRI2015 withheld from the anchor -> NNS2013 anchor). No test outcome is read.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=.   Usage: python build_lg.py build|r1|fit|pairs_other_folds"""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
OC = RN / "aiPHeed_objective_completion_20261111"; CACHE0 = OC / "cache"; CACHE = HERE / "cache_lg"; EV = HERE / "evidence"
for p in [str(RN / "aiPHeed_study_20261110" / "evidence" / "scripts"), str(RN / "aiPHeed_complete_validation" / "tests"), str(OC / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
          str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]:
    if p not in sys.path:
        sys.path.insert(0, p)
import opt_cache as OCB
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e164 import auto as A4
from app.e166 import nested_source as N
SEEDS = (168, 1, 2, 3, 4)


def make_pairs(S, i, origin):
    rel = M.released(i, Pv.ROUNDS)
    if "FNRI2015" not in rel:
        return pd.DataFrame()
    b0 = S.s8.base
    S.s8.base = b0[b0["survey"] != "FNRI2015"]
    rows = []
    try:
        for s in rel:
            if s in ("NNS2013", "FNRI2015"):
                continue
            d = M.rows_for(S, M8.targets(S.s8, [s]), list(range(1, 9)), origin)
            if d.empty:
                continue
            for h, g in d.groupby("lead"):
                prior = [r for r in M.released(M8.RQ[s] - h, Pv.ROUNDS) if r != "FNRI2015"]
                if not prior:
                    continue
                mu, _ = M.Hier().fit(S, prior).predict(g, g["T"].values)
                rows.append(g.assign(base=mu, e=g["y_true"].values - mu, lg_pair=1))
    finally:
        S.s8.base = b0
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build(survey, lead, pairs, H, Lp, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    P_ = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    npairs = 0
    if pairs:
        X = make_pairs(S, i, Pv.ORIGIN[survey])
        npairs = len(X)
        if npairs:
            P_.tr = pd.concat([P_.tr.assign(lg_pair=0), X], ignore_index=True)
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), Lp, H, S_P)
    tr = N.add_sources(Pv.add_inputs(S, P_.tr), Lp, H, S_P)
    AN = A4.anchors(S, P_, tr, te)
    AN = {a: AN[a] for a in OCB.T.ANC}
    tr, te = OCB.eng(S, tr), OCB.eng(S, te)
    te = te.drop(columns=[c for c in ("y_true", "se_true", "q_true", "p_true", "y", "e") if c in te], errors="ignore")
    return {"tr": tr, "te": te, "AN": AN, "origin": i, "npairs": npairs}


def load(o):
    """Same merges as run_qs.load (local as-of panel + candidate panel)."""
    from app.hcw import engine as Hh
    tr, te, AN = o["tr"], o["te"], o["AN"]
    L = pd.read_parquet(CACHE0 / "local_panel_asof.parquet")
    lc = [c for c in L.columns if c not in ("key", "qi") and c in tr.columns]
    tr = tr.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    cp = pd.read_parquet(CACHE0 / "cand_panel.parquet")
    new = [c for c in Hh.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    return tr, te, AN


def fit(arm, survey, seed):
    import engine_final as EF
    f = HERE / "parts" / f"{arm}__{survey}__1__{seed}.csv"
    if f.exists():
        return str(f)
    o = pickle.load(open(CACHE / f"{arm}_{survey}_1.pkl", "rb"))
    tr, te, AN = load(o)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    te[["key", "survey", "lead"]].assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cfg=r["cfg"], selected=";".join(r["model"].use_),
                                         n_train=len(tr), n_pairs=int(tr.get("lg_pair", pd.Series(0)).sum())).to_csv(f, index=False, lineterminator="\n")
    return str(f)


if __name__ == "__main__":
    cmd = sys.argv[1]
    CACHE.mkdir(exist_ok=True)
    if cmd == "build":
        H, Lp, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
        log = {}
        for arm, pairs, surveys in (("NOPAIR", False, ["ENNS2021"]), ("LG", True, ["ENNS2018", "ENNS2019", "ENNS2021"])):
            for sv in surveys:
                o = build(sv, 1, pairs, H, Lp, S_P)
                pickle.dump(o, open(CACHE / f"{arm}_{sv}_1.pkl", "wb"))
                tr = o["tr"]
                info = {"n_train": len(tr), "n_pairs": o["npairs"], "rounds": tr.groupby("survey").size().to_dict()}
                if o["npairs"]:
                    P = tr[tr["lg_pair"] == 1]
                    info.update({"pair_anchor_rounds": sorted(P["rq_anchor"].unique().tolist()), "nns2013_rq": M8.RQ["NNS2013"],
                                 "pair_gap_q": P["gap_q"].describe().round(2).to_dict(), "pair_targets": P.groupby("survey")["key"].nunique().to_dict(),
                                 "pair_target_release_ok": bool(all(M8.RQ[s] + 6 <= o["origin"] for s in P["survey"].unique())),
                                 "R2_anchor_is_nns2013": bool((P["rq_anchor"] == M8.RQ["NNS2013"]).all())})
                log[f"{arm}_{sv}"] = info
                print(arm, sv, json.dumps(info, default=str), flush=True)
        json.dump(log, open(EV / "LG_build_log.json", "w"), indent=1, default=str)
    elif cmd == "r1":
        a = pickle.load(open(CACHE0 / "ENNS2021_1.pkl", "rb")); b = pickle.load(open(CACHE / "NOPAIR_ENNS2021_1.pkl", "rb"))
        out = {}
        for part in ("tr", "te"):
            x, y = a[part], b[part]
            kk = [c for c in ("key", "survey", "lead", "T") if c in x]
            x, y = x.sort_values(kk).reset_index(drop=True), y.sort_values(kk).reset_index(drop=True)
            num = [c for c in x.columns if c in y.columns and pd.api.types.is_numeric_dtype(x[c])]
            d = (x[num].astype(float) - y[num].astype(float)).abs()
            nanm = (x[num].isna().values != y[num].isna().values).sum()
            out[part] = {"shape_cached": list(x.shape), "shape_rebuilt": list(y.shape), "same_keys": bool((x[kk].values == y[kk].values).all()),
                         "max_abs_diff": float(np.nanmax(d.values)) if len(num) else None, "nan_pattern_mismatch": int(nanm),
                         "cols_only_cached": sorted(set(x.columns) - set(y.columns)), "cols_only_rebuilt": sorted(set(y.columns) - set(x.columns)),
                         "worst_cols": d.max().sort_values(ascending=False).head(5).round(12).to_dict()}
        out["AN_max_abs_diff"] = {k: [float(np.nanmax(np.abs(np.asarray(a["AN"][k][j], float) - np.asarray(b["AN"][k][j], float)))) for j in (0, 1)] for k in a["AN"]}
        json.dump(out, open(EV / "LG_R1_table_repro.json", "w"), indent=1, default=str); print(json.dumps(out, indent=1, default=str))
    elif cmd == "fit":
        from joblib import Parallel, delayed
        jobs = [("NOPAIR", "ENNS2021", 168)] + [("LG", sv, s) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS]
        def safe(*j):
            try:
                return fit(*j)
            except Exception as ex:
                import traceback
                return f"FAIL {j} {ex} {traceback.format_exc()[-1200:]}"
        R = Parallel(n_jobs=16, verbose=5)(delayed(safe)(*j) for j in jobs)
        print("FAILED", [r for r in R if r.startswith("FAIL")])
