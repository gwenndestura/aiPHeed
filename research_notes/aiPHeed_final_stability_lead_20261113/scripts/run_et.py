r"""FINAL_IMPROVEMENT_PROTOCOL (sha c5e76bd5): FINAL-ET. Training rows and fitting are FINAL's, unchanged; test rows get the elapsed
time s = target quarter - reference quarter of the latest survey round released at the origin in place of gap_q (RATE multiplier,
spread, gap_q input). Only ENNS2021 Leads 1-6 have s != gap_q in test rows; elsewhere FINAL-ET == FINAL exactly.
Jobs:
  main  : ENNS2021 L1-6 x 5 seeds; each fit predicts the original rows (variant FINAL) and the s rows (variant ET);
          ENNS2021 L1 seed 168 also predicts ET rows with one input group missing (Rule 7e)
  pert  : Lead 1, seed 168, each round, 3 refits on a random 90 % of training provinces (Rule 7g, reported only);
          each predicts FINAL and ET rows
No test outcome is read. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python run_et.py [--jobs N]"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_lead as RL                      # noqa: E402  (paths, seeds)

RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}
LAG = 6
GROUPS = ("market", "climate", "employment", "poverty", "agri_fish", "news_aggregate")


def stale(i, T):
    return T - max(q for q in RQ.values() if q + LAG <= i)


def group_of(c):
    sys.path.insert(0, str(HERE.parent / "aiPHeed_final_standalone_20261113" / "scripts"))
    import rerun_final
    return rerun_final.group_of(c)


def job(kind, survey, lead, seed, sub=0):
    tag = f"ET__{survey}__{lead}__{seed}" if kind == "main" else f"PERT__{survey}__{lead}__{seed}__sub{sub}"
    f = HERE / "parts_et" / f"{tag}.csv"
    if f.exists():
        return str(f)
    for p in RL.PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    from app.hcw import engine as H
    tr, te, AN = run_qs.load(survey, lead)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    if kind == "pert":
        keys = np.array(sorted(tr["key"].unique()))
        keep = set(np.random.default_rng(sub).choice(keys, int(round(0.9 * len(keys))), replace=False))
        m = tr["key"].isin(keep).values
        tr = tr[m].reset_index(drop=True)
        AN = {a: (np.asarray(AN[a][0])[m], AN[a][1]) for a in AN}
    s = np.array([stale(i, T) for i, T in zip(te["i"], te["T"])])
    et = te.assign(gap_q=s.astype(te["gap_q"].dtype))
    blocks = [te.assign(variant="FINAL"), et.assign(variant="ET")]
    if kind == "main" and lead == 1 and seed == 168:
        allc = sorted({c for v in H.feature_sets().values() for c in v if c in te.columns})
        for g in GROUPS:
            blocks.append(et.assign(**{c: np.nan for c in allc if group_of(c) == g}, variant=f"ET_missing_{g}"))
    T = pd.concat(blocks, ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), len(blocks))) for a in AN}
    r = EF.fit_predict(tr, T, AN2, seed, rate="lin", miss="mind", cw="balanced")
    out = T[["key", "survey", "lead", "T", "i", "gap_q", "variant"]].assign(seed=seed, sub=sub, p=r["p"], mu=r["mu"], thr=r["thr"], cfg=r["cfg"])
    (HERE / "parts_et").mkdir(exist_ok=True)
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
    J = [("main", "ENNS2021", L, s) for L in range(1, 7) for s in RL.SEEDS]
    J += [("pert", sv, 1, 168, k) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for k in (1, 2, 3)]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
