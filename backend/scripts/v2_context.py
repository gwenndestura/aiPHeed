"""
Point-in-time context indicators for the v2 explanation: one primary indicator per trigger group (the pre-chosen
HFM-X drivers, PREREGISTRATION section 1.2), as known at a quarter-start issue. They are shown as context only; they
are never model inputs and never weighted. Every value carries its period and availability date and is checked with
as_of.assert_point_in_time (a value available on/after the issue raises LeakageError).

    python -I backend/scripts/v2_context.py 2026-10-01   -> backend/data/forecasting/context/context_<issue>.json
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting.as_of import assert_point_in_time  # noqa: E402
from app.forecasting.evidence import AREAS, DataState  # noqa: E402

EXP = REPO / "aipheed-backend-aligned" / "experiments"
E119 = EXP / "E119_Preprocessing" / "E119_REGIONAL_MODELING_DATASET.csv"
OUT = REPO / "backend" / "data" / "forecasting" / "context"


def e131():
    sys.path.insert(0, str(EXP / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
    spec = importlib.util.spec_from_file_location("e131_ctx", EXP / "E131_Objectives_Resolution" / "runner" / "e131_x1.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["e131_ctx"] = m
    spec.loader.exec_module(m)
    return m


def build(issue: date) -> dict:
    X = e131()
    cpi = X.cpi_quarterly()
    cpi["published"] = pd.to_datetime(cpi["available"])
    reg = pd.read_csv(E119)
    reg = reg[(reg.lead == 1) & (reg.issue_date == issue.isoformat())]
    pov = X.poverty_area()
    out = {"issue_date": issue.isoformat(), "areas": {}}
    for a in AREAS:
        rows = []
        c = cpi[(cpi.area == a) & (cpi.published.dt.date < issue)].sort_values("qi").tail(1)
        if len(c):
            assert_point_in_time(c, issue)
            rows.append(("market", "area rice CPI, year-on-year %", float(c.rice_yoy.iloc[0]), c.quarter.iloc[0],
                         str(c.published.dt.date.iloc[0]), "PSA OpenSTAT 0012M4ACP22 (E131)"))
        for g, col, lab in (("climate", "typhoons_PAR", "tropical cyclones entering PAR in the quarter"),
                            ("employment_ofw", "E1_unemployment_change_pp", "unemployment rate change, pp"),
                            ("news_nlp", "news_gdelt_shortage_share", "share of GDELT food-shortage articles")):
            if len(reg) and reg[col].iloc[0] == reg[col].iloc[0]:
                period = reg[f"{col}__period"].iloc[0]
                # E119 values are point-in-time by construction (its leakage tests); the period must end before the issue
                avail = pd.Period(str(period).replace("-", ""), freq="Q").end_time.date() if "-Q" in str(period) else None
                if avail is not None:
                    assert_point_in_time(pd.DataFrame({"published": [avail]}), issue)
                rows.append((g, lab, float(reg[col].iloc[0]), str(period), "before the issue (E119 point-in-time status)",
                             "E119 point-in-time regional dataset"))
        yrs = [y for y, d in X.POV_PUBLISHED.items() if d < issue]
        if yrs:
            rows.append(("poverty_vulnerability", "area poverty incidence, %", float(pov[a][max(yrs)]), str(max(yrs)),
                         str(X.POV_PUBLISHED[max(yrs)]), "PSA poverty statistics (E131)"))
        out["areas"][a] = {g: {"label": lab, "value": round(v, 4), "period": p, "available": av, "source": s,
                               "state": DataState.OBSERVED.value} for g, lab, v, p, av, s in rows}
    return out


if __name__ == "__main__":
    i = date.fromisoformat(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"context_{i.isoformat()}.json"
    p.write_text(json.dumps(build(i), indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(p.read_text())
