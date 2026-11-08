"""
E166 at Leads 3-8 (same frozen procedure, no change), to state its skill horizon and confirm the maximum reliable lead.

    python -m app.e166.longer_leads -> data/e166/out/all_rows_l3_8.csv, lead_horizon.json
"""
import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e156 import leads as LD
from app.e166 import nested_source as N
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
K = ["key", "survey", "lead"]

if __name__ == "__main__":
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    p = N.OUT / "all_rows_l3_8.csv"
    if p.exists():
        A = pd.read_csv(p)
    else:
        A = pd.concat([x for x in Parallel(n_jobs=12)(delayed(N.task)(s, h, H, L, S_P, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in range(3, 9)) if x is not None], ignore_index=True)
        A.to_csv(p, index=False, lineterminator="\n")
    A0 = pd.read_csv(N.OUT / "all_rows.csv")
    A = pd.concat([A0[A0["mode"] == "main"], A], ignore_index=True)
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    F = G.merge(A[K + ["mu", "p", "half"]].rename(columns={"mu": "mu_E166", "p": "E166", "half": "half_E166"}), on=K)
    r = LD.evaluate(F, "E166", "E166")
    skill = 0
    for x in sorted(r["leads"], key=lambda t: t["lead"]):
        if x["criteria"]["C2"] and x["lead"] == skill + 1:
            skill = x["lead"]
        else:
            break
    out = {"maximum_reliable_lead": r["maximum_reliable_lead"], "skill_horizon_beats_persistence_C2": skill,
           "per_lead": {x["lead"]: {"rows": x["rows"], "accuracy": x["accuracy"], "high_recall": x["high_recall"], "low_recall": x["low_recall"], "brier": x["brier_soft"], "brier_minus_persistence_ci95": x["brier_minus_persistence_ci95"], "failed": [c for c, v in x["criteria"].items() if not v]} for x in r["leads"]}}
    (N.OUT / "lead_horizon.json").write_text(json.dumps(out, indent=1, default=str), newline="\n")
    print(json.dumps(out, indent=1, default=str))
