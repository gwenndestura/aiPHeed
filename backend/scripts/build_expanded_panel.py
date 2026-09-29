"""
scripts/build_expanded_panel.py
----------------------------------
A SEPARATE, expanded companion to build_thesis_panel.py -- kept side by
side, not replacing it. build_thesis_panel.py stays exactly faithful to the
paper's 12 features (Equation 5); this script answers a different question:
"if every real government dataset already collected in this project is
used, at the same province-quarter grain and the same label_cpi target,
does real performance actually improve?"

Same label (label_cpi, Eq. 4 -- still the only one with full real coverage)
and same province x quarter grain as the thesis model. Adds real data from
sources the 12-feature model does not touch:
    PAGASA/NOAA climate  -- tc_count, tc_severe_flag, drought_alert,
                             rainfall_anomaly_pct
    BSP macro            -- ofw_remit_yoy_pct, fx_usd_php_avg (REAL
                             government OFW data, unlike the news-derived
                             trigger_ofw_remittance the 12-feature model
                             relies on)
    FRED/DOE fuel         -- diesel_php_per_l, brent_usd_per_bbl
    PSA poverty           -- poverty_incidence (annual; same real value
                             held across a year's quarters, not fabricated)
    NASA POWER agroclimate-- t2m_anomaly_pct, gwetroot_anomaly_pct
    PSA fuller CPI        -- cpi_food_minus_general_yoy

All real, already-collected data. Missing cells left as NaN, same as
build_thesis_panel.py -- LightGBM handles them natively.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ml.features import label_generator as lg

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "thesis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_FEATURE_COLS = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "trigger_market", "trigger_climate", "trigger_employment",
    "trigger_ofw_remittance", "trigger_fish_kill",
    "cpi_deviation", "unemployment_rate", "rice_price_qoq_change",
]
EXPANDED_FEATURE_COLS = BASE_FEATURE_COLS + [
    "tc_count", "tc_severe_flag", "drought_alert", "rainfall_anomaly_pct",
    "ofw_remit_yoy_pct", "fx_usd_php_avg",
    "diesel_php_per_l", "brent_usd_per_bbl",
    "poverty_incidence",
    "t2m_anomaly_pct", "gwetroot_anomaly_pct",
    "cpi_food_minus_general_yoy",
]


def _quarter_key(q: str) -> int:
    y, qn = q.split("-Q")
    return int(y) * 4 + int(qn)


def build_labels() -> pd.DataFrame:
    lg.MODEL_QUARTERS = [f"{yr}-Q{q}" for yr in range(2020, 2027) for q in range(1, 5)
                         if (yr, q) <= (2026, 3)]
    cpi_labels = lg._build_cpi_labels(ROOT / "data/processed/psa_indicators.parquet")
    return cpi_labels.rename(columns={"label_cpi": "label_stress"})


def build_base_features(labels: pd.DataFrame) -> pd.DataFrame:
    """Same 12 features as build_thesis_panel.py -- kept identical so the
    two panels are comparable apples-to-apples."""
    fssi = pd.read_parquet(ROOT / "data/processed/fssi_quarterly.parquet")[
        ["province_code", "quarter", "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]
    ]
    triggers = pd.read_parquet(ROOT / "data/processed/trigger_proportions.parquet")[
        ["province_code", "quarter", "trigger_market", "trigger_climate",
         "trigger_employment", "trigger_ofw_remittance", "trigger_fish_kill"]
    ]
    psa = pd.read_parquet(ROOT / "data/processed/psa_indicators.parquet")
    provinces = labels["province_code"].unique()
    unemp = psa[psa["province_code"].isin(provinces)][
        ["province_code", "quarter", "unemployment_rate"]
    ]

    cpi_full = psa[psa["province_code"].isin(provinces)][
        ["province_code", "quarter", "food_cpi"]
    ].copy()
    cpi_full["_qk"] = cpi_full["quarter"].map(_quarter_key)
    cpi_full = cpi_full.sort_values(["province_code", "_qk"])
    grp = cpi_full.groupby("province_code")["food_cpi"]
    cpi_full["cpi_rolling_mean"] = grp.transform(lambda s: s.rolling(window=24, min_periods=4).mean())
    cpi_full["cpi_deviation"] = cpi_full["food_cpi"] - cpi_full["cpi_rolling_mean"]
    cpi_dev = cpi_full[["province_code", "quarter", "cpi_deviation"]]

    rice = pd.read_parquet(ROOT / "data/processed/psa_rice_prices.parquet")
    rice = rice[rice["rice_class"] == "regular_milled"][
        ["province_code", "quarter", "price_php_per_kg"]
    ].drop_duplicates(subset=["province_code", "quarter"])
    rice["_qk"] = rice["quarter"].map(_quarter_key)
    rice = rice.sort_values(["province_code", "_qk"])
    rice["rice_price_qoq_change"] = rice.groupby("province_code")["price_php_per_kg"].diff()
    rice = rice[["province_code", "quarter", "rice_price_qoq_change"]]

    df = labels[["province_code", "quarter", "label_stress"]].copy()
    for src in (fssi, triggers, unemp, cpi_dev, rice):
        df = df.merge(src, on=["province_code", "quarter"], how="left")
    return df


def add_expanded_features(df: pd.DataFrame) -> pd.DataFrame:
    climate = pd.read_parquet(ROOT / "data/processed/pagasa_climate.parquet")[
        ["province_code", "quarter", "tc_count", "tc_severe_flag", "drought_alert"]
    ]
    # pagasa_climate's own rainfall_anomaly_pct is entirely null in this
    # dataset; province_rainfall.parquet (NASA POWER) has the real, complete
    # series for the same quantity -- used instead, not fabricated.
    rainfall = pd.read_parquet(ROOT / "data/processed/province_rainfall.parquet")[
        ["province_code", "quarter", "rainfall_anomaly_pct"]
    ]
    macro = pd.read_parquet(ROOT / "data/processed/bsp_macro.parquet")[
        ["province_code", "quarter", "ofw_remit_yoy_pct", "fx_usd_php_avg"]
    ]
    fuel = pd.read_parquet(ROOT / "data/processed/oil_prices.parquet")[
        ["province_code", "quarter", "diesel_php_per_l", "brent_usd_per_bbl"]
    ]
    agro = pd.read_parquet(ROOT / "data/processed/province_agroclimate.parquet")[
        ["province_code", "quarter", "t2m_anomaly_pct", "gwetroot_anomaly_pct"]
    ]
    cpi_full2 = pd.read_parquet(ROOT / "data/processed/cpi_full.parquet")[
        ["province_code", "quarter", "cpi_food_minus_general_yoy"]
    ].drop_duplicates(subset=["province_code", "quarter"])

    poverty = pd.read_parquet(ROOT / "data/processed/lgu_poverty.parquet")
    poverty_by_prov_year = (
        poverty.groupby(["province_code", "year"])["poverty_incidence_pct"]
        .mean().reset_index().rename(columns={"poverty_incidence_pct": "poverty_incidence"})
    )

    for src in (climate, rainfall, macro, fuel, agro, cpi_full2):
        df = df.merge(src, on=["province_code", "quarter"], how="left")

    df["_year"] = df["quarter"].str.slice(0, 4).astype(int)
    df = df.merge(poverty_by_prov_year, left_on=["province_code", "_year"],
                 right_on=["province_code", "year"], how="left")
    df = df.drop(columns=["_year", "year"])
    return df


def main() -> None:
    labels = build_labels()
    df = build_base_features(labels)
    df = add_expanded_features(df)
    df["_qk"] = df["quarter"].map(_quarter_key)
    df = df.sort_values(["province_code", "_qk"]).reset_index(drop=True)

    df.to_parquet(OUT_DIR / "panel_expanded.parquet", index=False)
    print(f"Built {len(df)} rows x {len(EXPANDED_FEATURE_COLS)} features "
          f"across {df['quarter'].nunique()} real quarters")
    missing = df[EXPANDED_FEATURE_COLS].isna().sum()
    print("Missing per feature (real gaps, left as NaN):")
    print(missing[missing > 0])
    print(f"Saved -> {OUT_DIR / 'panel_expanded.parquet'}")


if __name__ == "__main__":
    main()
