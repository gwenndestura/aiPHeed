"""E61 A4: target-definition review. Every candidate is built from the same published PSA CPI and SWS data
(2021-Q1..2026-Q3, authorized limit 2026-10-14); no outcome is relabelled and nothing here is used to choose a model.

Candidates (province-quarter, quarter means of published monthly YoY; thresholds fixed in advance, not tuned):
  T43    current: SWS H > 11.3 AND PS
  PS     provincial food-price pressure: food YoY > province 2021-22 P60 OR food-minus-headline > province P60 (E40)
  ABS4   food YoY > 4.0 (upper end of the government's 2-4% inflation target band)
  GAP0   food YoY > headline YoY (food prices rising faster than prices in general)
  ACC1   food YoY rose >= 1.0 point vs the previous quarter, or the gap rose >= 1.0 point (rising pressure; E58 RISE size)
  RFP    real food price level: food index / all-items index above the province's own 2021-22 mean (food relatively
         expensive, regardless of the current inflation rate)
  H&X    SWS H > 11.3 AND X, for X in ABS4, GAP0, ACC1, RFP
External check (weak, the only independent food-insecurity measure in the data): does a candidate's regional share
track the regional SWS hunger rate across quarters (Spearman)? For hunger-gated targets this is partly circular.
Also: the food price LEVEL now vs 2021 and vs 2023 (low inflation is not low prices).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a4_targets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, E = X.np, X.pd, X.L, X.F, X.E

DEFS = {
    "T43": "SWS Balance Luzon hunger > 11.3% AND PS (current E55-E58 target)",
    "PS": "food YoY > province 2021-22 P60 OR food-minus-headline YoY > province 2021-22 P60",
    "ABS4": "provincial food YoY > 4.0% (above the 2-4% inflation target band)",
    "GAP0": "provincial food YoY > provincial headline YoY",
    "ACC1": "food YoY up >= 1.0 point on the previous quarter, or food-minus-headline up >= 1.0 point",
    "RFP": "food CPI / all-items CPI above the province's 2021-22 mean (food relatively expensive)",
}


def build(d) -> pd.DataFrame:
    Y = F.t43_labels(d)
    Y = Y.sort_values(["province_code", "q"])
    Y["G"] = Y["F"] - Y["HL"]
    Y["ABS4"] = (Y["F"] > 4.0).astype(int)
    Y["GAP0"] = (Y["G"] > 0).astype(int)
    dF = Y.groupby("province_code")["F"].diff()
    dG = Y.groupby("province_code")["G"].diff()
    Y["ACC1"] = np.where(dF.isna(), np.nan, ((dF >= 1.0) | (dG >= 1.0)).astype(float))
    idx = d.idx.assign(q=lambda f: f["ym"].map(L.q_of_ym))
    lv = idx.pivot_table(index=["province_code", "q"], columns="commodity", values="index", aggfunc="mean").reset_index()
    lv["rfp"] = lv["food"] / lv["all_items"]
    base = lv[(lv["q"] >= L.qi("2021-Q1")) & (lv["q"] <= L.qi("2022-Q4"))].groupby("province_code")["rfp"].mean()
    lv["RFP"] = (lv["rfp"] > lv["province_code"].map(base)).astype(int)
    lv["rfp_vs_2122_pct"] = 100 * (lv["rfp"] / lv["province_code"].map(base) - 1)
    Y = Y.merge(lv[["province_code", "q", "food", "all_items", "rfp", "RFP", "rfp_vs_2122_pct"]], on=["province_code", "q"], how="left")
    Y["Hhigh"] = (Y["H_all"] > 11.3).astype(float).where(Y["H_all"].notna())
    for k in ("ABS4", "GAP0", "ACC1", "RFP"):
        Y[f"H&{k}"] = (Y["Hhigh"] * Y[k]).where(Y["Hhigh"].notna() & Y[k].notna())
    Y["target"] = Y["q"].map(L.qs)
    return Y


def price_levels(d) -> dict:
    """Food index level (quarter mean) in the latest complete quarter vs 2021-Q1 and 2023-Q1, and rice wholesale."""
    idx = d.idx.assign(q=lambda f: f["ym"].map(L.q_of_ym))
    lv = idx.pivot_table(index=["province_code", "q"], columns="commodity", values="index", aggfunc="mean")
    last = L.qi("2026-Q3")
    out = {}
    rice = pd.read_parquet(X.BACKEND / "data" / "processed" / "psa_rice_prices.parquet")
    rice = rice[rice["rice_class"] == "regular_milled"].set_index(["province_code", "quarter"])["price_php_per_kg"]
    for p in L.PROVS:
        f = lv.loc[p]["food"]
        a = lv.loc[p]["all_items"]
        nmon = int(((idx["province_code"] == p) & (idx["commodity"] == "food") & (idx["q"] == last)).sum())
        out[L.NAMES[p]] = {
            "food_index_2026Q3_vs_2021Q1_pct": float(100 * (f[last] / f[L.qi("2021-Q1")] - 1)),
            "food_index_2026Q3_vs_2023Q1_pct": float(100 * (f[last] / f[L.qi("2023-Q1")] - 1)),
            "all_items_2026Q3_vs_2021Q1_pct": float(100 * (a[last] / a[L.qi("2021-Q1")] - 1)),
            "months_in_2026Q3_mean": nmon,
            "rice_wholesale_php_kg_2023Q1": float(rice.get((p, "2023-Q1"), np.nan)),
            "rice_wholesale_php_kg_2025Q3": float(rice.get((p, "2025-Q3"), np.nan)),
            "rice_wholesale_php_kg_2026Q2": float(rice.get((p, "2026-Q2"), np.nan))}
    return out


def main():
    d, _, _ = E.load()
    Y = build(d)
    lab = Y[Y["T43"].notna()]
    cands = ["T43", "PS", "ABS4", "GAP0", "ACC1", "RFP", "H&ABS4", "H&GAP0", "H&ACC1", "H&RFP"]
    from scipy.stats import spearmanr
    rows = []
    hq = lab.groupby("target")["H_all"].first()
    ev = lab[lab["q"] >= L.qi("2024-Q2")]
    for c in cands:
        z = lab.dropna(subset=[c])
        share = z.groupby("target")[c].mean()
        rho = spearmanr(share, hq.loc[share.index]) if share.nunique() > 1 else None
        by_year = z.assign(y=z["q"] // 4).groupby("y")[c].mean().round(2).to_dict()
        prev = z[["province_code", "q", c]].assign(q=lambda f: f["q"] + 2).rename(columns={c: "lag2"})
        pz = z[["province_code", "q", c]].merge(prev, on=["province_code", "q"])      # same province, two quarters earlier
        persist = float((pz[c] == pz["lag2"]).mean())
        e = ev.dropna(subset=[c])
        rows.append({"target": c, "definition": DEFS.get(c, f"SWS H > 11.3 AND {c[2:]}"), "rows": int(len(z)),
                     "prevalence": float(z[c].mean()), "eval_rows_2024Q2_2026Q3": int(len(e)),
                     "eval_prevalence": float(e[c].mean()), "eval_HIGH": int(e[c].sum()),
                     "agreement_with_T43_eval": float((e[c] == e["T43"]).mean()),
                     "two_quarter_persistence": persist,
                     "spearman_regional_share_vs_SWS_hunger": None if rho is None else float(rho.statistic),
                     "spearman_p": None if rho is None else float(rho.pvalue),
                     "prevalence_by_year": {str(k): v for k, v in by_year.items()},
                     "2026Q3_share": float(z.loc[z["target"] == "2026-Q3", c].mean()) if (z["target"] == "2026-Q3").any() else None})
    T = pd.DataFrame(rows)
    X.write_csv(T.drop(columns=["prevalence_by_year"]), X.TABLES / "a4_target_comparison.csv")
    keep = ["target", "province_code", "H_all", "F", "HL", "G", "rfp_vs_2122_pct"] + cands
    X.write_csv(Y[keep].round(3), X.TABLES / "a4_target_labels_by_province_quarter.csv")
    lv = price_levels(d)
    X.dump({"definitions": DEFS, "comparison": rows, "price_levels": lv,
            "recent": Y[Y["q"] >= L.qi("2025-Q4")][keep].round(2).to_dict("records")}, X.OUT / "a4_targets.json")
    print(T.drop(columns=["definition"]).round(3).to_string())
    for k, v in lv.items():
        print(k, {a: round(b, 1) for a, b in v.items()})
    print(Y[Y["q"] >= L.qi("2025-Q4")][keep].round(2).to_string())


if __name__ == "__main__":
    main()
