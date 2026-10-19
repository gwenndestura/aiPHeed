"""E64 r1 (Objective 1 C): FSSI audit and the FSSI-v3 panel with full traceability.

  * FSSI-v3 per province-quarter 2021-Q1..2026-Q3 (articles of the quarter published before its end + 1 day, i.e. the
    issue date of an origin at that quarter), with n, status, mean intensity, bias weight and the article keys
  * FSSI-v2 (deployed) vs FSSI-v3 coverage: province-quarters with evidence, admitted articles
  * D-E64-2 effect: FSSI-v2 values with and without the 0.30 intensity filter its code applies
  * descriptive association of FSSI-v3 with the same quarter's provincial price pressure (PS) and regional hunger;
    no validation claim (FSSI is a news-tone index, not a measure of food insecurity)

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/r1_fssi_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

E64 = Path(__file__).resolve().parents[1]
BACKEND = E64.parents[2] / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
LAB = E64.parent / "E62_Final_System_Audit" / "tables" / "r1_labels_independent.csv"


def main():
    from app.news import pipeline_v3 as P
    rows, trace = [], {}
    for t in range(P.qi("2021-Q1"), P.qi("2026-Q3") + 1):
        arts = P.asof(t)
        for p in P.PROVINCE_CODES:
            f = P.fssi_v3(p, t, arts)
            keys = [a["article_key"] for a in arts if a["province_code"] == p]
            rows.append({"province_code": p, "quarter": P.qs(t), **{k: f[k] for k in ("n", "status", "fssi",
                                                                                        "mean_intensity", "bias_weight")}})
            trace[f"{p}|{P.qs(t)}"] = keys
    V3 = pd.DataFrame(rows)
    V3.to_csv(E64 / "tables" / "r1_fssi_v3_panel.csv", index=False, lineterminator="\n")
    (E64 / "out" / "r1_fssi_v3_article_keys.json").write_text(json.dumps(trace, indent=0), encoding="utf-8")
    V2 = pd.read_csv("data/news_e31/fssi_v2_panel.csv", dtype={"province_code": str})
    V2 = V2[V2["quarter"] <= "2026-Q3"]
    res = {"fssi_v3_status_counts": V3["status"].value_counts().to_dict(),
           "fssi_v2_status_counts": V2["evidence_status"].value_counts().to_dict(),
           "admitted_v3": int(V3["n"].sum()), "admitted_v2": int(V2["n_admitted"].sum()),
           "cells_with_value_v3": int(V3["fssi"].notna().sum()), "cells_with_value_v2": int(V2["FSSI_v2"].notna().sum()),
           "cells": int(len(V3))}
    # D-E64-2: what the 0.30 filter removes from FSSI-v2
    from app.news.fssi_v2 import build_fssi_v2
    from app.news.store import NewsStore
    qs = [f"{y}-Q{q}" for y in range(2021, 2027) for q in range(1, 5)]
    out = build_fssi_v2(NewsStore(Path("data/news_e31")), qs, write=False)
    art = out["articles"]
    res["fssi_v2_threshold_effect"] = {"admitted": int(len(art)), "below_0_30": int((art["food_insecurity_score"] < 0.30).sum()),
                                       "cells_with_admitted": int((out["panel"]["n_admitted"] > 0).sum()),
                                       "cells_with_value": int(out["panel"]["FSSI_v2"].notna().sum())}
    lab = pd.read_csv(LAB, dtype={"province_code": str})
    M = V3.merge(lab[["province_code", "quarter", "PS", "H_all", "F"]], on=["province_code", "quarter"], how="left")
    S = M[M["fssi"].notna() & M["PS"].notna()]
    res["descriptive_association"] = {
        "n_cells": int(len(S)),
        "spearman_fssi_vs_same_quarter_food_yoy": round(float(stats.spearmanr(S["fssi"], S["F"]).statistic), 3),
        "spearman_fssi_vs_PS": round(float(stats.spearmanr(S["fssi"], S["PS"]).statistic), 3),
        "spearman_fssi_vs_regional_hunger": round(float(stats.spearmanr(S["fssi"], S["H_all"], nan_policy="omit").statistic), 3),
        "note": "descriptive only; FSSI is a news-tone index of admitted headlines, not a measure of food insecurity"}
    (E64 / "out" / "r1_fssi_audit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
