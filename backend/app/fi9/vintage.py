"""Forecast-time (as-of) dataset for Lead 1 and the long data-vintage table behind it.

    python -m app.fi9.vintage build [--as-of YYYY-MM-DD]

Outputs (data/fi9/out):
  forecast_time_dataset_h1.csv   one row per issue date: every feature as it was known on that date, the target
                                 quarter (issue quarter + 1), its publication date and its label
  data_vintage_long.csv          every source value with observation period, availability date, level, unit, source
  leakage_checks.json            automated checks on the dataset (also run by tests/unit/test_fi9.py)
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from app.fi9 import OUT
from app.fi9 import quarters as Q

# attribute of app.fi5.features.FeatureBuilder -> (value columns, geographic level, unit, source, revision status)
SOURCES = {
    "sws": (["hunger", "moe"], "Balance Luzon (SWS area)", "% of families", "SWS Social Weather Survey releases",
            "as published; release date = published"),
    "cpi": (["yoy_all", "yoy_food", "yoy_rice"], "Region IV-A", "% year on year", "PSA OpenSTAT monthly CPI (2018=100)",
            "current vintage; availability = 10th of the following month (PSA release calendar)"),
    "palay": (["yoy_palay"], "Region IV-A", "% year on year", "PSA OpenSTAT palay production", "current vintage; +45 days"),
    "lfs": (["unemp_rate", "unemp_yoy"], "national", "%, pp", "PSA Labor Force Survey", "current vintage; +45 days"),
    "nasa": (["precip", "tmax"], "CALABARZON (mean of 5 province centroids)", "mm/day, deg C", "NASA POWER", "+30 days"),
    "tc": ([], "within 200 km of a CALABARZON province centroid", "storm passages", "IBTrACS", "available at the passage date"),
    "oni": (["oni"], "global (ENSO)", "deg C", "NOAA CPC ONI", "+10 days"),
    "remit": (["remit_yoy"], "national", "% year on year", "BSP via World Bank WDI BX.TRF.PWKR.CD.DT",
              "current vintage; annual; available 15 Feb of the next year"),
    "poverty": (["poverty_inc"], "Region IV-A", "% of population", "PSA official poverty statistics",
                "2006-2015 on the 2009 methodology, 2018+ on the 2018 methodology (break); official release dates"),
    "gdelt": ([], "Philippine news sources", "z-score", "GDELT", "quarter end"),
}
DOMAIN_OF = {"sws": "outcome", "cpi": "market", "palay": "market", "lfs": "employment", "nasa": "climate",
             "tc": "climate", "oni": "climate", "remit": "remittance", "poverty": "poverty", "gdelt": "news"}


def long_table(fb, sws: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for attr, (cols, level, unit, src, rev) in SOURCES.items():
        d = sws.copy() if attr == "sws" else getattr(fb, attr).copy()
        if attr == "sws":
            d = d.rename(columns={"published": "available_from"})
            d["period_end"] = [Q.end(Q.index(q)) for q in d["quarter"]]
        if attr == "tc":
            d = d.assign(storm_passage=1.0, available_from=d["t"])      # the feature counts passages up to the issue date
            cols = ["storm_passage"]
        if attr == "gdelt":
            cols = [c for c in d.columns if c.startswith("gdelt_")]
        m = d.melt(id_vars=["period_end", "available_from"], value_vars=cols, var_name="indicator", value_name="value")
        m["source_key"], m["domain"], m["geographic_level"], m["unit"], m["source"], m["revision_status"] = \
            attr, DOMAIN_OF[attr], level, unit, src, rev
        parts.append(m.dropna(subset=["value"]))
    out = pd.concat(parts, ignore_index=True)
    out["period_end"] = pd.to_datetime(out["period_end"]).dt.date
    out["available_from"] = pd.to_datetime(out["available_from"]).dt.date
    out["quality_status"] = np.where(out["source_key"].isin(["lfs", "remit"]), "national proxy (not regional)",
                                     np.where(out["source_key"] == "sws", "regional survey (Balance Luzon)", "official series"))
    return out.sort_values(["source_key", "indicator", "period_end"]).reset_index(drop=True)


def leakage_checks(X: pd.DataFrame, sws: pd.DataFrame) -> dict:
    iss = pd.to_datetime(X["issue_date"])
    pub = sws.set_index("quarter")["published"]
    last_pub = pd.to_datetime(X["last_reading_quarter"].map(pub))
    labelled = X[X["y"].notna()]
    return {
        "n_rows": int(len(X)), "n_labelled": int(len(labelled)),
        "target_is_next_quarter": bool((X["target_quarter"].map(Q.index) == X["issue_quarter"].map(Q.index) + 1).all()),
        "issue_date_inside_issue_quarter": bool(all(Q.qi_of(d) == Q.index(q) for d, q in zip(iss, X["issue_quarter"]))),
        "latest_reading_published_by_issue": bool((last_pub <= iss).all()),
        "target_published_after_issue": bool((pd.to_datetime(labelled["target_published"]) > pd.to_datetime(labelled["issue_date"])).all()),
        "no_duplicate_issue_dates": bool(not X["issue_date"].duplicated().any()),
        "no_duplicate_target_quarters": bool(not X["target_quarter"].duplicated().any()),
    }


def build(as_of: str | None = None) -> dict:
    from app.fi7.design import Designer
    D = Designer("operational", as_of=pd.Timestamp(as_of) if as_of else None)
    X = D.frame(1)
    X.drop(columns=["tqi", "issue_ts"]).to_csv(OUT / "forecast_time_dataset_h1.csv", index=False, lineterminator="\n")
    long_table(D.fb, D.q).to_csv(OUT / "data_vintage_long.csv", index=False, lineterminator="\n")
    chk = leakage_checks(X, D.q)
    (OUT / "leakage_checks.json").write_text(json.dumps(chk, indent=1))
    return chk


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()
    print(json.dumps(build(a.as_of), indent=1))
