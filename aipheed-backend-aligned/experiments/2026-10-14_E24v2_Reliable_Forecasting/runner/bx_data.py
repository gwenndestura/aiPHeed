"""E24v2: build provincial food-price series from the acquired PSA tables and run the comparability gate
(FROZEN_EVALUATION_PROTOCOL.md 2.2-2.4).  Run:  python -B runner/bx_data.py

Outputs (data/):
  monthly_yoy_1995_2025.csv   province x month: YoY of 01.1 Food, All items, Rice (index-based)
  quarterly_D_1995_2025.csv   province x quarter: F, mean5, D (index-based; complete quarters only)
  dnow_1995_2025.csv          province x quarter t: Dnow = mean over months 1-2 of t of (YoY_p - 5-province mean)
  comparability_gate.json     gate (i) vs E12 2021-2025 and gate (ii) vs PSA published YoY 2019-2020
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EXP = guard.EXP
ACQ = EXP / "acquisition"
OUT = EXP / "data"
CODE2PSGC = {"33": "PH040500000", "34": "PH040100000", "35": "PH040200000", "36": "PH040300000", "37": "PH040400000"}
COMMOD = {"0": "all", "2": "food", "5": "rice"}
MONTH = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                         "Dec"])}


def load_index() -> pd.DataFrame:
    parts = []
    for f in ("cpi_index_1994_2017_ACP28.csv", "cpi_index_2018_2020_ACP22.csv", "cpi_index_2021_2025_ACP22.csv"):
        d = pd.read_csv(ACQ / f, dtype=str)
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    d["province_code"] = d["Geolocation_code"].map(CODE2PSGC)
    d["series"] = d["Commodity Description_code"].map(COMMOD)
    d["year"] = d["Year"].astype(int)
    d["month"] = d["Period"].map(MONTH)
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    assert d["year"].max() <= 2025, "a year >= 2026 is present"
    assert not d.duplicated(["province_code", "series", "year", "month"]).any()
    return d[["province_code", "series", "year", "month", "value"]]


def yoy(idx: pd.DataFrame) -> pd.DataFrame:
    w = idx.pivot_table(index=["province_code", "year", "month"], columns="series", values="value").reset_index()
    w = w.sort_values(["province_code", "year", "month"])
    prev = w.copy()
    prev["year"] = prev["year"] + 1
    m = w.merge(prev, on=["province_code", "year", "month"], suffixes=("", "_prev"))
    for s in COMMOD.values():
        m[f"yoy_{s}"] = 100.0 * (m[s] / m[f"{s}_prev"] - 1.0)
    m["ym"] = m["year"] * 12 + m["month"] - 1
    m["quarter"] = m["year"].astype(str) + "-Q" + ((m["month"] - 1) // 3 + 1).astype(str)
    return m[["province_code", "year", "month", "ym", "quarter", "yoy_food", "yoy_all", "yoy_rice"]]


def quarterly(m: pd.DataFrame) -> pd.DataFrame:
    g = m.groupby(["province_code", "quarter"])
    q = g["yoy_food"].agg(["mean", "count"]).reset_index().rename(columns={"mean": "F", "count": "n_months"})
    q.loc[q["n_months"] != 3, "F"] = np.nan
    ok = q.groupby("quarter")["F"].transform(lambda v: v.notna().sum() == 5 and len(v) == 5)
    q["mean5"] = q.groupby("quarter")["F"].transform("mean").where(ok)
    q["D"] = (q["F"] - q["mean5"]).where(ok)
    return q.sort_values(["quarter", "province_code"]).reset_index(drop=True)


def dnow(m: pd.DataFrame) -> pd.DataFrame:
    """Dnow(p,t): mean over months 1-2 of quarter t of the monthly deviation from the five-province mean.
    Also rice and food-minus-all deviations over the same months (descriptive features)."""
    mm = m[((m["month"] - 1) % 3) < 2].copy()
    for c in ("yoy_food", "yoy_rice", "yoy_all"):
        ok = mm.groupby("ym")[c].transform(lambda v: v.notna().sum() == 5)
        mm[c + "_dev"] = (mm[c] - mm.groupby("ym")[c].transform("mean")).where(ok)
    g = mm.groupby(["province_code", "quarter"])
    out = g[["yoy_food_dev", "yoy_rice_dev"]].mean()
    out["n_months"] = g["yoy_food_dev"].count()
    out = out.reset_index().rename(columns={"yoy_food_dev": "Dnow", "yoy_rice_dev": "rice_dev_now"})
    out.loc[out["n_months"] != 2, ["Dnow", "rice_dev_now"]] = np.nan
    return out


def gate(q: pd.DataFrame, m: pd.DataFrame) -> dict:
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                       dtype={"province_code": str})
    a = comp[["province_code", "quarter", "F", "D"]].merge(q[["province_code", "quarter", "F", "D"]],
                                                          on=["province_code", "quarter"], suffixes=("_e12", "_idx"))
    a = a.dropna(subset=["D_e12", "D_idx"])
    dD = (a["D_idx"] - a["D_e12"]).abs()
    big = a["D_e12"].abs() >= 0.05
    sign = float((np.sign(a.loc[big, "D_idx"]) == np.sign(a.loc[big, "D_e12"])).mean())
    g1 = {"rows": int(len(a)), "max_abs_dD": float(dD.max()), "mean_abs_dD": float(dD.mean()),
          "max_abs_dF": float((a["F_idx"] - a["F_e12"]).abs().max()), "sign_agreement_absD_ge_0.05": sign,
          "rows_absD_ge_0.05": int(big.sum()), "pass": bool(dD.max() <= 0.20 and sign >= 0.95)}
    pub = pd.read_csv(ACQ / "cpi_yoy_2019_2020_ACP23.csv", dtype=str)
    pub = pub[pub["Commodity Description_code"] == "2"].copy()
    pub["province_code"] = pub["Geolocation_code"].map(CODE2PSGC)
    pub["year"], pub["month"] = pub["Year"].astype(int), pub["Period"].map(MONTH)
    pub["yoy_pub"] = pd.to_numeric(pub["value"], errors="coerce")
    b = pub.merge(m, on=["province_code", "year", "month"])
    d2 = (b["yoy_pub"] - b["yoy_food"]).abs()
    g2 = {"rows": int(len(b)), "median_abs_diff": float(d2.median()), "max_abs_diff": float(d2.max()),
          "pass": bool(d2.median() <= 0.15)}
    return {"gate_i_vs_E12_2021_2025": g1, "gate_ii_vs_PSA_published_yoy_2019_2020": g2,
            "backcast_valid": bool(g1["pass"] and g2["pass"])}


def main():
    OUT.mkdir(exist_ok=True)
    idx = load_index()
    m = yoy(idx)
    q = quarterly(m)
    dn = dnow(m)
    res = gate(q, m)
    res["coverage"] = {"monthly_first": f"{m['year'].min()}-{m.loc[m['year'] == m['year'].min(), 'month'].min():02d}",
                       "monthly_last": f"{m['year'].max()}-{m.loc[m['year'] == m['year'].max(), 'month'].max():02d}",
                       "quarters_with_D": int(q.dropna(subset=["D"])["quarter"].nunique()),
                       "first_D_quarter": q.dropna(subset=["D"])["quarter"].min(),
                       "last_D_quarter": q.dropna(subset=["D"])["quarter"].max(),
                       "missing_index_values": int(idx["value"].isna().sum())}
    m.to_csv(OUT / "monthly_yoy_1995_2025.csv", index=False, lineterminator="\n")
    q.to_csv(OUT / "quarterly_D_1995_2025.csv", index=False, lineterminator="\n")
    dn.to_csv(OUT / "dnow_1995_2025.csv", index=False, lineterminator="\n")
    (OUT / "comparability_gate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
