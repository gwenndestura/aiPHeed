"""
NASA POWER root-zone soil wetness per province centroid (public API, 1 request per second, no outcome read).

    python -m app.e146.soil fetch   -> data/e146/raw/gwetroot_monthly.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from functools import lru_cache

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e146 import RAW

URL = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=GWETROOT&community=AG"
       "&latitude={lat}&longitude={lon}&start=2000&end=2026&format=JSON")
CSV = RAW / "gwetroot_monthly.csv"


def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    rows, geo = [], F._geo()
    for k, xy in sorted(geo.items()):
        req = urllib.request.Request(URL.format(lat=round(xy[1], 3), lon=round(xy[0], 3)), headers={"User-Agent": "aipheed-research/1.0"})
        js = json.load(urllib.request.urlopen(req, timeout=120))
        for ym, v in js["properties"]["parameter"]["GWETROOT"].items():
            if not ym.endswith("13") and v > -900:          # month 13 is the annual mean; -999 is missing
                rows.append((k, ym[:4] + "-" + ym[4:], v))
        time.sleep(1.0)
    pd.DataFrame(rows, columns=["k", "month", "gwetroot"]).to_csv(CSV, index=False, lineterminator="\n")
    print(len(geo), len(rows))


@lru_cache(maxsize=None)
def _table() -> dict:
    d = pd.read_csv(CSV)
    d["p"] = pd.PeriodIndex(d["month"], freq="M")
    out = {k: g.set_index("p")["gwetroot"] for k, g in d.groupby("k")}
    from app.e168 import live_data as LD
    for k, s in LD.nasa("gwetroot").items():             # months after the archived file only
        old = out.get(k)
        out[k] = s if old is None else pd.concat([old, s[s.index > old.index.max()]]).sort_index()
    return out


def anomaly(k: str, issue: pd.Timestamp) -> float:
    """Protocol section 4: 3 months ending 2 full months before the issue date, against the same months of 2000-2009."""
    s = _table().get(k)
    if s is None:
        return np.nan
    end = issue.to_period("M") - 3
    months = pd.period_range(end - 2, end, freq="M")
    if not all(m in s.index for m in months):
        return np.nan
    clim = [s.reindex([pd.Period(year=y, month=m.month, freq="M") for m in months]).mean() for y in range(2000, 2010)]
    sd = float(np.std(clim, ddof=1))
    return float((s[months].mean() - np.mean(clim)) / sd) if sd > 0 else np.nan


if __name__ == "__main__":
    {"fetch": fetch}[sys.argv[1]]()
