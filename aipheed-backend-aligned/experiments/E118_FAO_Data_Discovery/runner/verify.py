"""E118 verification: tidy cleaned copies (raw files untouched), province standardization, real frequency and coverage,
and overlap with existing aiPHeed indicators.

    python verify.py    # ../data/clean/*.csv, ../out/acquired_coverage.csv, ../out/overlap_checks.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW, CLEAN, OUT = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "out"
X = ROOT.parent
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}
MON3 = {m[:3]: i for m, i in MONTHS.items()}
PROVS = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]


def std_geo(g: str) -> str | None:
    u = str(g).strip(". ").strip()
    up = u.upper()
    if "CALABARZON" in up or up.startswith("REGION IV-A") or up == "IV-A":
        return "Region IV-A"
    if up == "QUEZON CITY":
        return None                                      # NCR city, not Quezon province
    if up.startswith("CITY OF LUCENA") or up == "LUCENA CITY":
        return "Lucena City (HUC, Quezon)"
    for p in PROVS:
        if up == p.upper() or up == p.upper() + " PROVINCE":
            return p
    return None


def period(col: str):
    c = col.strip()
    m = re.match(r"(\d{4})\s+([A-Za-z]+)$", c)
    if m:
        y, p = int(m.group(1)), m.group(2).lower()
        if p in MONTHS:
            return "M", y * 12 + MONTHS[p]
        if p[:3] in MON3 and p not in ("annual", "ave"):
            return "M", y * 12 + MON3[p[:3]]
    m = re.match(r"(\d{4})\s+(?:Quarter\s?|Q)(\d)$", c)
    if m:
        return "Q", int(m.group(1)) * 4 + int(m.group(2)) - 1
    return None, None


def tidy(key: str) -> tuple[pd.DataFrame, str]:
    d = pd.read_csv(RAW / f"psa_{key}.csv", encoding="latin-1")
    idc = [c for c in d.columns if not re.match(r"^\d{4}|^Annual", c)]
    gcol = [c for c in idc if "geo" in c.lower() or "region" in c.lower() or "province" in c.lower()][0]
    item = [c for c in idc if c != gcol]
    long = d.melt(id_vars=idc, var_name="col", value_name="value")
    pp = long["col"].map(period)
    long["freq"], long["period"] = [p[0] for p in pp], [p[1] for p in pp]
    long = long[long["freq"].notna()]
    long["unit"] = long[gcol].map(std_geo)
    long = long[long["unit"].notna()]
    long["item"] = long[item].astype(str).agg(" | ".join, axis=1) if item else "value"
    long["value"] = pd.to_numeric(long["value"].astype(str).str.replace(",", ""), errors="coerce")
    freq = long["freq"].mode().iloc[0] if len(long) else None
    out = long[["unit", "item", "freq", "period", "value"]].copy()
    return out, freq


def fmt(freq, p):
    return f"{p // 12}-{p % 12 + 1:02d}" if freq == "M" else f"{p // 4}-Q{p % 4 + 1}"


def coverage(key, d, freq, meta):
    prov = d[d["unit"].isin(PROVS)]
    obs = prov[prov["value"].notna()]
    row = {"dataset": key, "title": meta.get("title"), "fao_dimension": meta.get("fao_dimension"), "table_updated": meta.get("table_updated"),
           "frequency": {"M": "monthly", "Q": "quarterly"}.get(freq, freq), "provinces_with_data": ", ".join(sorted(obs["unit"].unique())),
           "n_provinces": int(obs["unit"].nunique()), "items": int(prov["item"].nunique())}
    if len(obs):
        lo, hi = int(obs["period"].min()), int(obs["period"].max())
        exp = prov.groupby(["unit", "item"]).ngroups * (hi - lo + 1)
        got = obs.drop_duplicates(["unit", "item", "period"]).shape[0]
        per_prov = obs.groupby("unit")["period"].agg(["min", "max"])
        row.update({"first_period": fmt(freq, lo), "latest_period": fmt(freq, hi),
                    "latest_period_all_provinces": fmt(freq, int(per_prov["max"].min())),
                    "periods_span": hi - lo + 1, "observed_cells": got, "expected_cells": exp, "missing_pct": round(100 * (1 - got / exp), 1),
                    "duplicate_keys": int(prov.duplicated(["unit", "item", "period"]).sum()), "negative_values": int((obs["value"] < 0).sum())})
    return row


def power():
    rows = []
    for f in RAW.glob("nasa_power_monthly_*.json"):
        prov = f.stem.split("_")[-1]
        js = json.loads(f.read_text())
        for par, series in js["properties"]["parameter"].items():
            for k, v in series.items():
                y, m = int(k[:4]), int(k[4:])
                if m == 13 or v in (-999, -999.0):
                    continue
                rows.append({"unit": prov, "item": par, "freq": "M", "period": y * 12 + m - 1, "value": v})
    return pd.DataFrame(rows)


def overlap(clean):
    out = {}
    # retail rice (provincial, monthly) YoY vs existing A3 wholesale rice YoY (quarterly)
    r = clean["retail_cereals"]
    rice = r[r["item"].str.contains("Rice", case=False) & r["item"].str.contains("Regular", case=False)]
    rice = rice[rice["unit"].isin(PROVS)].copy()
    rice["q"] = rice["period"] // 3
    rq = rice.groupby(["unit", "q"])["value"].mean().reset_index()
    rq["yoy"] = rq.groupby("unit")["value"].transform(lambda s: 100 * (s / s.shift(4) - 1))
    a3 = pd.read_parquet(X / "E107_Twelve_Indicator_LightGBM" / "data_inputs" / "psa_rice_prices.parquet")
    a3["q"] = a3["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    a3 = a3.sort_values("q")
    a3["yoy"] = a3.groupby("province_name")["price_php_per_kg"].transform(lambda s: 100 * (s / s.shift(4) - 1))
    m = rq.merge(a3[["province_name", "q", "yoy"]].rename(columns={"province_name": "unit"}), on=["unit", "q"], suffixes=("_retail", "_a3")).dropna()
    out["retail_regular_rice_yoy_vs_A3"] = {"rows": int(len(m)), "corr": float(m["yoy_retail"].corr(m["yoy_a3"])) if len(m) > 5 else None,
                                            "rice_items": sorted(rice["item"].unique())[:6]}
    # bottom-30% food CPI YoY vs all-income food CPI YoY (existing A1/A2 source)
    b = clean["cpi_bottom30_yoy"]
    bf = b[(b["item"].str.strip() == "01.1 - FOOD") & b["unit"].isin(PROVS)]
    allf = pd.read_csv(X / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv", dtype={"province_code": str})
    code = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
    allf = allf[allf["commodity"] == "food"].assign(unit=lambda d: d["province_code"].map(code),
                                                     period=lambda d: d["reference_month"].str[:4].astype(int) * 12 + d["reference_month"].str[5:7].astype(int) - 1)
    m2 = bf.merge(allf[["unit", "period", "yoy_pct"]], on=["unit", "period"]).dropna()
    out["bottom30_food_yoy_vs_all_income_food_yoy"] = {"rows": int(len(m2)), "corr": float(m2["value"].corr(m2["yoy_pct"])) if len(m2) > 5 else None,
                                                       "mean_abs_diff_pp": float((m2["value"] - m2["yoy_pct"]).abs().mean()) if len(m2) else None,
                                                       "items": sorted(bf["item"].unique())[:4]}
    # key-commodity coverage (the whole-table missing share mixes in rarely reported items)
    keyc = {"retail_cereals": "RICE, REGULAR-MILLED", "retail_poultry": "CHICKEN", "retail_livestock": "PORK", "retail_fish": "TILAPIA",
            "retail_leafy_veg": "PECHAY", "retail_fruit_veg": "TOMATO", "farmgate_cereals": "PALAY", "wholesale_cereals": "RICE"}
    kc = {}
    for k, pat in keyc.items():
        g = clean[k][clean[k]["item"].str.upper().str.contains(pat) & clean[k]["unit"].isin(PROVS)]
        if not len(g):
            kc[k] = {"pattern": pat, "items": 0}
            continue
        it = g.groupby("item")["value"].apply(lambda v: v.notna().mean()).sort_values(ascending=False)
        best = g[g["item"] == it.index[0]]
        span = best[best["value"].notna()]
        kc[k] = {"pattern": pat, "best_item": it.index[0], "share_months_observed": round(float(it.iloc[0]), 3),
                 "by_province": {u: round(float(h["value"].notna().mean()), 3) for u, h in best.groupby("unit")},
                 "first": fmt("M", int(span["period"].min())), "last": fmt("M", int(span["period"].max()))}
    out["key_commodity_coverage"] = kc
    # NASA POWER rainfall: does it vary across provinces? (new information vs national typhoon / ENSO inputs)
    p = clean["nasa_power"]
    pr = p[p["item"] == "PRECTOTCORR"].pivot(index="period", columns="unit", values="value")
    out["nasa_rainfall_between_province_corr_mean"] = float(pr.corr().values[np.triu_indices(5, 1)].mean())
    out["nasa_rainfall_cv_between_provinces"] = float((pr.std(axis=1) / pr.mean(axis=1)).mean())
    # aquaculture vs fisheries total (overlap: aquaculture is a fisheries subsector)
    out["aquaculture_is_subsector_of_fisheries_total"] = True
    return out


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    log = json.loads((ROOT / "data" / "acquisition_log.json").read_text())
    rows, clean = [], {}
    for key, meta in log["tables"].items():
        if "error" in meta:
            rows.append({"dataset": key, "error": meta["error"]})
            continue
        try:
            d, freq = tidy(key)
        except Exception as e:  # noqa: BLE001
            rows.append({"dataset": key, "title": meta.get("title"), "error": f"not period-tidy ({type(e).__name__}); annual/static table"})
            continue
        if not len(d):
            rows.append({"dataset": key, "title": meta.get("title"), "frequency": "annual/static (no monthly or quarterly columns)"})
            continue
        d.to_csv(CLEAN / f"{key}.csv", index=False, lineterminator="\n")
        clean[key] = d
        rows.append(coverage(key, d, freq, meta))
    P = power()
    P.to_csv(CLEAN / "nasa_power_monthly.csv", index=False, lineterminator="\n")
    clean["nasa_power"] = P
    rows.append(coverage("nasa_power", P, "M", {"title": "NASA POWER monthly precipitation, temperature, humidity at province centroids", "fao_dimension": "stability"}))
    C = pd.DataFrame(rows)
    C.to_csv(OUT / "acquired_coverage.csv", index=False, lineterminator="\n")
    ov = overlap(clean)
    (OUT / "overlap_checks.json").write_text(json.dumps(ov, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(C[[c for c in ("dataset", "frequency", "n_provinces", "items", "first_period", "latest_period", "latest_period_all_provinces", "missing_pct", "duplicate_keys", "error") if c in C]].to_string())
    print(json.dumps(ov, indent=1, default=float))


if __name__ == "__main__":
    main()
