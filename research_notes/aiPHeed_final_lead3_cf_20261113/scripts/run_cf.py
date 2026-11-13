r"""PROTOCOL_CF (sha 054239a1): FINAL exactly as stored (engine_final.fit_predict, rate='lin', miss='mind', cw='balanced') on the same
cached walk-forward folds as run_lead.py, with ONE change: local price inputs missing at quarter i take the province's quarter i-1 value
(one quarter at most). No test outcome is read. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python run_cf.py [--jobs N]"""
import argparse, json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
SEEDS = (168, 1, 2, 3, 4)
FOLDS = [(sv, L) for sv, n in (("ENNS2018", 6), ("ENNS2019", 8), ("ENNS2021", 8)) for L in range(1, n + 1)]
CF_COLS = ["l_fg_yoy", "l_fg_rel", "l_terms", "l_rice_yoy", "l_rice_rel", "l_fish_yoy"]


def cf_panel():
    L = pd.read_parquet(CACHE / "local_panel_asof.parquet").sort_values(["key", "qi"]).reset_index(drop=True)
    prev = L.groupby("key")[CF_COLS].shift(1)
    contiguous = (L["qi"] - L.groupby("key")["qi"].shift(1)) == 1
    filled = {}
    for c in CF_COLS:
        m = L[c].isna() & prev[c].notna() & contiguous
        L.loc[m, c] = prev.loc[m, c]
        filled[c] = int(m.sum())
    return L, filled


def load_cf(survey, lead, L):
    from app.hcw import engine as H
    o = pickle.load(open(CACHE / f"{survey}_{lead}.pkl", "rb"))
    tr, te, AN = o["tr"], o["te"], o["AN"]
    lc = [c for c in L.columns if c not in ("key", "qi") and c in tr.columns]
    tr = tr.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.drop(columns=lc).merge(L[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    cp = pd.read_parquet(CACHE / "cand_panel.parquet")
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    return tr, te, AN


def job(survey, lead, seed):
    f = HERE / "parts" / f"CF__{survey}__{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    L, _ = cf_panel()
    tr, te, AN = load_cf(survey, lead, L)
    origin = pickle.load(open(CACHE / f"{survey}_{lead}.pkl", "rb"))["origin"]
    r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    m = r["model"]
    json.dump({"survey": survey, "lead": lead, "seed": seed, "origin": int(origin), "cfg": r["cfg"], "selected": list(m.use_),
               "test_missing_local": int(te[CF_COLS].isna().sum().sum()), "train_missing_local": int(tr[CF_COLS].isna().sum().sum())},
              open(HERE / "features" / f"CF__{survey}__{lead}__{seed}.json", "w"))
    out = te.reset_index(drop=True)[["key", "survey", "lead", "gap_q"]].assign(seed=seed, origin=origin, p=r["p"], mu=r["mu"], cfg=r["cfg"])
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
    _, filled = cf_panel(); print("cells filled by CF:", filled, flush=True)
    json.dump(filled, open(HERE / "evidence" / "CF_cells_filled.json", "w"), indent=1)
    J = [(sv, L, s) for sv, L in FOLDS for s in SEEDS]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
