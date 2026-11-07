"""
E174 Step B (docs/e174/PROTOCOL.md, blob 0552e845): E168 with the news inputs rebuilt from the pure zero-shot XLM-RoBERTa
Tier 1 (data/e174/out/news_panel.parquet). The frozen E168 task (app.e168.lgbm_only.task) runs unchanged; only the news panel
the province store reads is redirected.

    python -m app.e174.model run    -> data/e174/model/rows.csv
    python -m app.e174.model eval   -> data/e174/model/results.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
NEWS = D / "e174" / "out"
OUT = D / "e174" / "model"


def task(survey: str, lead: int):
    from app.e151 import prov as Pv
    Pv.OUT = NEWS                                      # zero-shot news panel + unchanged SWS signal (h2)
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e168 import lgbm_only as E
    from app.e168.longer_leads import guarded
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    o = guarded(survey, lead, H, L, S_P)
    return None if o is None else o[o["mode"] == "main"][["key", "survey", "lead", "mu", "p", "half", "cfg", "n_features"]]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "rows.csv").exists():
        raise SystemExit("already run")
    jobs = [(s, l) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for l in (1, 2, 3)]
    R = Parallel(n_jobs=9)(delayed(task)(s, l) for s, l in jobs)
    pd.concat([x for x in R if x is not None], ignore_index=True).to_csv(OUT / "rows.csv", index=False, lineterminator="\n")


def evaluate():
    from app.e147 import evaluate as E7
    X = pd.read_csv(OUT / "rows.csv").rename(columns={"p": "p174"})
    A = pd.concat([pd.read_csv(D / "e168" / "out" / "all_rows.csv"), pd.read_csv(D / "e168" / "out" / "all_rows_l3_8.csv")])
    A = A[A["mode"] == "main"][["key", "survey", "lead", "p"]].rename(columns={"p": "p168"})
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    res = {"protocol": "docs/e174/PROTOCOL.md blob 0552e845", "leads": {}}
    for L in (1, 2, 3):
        x = G[G["lead"] == L].merge(X[X["lead"] == L], on=["key", "survey", "lead"]).merge(A[A["lead"] == L], on=["key", "survey", "lead"])
        y, q = (x["y_high"] == 1).values, x["q_true"].values
        acc = lambda c: round(float(((x[c] >= 0.5) == y).mean()), 3)
        d = (x["p174"] - q) ** 2 - (x["p168"] - q) ** 2
        rng = np.random.default_rng(174)
        bs = [d.values[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
        vp = E7.diff_ci(x.rename(columns={"p174": "E174"}), "E174", "PERS", "q_true", np.random.default_rng(168), n=2000)
        res["leads"][L] = {"n": len(x), "accuracy_E174": acc("p174"), "accuracy_E168": acc("p168"), "accuracy_persistence": acc("PERS"),
                           "brier_E174": round(float(((x["p174"] - q) ** 2).mean()), 4), "brier_E168": round(float(((x["p168"] - q) ** 2).mean()), 4),
                           "brier_E174_minus_E168": round(float(d.mean()), 4), "ci95": [round(float(v), 4) for v in np.percentile(bs, [2.5, 97.5])],
                           "beats_persistence": bool(vp["ci95"][1] < 0), "max_abs_prob_change_vs_E168": round(float((x["p174"] - x["p168"]).abs().max()), 4),
                           "selected_configs": x.groupby("survey")["cfg"].first().to_dict()}
    c1 = all(res["leads"][L]["accuracy_E174"] >= 0.75 and res["leads"][L]["beats_persistence"] for L in (1, 2, 3))
    c2 = res["leads"][1]["ci95"][1] < 0.010
    res["checks"] = {"1_project_rule_leads_1_3": c1, "2_non_inferior_lead1_margin_0.010": c2}
    res["decision"] = "E174 ADOPTED (subject to new live issue, own seal and owner promotion)" if (c1 and c2) else "E168 STAYS SERVED; zero-shot version built and tested, not adopted"
    (OUT / "results.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps({k: v for k, v in res.items() if k != "leads"}, indent=1))
    for L, r in res["leads"].items():
        print(L, {k: v for k, v in r.items() if k != "selected_configs"})


if __name__ == "__main__":
    {"run": run, "eval": evaluate}[sys.argv[1]]()
