r"""PROTOCOL_SA Part B (sha 112ca651): FINAL-SA = FINAL with (i) the RATE multiplier capped at the longest training gap of each
fit (spread unchanged) and (ii) the training-chosen balanced-accuracy threshold recorded for the class decision.
Everything else is engine_final.fit_predict(rate='lin', miss='mind', cw='balanced'), unchanged.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python run_sa.py [--jobs N]"""
import argparse
import sys
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
OUT = HERE / "parts_sa"
PATHS = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts"), str(RN / "aiPHeed_hcw_optimization_20261112" / "scripts"),
         str(RN / "aiPHeed_hcw_independent_check_20261112" / "scripts"), str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts")]
SEEDS = (168, 1, 2, 3, 4)


def capped_class():
    import engine_final as EF

    Base = EF.M4                         # the original RATE class; its own base is the original engine_opt.M2

    class M4Cap(Base):
        """RATE with the multiplier capped at the longest gap seen in this fit's training rows (no time extrapolation)."""

        def fit(self, d):
            super().fit(d)
            if self.RATE != "none":
                self.gmax_ = float(d["gap_q"].values.astype(float).max())
            return self

        def predict(self, X):
            if self.RATE == "none":
                return super().predict(X)
            r = super(Base, self).predict(X)     # the plain LightGBM rate prediction (engine_opt.M2 is swapped while fitting)
            g = np.minimum(X["gap_q"].values.astype(float), self.gmax_)
            return EF._g(g, self.RATE, self.g0_) * r
    return EF, M4Cap


def job(survey, lead, seed):
    f = OUT / f"FINALSA__{survey}__{lead}__{seed}.csv"
    if f.exists():
        return str(f)
    for p in PATHS:
        if p not in sys.path:
            sys.path.insert(0, p)
    import run_qs
    EF, M4Cap = capped_class()
    tr, te, AN = run_qs.load(survey, lead)
    old = EF.M4
    EF.M4 = M4Cap                       # engine_final.fit_predict builds its class from the module-level M4
    try:
        r = EF.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")
    finally:
        EF.M4 = old
    out = te.reset_index(drop=True)[["key", "survey", "lead", "T", "i", "gap_q"]].assign(arm="FINALSA", seed=seed, p=r["p"], mu=r["mu"], cal=r["cal"],
                                                                                         thr=r["thr"], inner_brier=r["inner_brier"], cfg=r["cfg"])
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--one", nargs=3)
    a = ap.parse_args()
    if a.one:
        print(safe(a.one[0], int(a.one[1]), int(a.one[2])))
        sys.exit()
    J = [(sv, l, s) for l in (1, 2, 3) for sv in ("ENNS2018", "ENNS2019", "ENNS2021") for s in SEEDS]
    print(len(J), "jobs", flush=True)
    R = Parallel(n_jobs=a.jobs, verbose=5)(delayed(safe)(*j) for j in J)
    bad = [x for x in R if x.startswith("FAIL")]
    print("FAILED", len(bad), *bad[:6], sep="\n", flush=True)
