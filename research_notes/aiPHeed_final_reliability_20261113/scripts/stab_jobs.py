r"""PROTOCOL_REL G10a/G10b refits of the UNCHANGED FINAL procedure at Lead 1 (engine_final.fit_predict, rate='lin', miss='mind',
cw='balanced'; 5 seeds). Only the training rows change; no setting, threshold or input is altered and no test outcome is read here.
  dropround : remove one training survey round (2019 fold: 2015 or 2018; 2021 fold: 2015, 2018 or 2019)
  unseen    : remove every training row of the test provinces (the model never saw those provinces' surveys)
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python stab_jobs.py [--jobs N]"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
sys.path.insert(0, str(RN / "aiPHeed_final_7of7_20261113" / "scripts"))
from ablation import PATHS   # noqa: E402
OUT = HERE / "parts"
SEEDS = (168, 1, 2, 3, 4)


def job(survey, seed, kind, what):
    f = OUT / f"{kind.upper()}__{survey}__1__{seed}__{what}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    import run_qs
    tr, te, AN = run_qs.load(survey, 1)
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    m = (tr["survey"] != what).values if kind == "dropround" else ~tr["key"].isin(set(te["key"])).values
    n0 = len(tr)
    tr = tr[m].reset_index(drop=True)
    AN = {a: (np.asarray(v[0])[m], v[1]) for a, v in AN.items()}
    r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    out = te[["key", "survey", "lead"]].assign(seed=seed, kind=kind, what=what, p=r["p"], cfg=r["cfg"], train_rows=len(tr), train_rows_full=n0,
                                               train_rounds="+".join(sorted(tr["survey"].unique())))
    OUT.mkdir(exist_ok=True)
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
    ap = argparse.ArgumentParser(); ap.add_argument("--jobs", type=int, default=20); a = ap.parse_args()
    J = ([("ENNS2019", s, "dropround", w) for w in ("FNRI2015", "ENNS2018") for s in SEEDS]
         + [("ENNS2021", s, "dropround", w) for w in ("FNRI2015", "ENNS2018", "ENNS2019") for s in SEEDS]
         + [(sv, s, "unseen", "testprov") for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS])
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if str(x).startswith("FAIL")]
    print("FAILED", len(bad), *bad[:5], sep="\n", flush=True)
