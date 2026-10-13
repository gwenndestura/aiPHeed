"""
panel.py
--------
The label, and nothing else.

A row is one province x commodity x quarter. `label_shock` is 1 when PSA's
reported production volume falls more than 10% below that same series' own
expanding seasonal baseline -- the mean of prior in-window years for the same
quarter-of-year. The baseline only ever looks backward, so no row can see its
own future.

This is the one component of the original aiPHeed pipeline kept unchanged. It
is the part that is genuinely defensible: a real measured quantity from a
national statistics agency, on a real seasonal reference, with a threshold
chosen against skill-over-baseline rather than against accuracy.

The panel is produced by the existing builder, which fetches live from PSA
OpenStat:

    backend/scripts/build_food_availability_panel.py

This module does not re-implement that fetch. Duplicating it would create two
label definitions that drift apart, which is exactly the failure mode this
folder exists to avoid. It reads the builder's output and validates it.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PANEL_PATH = REPO / "backend" / "data" / "processed" / "food_availability_panel.parquet"

REQUIRED = ["group", "commodity", "province_name", "province_code",
            "year", "quarter_num", "quarter", "volume", "baseline",
            "dev_pct", "label_shock"]


def load_panel(path: Path | None = None) -> pd.DataFrame:
    """Read the production panel and assert it is shaped the way the model assumes."""
    path = path or PANEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build it first:\n"
            f"    cd backend && venv/Scripts/python.exe scripts/build_food_availability_panel.py"
        )
    df = pd.read_parquet(path)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"panel is missing columns: {missing}")

    # The label must be reconstructible from the columns that carry it. If this
    # fails the parquet has been edited by hand somewhere downstream.
    thr = float(df["shock_threshold_pct"].iloc[0])
    recomputed = (df["dev_pct"] < thr).astype(int)
    if not recomputed.equals(df["label_shock"].astype(int)):
        n = int((recomputed != df["label_shock"]).sum())
        raise ValueError(f"label_shock disagrees with dev_pct < {thr} on {n} rows")

    return df.sort_values(["group", "commodity", "province_code",
                           "year", "quarter_num"]).reset_index(drop=True)


if __name__ == "__main__":
    d = load_panel()
    print(f"rows          {len(d):,}")
    print(f"series        {d.groupby(['group','commodity','province_code']).ngroups:,}")
    print(f"quarters      {d['quarter'].min()} .. {d['quarter'].max()}  ({d['quarter'].nunique()})")
    print(f"shock rate    {d['label_shock'].mean():.4f}")
    print(f"threshold     {d['shock_threshold_pct'].iloc[0]:.0f}%")
    print()
    print(d.groupby("group")["label_shock"].agg(["size", "mean"]).to_string())
