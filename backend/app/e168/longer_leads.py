"""
Frozen E168 LightGBM-only procedure (app.e168.lgbm_only.task, unchanged since b11aa542) at Leads 3-8, so its skill
horizon can be determined. Nothing is re-selected by hand: the same nested procedure runs at each lead.

    python -m app.e168.longer_leads run    -> data/e168/out/all_rows_l3_8.csv
    python -m app.e168.longer_leads eval   -> data/e168/out/lead_horizon.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e147 import evaluate as E7
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e156 import leads as LD
from app.e168.lgbm_only import OUT, task

ROWS = OUT / "all_rows_l3_8.csv"


def guarded(s, h, H, L, S_P):
    """Same skip rule as E170/E171: no forecast where no survey round was released or no training rows exist at the origin."""
    from app.e148 import model as M8
    from app.e150 import model as M
    from app.e151 import prov as Pv
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    i = M8.RQ[s] - h
    if not M.released(i, Pv.ROUNDS) or M.Pipeline(Pv.Store2(None), i, Pv.ROUNDS, Pv.ORIGIN[s]).tr.empty:
        return None
    return task(s, h, H, L, S_P, "main")


def run():
    if ROWS.exists():
        raise SystemExit("already run")
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(3, 9)]
    R = Parallel(n_jobs=12)(delayed(guarded)(s, h, H, L, S_P) for s, h in jobs)
    pd.concat([x for x in R if x is not None], ignore_index=True).to_csv(ROWS, index=False, lineterminator="\n")


def evaluate():
    A = pd.concat([pd.read_csv(OUT / "all_rows.csv"), pd.read_csv(ROWS)], ignore_index=True)
    A = A[A["mode"] == "main"]
    G = pd.read_csv(OUT.parent.parent / "e158" / "out" / "oof.csv")
    rng = np.random.default_rng(168)
    res = {"model": "E168 LightGBM-only (frozen)", "threshold_accuracy": 0.75, "leads": {}}
    for Ld in range(1, 9):
        x = G[G["lead"] == Ld].merge(A[A["lead"] == Ld][["key", "survey", "lead", "mu", "p", "half"]], on=["key", "survey", "lead"]).rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"})
        if len(x) < 10:
            continue
        ev = LD.evaluate(x, "E168", "E168")["leads"][0]
        d = E7.diff_ci(x, "E168", "PERS", "q_true", rng, n=2000)
        res["leads"][Ld] = {"rows": int(len(x)), "correct": int(((x["E168"] >= .5) == (x["y_high"] == 1)).sum()), "accuracy": ev["accuracy"], "high_recall": ev["high_recall"], "low_recall": ev["low_recall"],
                            "precision": ev["precision"], "brier": ev["brier_soft"], "persistence_accuracy": round(float(((x["PERS"] >= .5) == (x["y_high"] == 1)).mean()), 3),
                            "brier_minus_persistence": round(d["diff"], 4), "brier_minus_persistence_ci95": [round(z, 4) for z in d["ci95"]],
                            "beats_persistence_C2": bool(d["ci95"][1] < 0), "criteria_E156": ev["criteria"]}
    def horizon(ok):
        h = 0
        for Ld in range(1, 9):
            if Ld in res["leads"] and ok(res["leads"][Ld]) and Ld == h + 1:
                h = Ld
            else:
                break
        return h
    res["skill_horizon_beats_persistence"] = horizon(lambda r: r["beats_persistence_C2"])
    res["horizon_75pct_and_beats_persistence"] = horizon(lambda r: r["beats_persistence_C2"] and r["accuracy"] >= 0.75)
    res["maximum_reliable_lead_E156"] = horizon(lambda r: all(r["criteria_E156"].values()))
    (OUT / "lead_horizon.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    for Ld, r in res["leads"].items():
        print(Ld, r["rows"], r["correct"], r["accuracy"], "pers", r["persistence_accuracy"], "recallH", r["high_recall"], "brier", r["brier"], "C2", r["beats_persistence_C2"], r["brier_minus_persistence_ci95"])
    print({k: res[k] for k in ("skill_horizon_beats_persistence", "horizon_75pct_and_beats_persistence", "maximum_reliable_lead_E156")})


if __name__ == "__main__":
    {"run": run, "eval": evaluate}[sys.argv[1]]()
