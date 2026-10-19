"""E62 r1: recompute the T43 / PS outcome labels from the raw source files only (no experiment library), and check
them against the E58 events file and the E61 label table.

Sources (read-only):
  PSA CPI YoY, food and all items, monthly, CALABARZON provinces: E40 data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv
  SWS hunger rounds with posting dates: backend/data/inputs/sws_rounds.csv
  Frozen thresholds: E40 label_spec.json (H 11.3; province P60 of food YoY and food-minus-headline, 2021-2022)

Label (E55 t43_labels): HIGH iff mean H of all rounds in quarter q > 11.3 AND (quarter-mean food YoY > food P60 OR
quarter-mean (food - headline) YoY > gap P60). Quarter means need all three months.

    backend/venv/Scripts/python.exe -B runner/r1_labels_independent.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
ROOT = EXP.parents[1]
YOY = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
SWS = ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv"
SPEC = EXP / "E40_SWS_CPI_Tiers" / "label_spec.json"
EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
E61_LABELS = EXP / "E61_E58_Low_Forecast_Investigation" / "tables" / "a4_target_labels_by_province_quarter.csv"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def qlabel(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def labels() -> pd.DataFrame:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))["thresholds"]
    y = pd.read_csv(YOY, dtype={"province_code": str})
    assert y["reference_month"].min() >= "2021-01", "pre-2021 row in CPI YoY"
    assert not y.duplicated(["province_code", "commodity", "reference_month"]).any(), "duplicate CPI rows"
    y["quarter"] = y["reference_month"].map(qlabel)
    g = y.groupby(["province_code", "commodity", "quarter"])["yoy_pct"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3]
    w = g.pivot_table(index=["province_code", "quarter"], columns="commodity", values="mean").reset_index()
    w = w.rename(columns={"food": "F", "all_items": "HL"})
    w["G"] = w["F"] - w["HL"]
    s = pd.read_csv(SWS)
    assert s["quarter"].min() >= "2021-Q1", "pre-2021 SWS round"
    h_all = s.groupby("quarter")["H"].mean()
    w["H_all"] = w["quarter"].map(h_all)
    w["thr_food"] = w["province_code"].map(spec["food"])
    w["thr_gap"] = w["province_code"].map(spec["gap"])
    w["food_margin"] = w["F"] - w["thr_food"]
    w["gap_margin"] = w["G"] - w["thr_gap"]
    w["PS"] = ((w["food_margin"] > 0) | (w["gap_margin"] > 0)).astype(int)
    w["T43"] = np.where(w["H_all"].notna(), ((w["H_all"] > spec["H"]) & (w["PS"] == 1)).astype(float), np.nan)
    w["province"] = w["province_code"].map(NAMES)
    return w.sort_values(["province_code", "quarter"]).reset_index(drop=True)


def main():
    W = labels()
    (E62 / "tables").mkdir(exist_ok=True)
    W.to_csv(E62 / "tables" / "r1_labels_independent.csv", index=False, float_format="%.4f", lineterminator="\n")
    ev = pd.read_csv(EVENTS, dtype={"province_code": str}).rename(columns={"target": "quarter"})
    m = ev.merge(W, on=["province_code", "quarter"], how="left")
    mism_ev = m[m["HIGH"] != m["T43"]]
    e61 = pd.read_csv(E61_LABELS, dtype={"province_code": str}).rename(columns={"target": "quarter"})
    m2 = e61.merge(W, on=["province_code", "quarter"], suffixes=("_e61", ""))
    both = m2["T43_e61"].notna() | m2["T43"].notna()
    mism_61 = m2[both & (m2["T43_e61"].fillna(-1) != m2["T43"].fillna(-1))]
    maxdiff = float(np.nanmax(np.abs(m2["F_e61"] - m2["F"])))
    res = {"rows": int(len(W)), "quarters": [W["quarter"].min(), W["quarter"].max()],
           "events_rows_compared": int(len(m)), "events_mismatches": mism_ev[["quarter", "province", "HIGH", "T43"]].to_dict("records"),
           "e61_rows_compared": int(len(m2)), "e61_label_mismatches": mism_61[["quarter", "province_code"]].to_dict("records"),
           "e61_max_abs_food_yoy_diff": maxdiff,
           "HIGH_by_quarter_2024Q2_2026Q3": W[(W["quarter"] >= "2024-Q2") & (W["quarter"] <= "2026-Q3")]
           .groupby("quarter")["T43"].sum().astype(int).to_dict(),
           "n_HIGH_50": int(W[(W["quarter"] >= "2024-Q2") & (W["quarter"] <= "2026-Q3")]["T43"].sum()),
           "H_all_by_quarter": pd.read_csv(SWS).groupby("quarter")["H"].mean().round(3).to_dict()}
    (E62 / "out").mkdir(exist_ok=True)
    (E62 / "out" / "r1_labels_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "H_all_by_quarter"}, indent=1))


if __name__ == "__main__":
    main()
