"""Compare every held PSA input file used by the FIRI v2 / E107 feature pipeline with the fresh OpenSTAT pull
(data/raw/, from pull_public.py), value by value, 2021+. Writes out/reconcile.json and out/reconcile_<source>.csv.

A difference is a revision or a data defect; a period present only in the fresh pull is newly published data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
EXP = AUD.parent
RAW = AUD / "data" / "raw"
OUT = AUD / "out"
OUT.mkdir(exist_ok=True)
PROVS = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
         "Batangas": "PH040500000"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
MON3 = [m[:3] for m in MONTHS]


def _wide_to_long(d: pd.DataFrame, id_cols: list[str]) -> pd.DataFrame:
    long = d.melt(id_vars=id_cols, var_name="yp", value_name="value")
    long["year"] = long["yp"].str[:4].astype(int)
    long["period"] = long["yp"].str[5:].str.strip()
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    for c in id_cols:
        long[c] = long[c].astype(str).str.strip(". ")
    return long.drop(columns="yp")


def _cmp(held: pd.DataFrame, fresh: pd.DataFrame, keys: list[str], name: str, tol: float) -> dict:
    j = held.merge(fresh, on=keys, how="outer", suffixes=("_held", "_fresh"), indicator=True)
    both = j[(j["_merge"] == "both") & j["value_held"].notna() & j["value_fresh"].notna()]
    diff = (both["value_held"] - both["value_fresh"]).abs()
    j.to_csv(OUT / f"reconcile_{name}.csv", index=False)
    only_fresh = j[(j["_merge"] == "right_only") & j["value_fresh"].notna()]
    held_nan_fresh_value = j[(j["_merge"] == "both") & j["value_held"].isna() & j["value_fresh"].notna()]
    return {"compared": int(len(both)), "equal_within_tol": int((diff <= tol).sum()), "tolerance": tol,
            "max_abs_diff": float(diff.max()) if len(diff) else None,
            "differing": both.loc[diff > tol, keys + ["value_held", "value_fresh"]].head(20).to_dict("records"),
            "new_in_fresh": int(len(only_fresh)) + int(len(held_nan_fresh_value)),
            "new_periods": sorted({str(x) for x in pd.concat([only_fresh, held_nan_fresh_value])[keys[-1]]})[:20]}


def cpi() -> dict:
    f = _wide_to_long(pd.read_csv(RAW / "psa_cpi_ACP22.csv"), ["Geolocation", "Commodity Description"])
    f = f[f["period"].isin(MON3) & f["Geolocation"].isin(PROVS)]
    f["ym"] = f["year"] * 12 + f["period"].map({m: i for i, m in enumerate(MON3)})
    f = f.rename(columns={"Geolocation": "province", "Commodity Description": "commodity"})
    h = pd.read_csv(EXP / "E41_Lead2_Audit" / "data_acquired" / "cpi_index_ACP22.csv")
    h = h[h["Period"].isin(MON3)]
    h = pd.DataFrame({"province": h["Geolocation"].str.strip(". "), "commodity": h["Commodity Description"],
                      "ym": h["Year"] * 12 + h["Period"].map({m: i for i, m in enumerate(MON3)}), "value": h["value"]})
    keys = ["province", "commodity", "ym"]
    res = {"index": _cmp(h, f[keys + ["value"]][f["ym"] >= 2021 * 12], keys, "cpi_index", 0.05)}
    # YoY recomputed from the fresh index vs the PSA-published YoY the label uses (E40 file)
    f = f.sort_values(keys)
    f["yoy"] = f.groupby(["province", "commodity"])["value"].transform(lambda s: 100 * (s / s.shift(12) - 1))
    y = pd.read_csv(EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv",
                    dtype={"province_code": str})
    inv = {v: k for k, v in PROVS.items()}
    y = pd.DataFrame({"province": y["province_code"].map(inv),
                      "commodity": y["commodity"].map({"food": "01.1 - FOOD", "all_items": "0 - ALL ITEMS"}),
                      "ym": y["reference_month"].str[:4].astype(int) * 12 + y["reference_month"].str[5:7].astype(int) - 1,
                      "value": y["yoy_pct"]})
    fy = f[["province", "commodity", "ym", "yoy"]].rename(columns={"yoy": "value"})
    res["yoy_published_vs_recomputed"] = _cmp(y, fy[fy["ym"] >= 2021 * 12], keys, "cpi_yoy", 0.15)
    res["latest_month_fresh"] = int(f.dropna(subset=["value"])["ym"].max())
    return res


def rice() -> dict:
    f = _wide_to_long(pd.read_csv(RAW / "psa_rice_wholesale_AWB01.csv"), ["Geolocation", "Commodity"])
    f = f[f["period"].isin(MONTHS) & f["Geolocation"].isin(PROVS) & (f["Commodity"] == "Regular Milled Rice (RMR)")]
    f["q"] = f["year"].astype(str) + "-Q" + (f["period"].map({m: i for i, m in enumerate(MONTHS)}) // 3 + 1).astype(str)
    g = f.groupby(["Geolocation", "q"])["value"].agg(["mean", "count"]).reset_index()
    months = g.rename(columns={"count": "months"})
    fq = g.rename(columns={"Geolocation": "province", "mean": "value"})[["province", "q", "value"]]
    h = pd.read_parquet(EXP / "E107_Twelve_Indicator_LightGBM" / "data_inputs" / "psa_rice_prices.parquet")
    h = pd.DataFrame({"province": h["province_name"], "q": h["quarter"], "value": h["price_php_per_kg"]})
    res = _cmp(h, fq[fq["q"] >= "2021-Q1"], ["province", "q"], "rice", 0.02)
    res["quarters_with_fewer_than_3_months"] = months[(months["months"] < 3) & (months["q"] >= "2021-Q1")][
        ["Geolocation", "q", "months"]].to_dict("records")
    return res


def production(raw: str, held: Path, held_cols: tuple, crop_map: dict, name: str) -> dict:
    d = pd.read_csv(RAW / raw)
    idc = list(d.columns[:2])
    f = _wide_to_long(d, idc)
    f = f[f["period"].str.startswith("Quarter")]
    f["q"] = f["year"].astype(str) + "-Q" + f["period"].str[-1]
    f = f.rename(columns={idc[0]: "series", idc[1]: "geo"}) if "Geolocation" in idc[1] else \
        f.rename(columns={idc[0]: "geo", idc[1]: "series"})
    f = f[f["geo"].isin(PROVS) & f["series"].isin(crop_map)]
    f["series"] = f["series"].map(crop_map)
    h = pd.read_csv(held)
    gcol, scol, pcol = held_cols
    h = pd.DataFrame({"geo": h["Geolocation"].astype(str).str.strip(". "), "series": h[scol].astype(str).str.strip(". "),
                      "q": h["Year"].astype(str) + "-Q" + h[pcol].astype(str).str[-1], "value": h["value"]})
    h = h[h["geo"].isin(PROVS) & h["series"].isin(crop_map.values())]
    res = _cmp(h, f[f["q"] >= "2021-Q1"][["geo", "series", "q", "value"]], ["geo", "series", "q"], name, 0.5)
    res["latest_quarter_fresh"] = f.dropna(subset=["value"])["q"].max()
    return res


def lfs() -> dict:
    d = pd.read_csv(RAW / "psa_lfs_FKEI2.csv")
    d = d[d["Month"].isin(MONTHS)].copy()
    d["value"] = pd.to_numeric(d["Unemployment Rate Both sexes"], errors="coerce")
    d["ym"] = d["Year"].astype(int) * 12 + d["Month"].map({m: i for i, m in enumerate(MONTHS)})
    h = pd.read_csv(EXP / "E41_Lead2_Audit" / "data_acquired" / "lfs_rates_national.csv")
    h = h[(h["Rates"] == "Unemployment Rate") & h["Month"].isin(MONTHS)]
    h = pd.DataFrame({"ym": h["Year"] * 12 + h["Month"].map({m: i for i, m in enumerate(MONTHS)}), "value": h["value"]})
    res = _cmp(h, d[d["ym"] >= 2021 * 12][["ym", "value"]], ["ym"], "lfs", 0.01)
    res["latest_month_fresh"] = int(d.dropna(subset=["value"])["ym"].max())
    res["months_without_survey_2021plus"] = int(d[(d["ym"] >= 2021 * 12)]["value"].isna().sum())
    return res


def main():
    res = {"cpi": cpi(), "rice": rice(),
           "palay_corn": production("psa_palay_corn_EVCP0.csv",
                                    EXP / "E41_Lead2_Audit" / "data_acquired" / "palay_corn_production.csv",
                                    ("Geolocation", "Ecosystem/Croptype", "Period"), {"Palay": "Palay", "Corn": "Corn"},
                                    "palay_corn"),
           "fisheries": production("psa_fisheries_GVFP1.csv",
                                   EXP / "E41_Lead2_Audit" / "data_acquired" / "fisheries_production.csv",
                                   ("Geolocation", "Subsector", "Quarter"),
                                   {"FISHERIES": "FISHERIES", "Aquaculture": "Aquaculture"}, "fisheries"),
           "lfs": lfs()}
    (OUT / "reconcile.json").write_text(json.dumps(res, indent=1, default=str))
    for k, v in res.items():
        print(k, json.dumps(v, default=str)[:700])


if __name__ == "__main__":
    main()
