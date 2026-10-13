"""
features.py
-----------
Twelve features. All of them come out of the panel itself.

The claim this folder is built to test is that a commodity's own production
history predicts its next shortfall better than forty external series do. So
every feature here is a transformation of one column -- `dev_pct`, the series'
percentage deviation from its own seasonal baseline -- plus the three
identifiers needed to tell one series from another.

No news corpus. No transformer. No CPI, fuel, remittance, unemployment,
poverty, rainfall, ENSO or cyclone feed. Nothing is fetched. If PSA publishes
the production table, the model runs.

Every feature is shifted before use. A row at quarter t sees t-1 and earlier
and nothing else, and that is enforced structurally by `.shift()` inside the
groupby rather than by a filter applied afterwards.
"""
from __future__ import annotations

import pandas as pd

SERIES_KEY = ["group", "commodity", "province_code"]

# ---------------------------------------------------------------------------
# The feature set
# ---------------------------------------------------------------------------
RECENT = [
    "shock_lag1",       # did this series shortfall last quarter
    "shock_lag2",       # and the quarter before
    "dev_lag1",         # by how much, last quarter
]
SEASONAL = [
    "shock_lag4",       # same quarter one year ago -- the annual cycle
    "dev_lag4",
    "dev_roll4",        # mean deviation over the trailing year
    "series_vol",       # how erratic this series is, expanding std
    "shock_rate_qoy",   # how often THIS series fails in THIS quarter-of-year
    "dev_qoy_mean",     # and its mean deviation in that quarter-of-year
]
IDENTITY = [
    "quarter_num",      # 1-4, where in the agricultural year we are
    "group_code",       # fisheries / fruit / vegetable
    "province_idx",
]

LEAN_FEATURES = RECENT + SEASONAL + IDENTITY


def build_features(panel: pd.DataFrame, drop_incomplete: bool = True) -> pd.DataFrame:
    """
    Attach the twelve features. Input is the raw panel from panel.load_panel().

    drop_incomplete=False keeps the opening quarters of every series, which have
    no short lags and so cannot be modelled. Only leakage_check() uses that
    form: the shifts have to be verified on the same row set they were computed
    on, and dropping rows first would renumber the shift and make correct
    features look wrong.
    """
    df = panel.sort_values(SERIES_KEY + ["year", "quarter_num"]).reset_index(drop=True)
    g = df.groupby(SERIES_KEY)

    # -- recent history -----------------------------------------------------
    df["shock_lag1"] = g["label_shock"].shift(1)
    df["shock_lag2"] = g["label_shock"].shift(2)
    df["dev_lag1"] = g["dev_pct"].shift(1)

    # -- annual cycle -------------------------------------------------------
    # Production is seasonal. The same quarter a year back agrees with the label
    # far more often than the immediately preceding quarter does, which is why
    # seasonal persistence -- not naive persistence -- is the baseline to beat.
    df["shock_lag4"] = g["label_shock"].shift(4)
    df["dev_lag4"] = g["dev_pct"].shift(4)
    df["dev_roll4"] = g["dev_pct"].transform(
        lambda x: x.shift(1).rolling(4, min_periods=2).mean())
    df["series_vol"] = g["dev_pct"].transform(
        lambda x: x.shift(1).expanding(min_periods=3).std())

    # Quarter-of-year specific history. A rate pooled across all quarters gives
    # a series that reliably fails in Q3 and never in Q1 one blended number that
    # describes neither quarter. Grouping by quarter_num as well means a 2025-Q3
    # row averages 2024-Q3 and 2022-Q3 and nothing else; shift(1) inside that
    # group keeps it strictly backward-looking.
    qoy = df.groupby(SERIES_KEY + ["quarter_num"])
    df["shock_rate_qoy"] = qoy["label_shock"].transform(
        lambda x: x.shift(1).expanding(min_periods=1).mean())
    df["dev_qoy_mean"] = qoy["dev_pct"].transform(
        lambda x: x.shift(1).expanding(min_periods=1).mean())

    # -- identity -----------------------------------------------------------
    df["group_code"] = df["group"].astype("category").cat.codes
    df["province_idx"] = df["province_code"].astype("category").cat.codes

    # Only the two short lags are required. Demanding shock_lag4 would discard
    # every 2021 row, because the panel opens at 2021-Q1 and nothing inside the
    # window can supply a fourth lag for that year. LightGBM splits on NaN, so
    # those rows enter with the seasonal lags absent rather than not entering.
    before = len(df)
    if drop_incomplete:
        df = df.dropna(subset=["shock_lag1", "shock_lag2"]).reset_index(drop=True)

    df.attrs["rows_dropped_for_lags"] = before - len(df)
    return df


def leakage_check(panel: pd.DataFrame) -> list[str]:
    """
    Structural assertions that a feature cannot contain its own label.

    Takes the RAW panel, not the modelling frame, and rebuilds features without
    the lag dropna. Verifying shifts on the dropped frame would compare each
    feature against a shift over a different row set and report every opening
    quarter as a mismatch.

    Returns a list of failures; empty means every check passed. train.py runs
    this and refuses to train on a failure, so the guarantee is executed rather
    than asserted in a comment.
    """
    fails: list[str] = []
    df = build_features(panel, drop_incomplete=False)

    # 1. The label itself and the quantities it is computed from must not be
    #    in the feature list under any name.
    forbidden = {"label_shock", "dev_pct", "volume", "baseline", "shock_threshold_pct"}
    leaked = forbidden & set(LEAN_FEATURES)
    if leaked:
        fails.append(f"label-derived columns present as features: {sorted(leaked)}")

    # 2. Every lagged feature must equal a strictly prior value of its source.
    d = df.sort_values(SERIES_KEY + ["year", "quarter_num"])
    g = d.groupby(SERIES_KEY)
    for feat, src, k in [("shock_lag1", "label_shock", 1),
                         ("shock_lag2", "label_shock", 2),
                         ("shock_lag4", "label_shock", 4),
                         ("dev_lag1", "dev_pct", 1),
                         ("dev_lag4", "dev_pct", 4)]:
        expected = g[src].shift(k)
        bad = int((d[feat].notna() & (d[feat] != expected)).sum())
        if bad:
            fails.append(f"{feat} disagrees with {src}.shift({k}) on {bad} rows")

    # 3. The first observation of each (series, quarter-of-year) has no prior
    #    same-quarter history, so its qoy features must be NaN.
    first = d.groupby(SERIES_KEY + ["quarter_num"]).head(1)
    for feat in ["shock_rate_qoy", "dev_qoy_mean"]:
        bad = int(first[feat].notna().sum())
        if bad:
            fails.append(f"{feat} is populated on {bad} first-occurrence rows")

    return fails


if __name__ == "__main__":
    from panel import load_panel

    raw = load_panel()
    d = build_features(raw)
    print(f"rows {len(d):,}  (dropped {d.attrs['rows_dropped_for_lags']} for missing short lags)")
    print(f"quarters {d['quarter'].min()} .. {d['quarter'].max()}")
    print(f"features {len(LEAN_FEATURES)}: {LEAN_FEATURES}")
    print()
    print("correlation with label:")
    for f in LEAN_FEATURES:
        print(f"  {f:18s} {d[f].corr(d['label_shock']):+.4f}   "
              f"missing {d[f].isna().mean():5.1%}")
    print()
    fails = leakage_check(raw)
    print("leakage check:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("   ", f)
