"""E128 regional as-of panel: one row per (origin t, lead k), k = 1..4, origins 2021-Q1 .. 2026-Q3.

Features come from the E119 point-in-time regional dataset (features depend on the origin only; checked) plus a few
as-of transforms computed here from values that were themselves available at earlier issue dates. Targets are the
SWS Balance Luzon quarter means of non-commissioned rounds (FINAL_FOOD_INSECURITY_LIGHTGBM verified series). Read only.

    from build_panel import build
    panel, rounds = build()
"""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
X = ROOT.parent
INPUTS = {
    "e119_regional": X / "E119_Preprocessing/E119_REGIONAL_MODELING_DATASET.csv",
    "e119_n1": X / "E119_Preprocessing/out/indicators/N1/observations_clean.csv",
    "sws_rounds": X / "FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv",
}
ORIGINS = list(range(2021 * 4, 2026 * 4 + 3))          # 2021-Q1 .. 2026-Q3
LEADS = (1, 2, 3, 4)
HUNGER_THRESHOLD = 11.3                                # frozen E40 label_spec (2026-10-15); hunger term of T43c

GROUPS = {
    "hunger_history": ["H1_bl_latest", "H1_bl_change", "H1_bl_mean4", "H1_staleness_q"],
    "market": ["region_cpi_food_yoy_pct", "region_cpi_headline_yoy_pct", "farmgate_palay_yoy_pct", "food_yoy_change_1q",
               "C3_palay_corn_drop", "C4_fisheries_drop", "aquaculture_production_yoy_pct",
               "vegetables_rootcrops_production_yoy_pct"],
    "climate": ["C1_el_nino_in_force", "oni_quarter_mean", "typhoons_PAR", "rainfall_anomaly_mm", "temperature_anomaly_c"],
    "employment_ofw": ["unemployment_rate_pct", "E1_unemployment_change_pp", "E2_remittance_decline_pct"],
    "news_nlp": ["news_gdelt_agri_supply_share", "news_gdelt_assistance_share", "news_gdelt_jobs_income_share",
                 "news_gdelt_shortage_share", "news_local_articles_log"],
    "poverty_vulnerability": [],                       # no time-varying regional series (see the data inventory)
}
PRODUCTION = ["C3_palay_corn_drop", "C4_fisheries_drop", "aquaculture_production_yoy_pct", "vegetables_rootcrops_production_yoy_pct"]
ALL_FEATURES = [f for g in GROUPS.values() for f in g]
OFFICIAL = GROUPS["market"] + GROUPS["employment_ofw"]  # PSA (CPI, farmgate, production, LFS) + BSP remittances
NEWS = GROUPS["news_nlp"]


def qs(q):
    return f"{q // 4}-Q{q % 4 + 1}"


def qparse(s):
    y, k = s.split("-Q")
    return int(y) * 4 + int(k) - 1


def qstart(q):
    return date(q // 4, (q % 4) * 3 + 1, 1)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sws_quarters(rounds):
    r = rounds[~rounds["commissioned"].astype(bool)].copy()
    r["q"] = r["quarter"].map(qparse)
    r["published"] = pd.to_datetime(r["published"]).dt.date
    return r


def known_quarter_means(r, issue):
    """Quarter means of Balance Luzon from rounds published before the issue date (partial quarters included, as at the time)."""
    k = r[r["published"] < issue]
    return k.groupby("q")["balance_luzon"].mean().sort_index()


def build():
    reg = pd.read_csv(INPUTS["e119_regional"])
    rounds = pd.read_csv(INPUTS["sws_rounds"])
    n1 = pd.read_csv(INPUTS["e119_n1"])
    r = sws_quarters(rounds)
    final = r.groupby("q").agg(y=("balance_luzon", "mean"), published=("published", "max"), n_rounds=("balance_luzon", "size"))

    base = reg[reg["lead"] == 1].copy()
    base["t"] = base["origin"].map(qparse)
    base = base.set_index("t").sort_index()
    for c in [c for c in base.columns if c.endswith("__period")]:
        base[c] = base[c].astype(str)

    arts = n1[n1["feature"] == "N1_admitted_articles"].groupby("period")["value"].sum()   # 5 provinces, quarter of publication
    rows = []
    for t in ORIGINS:
        iss = qstart(t + 1)
        b = base.loc[t]
        km = known_quarter_means(r, iss)
        feat = {c: b.get(c, np.nan) for c in ALL_FEATURES if c in base.columns}
        feat["H1_bl_mean4"] = km.tail(4).mean() if len(km) else np.nan
        prev = base.loc[t - 1, "region_cpi_food_yoy_pct"] if (t - 1) in base.index else np.nan
        feat["food_yoy_change_1q"] = b["region_cpi_food_yoy_pct"] - prev if pd.notna(prev) else np.nan
        # local news volume: quarter t-1 (complete before the issue; same rule E119 uses for the GDELT shares)
        feat["news_local_articles_log"] = np.log1p(arts.get(t - 1, np.nan)) if (t - 1) in arts.index else np.nan
        latest_q = km.index.max() if len(km) else np.nan
        for k in LEADS:
            tq = t + k
            lab = final.loc[tq] if tq in final.index else None
            rows.append({
                "origin": qs(t), "t": t, "issue_date": iss.isoformat(), "lead": k, "target_quarter": qs(tq), "target_q": tq,
                "target_quarter_end": (qstart(tq + 1)).isoformat(),
                "months_issue_to_target_end": 3 * k,
                "latest_sws_quarter": qs(int(latest_q)) if pd.notna(latest_q) else "",
                "latest_sws_published": r[r["published"] < iss]["published"].max().isoformat() if len(km) else "",
                "true_sws_horizon_q": (tq - int(latest_q)) if pd.notna(latest_q) else np.nan,
                "latest_cpi_period": b["region_cpi_food_yoy_pct__period"],
                "latest_news_period": b["news_gdelt_shortage_share__period"],
                "y_bl_hunger": lab["y"] if lab is not None else np.nan,
                "y_published": lab["published"].isoformat() if lab is not None else "",
                "y_n_rounds": int(lab["n_rounds"]) if lab is not None else 0,
                **feat,
            })
    panel = pd.DataFrame(rows)
    panel["y_high"] = np.where(panel["y_bl_hunger"].notna(), (panel["y_bl_hunger"] > HUNGER_THRESHOLD).astype(float), np.nan)
    assert panel["t"].min() >= 2021 * 4 and panel["target_q"].min() >= 2021 * 4, "pre-2021 row"
    return panel, r


def input_hashes():
    return {k: sha(v) for k, v in INPUTS.items()}


if __name__ == "__main__":
    p, _ = build()
    print(p.shape)
    print(p[p.lead == 1][["origin", "issue_date", "target_quarter", "y_bl_hunger", "y_high", "H1_bl_latest", "H1_bl_mean4",
                          "news_local_articles_log", "food_yoy_change_1q"]].to_string())
