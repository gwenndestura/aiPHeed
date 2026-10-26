"""FIRI v2 data audit (12 indicators): coverage matrix, corrections, feature lineage and the audited training table.

    python audit_build.py        # needs pull_public.py, reconcile.py and typhoons.py outputs

Writes out/coverage_matrix.csv, out/corrections.json, out/feature_change.csv, out/training_table_lead{1..4}.csv,
out/target_observations.json. Corrections are applied to the in-memory E107 "extra" inputs only (the held files are
not edited); `corrected_data()` is the single place the rerun takes its inputs from.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
EXP = AUD.parent
sys.path.insert(0, str(EXP / "FINAL_THESIS_OBJECTIVES" / "runner"))
import ch1_lib as C  # noqa: E402

FM, B, E, L, NF, np, pd = C.FM, C.B, C.E, C.L, C.NF, C.np, C.pd
OUT = AUD / "out"
DATA = AUD / "data"
QUARTERS = [f"{y}-Q{k}" for y in range(2021, 2027) for k in range(1, 5) if f"{y}-Q{k}" <= "2026-Q3"]
NAMES = L.NAMES


# ================================================================================================ corrected inputs
def bsp_quarterly() -> pd.DataFrame:
    """Quarterly cash remittance levels from BSP cumulative figures: Q2 = H1-Q1, Q3 = 9M-H1, Q4 = FY-9M."""
    c = pd.read_csv(DATA / "bsp_cash_remittances_cumulative.csv").set_index(["year", "period"])["cash_remittances_usd_bn"]
    rows = []
    for y in sorted({k[0] for k in c.index}):
        g = lambda p: c.get((y, p))  # noqa: E731
        vals = {1: g("Q1"), 2: (g("H1") - g("Q1")) if g("H1") and g("Q1") else None,
                3: (g("9M") - g("H1")) if g("9M") and g("H1") else None,
                4: (g("FY") - g("9M")) if g("FY") and g("9M") else None}
        for k, v in vals.items():
            if v is not None:
                rows.append({"quarter": f"{y}-Q{k}", "q": L.qi(f"{y}-Q{k}"), "cash_remit_usd_bn": round(float(v), 4)})
    return pd.DataFrame(rows)


def rice_fresh() -> pd.DataFrame:
    """Quarterly mean of the fresh monthly regular-milled wholesale prices, complete quarters (3 months) only."""
    d = pd.read_csv(DATA / "raw" / "psa_rice_wholesale_AWB01.csv")
    long = d.melt(id_vars=["Geolocation", "Commodity"], var_name="yp", value_name="v")
    long["Geolocation"] = long["Geolocation"].str.strip(". ")
    long = long[long["Geolocation"].isin(NAMES.values()) & (long["Commodity"] == "Regular Milled Rice (RMR)")]
    mon = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"]
    long["m"] = long["yp"].str[5:].str.strip()
    long = long[long["m"].isin(mon)]
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["quarter"] = long["yp"].str[:4] + "-Q" + (long["m"].map({m: i for i, m in enumerate(mon)}) // 3 + 1).astype(str)
    g = long.dropna(subset=["v"]).groupby(["Geolocation", "quarter"])["v"].agg(["mean", "count"]).reset_index()
    return g[g["count"] == 3]


_CORR: dict = {}


def corrected_data():
    """(d, x) with x's remittances, typhoon counts and 2026-Q3 rice replaced by the audited values."""
    if "dx" in _CORR:
        return _CORR["dx"]
    d, x = E.data()
    # a distinct Data object: E107's feature_table cache is keyed on id(d) only, so the corrected x would otherwise
    # be answered from the cache built with the held x (found in this audit)
    import dataclasses
    d = dataclasses.replace(d)
    x = {k: v.copy() for k, v in x.items()}
    bq = bsp_quarterly().set_index("q")["cash_remit_usd_bn"]
    x["ofw"]["ofw_cash_remit_usd_bn"] = x["ofw"]["q"].map(bq)                   # NaN where BSP has no quarter yet
    tc = pd.read_csv(OUT / "typhoons_recomputed.csv", dtype={"province_code": str}).set_index(
        ["province_code", "quarter"])["tc_count_recomputed"]
    x["climate"]["tc_count"] = [float(tc.get((p, q), np.nan)) for p, q in zip(x["climate"]["province_code"],
                                                                              x["climate"]["quarter"])]
    rf = rice_fresh().set_index(["Geolocation", "quarter"])["mean"]
    x["rice"]["price_php_per_kg"] = [float(rf.get((n, q), v)) for n, q, v in
                                     zip(x["rice"]["province_name"], x["rice"]["quarter"], x["rice"]["price_php_per_kg"])]
    _CORR["dx"] = (d, x)
    return d, x


# ================================================================================================ coverage matrix
def _span(df, qcol="quarter"):
    s = df.dropna()
    return (s[qcol].min(), s[qcol].max()) if len(s) else (None, None)


def coverage() -> pd.DataFrame:
    d, x = E.data()
    rows = []

    def add(code, source, freq, geo, n_obs, first, last, missing, note, rule, status, action):
        rows.append({"indicator": code, "label": C.E.FI.LABELS[code] if hasattr(C.E, "FI") else code,
                     "source": source, "frequency": freq, "geography": geo, "n_valid_obs_2021plus": n_obs,
                     "first": first, "last": last, "missing_2021Q1_2026Q3": missing, "availability_rule": rule,
                     "validation": status, "action": action, "note": note})
    # A1/A2: provincial CPI
    y = d.yoy
    for code, com in (("A1", "food"), ("A2", "all_items")):
        s = y[y["commodity"] == com]
        months = s.groupby("province_code")["ym"].agg(["min", "max", "count"])
        add(code, "PSA OpenSTAT 0012M4ACP22 (CPI 2018=100) + PSA-published YoY", "monthly", "province (5)",
            int(s["yoy"].notna().sum()), L.ym_s(int(months["min"].min())), L.ym_s(int(months["max"].max())),
            int((s["yoy"].isna()).sum()),
            "A1 = projected target-quarter food YoY (latest index held flat over base months) minus province P60; "
            "A2 = latest headline YoY minus province P60" if code == "A1" else "headline YoY minus province 2021-22 P60",
            "month m used from O(t) if m <= month 2 of quarter t (PSA releases ~day 5 of m+1)",
            "verified: 690/690 index values equal the fresh PSA pull; published YoY = recomputed within 0.05",
            "none needed")
    r = x["rice"]
    add("A3", "PSA OpenSTAT 0052M4AWB01 regular-milled rice, wholesale", "monthly -> quarterly mean", "province (5)",
        int(r["price_php_per_kg"].notna().sum()), r["quarter"].min(), r["quarter"].max(),
        5 * len(QUARTERS) - int(r["price_php_per_kg"].notna().sum()), "YoY % of quarter t-1 vs t-5",
        "quarter t-1 at O(t)", "107/112 equal; 2026-Q3 held = Jul-Aug only (fetched 2026-09-09)",
        "2026-Q3 replaced by the complete 3-month mean (affects only origins >= 2026-Q4)")
    add("V1", "PSA 2021 municipal SAE poverty + POPCEN 2024 population + land area (lgu_vulnerability.csv)", "static",
        "142 LGUs -> province", 142, "2021 (SAE)", "2024 (POPCEN)", 1,
        "0.6 x min-max poverty + 0.4 x min-max density across the 5 provinces; constant over time",
        "used at every origin (FIRI Amendment 1: SAE 2021 published 2023, POPCEN 2024 published 2025)",
        "142/142 LGUs; 141 with own SAE (Lucena: province substitute)", "none; disclosed as static")
    add("C1", "PAGASA ENSO Alert and Warning System items (enso_context.PAGASA_ENSO)", "event", "national",
        len(C.E.CW.PAGASA_ENSO) if hasattr(C.E.CW, "PAGASA_ENSO") else 18, "2023-03-24", "2026-10-07", 0,
        "1 if the latest El Nino item before O(t) is an Alert/Advisory in force", "items dated before O(t)",
        "checked against PAGASA monitoring page (strong El Nino, updated 2026-10-21, after the last issue date)",
        "none needed")
    c = x["climate"]
    add("C2", "NOAA IBTrACS v04r01 WP best tracks", "6-hourly fixes -> quarterly count", "province centroid, 300 km",
        int(c["tc_count"].notna().sum()), c["quarter"].min(), c["quarter"].max(), 0,
        "distinct storms with a fix within 300 km of the province centroid in quarter t",
        "quarter t (complete at O(t))", "108/115 equal on recomputation; 7 differ by 1 (borderline storms; held "
        "centroids undocumented; held 2026-Q3 fetched mid-quarter)",
        "replaced by the documented recomputation (area-weighted centroids of the app's province boundaries)")
    p = d.prod
    for code, ser in (("C3", ("palay", "corn")), ("C4", ("fish",))):
        s = p[p["series"].isin(ser)]
        add(code, "PSA OpenSTAT 0012E4EVCP0 (palay, corn)" if code == "C3" else "PSA OpenSTAT 0132E4GVFP1 (fisheries)",
            "quarterly", "province (5)", int(s["value"].notna().sum()), L.qs(int(s["q"].min())), L.qs(int(s["q"].max())),
            0, "-(lower of palay/corn YoY, t-1 vs t-5)" if code == "C3" else "-(fisheries YoY, t-1 vs t-5)",
            "quarter t-1 at O(t)", "220/220 equal to the fresh PSA pull; latest published 2026-Q2", "none needed")
    lf = d.lfs[d.lfs["series"] == "ur"]
    add("E1", "PSA OpenSTAT 0021B3FKEI2 LFS unemployment rate", "monthly (some months not surveyed)", "national",
        int(lf["value"].notna().sum()), L.ym_s(int(lf["ym"].min())), L.ym_s(int(lf["ym"].max())), 4,
        "quarter-mean unemployment t-1 minus t-5 (points)", "months of quarter t-1 at O(t)",
        "68/68 equal to the fresh PSA pull", "none needed; national value shared by all provinces")
    o = x["ofw"].drop_duplicates("q")
    add("E2", "BSP OFW cash remittances (held: curated file)", "quarterly", "national",
        int(o["ofw_cash_remit_usd_bn"].notna().sum()), o["quarter"].min(), "2025-Q4", 3,
        "-(YoY %, t-1 vs t-5)", "quarter t-1 at O(t) (BSP releases ~day 15 of month 2 after the quarter)",
        "DEFECT: held levels disagree with BSP releases (e.g. Q1 2025 8.65 vs BSP 8.44; Q2 2021 7.96 vs 7.28); "
        "2026-Q1/Q2 missing", "rebuilt from BSP cumulative releases (22 cited figures); 2026-Q1/Q2 added")
    fs = [NF.NI.corpus_frame().groupby("quarter").size()]
    add("N1", "Project RSS corpus (E31+E60, 9,659 headlines) -> FSSI-v3 (XLM-R zero-shot); GDELT GKG (58,576 docs); "
        "E113 GDELT price-news composite", "daily -> issue-date windows", "region (province tag on 33%)",
        int(fs[0].sum()), fs[0].index.min(), fs[0].index.max(), 0,
        "N1 FSSI-v3 (NaN unless >= 5 admitted headlines); G_pri_yoy; NG_gap_price",
        "headlines / documents published before O(t)",
        "FSSI-v3 sufficient in 17% of province-quarters (sparse); GDELT columns 0% missing from 2022",
        "none; sparse FSSI disclosed")
    add("H1", "SWS involuntary hunger, Balance Luzon (verified non-commissioned series)", "quarterly rounds",
        "Balance Luzon (region)", int(len(C.bl_quarters())), "2021-Q2", "2026-Q3", 3,
        "P(hunger at t+k > 11.3) from the latest reading and its past errors (corrected pi_H)",
        "rounds published before O(t)",
        "DEFECT (fixed in FINAL_THESIS_OBJECTIVES): backend series included the commissioned 2025-Q1 round and "
        "dropped regular 2025-Q2/Q3 rounds", "verified series used")
    return pd.DataFrame(rows)


# ================================================================================================ change and table
def feature_change() -> pd.DataFrame:
    """E107 feature values with the held vs the corrected inputs, every origin and province, Lead 1."""
    held = E.feature_table(1)
    d, x = corrected_data()
    corr = E.feature_table(1, range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1), d, x)
    j = held.merge(corr, on=["t", "province_code"], suffixes=("_held", "_corr"))
    rows = []
    for col in E.COLUMNS:
        a, b = j[f"{col}_held"], j[f"{col}_corr"]
        ch = ~((a == b) | (a.isna() & b.isna()))
        rows.append({"feature": col, "rows": len(j), "changed": int(ch.sum()),
                     "newly_available": int((a.isna() & b.notna()).sum()),
                     "max_abs_change": float((a - b).abs().max()) if ch.any() else 0.0,
                     "origins_changed": sorted({L.qs(int(t)) for t in j.loc[ch, "t"]})[:30]})
    return pd.DataFrame(rows)


def training_table(k: int) -> pd.DataFrame:
    d, x = corrected_data()
    X = C.build_X(k, d, x)
    lab = C.labels()
    T = X.merge(lab.rename(columns={"q": "target_q_lab"}), left_on=["province_code", "target_q"],
                right_on=["province_code", "target_q_lab"], how="left")
    T["target_quarter"] = T["target_q"].map(L.qs)
    T["origin"] = T["t"].map(L.qs)
    keep = ["origin", "issue_date", "province_code", "target_quarter", "lead_days", "sws_newest_q",
            "sws_newest_published", "true_horizon", "psa_newest_month", "news_latest_published"] + C.COLS + \
           ["y", "price", "hunger", "H", "F", "HL"]
    return T[[c for c in keep if c in T.columns]]


def target_observations() -> dict:
    lab = C.labels()
    r = FM.rounds("primary")
    bl = r[r["area"] == "BL"]
    return {"sws_rounds_2021plus": int(bl["published"].nunique()), "sws_quarters_with_reading": int(bl["q"].nunique()),
            "t43c_labelled_province_quarters": int(len(lab)), "t43c_labelled_quarters": int(lab["q"].nunique()),
            "t43c_high": int(lab["y"].sum()),
            "independent_hunger_values": int(bl["q"].nunique()),
            "independent_price_series": "5 provinces x 20 quarters, but provincial food inflation co-moves "
                                        "(mean pairwise correlation reported in UPDATED_FORECAST_EVALUATION.md)",
            "price_condition_pairwise_corr": float(lab.pivot_table(index="q", columns="province_code", values="F")
                                                   .corr().where(lambda m: ~np.eye(5, dtype=bool)).stack().mean())}


def main():
    cov = coverage()
    cov.to_csv(OUT / "coverage_matrix.csv", index=False)
    ch = feature_change()
    ch.to_csv(OUT / "feature_change.csv", index=False)
    print(ch[["feature", "changed", "newly_available", "max_abs_change"]].to_string(index=False))
    for k in (1, 2, 3, 4):
        training_table(k).to_csv(OUT / f"training_table_lead{k}.csv", index=False, float_format="%.6g")
    tobs = target_observations()
    FM.write_json(OUT / "target_observations.json", tobs)
    print(tobs)
    bq = bsp_quarterly()
    bq.to_csv(DATA / "bsp_cash_remittances_quarterly.csv", index=False)
    print(bq.tail(8).to_string(index=False))


if __name__ == "__main__":
    main()
