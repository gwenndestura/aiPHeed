"""E55 feature audit (score-free): for every E55-LGBM input, its source, geography, reference period at the issue
date, publication rule, transformation, missingness over the twelve origins, and use in training and inference.

    backend/venv/Scripts/python.exe -B runner/e55_feature_audit.py   -> tables/feature_audit.csv
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e55_lib as F  # noqa: E402

L, P2, M, np, pd = F.L, F.P2, F.M, F.np, F.pd
META = {
    # col: (group, source, geography, reference period at O(t), transformation)
    "F_hat_M1": ("market", "PSA CPI food index (OpenSTAT 0012M4ACP22)", "province", "months through m0 (published before O(t))", "E41 M1 drift projection of quarter-mean food YoY at t+2"),
    "F_now": ("market", "PSA CPI food YoY", "province", "latest two published months", "mean YoY, %"),
    "D_now": ("market", "PSA CPI food YoY", "province", "latest two published months", "province minus five-province mean"),
    "gap_now": ("market", "PSA CPI food and all-items YoY", "province", "latest two published months", "food minus headline YoY"),
    "rice_whsl_yoy": ("market", "PSA wholesale rice prices", "province", "quarter t-1", "YoY %"),
    "tariff_yoy_regime": ("market", "EO 62 (2024) rice tariff cut", "national", "orders announced before O(t)", "share of target months whose YoY compares post-cut with pre-cut"),
    "import_suspension_share": ("market", "DA rice import suspension orders", "national", "announced before O(t)", "share of target months covered"),
    "price_ceiling_share": ("market", "rice price ceiling / MSRP orders", "national", "announced before O(t)", "share of target months covered"),
    "food_emergency_share": ("market", "food security emergency declaration", "national", "announced before O(t)", "share of target months covered"),
    "tc_count": ("climate", "IBTrACS typhoon tracks", "province (300 km)", "quarter t", "count"),
    "tc_count_l1": ("climate", "IBTrACS typhoon tracks", "province (300 km)", "quarter t-1", "count"),
    "enso": ("climate", "NOAA ONI", "national", "quarter t-1", "El Nino 1 / neutral 0 / La Nina -1"),
    "enso_l2": ("climate", "NOAA ONI", "national", "quarter t-2", "phase code"),
    "palay_yoy": ("climate", "PSA palay production (OpenSTAT 0012E4EVCP0)", "province", "quarter t-1", "YoY %"),
    "corn_yoy": ("climate", "PSA corn production", "province", "quarter t-1", "YoY %"),
    "enso_x_mom": ("climate", "ONI x CPI momentum", "province", "t-1 / latest months", "interaction"),
    "tcl1_x_palay": ("climate", "typhoons x palay", "province", "t-1", "interaction"),
    "fish_yoy": ("fish_kill", "PSA fisheries production (0132E4GVFP1)", "province", "quarter t-1", "YoY %; no official fish-kill event series exists"),
    "aqua_yoy": ("fish_kill", "PSA aquaculture production", "province", "quarter t-1", "YoY %"),
    "ur_yoy": ("employment", "PSA LFS unemployment rate", "national", "quarter t-1", "YoY points"),
    "under_yoy": ("employment", "PSA LFS underemployment rate", "national", "quarter t-1", "YoY points"),
    "remit_usd_yoy": ("ofw_remittance", "BSP OF cash remittances", "national", "quarter t-1 (dataset ends 2025-Q4)", "YoY %"),
    "remit_php_yoy": ("ofw_remittance", "BSP remittances x USD/PHP", "national", "quarter t-1 (dataset ends 2025-Q4)", "YoY %"),
    "fx_yoy": ("ofw_remittance", "ECB USD/PHP reference rate", "national", "quarter t-1", "YoY %"),
    "news_market": ("market", "news corpus, trigger classifier", "province", "quarter t", "share of titles"),
    "news_climate": ("climate", "news corpus, trigger classifier", "province", "quarter t", "share of titles"),
    "news_fish_kill": ("fish_kill", "news corpus, trigger classifier", "province", "quarter t", "share of titles"),
    "news_employment": ("employment", "news corpus, trigger classifier", "province", "quarter t", "share of titles"),
    "news_ofw_remittance": ("ofw_remittance", "news corpus, trigger classifier", "province", "quarter t", "share of titles"),
    "news_n": ("other", "news corpus", "province", "quarter t", "article count"),
    "pov": ("poverty", "PSA 2021 municipal SAE (141 LGUs)", "province mean of municipal estimates", "2021 (published 2024; known from O >= 2025-01-01 in POV-AS)", "centred across provinces"),
    "base_m (offset)": ("market", "PSA CPI food and all-items index", "province", "months through m0", "base-effect projection of food YoY and gap at t+2 -> structural probability -> LightGBM init_score"),
    "H (hunger gate)": ("hunger", "SWS Balance Luzon hunger (sws_rounds.csv, approved rounds)", "region", "rounds posted before O(t)", "I7 ridge -> P(H(t+2) > 11.3)"),
}


def main():
    d, X, B = F.E.load()
    origins = list(range(L.qi("2023-Q4"), L.qi("2026-Q3") + 1))
    XB = F.add_poverty(X.merge(B, on=["t", "province_code"]), "AS")
    XB = XB[XB["t"].isin(origins)]
    cols = F.feature_cols("all") + ["pov"]
    rows = []
    for c, (g, src, geo, ref, tf) in META.items():
        if c in XB:
            miss = float(XB[c].isna().mean())
            per = XB.groupby("t")[c].apply(lambda s: s.isna().all())
            missing_origins = [L.qs(t) for t, v in per.items() if v]
        else:
            miss, missing_origins = (float(XB["base_1.0"].isna().mean()) if c.startswith("base") else 0.0), []
        use = ("E55-LGBM trees (all-groups configurations)" if c in F.feature_cols("all") else
               "POV-AS / POV-LA arms only" if c == "pov" else "E55-LGBM offset" if c.startswith("base") else
               "E55-LGBM hunger gate")
        rows.append({"feature": c, "group": g, "source": src, "geography": geo, "reference_at_issue": ref,
                     "transformation": tf, "share_missing_2023Q4_2026Q3_origins": round(miss, 3),
                     "origins_all_missing": ";".join(missing_origins), "use": use,
                     "in_market_only_set": c in F.feature_cols("market")})
    assert set(F.feature_cols("all")) <= set(META), set(F.feature_cols("all")) - set(META)
    out = F.E55 / "tables"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "feature_audit.csv", index=False)
    print(len(rows), "features audited")


if __name__ == "__main__":
    main()
