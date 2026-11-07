"""
Controlled group-level permutation of the frozen E168 procedure (Part 2.3 of the 2026-11-07 completion brief).

For each trigger group, that group's columns (government and news) are permuted across provinces with a fixed seed in the
training and test rows (app.e163.model.shuffle_cols); the full nested E168 procedure (app.e168.lgbm_only.task) then runs
unchanged at Lead 1 for ENNS 2018, 2019 and 2021. A group carries province-specific information only if permuting it makes
the Brier score significantly worse. Nothing is selected on these results.

    python -m app.e168.group_permutation run   -> data/e168/out/group_permutation.csv
    python -m app.e168.group_permutation eval  -> data/e168/out/group_permutation.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e168" / "out"
ROWS = OUT / "group_permutation.csv"
GROUPS = ("market", "climate", "employment", "remittance", "poverty")
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")


def _job(group: str, survey: str, seed: int) -> pd.DataFrame:
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e163 import model as C
    from app.e168 import lgbm_only as E
    E.TRIG = [c for c in E.GNT if C.gmap(c) == group]
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    o = E.task(survey, 1, H, L, S_P, f"shuf{seed}")
    o["group"], o["seed"], o["n_permuted_cols"] = group, seed, len(E.TRIG)
    return o


def run():
    if ROWS.exists():
        raise SystemExit("already run")
    jobs = [(g, s, 1) for g in GROUPS for s in SURVEYS]
    R = Parallel(n_jobs=8)(delayed(_job)(*j) for j in jobs)
    pd.concat(R, ignore_index=True).to_csv(ROWS, index=False, lineterminator="\n")


def evaluate():
    P = pd.read_csv(ROWS)
    A = pd.read_csv(OUT / "all_rows.csv")
    A = A[(A["mode"] == "main") & (A["lead"] == 1)][["key", "survey", "p"]]
    G = pd.read_csv(BACKEND_DIR / "data" / "e158" / "out" / "oof.csv")
    G = G[G["lead"] == 1][["key", "survey", "y_high", "q_true"]]
    base = G.merge(A, on=["key", "survey"])
    rng = np.random.default_rng(168)
    res = {"lead": 1, "rows": len(base), "method": __doc__.strip().splitlines()[2], "groups": {}}
    for g in GROUPS:
        x = base.merge(P[P["group"] == g][["key", "survey", "p"]].rename(columns={"p": "p_perm"}), on=["key", "survey"])
        d = (x["p"] - x["q_true"]) ** 2 - (x["p_perm"] - x["q_true"]) ** 2      # negative: real inputs better
        bs = [d.values[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
        acc = lambda c: float(((x[c] >= 0.5) == (x["y_high"] == 1)).mean())
        res["groups"][g] = {"n": len(x), "brier_real": round(float(((x["p"] - x["q_true"]) ** 2).mean()), 4),
                            "brier_permuted": round(float(((x["p_perm"] - x["q_true"]) ** 2).mean()), 4),
                            "real_minus_permuted": round(float(d.mean()), 4), "ci95": [round(float(v), 4) for v in np.percentile(bs, [2.5, 97.5])],
                            "accuracy_real": round(acc("p"), 3), "accuracy_permuted": round(acc("p_perm"), 3),
                            "max_abs_prob_change": round(float((x["p"] - x["p_perm"]).abs().max()), 4),
                            "province_specific_information": bool(np.percentile(bs, 97.5) < 0)}
    (OUT / "group_permutation.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"run": run, "eval": evaluate}[sys.argv[1]]()
