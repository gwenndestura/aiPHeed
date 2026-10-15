"""E40 label: SWS + provincial CPI binary HIGH/LOW label with a FROZEN 2021-Q1..2022-Q4 reference window (researcher's
specification, 2026-10-15). No data before 2021-01 is read anywhere (asserted).

Signals for province p, quarter q (each quarter's own published data):
  sws_hi  = H_q > P_k(H over the frozen window)                       (regional; one value for all provinces)
  cpi_hi  = food_pq > P_k(food_p over the frozen window)              (province-specific)
  gap_hi  = (food_pq - headline_pq) > P_k(gap_p over the frozen window) (province-specific)
  cpi_rel = food_pq - mean of the five provinces (reported, used for ranking and ties)
Label (binary): both_q = sws_hi AND (cpi_hi OR gap_hi)
        HIGH (1) = both_q AND both_{q-1} (two consecutive quarters; a missing previous quarter cannot confirm)
        LOW  (0) = otherwise. No third class.
Missing SWS quarters (no approved round: 2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) have no label; never zero-filled.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

E40 = Path(__file__).resolve().parents[1]
ROOT = E40.parents[2]
INP = ROOT / "backend" / "data" / "inputs"
CPI = E40 / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
WINDOW = ("2021-Q1", "2022-Q4")          # frozen burn-in; never recomputed with later data
SCORE_FROM = "2023-Q1"
GRID = [60, 65, 70, 75, 80, 85]
SWS_ABS = 21.1
SWS_ABS_NOTE = ("21.1% = SWS 2020 annual average hunger, as supplied by the researcher (2026-10-15); not verified in this "
                "run. It is a pre-2021 statistic used as a threshold, an explicit exception to the study-window rule, so it "
                "is reported as a variant only and never selected as the primary label.")
EARLIEST = "2021-01"


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qn(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def monthly_cpi() -> pd.DataFrame:
    m = pd.read_csv(CPI, dtype={"province_code": str})
    assert m["reference_month"].min() >= EARLIEST, "pre-2021 CPI value found"
    m["quarter"] = m["reference_month"].str[:4] + "-Q" + ((m["reference_month"].str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    m["month_in_q"] = (m["reference_month"].str[5:7].astype(int) - 1) % 3 + 1
    return m


def quarterly_inputs() -> pd.DataFrame:
    m = monthly_cpi()
    q = m.pivot_table(index=["province_code", "quarter"], columns="commodity", values="yoy_pct", aggfunc=["mean", "size"])
    q.columns = [f"{a}_{b}" for a, b in q.columns]
    q = q.reset_index()
    q = q[(q["size_food"] == 3) & (q["size_all_items"] == 3)]
    q = q.rename(columns={"mean_food": "food", "mean_all_items": "headline"})[["province_code", "quarter", "food", "headline"]]
    q["cpi_gap"] = q["food"] - q["headline"]
    q["cpi_rel"] = q["food"] - q.groupby("quarter")["food"].transform("mean")
    r = pd.read_csv(INP / "sws_rounds.csv")
    a = r[r["definition_A"].astype(str) == "True"]
    assert a["quarter"].map(qi).min() >= qi("2021-Q1"), "pre-2021 SWS round found"
    q["H"] = q["quarter"].map(a.groupby("quarter")["H"].mean())
    q["H_posted"] = q["quarter"].map(a.groupby("quarter")["published"].max())
    return q.sort_values(["quarter", "province_code"]).reset_index(drop=True)


def frozen_thresholds(q: pd.DataFrame, pct: int) -> dict:
    """Percentile thresholds from the frozen window ONLY (2021-Q1..2022-Q4)."""
    w = q[(q["quarter"].map(qi) >= qi(WINDOW[0])) & (q["quarter"].map(qi) <= qi(WINDOW[1]))]
    h = w.drop_duplicates("quarter")["H"].dropna()
    return {"pct": pct, "window": list(WINDOW), "n_window_quarters_H": int(len(h)),
            "H": float(np.percentile(h, pct)),
            "food": {p: float(np.percentile(w[w.province_code == p]["food"], pct)) for p in PROVS},
            "gap": {p: float(np.percentile(w[w.province_code == p]["cpi_gap"], pct)) for p in PROVS}}


def label(q: pd.DataFrame, thr: dict, sws_abs: float | None = None) -> pd.DataFrame:
    """sws_abs: optional absolute SWS cutoff (reported variant only; see SWS_ABS_NOTE)."""
    out = q.copy()
    h_cut = thr["H"] if sws_abs is None else sws_abs
    out["sws_hi"] = np.where(out["H"].isna(), np.nan, (out["H"] > h_cut).astype(float))
    out["cpi_hi"] = (out["food"] > out["province_code"].map(thr["food"])).astype(float)
    out["gap_hi"] = (out["cpi_gap"] > out["province_code"].map(thr["gap"])).astype(float)
    out["cpi_any"] = ((out["cpi_hi"] + out["gap_hi"]) > 0).astype(float)
    out["both"] = np.where(out["sws_hi"].isna(), np.nan, out["sws_hi"] * out["cpi_any"])
    prev = {(r.province_code, qi(r.quarter)): r.both for r in out.itertuples()}
    ys = []
    for r in out.itertuples():                       # binary only: HIGH (1) / LOW (0); missing SWS -> no label
        if r.sws_hi != r.sws_hi:
            ys.append(None)
            continue
        ys.append(1 if (r.both == 1 and prev.get((r.province_code, qi(r.quarter) - 1)) == 1) else 0)
    out["y_high"] = ys
    out["label"] = out["y_high"].map({1: "HIGH", 0: "LOW"})
    out["scored_period"] = out["quarter"].map(qi) >= qi(SCORE_FROM)
    return out


def prevalence(lab: pd.DataFrame, quarters=None) -> dict:
    s = lab[lab["scored_period"] & lab["y_high"].notna()]
    if quarters is not None:
        s = s[s["quarter"].isin(quarters)]
    by_year = s.assign(y=s["quarter"].str[:4]).groupby("y")["y_high"].mean().to_dict()
    per_q = s.groupby("quarter")["y_high"].agg(lambda t: t.nunique() == 1)
    return {"HIGH_share": float(s["y_high"].mean()) if len(s) else None,
            "rows": int(len(s)), "HIGH_share_by_year": {k: float(v) for k, v in by_year.items()},
            "HIGH_share_by_quarter": s.groupby("quarter")["y_high"].mean().round(3).to_dict(),
            "quarters_all_five_identical": int(per_q.sum()), "quarters": int(len(per_q))}


def tune(q: pd.DataFrame, dev_quarters: list[str]) -> tuple[int | None, list[dict]]:
    """Researcher's rule: choose the percentile (one common cutoff for the three signals, P60..P85) ONLY so that the
    HIGH share of scored DEVELOPMENT province-quarters is within 10-30% and no year exceeds 40%. The 4-quarter blind
    holdout is excluded. Among passing settings the one closest to P75 (the specification's default) is kept."""
    rows = []
    for pct in GRID:
        p = prevalence(label(q, frozen_thresholds(q, pct)), dev_quarters)
        ok = p["HIGH_share"] is not None and 0.10 <= p["HIGH_share"] <= 0.30 and all(v <= 0.40 for v in p["HIGH_share_by_year"].values())
        rows.append({"pct": pct, "dev_HIGH_share": p["HIGH_share"], "dev_HIGH_by_year": p["HIGH_share_by_year"],
                     "dev_all_five_identical": p["quarters_all_five_identical"], "passes": ok})
    passing = [r["pct"] for r in rows if r["passes"]]
    return (min(passing, key=lambda x: (abs(x - 75), x)) if passing else None), rows
