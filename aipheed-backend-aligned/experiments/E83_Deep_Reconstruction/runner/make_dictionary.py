"""E83 data dictionary: hand-written metadata per variable + missingness measured on the Lead-2 feature table."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

run = Path(sys.argv[1])
X = pd.read_csv(run / "features_r2_k2.csv" if (run / "features_r2_k2.csv").exists() else run / "features_k2.csv")
X = X[X["t"] >= 2023 * 4 - 2]            # origins of the evaluated Lead-2 targets (2023-Q1 onward)

# variable: (driver, source, geography, frequency, value at origin O(t), transformation, expected sign, role, limitation)
M = {
 "F_last": ("D1 prices", "PSA CPI food YoY (OpenSTAT 0012M4ACP22)", "province", "monthly", "quarter t-1 mean (complete)", "mean of 3 published YoY", "+", "predictor", "-"),
 "F_now": ("D1 prices", "PSA CPI food YoY", "province", "monthly", "months 1-2 of quarter t", "mean of 2 published YoY", "+", "predictor", "month 3 not yet published at O(t)"),
 "gap_now": ("D1 prices", "PSA CPI food and all-items YoY", "province", "monthly", "months 1-2 of quarter t", "food minus headline YoY", "+", "predictor", "-"),
 "mom3": ("D1 prices", "PSA CPI food index", "province", "monthly", "m0 vs m0-3", "100 x log change", "+", "predictor", "-"),
 "F_hat_k": ("D1 prices", "PSA CPI food index", "province", "monthly", "index to m0; base months 12 earlier", "base-effect projection of target-quarter YoY (12-month drift)", "+", "predictor", "drift misses policy and weather breaks"),
 "G_hat_k": ("D1 prices", "PSA CPI food and all-items index", "province", "monthly", "index to m0", "projected food minus headline YoY", "+", "predictor", "-"),
 "D_now": ("D1 prices", "PSA CPI food YoY", "province", "monthly", "months 1-2 of quarter t", "F_now minus five-province mean", "+", "predictor", "relative only"),
 "rice_whsl_yoy": ("D1 prices", "PSA wholesale rice prices", "province", "monthly->quarter", "quarter t-1", "YoY % of quarter mean", "+", "predictor", "wholesale, not retail"),
 "tariff_yoy_regime": ("D1 prices (policy)", "EO 62 s.2024 (lawphil)", "national", "event", "announced before O(t)", "share of target months whose YoY compares post-cut with pre-cut", "-", "predictor", "events list ends 2025-12"),
 "import_suspension_share": ("D1 prices (policy)", "EO 93/102 s.2025", "national", "event", "announced before O(t)", "share of target months in force", "-/+", "predictor", "events list ends 2025-12"),
 "price_ceiling_share": ("D1 prices (policy)", "EO 39 s.2023", "national", "event", "announced before O(t)", "share of target months in force", "-", "predictor", "-"),
 "food_emergency_share": ("D1 prices (policy)", "DA DC 3 s.2025", "national", "event", "announced before O(t)", "share of target months in force", "-", "predictor", "end date = stated window"),
 "tc_count": ("D2 climate", "NOAA IBTrACS tracks (not PAGASA)", "province (300 km)", "event", "quarter t", "count of tropical cyclones within 300 km", "+", "predictor", "exposure, not observed damage; 2026-Q3 incomplete"),
 "tc_max_signal": ("D2 climate", "IBTrACS / PAGASA signal bands", "province", "event", "quarter t", "max wind-signal band", "+", "predictor", "exposure"),
 "tc_severe": ("D2 climate", "IBTrACS", "province", "event", "quarter t", "severe-cyclone flag", "+", "predictor", "exposure"),
 "enso": ("D2 climate", "NOAA CPC ONI", "global index", "monthly", "quarter t-1", "El Nino 1 / neutral 0 / La Nina -1", "+ (El Nino)", "predictor", "not local"),
 "palay_yoy": ("D3 agriculture", "PSA palay production (OpenSTAT)", "province", "quarterly", "quarter t-1", "YoY %", "-", "predictor", "observed output, not damage"),
 "corn_yoy": ("D3 agriculture", "PSA corn production", "province", "quarterly", "quarter t-1", "YoY %", "-", "predictor", "-"),
 "fish_yoy": ("D3 agriculture", "PSA fisheries production", "province", "quarterly", "quarter t-1", "YoY %", "-", "predictor", "-"),
 "aqua_yoy": ("D3 agriculture", "PSA aquaculture production", "province", "quarterly", "quarter t-1", "YoY %", "-", "predictor", "-"),
 "ur_last": ("D4 household economy", "PSA LFS unemployment rate", "national", "monthly", "quarter t-1", "quarter mean", "+", "predictor", "national only; no provincial monthly LFS"),
 "ur_yoy": ("D4 household economy", "PSA LFS", "national", "monthly", "quarter t-1", "change vs t-5", "+", "predictor", "national only"),
 "under_last": ("D4 household economy", "PSA LFS underemployment", "national", "monthly", "quarter t-1", "quarter mean", "+", "predictor", "national only"),
 "remit_usd_yoy": ("D4 household economy", "BSP OFW cash remittances", "national", "monthly", "quarter t-1", "YoY %", "-", "predictor", "national only"),
 "fx_yoy": ("D4 household economy", "BSP USD/PHP", "national", "monthly", "quarter t-1", "YoY %", "+", "predictor", "-"),
 "H_last": ("Hunger history (target component)", "SWS Balance Luzon involuntary hunger", "region", "quarterly survey", "latest round posted before O(t)", "level %", "+", "lagged outcome", "sampling error approx. +/-4-5 pp (Balance Luzon)"),
 "H_chg": ("Hunger history", "SWS", "region", "quarterly", "latest two posted", "difference", "+", "lagged outcome", "-"),
 "H_age": ("Hunger history", "SWS", "region", "quarterly", "latest posted", "quarters since the reading", "?", "data-quality", "-"),
 "news_market": ("D5 news (v0, E40)", "Google News RSS headlines", "province", "daily", "quarter t, published before O(t)", "share of articles hitting the trigger lexicon", "+", "predictor", "headline-only; collected 2026-10-14 retroactively"),
 "news_climate": ("D5 news (v0)", "as above", "province", "daily", "as above", "share", "+", "predictor", "as above"),
 "news_n": ("D5 news (v0)", "as above", "province", "daily", "as above", "article count", "?", "coverage", "corpus growth"),
 "n3_fssi": ("D5 news (E64 N3)", "headlines + XLM-R intensity", "province", "daily", "quarter t before O(t)", "FSSI-v3", "+", "predictor", "-"),
 "n3_market_rw": ("D5 news (E64 N3)", "headlines, classifier v2", "province", "daily", "before O(t)", "recency-weighted count (30-day half-life)", "+", "predictor", "not volume-normalised"),
 "ev_adv_prices": ("D5 news (E83 N2 events)", "headlines + lead text where recovered", "province shrunk to region (kappa 5)", "daily", "quarter t before O(t)", "adverse events per 100 collected articles, severity-weighted", "+", "predictor", "sparse: ~6 relevant articles per province-quarter"),
 "ev_net_all": ("D5 news (E83 N2)", "as above", "as above", "daily", "as above", "adverse minus improving events, all drivers", "+", "predictor", "as above"),
 "ev_net_all_d": ("D5 news (E83 N2)", "as above", "as above", "daily", "quarters t and t-1", "change in net adverse events", "+", "predictor", "as above"),
 "ld_cov": ("D5 news (E83 N1 lead text)", "publisher lead text (DA, BusinessWorld, DSWD FO4A, SunStar)", "region", "daily", "before O(t)", "share of relevant articles with recovered lead", "?", "coverage", "lead text mostly government press releases"),
 "sim_p": ("Structural (all)", "derived from CPI and SWS", "province", "-", "O(t)", "Monte Carlo P(T43 HIGH at t+k)", "+", "derived estimate", "independence of hunger and price assumed"),
}
rows = []
for v, m in M.items():
    miss = f"{100 * X[v].isna().mean():.0f}%" if v in X else "n/a"
    rows.append("| " + " | ".join([f"`{v}`", m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], miss, m[8]]) + " |")
head = ("| Variable | Driver | Source | Geography | Frequency | Value used at origin O(t) | Transformation | Expected sign | "
        "Role | Missing (Lead-2 eval origins) | Limitation |\n|" + "---|" * 11)
text = ("# E83 data dictionary\n\nAll inputs are restricted to 2021-01 .. data published by 2026-10-14. O(t) = first day of quarter t+1. "
        "Target T43 is a constructed proxy (PROTOCOL section 2), not an observed food-insecurity rate. FNRI FIES (NNS 2025: "
        "CALABARZON 22.6% moderate or severe, region only, secondary reporting) is an external face-validity reference "
        "only; no municipal outcome exists.\n\n" + head + "\n" + "\n".join(rows) + "\n")
(run.parents[1] / "DATA_DICTIONARY.md").write_text(text, encoding="utf-8")
print(text[:600])
