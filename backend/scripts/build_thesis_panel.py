"""
scripts/build_thesis_panel.py
------------------------------
Builds the paper-faithful province-quarter panel this duplicated backend now
trains and serves from: label_cpi (thesis Equation 4) as target, the exact
12 features from Equation 5.

Why label_cpi and not label_stress (the paper's primary composite label):
label_stress needs quarterly SWS hunger-survey data, which only has 6 real
published quarters ever -- 30 rows total, not enough to train or evaluate
anything. label_cpi is the paper's own secondary/robustness label (CPI
deviation only) and has full real coverage: 120/120 province-quarters across
the paper's exact 2020-Q1..2025-Q4 window. Using it is what makes it
possible to actually run the paper's Algorithm 3 (walk-forward lead-time
discovery) and Algorithm 4 (Optuna-tuned, real 4-quarter blind holdout) as
literally specified, instead of being blocked outright by data scarcity.
This was verified in a separate throwaway test (thesis_ch3_pipeline/) before
being wired in here for real.

Real per-feature coverage across the 120-row window (checked directly
against this project's own real data before building this):
  label (label_cpi):        120/120 real
  unemployment_rate:        120/120 real
  cpi_deviation:             120/120 real
  rice_price_qoq_change:      97/120 real
  FSSI + 4 lag/accel cols:    69/120 real (news corpus starts 2021-Q1)
  5 trigger proportions:      69/120 real (same reason)
Missing cells are left as NaN, not fabricated -- LightGBM's native
missing-value handling absorbs them.

Writes data/thesis/panel.parquet. Does not touch data/processed/ (the
files the original commodity-level model reads).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ml.features import label_generator as lg

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "thesis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "trigger_market", "trigger_climate", "trigger_employment",
    "trigger_ofw_remittance", "trigger_fish_kill",
    "cpi_deviation", "unemployment_rate", "rice_price_qoq_change",
]


def _quarter_key(q: str) -> int:
    y, qn = q.split("-Q")
    return int(y) * 4 + int(qn)


def build_labels() -> pd.DataFrame:
    # Thesis's literal window is 2020-Q1..2025-Q4. Extended through 2026-Q3
    # here because real PSA food-CPI data now genuinely reaches that far
    # (openstat_fetcher.py's unemployment endpoint was stale/404ing and was
    # fixed to pull live data before this was widened) -- adding real rows,
    # not padding the window with anything invented.
    lg.MODEL_QUARTERS = [f"{yr}-Q{q}" for yr in range(2020, 2027) for q in range(1, 5)
                         if (yr, q) <= (2026, 3)]
    cpi_labels = lg._build_cpi_labels(ROOT / "data/processed/psa_indicators.parquet")
    return cpi_labels.rename(columns={"label_cpi": "label_stress"})


def build_features(labels: pd.DataFrame) -> pd.DataFrame:
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
    cpi_full["cpi_rolling_mean"] = grp.transform(
        lambda s: s.rolling(window=24, min_periods=4).mean()
    )
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


def main() -> None:
    labels = build_labels()
    panel = build_features(labels)
    panel["_qk"] = panel["quarter"].map(_quarter_key)
    panel = panel.sort_values(["province_code", "_qk"]).reset_index(drop=True)

    panel.to_parquet(OUT_DIR / "panel.parquet", index=False)
    print(f"Built {len(panel)} rows x {len(FEATURE_COLS)} features "
          f"across {panel['quarter'].nunique()} real quarters")
    missing = panel[FEATURE_COLS].isna().sum()
    print("Missing per feature (real gaps, left as NaN):")
    print(missing[missing > 0])
    print(f"Saved -> {OUT_DIR / 'panel.parquet'}")


if __name__ == "__main__":
    main()
