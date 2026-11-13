"""PROTOCOL_FINAL.md runner. Run from C:\\Users\\admin\\aipheed_hcw\\backend with PYTHONPATH=. :
  python run_final.py --set rev  ARM [ARM ...]     held-out round FNRI2015 (Leads 1-2)
  python run_final.py --set fwd  ARM [ARM ...]     forward folds (Leads 1-3)
  python run_final.py --one SET ARM SURVEY LEAD SEED"""
import argparse
import json
import sys
from pathlib import Path

from joblib import Parallel, delayed

STUDY = Path(__file__).resolve().parents[1]
RN = STUDY.parent
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(STUDY / "scripts")]
SEEDS = (168, 1, 2, 3, 4)
ARMS = {
    "BASE": {},
    "RATE": dict(rate="lin"), "RATE_SQRT": dict(rate="sqrt"),
    "IMPUTE": dict(miss="median"), "RIMP": dict(miss="rimp"), "MIND": dict(miss="mind"), "DROPGAP": dict(miss="dropgap"),
    "COMP": dict(comp=True),
}
FINAL_FILE = STUDY / "evidence" / "final_config.json"
if FINAL_FILE.exists():
    ARMS["FINAL"] = json.loads(FINAL_FILE.read_text())["config"]


def job(sset, arm, survey, lead, seed):
    parts = STUDY / ("parts_rev" if sset == "rev" else "parts_fwd")
    f = parts / f"{arm}__{survey}__{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_final as EF
    if sset == "rev":
        import run_rev
        tr, te, AN, truth = run_rev.build(lead)
        idc = truth
    else:
        import run_qs
        tr, te, AN = run_qs.load(survey, lead)
        idc = te.reset_index(drop=True)[["key", "survey", "lead", "T", "i"]]
    r = EF.fit_predict(tr, te, AN, seed, **ARMS[arm])
    out = idc.assign(arm=arm, seed=seed, p=r["p"], mu=r["mu"], cal=r["cal"], thr=r["thr"], sse=r["sse"], inner_brier=r["inner_brier"], cfg=r["cfg"],
                     use="|".join(r["model"].use_), info=json.dumps(r["info"]))
    parts.mkdir(exist_ok=True)
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
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--set", default="rev")
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--one", nargs=5)
    a = ap.parse_args()
    if a.one:
        print(safe(a.one[0], a.one[1], a.one[2], int(a.one[3]), int(a.one[4])))
        sys.exit()
    arms = a.arms or list(ARMS)
    if a.set == "rev":
        J = [("rev", arm, "FNRI2015", l, s) for arm in arms for l in (1, 2) for s in SEEDS]
    else:
        J = [("fwd", arm, sv, l, s) for arm in arms for l in (1, 2, 3) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
