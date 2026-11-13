r"""FINAL (RATE + MIND) exactly as stored (engine_final.fit_predict, rate='lin', miss='mind', cw='balanced') at every fold-lead the
cached walk-forward folds support: ENNS2018 leads 1-6, ENNS2019 1-8, ENNS2021 1-8, seeds 168/1/2/3/4. Saves per fit the
forecasts, the training-chosen threshold and calibration, the selected inputs and their LightGBM gain importance.
No test outcome is read. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python run_lead.py [--jobs N]"""
import argparse, json, pickle, sys
from pathlib import Path
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
SEEDS = (168, 1, 2, 3, 4)
FOLDS = [(sv, L) for sv, n in (("ENNS2018", 6), ("ENNS2019", 8), ("ENNS2021", 8)) for L in range(1, n + 1)]


def job(survey, lead, seed, arm="FINALL", patch=None):
    f = HERE / "parts_lead" / f"{arm}__{survey}__{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    tr, te, AN = run_qs.load(survey, lead)
    origin = pickle.load(open(CACHE / f"{survey}_{lead}.pkl", "rb"))["origin"]
    old = EF.M4
    if patch is not None:
        EF.M4 = patch(EF)
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        EF.M4 = old
    m = r["model"]
    imp = dict(zip(m.use_, [float(x) for x in m.m_.booster_.feature_importance("gain")]))
    json.dump({"survey": survey, "lead": lead, "seed": seed, "origin": int(origin), "cfg": r["cfg"], "selected": list(m.use_), "gain": imp,
               "train_rows": int(len(tr)), "train_rounds": sorted(tr["survey"].unique()), "train_gaps": sorted(int(g) for g in tr["gap_q"].unique()),
               "test_gaps": sorted(int(g) for g in te["gap_q"].unique()), "train_high_share": float((tr["y_true"] >= 0).mean())},
              open(HERE / "features_lead" / f"{arm}__{survey}__{lead}__{seed}.json", "w"))
    out = te.reset_index(drop=True)[["key", "survey", "lead", "T", "i", "gap_q"]].assign(arm=arm, seed=seed, origin=origin, p=r["p"], mu=r["mu"], cal=r["cal"],
                                                                                         thr=r["thr"], inner_brier=r["inner_brier"], cfg=r["cfg"])
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
    ap.add_argument("--jobs", type=int, default=20)
    a = ap.parse_args()
    J = [(sv, L, s) for sv, L in FOLDS for s in SEEDS]
    J.sort(key=lambda j: -j[1])                     # long leads first (not yet scored anywhere)
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
