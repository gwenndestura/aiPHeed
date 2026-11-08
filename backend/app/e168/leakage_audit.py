"""
Feature-level leakage test for E168 (complements the survey-label corruption test in results.json).

At each Lead-1 origin i (ENNS 2018, 2019, 2021), every panel row dated AFTER the origin (qi > i) is replaced with random noise
in every input panel the procedure reads:
  CPI panel (S.cpi), government panel (S.s8.gov), news panel (S.P / S.news), SWS signal (S.h2), local panel (L), SunStar panel (S_P)
The full frozen E168 procedure (app.e168.lgbm_only.task) then runs. If no feature reads beyond its origin, the forecasts are
identical to the uncorrupted run. Release lags inside each panel are documented series by series in docs/final/LEAKAGE_AUDIT_E168.md.

    python -m app.e168.leakage_audit -> data/e168/out/feature_leakage_test.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e168" / "out"


def _noise_after(df: pd.DataFrame, i: int, qcol: str | None, rng) -> pd.DataFrame:
    df = df.copy()
    q = df.index.get_level_values(qcol) if qcol and qcol in (df.index.names or []) else df[qcol]
    m = np.asarray(q) > i
    num = df.select_dtypes("number").columns
    df.loc[m, num] = rng.normal(0, 50, (int(m.sum()), len(num)))
    return df


def run_one(survey: str, corrupt: bool) -> pd.DataFrame:
    from app.e148 import model as M8
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e168 import lgbm_only as E
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    i = M8.RQ[survey] - 1
    if corrupt:
        rng = np.random.default_rng(1680)
        L, S_P = _noise_after(L, i, "qi", rng), _noise_after(S_P, i, "qi", rng)
        orig = Pv.Store2.__init__

        def init(self, *a, **k):
            orig(self, *a, **k)
            self.cpi = _noise_after(self.cpi, i, "qi", rng)
            if getattr(self, "news", None) is not None:
                self.news = _noise_after(self.news, i, "qi", rng)
            if getattr(self, "P", None) is not None:
                self.P = _noise_after(self.P, i, "qi", rng)
            if hasattr(self, "s8") and hasattr(self.s8, "gov"):
                self.s8.gov = _noise_after(self.s8.gov, i, "qi", rng)
            if isinstance(getattr(self, "h2", None), dict):
                self.h2 = {kk: (rng.normal(0, 50) if kk[1] > i else v) for kk, v in self.h2.items()}
        Pv.Store2.__init__ = init
    o = E.task(survey, 1, H, L, S_P, "main")
    return o[["key", "survey", "mu", "p"]].assign(corrupt=corrupt)


def main():
    jobs = [(s, c) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for c in (False, True)]
    R = pd.concat(Parallel(n_jobs=6)(delayed(run_one)(s, c) for s, c in jobs), ignore_index=True)
    a = R[~R["corrupt"]].merge(R[R["corrupt"]], on=["key", "survey"], suffixes=("", "_c"))
    res = {"rows": len(a), "max_abs_change_logit": float((a["mu"] - a["mu_c"]).abs().max()),
           "max_abs_change_prob": float((a["p"] - a["p_c"]).abs().max()),
           "panels_corrupted_after_origin": ["cpi_panel", "gov_panel", "news_panel", "h2_signal", "local_panel", "sunstar_panel"],
           "passed": bool((a["mu"] - a["mu_c"]).abs().max() < 1e-9)}
    (OUT / "feature_leakage_test.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
