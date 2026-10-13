"""
app/ml/features/feature_matrix.py
------------------------------------
Multi-scale fused feature matrix builder (province-quarter level).

Fuses ALL eleven primary-data parquets with NLP features into a single
training-ready DataFrame. This is the input to LightGBM.

Feature groups and sources:
  1. NLP / FSSI      : FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel
  2. Triggers (5-cat): trigger_market, trigger_climate, trigger_employment,
                       trigger_ofw_remittance, trigger_fish_kill (proportions)
  3. Food CPI        : food_cpi, food_cpi_yoy, food_minus_headline_yoy
  4. Rice prices     : rice_price_regular (PSA wholesale RMR, live, 2021-)
  5. Macro / Labour  : unemployment_rate, poverty_incidence
  6. BSP             : ofw_remit_yoy_pct, fx_usd_php_avg
  7. Fuel            : diesel_php_per_l, brent_usd_per_bbl
  8. Climate         : tc_count, rainfall_anomaly_pct, enso_numeric, drought_alert
  9. Commodity basket: veg_price_mean, fish_price_mean, livestock_price_mean
 10. BERTopic props  : topic_N_pct columns (supplementary, if available)

NOTE: pct_total_hunger (SWS) is NOT included here. The primary label label_stress is the
composite SWS hunger + PSA food CPI deviation score thresholded at the global median, so
including SWS hunger directly as a feature would be label leakage. The label generator
reads sws_hunger.parquet independently.

LightGBM formula reference (Backend Guide v3):
    y_hat_p,t+3 = F(FSSI_t, FSSI_t-1, FSSI_t-2, dFSSI_t,
                    trigger_5cat_t, BERTopic_t, food_CPI_t, headline_CPI_t,
                    food_minus_headline_yoy_t, rice_t, commodity_basket_t,
                    tc_count_t, rainfall_anom_t, ENSO_t, drought_t,
                    ofw_remit_t, fx_php_usd_t, diesel_t, gasoline_t,
                    brent_t, unemployment_t, poverty_incidence_t)

Usage:
    from app.ml.features.feature_matrix import build_feature_matrix
    features_df = build_feature_matrix()
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_PATH = Path("data/processed/features_fused.parquet")

CALABARZON_PROVINCES = [
    "PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000",
]

# Section 3.3.2.6 / 3.3.1.1: the training window is 2020-Q1 through 2025-Q4 —
# 24 quarters across 5 provinces, the 120-row backbone grid the approved
# methodology fuses onto. The window is a methodological constant, not a
# calendar-tracking value: Algorithm 3's fold structure, the 4-quarter holdout
# in Algorithm 4 and the "120 province-quarter pairs" median in Equation 3 are
# all defined against it.
MODEL_START_YEAR = 2020
MODEL_END_QUARTER = "2025-Q4"

# Equation 5, CPI_dev: trailing quarters in the province's own rolling mean.
CPI_DEV_WINDOW = 4


def last_completed_quarter(today: date | None = None) -> str:
    """
    The most recent quarter that has actually finished.

    Used by the quarterly scheduler (Rule 1, Quarter Self-Update) to name the
    cycle being run. It does NOT set the training window — see MODEL_QUARTERS.
    """
    today = today or datetime.now(timezone.utc).date()
    q = (today.month - 1) // 3 + 1
    year, q = (today.year - 1, 4) if q == 1 else (today.year, q - 1)
    return f"{year}-Q{q}"


def model_quarters(start_year: int = MODEL_START_YEAR,
                   end_quarter: str = MODEL_END_QUARTER) -> list[str]:
    """Every quarter from start_year-Q1 through end_quarter, inclusive."""
    end_year, end_q = int(end_quarter[:4]), int(end_quarter[-1])
    return [f"{yr}-Q{q}"
            for yr in range(start_year, end_year + 1)
            for q in range(1, 5)
            if (yr, q) <= (end_year, end_q)]


# 2020-Q1 .. 2025-Q4 — 24 quarters; × 5 provinces = the 120-row backbone.
MODEL_QUARTERS: list[str] = model_quarters()

# ENSO phase → numeric encoding (for LightGBM ordinal)
ENSO_ENCODE: dict[str, int] = {
    "LA_NINA":   -1,
    "NEUTRAL":    0,
    "EL_NINO":    1,
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _fix_cpi_quarter(q: str) -> str:
    """Fix cpi_full.parquet quarter format '2020.0-Q1.0' → '2020-Q1'."""
    try:
        parts = str(q).split("-")
        year = parts[0].split(".")[0]          # '2020.0' → '2020'
        qpart = parts[1].split(".")[0]         # 'Q1.0'  → 'Q1'
        return f"{year}-{qpart}"
    except Exception:
        return q


def _quarter_to_int(q: str) -> int:
    try:
        year, qpart = q.split("-")
        return int(year) * 4 + int(qpart[1]) - 1
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Individual source loaders
# ---------------------------------------------------------------------------

def _load_fssi(path: Path) -> pd.DataFrame:
    """
    Load the FSSI level only.

    The lags and the acceleration are deliberately NOT taken from this file.
    `fssi_builder` computes them with `shift(1)` over the rows it holds, and it
    holds only the province-quarters that have at least one retained article --
    110 of the 120 here. A shift over that frame reaches the last quarter that
    carried news, not the previous calendar quarter, so after a gap `FSSI_lag1`
    named a quarter two or three periods back and `FSSI_accel` reported a change
    that spanned the gap. They are rebuilt below on the completed 120-row
    backbone, by the same true calendar shift every other lag feature uses.
    """
    df = pd.read_parquet(path)
    cols = ["province_code", "quarter", "FSSI"]
    return df[[c for c in cols if c in df.columns]].copy()


def _load_triggers(path: Path) -> pd.DataFrame:
    """Load 5-category trigger proportions."""
    df = pd.read_parquet(path)
    trigger_cols = [
        "trigger_market", "trigger_climate", "trigger_employment",
        "trigger_ofw_remittance", "trigger_fish_kill",
    ]
    keep = ["province_code", "quarter"] + [c for c in trigger_cols if c in df.columns]
    return df[keep].copy()


def _load_psa(path: Path) -> pd.DataFrame:
    """Load PSA OpenStat indicators: food_cpi, food_cpi_yoy, rice_price, unemployment, poverty."""
    df = pd.read_parquet(path)
    keep = [
        "province_code", "quarter",
        "food_cpi", "food_cpi_yoy", "rice_price_regular",
        "unemployment_rate", "poverty_incidence",
    ]
    return df[[c for c in keep if c in df.columns]].copy()


def _load_cpi_full(path: Path) -> pd.DataFrame:
    """Load headline CPI and food-vs-headline gap feature."""
    df = pd.read_parquet(path)
    df["quarter"] = df["quarter"].apply(_fix_cpi_quarter)
    # cpi_food_nab / cpi_food_yoy_pct are the same food CPI that
    # psa_indicators.parquet carries as food_cpi / food_cpi_yoy -- but this
    # fetcher is live and that one stopped at 2025-Q4, so 2026 food CPI was
    # being forward-filled from 2025-Q4 while the real values sat here unused.
    # They are emitted under _live names and given precedence after the merge.
    keep = ["province_code", "quarter", "cpi_food_minus_general_yoy",
            "cpi_all_items", "cpi_food_nab", "cpi_food_yoy_pct"]
    out = df[[c for c in keep if c in df.columns]].copy()
    out = out.rename(columns={
        "cpi_food_minus_general_yoy": "food_minus_headline_yoy",
        "cpi_all_items": "headline_cpi",
        "cpi_food_nab": "food_cpi_live",
        "cpi_food_yoy_pct": "food_cpi_yoy_live",
    })
    return out


def _load_bsp(path: Path) -> pd.DataFrame:
    """Load BSP OFW remittance growth and FX rate."""
    df = pd.read_parquet(path)
    keep = ["province_code", "quarter", "ofw_remit_yoy_pct", "fx_usd_php_avg"]
    return df[[c for c in keep if c in df.columns]].copy()


def _load_oil(path: Path) -> pd.DataFrame:
    """Load DOE/EIA fuel prices."""
    df = pd.read_parquet(path)
    keep = [
        "province_code", "quarter",
        "diesel_php_per_l", "gasoline_php_per_l", "brent_usd_per_bbl",
    ]
    return df[[c for c in keep if c in df.columns]].copy()


MEASURED_RAINFALL_PATH = Path("data/processed/province_rainfall.parquet")


def _load_pagasa(path: Path) -> pd.DataFrame:
    """
    Load climate features: tc_count, rainfall_anomaly, ENSO, drought.

    rainfall_anomaly_pct is taken from province_rainfall.parquet when present --
    NASA POWER PRECTOTCORR measured at interior sample points per province,
    anomaly against the 1991-2020 WMO normal (scripts/build_province_rainfall.py).
    The PAGASA table supplies it only as a fallback, and there it is a single
    CALABARZON series inherited to every province: its province split was
    manufactured as Quezon x a constant and was demoted on 2026-09-01.

    Measured cross-province correlation is 0.938 (Batangas-Rizal 0.875,
    Laguna-Quezon 0.998) against exactly 1.0000 for the manufactured series --
    adjacent provinces genuinely share weather systems, but they are no longer
    identical by construction.
    """
    df = pd.read_parquet(path)
    keep = [
        "province_code", "quarter",
        "tc_count", "tc_severe_flag", "rainfall_anomaly_pct",
        "enso_phase", "drought_alert",
    ]
    out = df[[c for c in keep if c in df.columns]].copy()
    if "enso_phase" in out.columns:
        out["enso_numeric"] = out["enso_phase"].map(ENSO_ENCODE).fillna(0).astype(int)
        out = out.drop(columns=["enso_phase"])

    if MEASURED_RAINFALL_PATH.exists():
        measured = pd.read_parquet(MEASURED_RAINFALL_PATH)[
            ["province_code", "quarter", "rainfall_anomaly_pct"]
        ].rename(columns={"rainfall_anomaly_pct": "rainfall_measured"})
        out = out.merge(measured, on=["province_code", "quarter"], how="left")
        n_measured = int(out["rainfall_measured"].notna().sum())
        out["rainfall_anomaly_pct"] = out["rainfall_measured"].fillna(
            out.get("rainfall_anomaly_pct")
        )
        out = out.drop(columns=["rainfall_measured"])
        logger.info(
            "_load_pagasa: rainfall_anomaly_pct from NASA POWER for %d of %d "
            "province-quarters (remainder falls back to the regional series)",
            n_measured, len(out),
        )
    else:
        logger.warning(
            "_load_pagasa: %s not found -- rainfall_anomaly_pct falls back to the "
            "CALABARZON-level series with no province variation. Run "
            "scripts/build_province_rainfall.py for measured values.",
            MEASURED_RAINFALL_PATH,
        )
    return out


def _load_commodity(path: Path) -> pd.DataFrame:
    """
    Load PSA NRP commodity prices and pivot to wide format.

    commodity_group → mean price per province-quarter.
    Groups: fruit_veg, fish, livestock/poultry, others.
    """
    df = pd.read_parquet(path)
    if "province_code" not in df.columns or "commodity_group" not in df.columns:
        logger.warning("_load_commodity: unexpected schema, returning empty.")
        return pd.DataFrame()

    # Pivot: mean price per commodity_group per province-quarter
    pivot = (
        df.groupby(["province_code", "quarter", "commodity_group"])["price_php_per_kg"]
        .mean()
        .reset_index()
        .pivot_table(
            index=["province_code", "quarter"],
            columns="commodity_group",
            values="price_php_per_kg",
            aggfunc="mean",
        )
        .reset_index()
    )

    # Rename columns to avoid conflicts
    pivot.columns = [
        f"commodity_{c}" if c not in ("province_code", "quarter") else c
        for c in pivot.columns
    ]
    return pivot


def _load_sws(path: Path) -> pd.DataFrame:
    """
    Intentionally returns an empty DataFrame.

    pct_total_hunger is the raw SWS value used in the composite stress score
    that defines label_stress = stress_score > global_median, where
    stress_score = sws_hunger + 2 * (food_cpi_yoy - regional_mean). Including
    pct_total_hunger as a training feature would be label leakage. The label
    generator reads sws_hunger.parquet directly and independently.
    """
    return pd.DataFrame()


def _load_rice_prices(path: Path) -> pd.DataFrame:
    """
    Load live PSA wholesale Regular Milled Rice prices (2021 to present).

    This replaces the old Ricelytics gap-fill. commodity_prices.parquet carries
    real PSA NRP retail prices only through 2021 -- that table was retired with
    the 2012-based series -- and everything after it was CPI-food-YoY
    extrapolated from a 2021-Q4 anchor. The series loaded here is observed for
    every quarter in the window, so it takes precedence over that extrapolation
    rather than merely filling its gaps.
    """
    df = pd.read_parquet(path)
    rice = (df[df["rice_class"] == "regular_milled"].copy()
            if "rice_class" in df.columns else df.copy())
    if rice.empty:
        return pd.DataFrame()
    rice = rice.rename(columns={"price_php_per_kg": "psa_rice_price_regular"})
    keep = ["province_code", "quarter", "psa_rice_price_regular"]
    return rice[[c for c in keep if c in rice.columns]].copy()


def _load_topic_proportions(path: Path) -> pd.DataFrame | None:
    """Load BERTopic province-quarter proportions (optional)."""
    if not path.exists():
        logger.info("_load_topic_proportions: file not found (%s) — skipping BERTopic features.", path)
        return None
    df = pd.read_parquet(path)
    logger.info("_load_topic_proportions: loaded %d rows, %d topic columns", len(df), len(df.columns) - 2)
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_feature_matrix(
    fssi_path:       Path = Path("data/processed/fssi_quarterly.parquet"),
    triggers_path:   Path = Path("data/processed/trigger_proportions.parquet"),
    psa_path:        Path = Path("data/processed/psa_indicators.parquet"),
    cpi_full_path:   Path = Path("data/processed/cpi_full.parquet"),
    bsp_path:        Path = Path("data/processed/bsp_macro.parquet"),
    oil_path:        Path = Path("data/processed/oil_prices.parquet"),
    pagasa_path:     Path = Path("data/processed/pagasa_climate.parquet"),
    commodity_path:  Path = Path("data/processed/commodity_prices.parquet"),
    sws_path:        Path = Path("data/processed/sws_hunger.parquet"),
    ricelytics_path: Path = Path("data/processed/psa_rice_prices.parquet"),
    # Section 3.3.2.6 fuses ten sources into a 120 x 45 matrix and does not list
    # BERTopic among them. Topic proportions are Objective 1's latent risk
    # patterns, reported on their own; they enter the matrix only if a path is
    # passed explicitly.
    topic_path:      Path | None = None,
    save_path:       Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """
    Fuse all eleven primary-data sources + NLP features into features_fused.parquet.

    All sources are merged on (province_code, quarter) using left joins from
    a backbone grid of 5 provinces × every quarter in MODEL_QUARTERS. NaN values
    from missing coverage are forward-filled where safe (macro series), then
    zero-filled as a last resort with a flag.

    Returns
    -------
    pd.DataFrame
        province_code, quarter (join keys) + all feature columns.
        Filtered to MODEL_QUARTERS (2020-Q1 through 2025-Q4), 5 CALABARZON
        provinces only — the 120-row backbone of Section 3.3.2.6.
    """

    # --- Backbone grid: 5 provinces × every quarter in the window ---
    logger.info("feature matrix window: %s .. %s (%d quarters)",
                MODEL_QUARTERS[0], MODEL_QUARTERS[-1], len(MODEL_QUARTERS))
    backbone = pd.DataFrame([
        {"province_code": p, "quarter": q}
        for p in CALABARZON_PROVINCES
        for q in MODEL_QUARTERS
    ])
    backbone["_q_int"] = backbone["quarter"].apply(_quarter_to_int)
    backbone = backbone.sort_values(["province_code", "_q_int"])

    def _left_merge(base: pd.DataFrame, right: pd.DataFrame, tag: str) -> pd.DataFrame:
        if right.empty:
            logger.warning("_left_merge[%s]: empty DataFrame — skipping.", tag)
            return base
        before = len(base)
        merged = base.merge(right, on=["province_code", "quarter"], how="left")
        new_cols = [c for c in merged.columns if c not in base.columns]
        na_counts = {c: merged[c].isna().sum() for c in new_cols if merged[c].isna().any()}
        if na_counts:
            logger.debug("_left_merge[%s]: NaN counts after merge: %s", tag, na_counts)
        return merged

    # Build merged DataFrame step by step
    df = backbone.copy()

    # 1. FSSI
    try:
        df = _left_merge(df, _load_fssi(fssi_path), "FSSI")
    except FileNotFoundError:
        logger.warning("FSSI parquet not found at %s — FSSI features will be NaN.", fssi_path)

    # 2. Trigger proportions
    try:
        df = _left_merge(df, _load_triggers(triggers_path), "Triggers")
    except FileNotFoundError:
        logger.warning("Trigger proportions not found — trigger features will be NaN.")

    # 3. PSA indicators
    df = _left_merge(df, _load_psa(psa_path), "PSA")

    # 4. CPI full (food-vs-headline gap)
    df = _left_merge(df, _load_cpi_full(cpi_full_path), "CPI_Full")
    # Provincial PSA wins; the region-level series only fills what it leaves
    # empty. cpi_full is OpenStat table 0012M4ACP22 queried at the Region IV-A
    # geocode and cross-joined to the five provinces ("Region IV-A inherited to
    # provinces", per its own source_note), so it is identical across provinces
    # in every quarter. psa_indicators is table 0012M4ACP23 queried per
    # province, and does vary. Letting the region copy win erased the
    # provincial dimension of food_cpi_yoy -- the one term in Equation 3 that
    # separates provinces within a quarter, and an input Equation 5 names per
    # province. Section 3.3.1.2 specifies provincial indicators, so the
    # provincial source takes precedence. The live series still covers quarters
    # PSA has not published, which is what it was added for; inside the
    # approved window PSA is complete, so there it changes nothing.
    for live, stale in (("food_cpi_live", "food_cpi"),
                        ("food_cpi_yoy_live", "food_cpi_yoy")):
        if live in df.columns:
            df[stale] = (df[stale].combine_first(df[live])
                         if stale in df.columns else df[live])
    df = df.drop(columns=["food_cpi_live", "food_cpi_yoy_live"], errors="ignore")

    # 5. BSP macro
    df = _left_merge(df, _load_bsp(bsp_path), "BSP")

    # 6. Oil prices
    df = _left_merge(df, _load_oil(oil_path), "Oil")

    # 7. PAGASA climate
    df = _left_merge(df, _load_pagasa(pagasa_path), "PAGASA")

    # 8. Commodity prices (PSA NRP — wide pivot)
    try:
        df = _left_merge(df, _load_commodity(commodity_path), "Commodity")
    except Exception as exc:
        logger.warning("Commodity prices failed to load: %s", exc)

    # 9. Live PSA wholesale rice prices, 2021 to present
    try:
        rice_ext = _load_rice_prices(ricelytics_path)
        if not rice_ext.empty:
            df = _left_merge(df, rice_ext, "PSA rice")
            if "psa_rice_price_regular" in df.columns:
                if "rice_price_regular" not in df.columns:
                    df["rice_price_regular"] = pd.NA
                # The observed series wins wherever it exists; the extrapolated
                # commodity_prices value survives only where PSA suppressed the
                # cell. Before this, four years of extrapolation outranked real
                # data purely because it was merged first.
                before = df["rice_price_regular"].notna().sum()
                df["rice_price_regular"] = df["psa_rice_price_regular"].combine_first(
                    df["rice_price_regular"]
                )
                logger.info(
                    "rice_price_regular: %d of %d rows now come from the live "
                    "PSA series (was %d rows of mixed real/extrapolated)",
                    int(df["psa_rice_price_regular"].notna().sum()), len(df), before,
                )
    except Exception as exc:
        logger.warning("PSA rice load failed: %s", exc)

    # 11. BERTopic proportions (optional)
    topic_df = _load_topic_proportions(topic_path) if topic_path is not None else None
    if topic_df is not None:
        df = _left_merge(df, topic_df, "BERTopic")

    # --- Post-merge cleanup ---

    # Coerce every feature column to a numeric dtype before the fill rule runs.
    # A source that yields nothing leaves an all-None column of dtype object,
    # which silently escapes both the forward fill and the zero fill below --
    # `rainfall_anomaly_pct` reached the model that way, entirely empty, and
    # broke three of the Research Question 3 baselines before it was caught.
    # Coercing first means a dead source produces zeros the fill rule accounts
    # for, and feature_provenance.json records how many.
    for col in df.columns:
        if col in ("province_code", "quarter"):
            continue
        if df[col].dtype == object:
            coerced = pd.to_numeric(df[col], errors="coerce")
            logger.warning(
                "%s arrived as dtype object (%d of %d values null); coerced to "
                "numeric so the Section 3.3.2.6 fill rule applies to it",
                col, int(coerced.isna().sum()), len(coerced),
            )
            df[col] = coerced

    # Section 3.3.2.6: "Sparse series will be forward-filled within each
    # province." Applied to every numeric column, which is what the approved
    # rule says — the fill is per-province so no value ever crosses a province
    # boundary, and forward-only so no value is ever drawn from a later quarter
    # (Rule 3, No Look-Ahead Bias).
    #
    # pct_total_hunger is not in this matrix at all — see module docstring. It
    # is an input to the label, so carrying it as a feature would be leakage.
    #
    # Every filled cell is recorded in feature_provenance.json. A forward-filled
    # value is indistinguishable from a measured one once it is in the matrix,
    # so without this record an exhausted source looks like full coverage. The
    # record changes no value; it reports what the approved fill rule did.
    provenance: dict[str, dict] = {}
    ff_cols = [c for c in df.select_dtypes(include=[np.number]).columns
               if c != "_q_int"]
    for col in ff_cols:
        missing_before = df[col].isna()
        if not missing_before.any():
            continue
        forward = df.groupby("province_code")[col].transform(lambda s: s.ffill())
        ff_mask = missing_before & forward.notna()
        # Leading gaps have no earlier observation to carry forward; they fall
        # through to the zero-fill below, which is the approved second clause.
        lead_mask = missing_before & forward.isna()
        df[col] = forward

        provenance[col] = {
            "forward_filled": int(ff_mask.sum()),
            "leading_gap": int(lead_mask.sum()),
            "forward_filled_quarters": sorted(df.loc[ff_mask, "quarter"].unique()),
            "leading_gap_quarters": sorted(df.loc[lead_mask, "quarter"].unique()),
        }
        if ff_mask.any():
            logger.info(
                "%s: %d cells carried forward within province (%s)",
                col, int(ff_mask.sum()),
                ", ".join(sorted(df.loc[ff_mask, "quarter"].unique())),
            )

    prov_path = Path("data/processed/feature_provenance.json")
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    prov_path.write_text(json.dumps(
        {"window": [MODEL_QUARTERS[0], MODEL_QUARTERS[-1]],
         "generated_at": datetime.now(timezone.utc).isoformat(),
         "imputed": provenance}, indent=2))
    if provenance:
        logger.warning("imputation summary written -> %s (%d columns affected)",
                       prov_path, len(provenance))

    # ── Temporal lag features for primary data (momentum signal) ─────────
    # Mirrors the FSSI_lag1/lag2/accel pattern that the model already uses.
    # Adds 1-quarter lag and acceleration (Δ vs t-1) for the most informative
    # primary signals: food prices, labor, climate, remittances, fuel.
    df = df.sort_values(["province_code", "quarter"]).reset_index(drop=True)
    LAG_FEATURES = [
        "FSSI",
        "food_cpi_yoy",
        "food_minus_headline_yoy",
        "unemployment_rate",
        "ofw_remit_yoy_pct",
        "rainfall_anomaly_pct",
        "rice_price_regular",
        "diesel_php_per_l",
    ]
    for col in LAG_FEATURES:
        if col in df.columns:
            df[f"{col}_lag1"]  = df.groupby("province_code")[col].shift(1)
            df[f"{col}_accel"] = df[col] - df[f"{col}_lag1"]

    # Equation 5 names a two-quarter FSSI lag as well, which no other feature
    # carries, so it is built here rather than in the loop above.
    if "FSSI" in df.columns:
        df["FSSI_lag2"] = df.groupby("province_code")["FSSI"].shift(2)

    # CPI_dev(t), Equation 5. The legend defines it as "food CPI deviation from
    # the rolling provincial mean": the province's food CPI year-on-year change
    # minus the mean of that same province's previous quarters. The model was
    # previously fed the raw food_cpi_yoy level in this slot, which is not a
    # deviation at all.
    #
    # The legend does not fix the window. Four quarters is used -- one year,
    # matching the year-on-year basis of the series -- over quarters t-4..t-1
    # only, so the mean never includes the quarter being estimated or any later
    # one (Rule 3). At least two prior quarters are required; the first
    # quarters of the window have none and are zero-filled below with every
    # other remaining gap (Section 3.3.2.6), which the provenance record counts.
    if "food_cpi_yoy" in df.columns:
        prior_mean = (
            df.groupby("province_code")["food_cpi_yoy"]
            .transform(lambda s: s.shift(1).rolling(CPI_DEV_WINDOW, min_periods=2).mean())
        )
        df["cpi_dev"] = df["food_cpi_yoy"] - prior_mean

    # Section 3.3.2.6: "Sparse series will be forward-filled within each
    # province; remaining gaps will be zero-filled." The forward fill above
    # covers the first clause; every numeric column still carrying a gap is
    # zero-filled here, which is the second.
    #
    # Each zero-filled cell is counted into the provenance record written
    # below, so a reader can always tell an imputed zero from a measured one.
    # The record changes no value — it only reports what the approved fill
    # rule did.
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    zero_filled = {c: int(df[c].isna().sum())
                   for c in numeric_cols if df[c].isna().any()}
    for col in zero_filled:
        df[col] = df[col].fillna(0.0)
    if zero_filled:
        logger.info(
            "zero-filled remaining gaps per Section 3.3.2.6: %s",
            ", ".join(f"{c}={n}" for c, n in sorted(zero_filled.items())),
        )
        for col, n in zero_filled.items():
            provenance.setdefault(col, {})["zero_filled"] = n
        prov_path.write_text(json.dumps(
            {"window": [MODEL_QUARTERS[0], MODEL_QUARTERS[-1]],
             "generated_at": datetime.now(timezone.utc).isoformat(),
             "imputed": provenance}, indent=2))

    # Drop helper column
    df = df.drop(columns=["_q_int"], errors="ignore")
    # Drop metadata columns that shouldn't be features
    df = df.drop(columns=["psa_rice_price_regular"], errors="ignore")

    logger.info(
        "build_feature_matrix: final shape %s | %d feature columns",
        df.shape,
        len(df.columns) - 2,  # subtract province_code + quarter
    )

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(save_path, index=False)
        logger.info("Feature matrix saved → %s", save_path)

    return df
