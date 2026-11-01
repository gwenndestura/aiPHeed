"""
v4 point-in-time feature snapshots (docs/aipheed/v4/PREREGISTRATION.md section 2.1): the 6 pre-declared exogenous
features per (P-DASH issue, SWS area), as known before 00:00 PHT of the issue day. Write-once.

    python -I backend/scripts/v4_features.py      -> backend/data/forecasting/v4_feature_snapshots.csv
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "backend" / "scripts"))
from app.forecasting.as_of import assert_point_in_time  # noqa: E402
from app.forecasting.evidence import AREAS  # noqa: E402
from app.forecasting.v2.select import issues  # noqa: E402
from app.forecasting.v4.features import FEATURES, SNAPSHOTS  # noqa: E402
import v2_context  # noqa: E402

E119_COLS = ("typhoons_PAR", "oni_quarter_mean", "E1_unemployment_change_pp", "news_gdelt_shortage_share")


def build(last: date) -> pd.DataFrame:
    X = v2_context.e131()
    cpi = X.cpi_quarterly()
    cpi["published"] = pd.to_datetime(cpi["available"])
    reg = pd.read_csv(v2_context.E119)
    reg = reg[reg.lead == 1]
    pov = X.poverty_area()
    rows = []
    for issue in issues(last):
        g = reg[reg.issue_date == issue.isoformat()]
        yrs = [y for y, d in X.POV_PUBLISHED.items() if d < issue]
        for a in AREAS:
            rec = {"issue": issue.isoformat(), "area": a}
            c = cpi[(cpi.area == a) & (cpi.published.dt.date < issue)].sort_values("qi").tail(1)
            if len(c):
                assert_point_in_time(c, issue)
            rec["rice_yoy"] = float(c.rice_yoy.iloc[0]) if len(c) and c.rice_yoy.iloc[0] == c.rice_yoy.iloc[0] else None
            rec["rice_yoy__period"] = c.quarter.iloc[0] if len(c) else None
            for f in E119_COLS:
                v = g[f].iloc[0] if len(g) else None
                rec[f] = float(v) if v is not None and v == v else None
                rec[f"{f}__period"] = g[f"{f}__period"].iloc[0] if len(g) else None
            rec["poverty"] = pov[a][max(yrs)] if yrs else None
            rec["poverty__period"] = str(max(yrs)) if yrs else None
            rows.append(rec)
    d = pd.DataFrame(rows)
    assert set(FEATURES) <= set(d.columns)
    return d


if __name__ == "__main__":
    if SNAPSHOTS.exists():
        sys.exit(f"{SNAPSHOTS} exists: snapshots are write-once")
    d = build(date(2026, 10, 1))
    d.to_csv(SNAPSHOTS, index=False, lineterminator="\n")
    print(d[["issue", "area", *FEATURES]].tail(12).to_string())
    print(d[list(FEATURES)].notna().sum().to_string())
