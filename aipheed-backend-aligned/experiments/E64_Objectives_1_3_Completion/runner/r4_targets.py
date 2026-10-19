"""E64 r4 (Objective 2 B, PROTOCOL section 3): descriptive comparison of the reference target T43 with T43-F and T43-HL.
Never used to choose a model. Thresholds are 2021-2022 P60s (the E40 frozen window); no pre-2021 data, no later data.

  T43     H > 11.3 AND (food > P60_food OR gap > P60_gap)            (reference, served)
  T43-F   H > 11.3 AND food > P60_food                              (no gap condition)
  T43-HL  H > 11.3 AND (food > P60_food OR gap > P60_gap OR headline > P60_headline)

Reports base rates on 2021-Q2..2026-Q3 and on the 50 evaluation rows, agreement with T43, how each relates to the
regional hunger level, and the scores of E56 and the E64 candidates against each (if the sealed file exists).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/r4_targets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

E64 = Path(__file__).resolve().parents[1]
EXP = E64.parent
LAB = EXP / "E62_Final_System_Audit" / "tables" / "r1_labels_independent.csv"
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
S64 = E64 / "sealed" / "candidates.csv"


def main():
    W = pd.read_csv(LAB, dtype={"province_code": str})
    win = W[(W["quarter"] >= "2021-Q1") & (W["quarter"] <= "2022-Q4")]
    thr_hl = win.groupby("province_code")["HL"].quantile(0.6)
    W["thr_hl"] = W["province_code"].map(thr_hl)
    hh = W["H_all"] > 11.3
    W["T43_F"] = np.where(W["H_all"].notna(), (hh & (W["food_margin"] > 0)).astype(float), np.nan)
    W["T43_HL"] = np.where(W["H_all"].notna(), (hh & ((W["food_margin"] > 0) | (W["gap_margin"] > 0) |
                                                     (W["HL"] > W["thr_hl"]))).astype(float), np.nan)
    L = W[W["T43"].notna()]
    ev = L[(L["quarter"] >= "2024-Q2") & (L["quarter"] <= "2026-Q3")]
    res = {"headline_P60_2021_2022": thr_hl.round(3).to_dict(), "targets": {}}
    for t in ("T43", "T43_F", "T43_HL"):
        res["targets"][t] = {"base_rate_all": round(float(L[t].mean()), 3), "n_all": int(len(L)),
                             "base_rate_eval50": round(float(ev[t].mean()), 3), "HIGH_eval50": int(ev[t].sum()),
                             "agreement_with_T43_eval50": round(float((ev[t] == ev["T43"]).mean()), 3),
                             "HIGH_by_quarter_eval": ev.groupby("quarter")[t].sum().astype(int).to_dict(),
                             "spearman_quarter_share_vs_hunger": round(float(
                                 L.groupby("quarter").agg(s=(t, "mean"), h=("H_all", "first")).corr("spearman").iloc[0, 1]), 3)}
    rows = pd.read_csv(S57, dtype={"province_code": str})[["target", "province_code", "E56_p"]]
    arms = {"E56": rows.set_index(["target", "province_code"])["E56_p"]}
    if S64.exists():
        c = pd.read_csv(S64, dtype={"province_code": str}).set_index(["target", "province_code"])
        for a in ("A", "C", "D", "E", "A-S", "D-S", "B"):
            arms[f"E64-{a}"] = c[f"{a}_p"]
    sc = []
    E = ev.set_index(["quarter", "province_code"])
    for name, p in arms.items():
        p = p.reindex(E.index.rename(["target", "province_code"]))
        for t in ("T43", "T43_F", "T43_HL"):
            y = E[t].to_numpy()
            pp = p.to_numpy()
            sc.append({"arm": name, "target": t, "accuracy": round(float(((pp >= .5) == y).mean()), 3),
                       "brier": round(float(np.mean((pp - y) ** 2)), 4), "HIGH": int(y.sum())})
    pd.DataFrame(sc).to_csv(E64 / "tables" / "r4_target_scores.csv", index=False, lineterminator="\n")
    W.to_csv(E64 / "tables" / "r4_target_labels.csv", index=False, float_format="%.4f", lineterminator="\n")
    res["scores_note"] = "descriptive only; the models were trained on T43 (its PS part), so scores on other targets are not fair comparisons"
    (E64 / "out" / "r4_targets.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print(pd.DataFrame(sc).to_string())


if __name__ == "__main__":
    main()
