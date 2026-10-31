"""E129 provincial CPI / price audit (read only): can the five provincial series distinguish food-price conditions?

    python cpi_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
X = ROOT.parent
REPO = X.parents[1]
sys.path.insert(0, str(REPO / "backend"))
from app.ml.inference import firi as FI  # noqa: E402

PROVS = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def quarterly_yoy():
    c = pd.read_csv(X / "E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv", dtype={"yoy_pct": float})
    c["province"] = c["province_code"].map(FI.PROVINCES)
    c["q"] = c["reference_month"].str[:4] + "-Q" + ((c["reference_month"].str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    n = c.groupby(["province", "commodity", "q"])["yoy_pct"].transform("size")
    c = c[n == 3]                                       # complete quarters only
    return c.groupby(["province", "commodity", "q"])["yoy_pct"].mean().unstack("province")[PROVS]


def decompose(w):
    """Two-way (quarter, province) decomposition of a quarter x province table."""
    w = w.dropna()
    g = w.values.mean()
    t_eff = w.mean(axis=1) - g
    p_eff = w.mean(axis=0) - g
    resid = w.values - g - t_eff.values[:, None] - p_eff.values[None, :]
    ss_t = (t_eff ** 2).sum() * w.shape[1]
    ss_p = (p_eff ** 2).sum() * w.shape[0]
    ss_r = (resid ** 2).sum()
    tot = ss_t + ss_p + ss_r
    ranks = w.rank(axis=1)
    rank_changes = float((ranks.diff().abs().sum(axis=1) > 0).iloc[1:].mean())
    top = w.idxmax(axis=1).value_counts().to_dict()
    corr = w.corr().values[np.triu_indices(5, 1)]
    return dict(quarters=len(w), share_time=ss_t / tot, share_province_persistent=ss_p / tot, share_province_by_time=ss_r / tot,
                mean_cross_province_sd=float(w.std(axis=1).mean()), median_spread_max_min=float((w.max(axis=1) - w.min(axis=1)).median()),
                max_spread=float((w.max(axis=1) - w.min(axis=1)).max()), pairwise_corr_min=float(corr.min()), pairwise_corr_median=float(np.median(corr)),
                share_quarters_rank_order_changes=rank_changes, highest_province_counts=top,
                province_means={k: round(float(v), 3) for k, v in w.mean().items()})


def bottom30():
    b = pd.read_csv(X / "E118_FAO_Data_Discovery/data/clean/cpi_bottom30_yoy.csv")
    b = b[b["unit"].isin(PROVS) & b["item"].str.startswith("01 - FOOD")].copy()
    b["y"], b["m"] = (b["period"] // 12).astype(int), (b["period"] % 12).astype(int)
    b = b[b["y"] >= 2021]
    b["q"] = b["y"].astype(str) + "-Q" + (b["m"] // 3 + 1).astype(str)
    n = b.groupby(["unit", "q"])["value"].transform("size")
    return b[n == 3].groupby(["q", "unit"])["value"].mean().unstack()[PROVS]


def retail_rice():
    r = pd.read_csv(X / "E118_FAO_Data_Discovery/data/clean/retail_cereals.csv")
    r = r[r["unit"].isin(PROVS) & (r["item"] == "RICE, REGULAR-MILLED, 1 KG")].copy()
    r["y"], r["m"] = (r["period"] // 12).astype(int), (r["period"] % 12).astype(int)
    r = r[r["y"] >= 2021]
    r["q"] = r["y"].astype(str) + "-Q" + (r["m"] // 3 + 1).astype(str)
    w = r.groupby(["q", "unit"])["value"].mean().unstack()[PROVS]
    yoy = 100 * (w / w.shift(4) - 1)
    return w, yoy.iloc[4:]


def ledger():
    led = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/data/psa_cpi_availability_ledger_20261029.csv")
    return led["class"].value_counts().to_dict(), len(led)


def main():
    OUT.mkdir(exist_ok=True)
    q = quarterly_yoy()
    res = {}
    for com in ("food", "all_items"):
        res[f"cpi_{com}_yoy"] = decompose(q.loc[com])
    w = q.loc["food"].dropna()
    res["food_minus_headline_gap"] = decompose((q.loc["food"] - q.loc["all_items"]).dropna())
    res["bottom30_food_yoy"] = decompose(bottom30())
    lvl, yoy = retail_rice()
    res["retail_regular_rice_price_level"] = decompose(lvl)
    res["retail_regular_rice_yoy"] = decompose(yoy)
    cls, n = ledger()
    res["cpi_release_ledger"] = dict(rows=n, evidence_class_counts=cls)
    q.loc["food"].round(3).to_csv(OUT / "cpi_food_yoy_quarterly_by_province.csv")
    json.dump(res, open(OUT / "cpi_audit.json", "w"), indent=2, default=float)
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
