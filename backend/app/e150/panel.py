"""
E150 quarterly panel: E148's government panel + monthly provincial food-only CPI + SWS-learned quarterly response. Reads no 2021 label.

    python -m app.e150.panel cpi -> data/e150/out/cpi_panel.parquet, audit in feature_availability.csv

CPI: 01.1 Food and rice only. Year-on-year is always computed inside one base (2012 base through December 2018, 2018 base after), so the two
indices are never spliced. Release: a month's CPI is usable from the first day of the second following month (PSA publishes around the 5th).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e147 import features as Fe
from app.e148 import panel as Pn
from app.e150 import OUT, RAW
from app.fi5.target import qindex

MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
CPI_COLS = ["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_3m", "cpi_food_accel", "cpi_food_rel_nat", "cpi_age_m"]
ALIAS = {"cotabato": "northcotabato", "cotabato(northcotabato)": "northcotabato", "northcotabato": "northcotabato", "davaodeoro": "compostelavalley", "davaodeoro(compostelavalley)": "compostelavalley",
         "compostelavalley": "compostelavalley", "samar": "westernsamar", "samar(westernsamar)": "westernsamar", "tawi-tawi": "tawitawi", "maguindanaodelnorte": "maguindanao", "mountainprovince": "mountain"}


def _yoy_table() -> pd.DataFrame:
    d = pd.read_csv(RAW / "cpi_monthly.csv")
    d = d[d["period"].isin(MONTHS)].dropna(subset=["value"]).copy()
    d["k"] = d["geo"].str.replace(".", "", regex=False).str.strip().map(F.nospace)
    d["k"] = d["k"].map(lambda x: ALIAS.get(x, x))
    d["m"] = d["year"].astype(int) * 12 + d["period"].map(MONTHS) - 1
    d = d.drop_duplicates(["k", "commodity", "base", "m"])
    d = d.sort_values(["k", "commodity", "base", "m"])
    lag = d[["k", "commodity", "base", "m", "value"]].assign(m=lambda x: x["m"] + 12).rename(columns={"value": "v0"})
    d = d.merge(lag, on=["k", "commodity", "base", "m"], how="left")
    d["yoy"] = 100 * (d["value"] / d["v0"] - 1)
    # 2012 base through Dec 2018, 2018 base from Jan 2019
    use = ((d["base"] == 2012) & (d["m"] <= 2018 * 12 + 11)) | ((d["base"] == 2018) & (d["m"] >= 2019 * 12))
    return d[use & d["yoy"].notna()][["k", "commodity", "m", "yoy"]]


def cpi_panel() -> pd.DataFrame:
    Y = _yoy_table()
    keys = Fe.base_rows()["key"].drop_duplicates().tolist()
    F_ = Y[Y["commodity"] == "food"].pivot_table(index="m", columns="k", values="yoy")
    R_ = Y[Y["commodity"] == "rice"].pivot_table(index="m", columns="k", values="yoy")
    nat = F_["philippines"] if "philippines" in F_ else F_.mean(axis=1)
    rows = []
    for i in range(Pn.FIRST, Pn.LAST + 1):
        d = Pn.q_start(i)
        last = d.year * 12 + d.month - 1 - 2                # a month is usable from the first day of the second following month
        for key in keys:
            k = key.replace(" ", "")
            r = {"key": key, "qi": i}
            if k in F_ and last in F_.index:
                s = F_[k].dropna()
                s = s[s.index <= last]
                if len(s):
                    lm = int(s.index[-1])
                    r.update(cpi_food_yoy=float(s.iloc[-1]), cpi_age_m=last - lm, cpi_food_3m=float(s.iloc[-3:].mean()), cpi_food_accel=float(s.iloc[-1] - s.iloc[-4]) if len(s) >= 4 else np.nan, cpi_food_rel_nat=float(s.iloc[-1] - nat.get(lm, np.nan)))
            if k in R_:
                s = R_[k].dropna()
                s = s[s.index <= last]
                if len(s):
                    r["cpi_rice_yoy"] = float(s.iloc[-1])
            rows.append(r)
    P = pd.DataFrame(rows)
    for c in CPI_COLS:
        if c not in P:
            P[c] = np.nan
    OUT.mkdir(parents=True, exist_ok=True)
    P.to_parquet(OUT / "cpi_panel.parquet", index=False)
    print(P.shape, P[CPI_COLS].notna().mean().round(3).to_dict(), "keys without CPI", sorted(P[P["cpi_food_yoy"].isna()]["key"].unique())[:15])
    for q in ("2015-Q2", "2019-Q2", "2021-Q2", "2026-Q4"):
        x = P[P["qi"] == qindex(q)]
        print(q, x[["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_rel_nat"]].describe().loc[["mean", "min", "max"]].round(2).to_dict())
    return P


if __name__ == "__main__":
    {"cpi": cpi_panel}[sys.argv[1]]()
