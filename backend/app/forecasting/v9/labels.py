"""
v9 audit of the thesis label (docs/aipheed/v9/STAGE1_CIRCULARITY_PROTOCOL.md): the composite SWS + provincial food-CPI
label, its two components, and the point-in-time predictors. These reproduce existing rules for audit; none is adopted.
Provincial CPI and rice become available at quarter end + 10 days (lock C4); SWS through the one as_of selector.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.forecasting.as_of import as_of
from app.forecasting.sws import load_rounds, qi, qs, quarter_table

PROC = Path(__file__).resolve().parents[3] / "data" / "processed"
PROVINCES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
ALPHA = 2.0                     # label_generator.ALPHA
LAST_DEV_QUARTER = "2026-Q3"    # development limit; later quarters are sealed and never loaded into features
PRICE = ["food_yoy", "food_yoy_dev", "cpi_z", "cpi_flag", "rice_qoq"]
OTHER = ["FSSI", "FSSI_lag1", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
         "trigger_ofw_remittance", "trigger_fish_kill", "unemployment", "sws_latest", "h"]


def quarter_end(q: str) -> date:
    y, n = int(q[:4]), int(q[-1])
    return date(y + (n == 4), 1 if n == 4 else 3 * n + 1, 1) - timedelta(days=1)


def issue_of(d: str) -> date:
    return date(int(d[:4]), 3 * int(d[-1]) - 2, 1)


def price_table() -> pd.DataFrame:
    """Provincial CPI per quarter, 2021-Q1 to the development limit: yoy (2022+ only), rolling z and flag from 2021 only."""
    p = pd.read_parquet(PROC / "psa_indicators.parquet")
    p = p[p.province_code.isin(PROVINCES) & (p.quarter >= "2021-Q1") & (p.quarter <= LAST_DEV_QUARTER)]
    p = p[["province_code", "quarter", "food_cpi", "food_cpi_yoy", "unemployment_rate"]].copy()
    p["qi"] = p.quarter.map(qi)
    p = p.sort_values(["province_code", "qi"]).reset_index(drop=True)
    p["food_yoy"] = p.food_cpi_yoy.where(p.quarter >= "2022-Q1")
    p["food_yoy_dev"] = p.food_yoy - p.groupby("quarter").food_yoy.transform("mean")
    g = p.groupby("province_code").food_cpi
    mean = g.transform(lambda s: s.rolling(24, min_periods=4).mean())
    sd = g.transform(lambda s: s.rolling(24, min_periods=4).std())
    p["cpi_z"] = (p.food_cpi - mean) / sd
    p["cpi_flag"] = (p.food_cpi > mean + sd).astype(float).where(mean.notna())
    r = pd.read_parquet(PROC / "psa_rice_prices.parquet")
    r = r[(r.rice_class == "regular_milled") & r.province_code.isin(PROVINCES) & (r.quarter <= LAST_DEV_QUARTER)]
    r = r[["province_code", "quarter", "price_php_per_kg"]].drop_duplicates(["province_code", "quarter"]).copy()
    r["qi"] = r.quarter.map(qi)
    r = r.sort_values(["province_code", "qi"])
    # A change is computed only between consecutive quarters; a gap stays missing.
    same = r.groupby("province_code").qi.diff().eq(1)
    r["rice_qoq"] = r.groupby("province_code").price_php_per_kg.diff().where(same)
    return p.merge(r[["province_code", "quarter", "rice_qoq"]], on=["province_code", "quarter"], how="left")


def label_table() -> pd.DataFrame:
    """One row per province-quarter with a published SWS round and a YoY base: L-COMP, L-SWS, L-CPI, and when known."""
    q = quarter_table(load_rounds())
    q = q[(q.area == "balance_luzon") & (q.quarter <= LAST_DEV_QUARTER)][["quarter", "y", "published"]]
    p = price_table().merge(q.rename(columns={"y": "sws"}), on="quarter", how="left")
    p["cpi_flag_prev"] = p.groupby("province_code").cpi_flag.shift(1)
    p["L_CPI"] = ((p.cpi_flag == 1) & (p.cpi_flag_prev == 1)).astype(float).where(p.cpi_flag_prev.notna())
    t = p[p.sws.notna() & p.food_yoy.notna()].copy()
    t["stress"] = t.sws + ALPHA * t.food_yoy_dev
    t["L_COMP"] = (t.stress > t.stress.median()).astype(int)
    t["L_SWS"] = (t.sws > t.sws.median()).astype(int)
    t["L_CPI"] = t.L_CPI.astype(int)
    t["known"] = [max(pub, quarter_end(x) + timedelta(days=10)) for pub, x in zip(t.published, t.quarter)]
    return t.reset_index(drop=True)


def news_table() -> pd.DataFrame:
    f = pd.read_parquet(PROC / "fssi_quarterly.parquet")[["province_code", "quarter", "FSSI", "FSSI_lag1", "FSSI_accel"]]
    t = pd.read_parquet(PROC / "trigger_proportions.parquet").drop(columns=["article_count"])
    n = f.merge(t, on=["province_code", "quarter"], how="outer")
    return n[(n.quarter >= "2021-Q1") & (n.quarter <= LAST_DEV_QUARTER)]


def features(dash: str, lead: int, prices: pd.DataFrame, news: pd.DataFrame, rounds: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time row per province at the issue of dashboard quarter dash. CPI/rice/unemployment: quarter dash - 2
    (lock C4); news: dash - 1; SWS: mean of the latest quarter with a round published strictly before the issue."""
    issue, d = issue_of(dash), qi(dash)
    assert quarter_end(qs(d - 2)) + timedelta(days=10) < issue
    known = as_of(rounds[rounds.area == "balance_luzon"], issue)
    latest = known[known.quarter == known.quarter.max()].value.mean() if len(known) else np.nan
    a = prices[prices.quarter == qs(d - 2)][["province_code", *PRICE, "unemployment_rate"]].rename(
        columns={"unemployment_rate": "unemployment"})
    n = news[news.quarter == qs(d - 1)].drop(columns="quarter")
    out = pd.DataFrame({"province_code": PROVINCES}).merge(a, how="left").merge(n, how="left")
    out["sws_latest"], out["h"] = latest, lead
    out["issue"], out["dash"], out["target"] = issue, dash, qs(d - 1 + lead)
    return out
