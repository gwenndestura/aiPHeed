"""E65 r2 (PROTOCOL section 3): climate-feature availability and contribution audit for the 2026-Q3, 2026-Q4 and
2027-Q1 forecasts, ENSO counterfactuals with each origin's own fitted model, and the CPI projection the price part
would need for P >= 0.5.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit/runner/r2_climate_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e65_lib as H  # noqa: E402
import r1_trace as T  # noqa: E402

L, P2, F, G, np, pd = H.L, H.P2, H.F, H.G, H.np, H.pd
from scipy.optimize import brentq  # noqa: E402

# Static metadata per climate input (sources: feature_schema.json, pagasa_climate_fetcher.py, e43/e44 code)
META = {
    "enso": ("NOAA CPC ONI, quarter mean of the 3-month seasons centred in quarter t-1, coded El Nino +1 / neutral 0 / "
             "La Nina -1 (binary phase; intensity discarded)", "t-1",
             "last season of t-1 is published early in month 2 of t: available before O(t)", "observed",
             "province rows are copies of one national/Pacific index (no provincial variation)"),
    "enso_l2": ("same as enso, quarter t-2", "t-2", "available", "observed", "national/Pacific index"),
    "enso_x_mom": ("enso x 3-month food-CPI momentum", "t-1 / latest CPI months", "available", "observed",
                   "province (through CPI momentum)"),
    "tc_count": ("NOAA IBTrACS WP v04r01: storms passing within 300 km of the province centroid in quarter t",
                 "t", "complete at O(t) for back-tests; for the 2027-Q1 forecast the file was fetched 2026-09-09, so "
                 "2026-Q3 stops on 09-09 and a storm after that is counted as 0 (no-storm fill)", "observed",
                 "province centroid"),
    "tc_count_l1": ("IBTrACS, quarter t-1", "t-1", "available", "observed", "province centroid"),
    "palay_yoy": ("PSA palay production (OpenSTAT 0012E4EVCP0), quarter t-1 YoY", "t-1",
                  "released about 6-7 weeks after the quarter: available", "observed", "province"),
    "corn_yoy": ("PSA corn production, quarter t-1 YoY", "t-1", "available", "observed", "province"),
    "tcl1_x_palay": ("tc_count_l1 x palay_yoy", "t-1", "available", "observed", "province"),
    "news_climate": ("share of the quarter's geocoded food news tagged Climate Stress (E40 keyword classifier)", "t",
                     "articles dated before O(t) only; collection was retrospective (E62 r5)", "observed (text)",
                     "province (attributed articles)"),
}
NOT_IN_MODEL = [
    ("ENSO intensity class (WEAK..VERY_STRONG)", "pagasa_climate.parquet `enso_intensity`", "in the data file, not used"),
    ("drought_alert", "pagasa_climate.parquet: El Nino and quarter-mean ONI >= 1.0 (derived from ONI; not a PAGASA "
     "drought advisory)", "in the data file, not used"),
    ("rainfall_anomaly_pct", "null in pagasa_climate.parquet; province_rainfall.parquet (NASA POWER) holds pre-2021 "
     "rows and is refused by the study-window rule", "no in-window rainfall series"),
    ("PAGASA ENSO Alert/Advisory status and strength outlook", "PAGASA press releases / advisories (sources/SOURCES.md)",
     "not in the pipeline"),
    ("PAGASA monthly rainfall outlook / drought-dry spell assessment by province", "PAGASA advisories (PDF text)",
     "not in the pipeline; no machine-readable 2021-2026 provincial series was assembled"),
    ("NOAA/IRI ENSO forecast plume (Nino 3.4 forecast)", "not collected", "not in the pipeline"),
]


def p_of(fx, te, hte):
    return float(fx["model"].predict(te)[0]) * T.p_hunger(fx["hc"], hte)


def main():
    H.verify_protocol()
    d, X, B = H.E.load()
    space = G.search_space()
    parts = {k: T.origin_parts(d, X, B, t, space) for k, t in T.ORIG.items()}
    rows, cf, need = [], [], []
    for k, fx in parts.items():
        te = fx["te"].reset_index(drop=True)
        hte = fx["hte"]
        bst = fx["model"].model.booster_
        splits = dict(zip(bst.feature_name(), bst.feature_importance("split").tolist()))
        sh = fx["model"].contributions(te)
        hterms, _, _, _ = T.hunger_terms(fx["hc"], hte)
        hm = fx["hc"]["model"]
        for f, (src, ref, avail, kind, level) in META.items():
            vals = te[f].tolist() if f in te else [np.nan] * 5
            rows.append({"target": k, "issue_date": str(L.origin(T.ORIG[k]).date()), "feature": f,
                         "reference_period": L.qs(T.ORIG[k] + {"t": 0, "t-1": -1, "t-2": -2}.get(ref.split()[0], 0))
                         if ref.split()[0] in ("t", "t-1", "t-2") else ref,
                         "values_by_province": "; ".join(f"{L.NAMES[p]} {v:.3g}" if pd.notna(v) else f"{L.NAMES[p]} NaN"
                                                        for p, v in zip(L.PROVS, vals)),
                         "n_missing": int(pd.isna(vals).sum()), "source": src, "availability_at_issue": avail,
                         "observed_or_forecast": kind, "spatial_level": level,
                         "price_model_splits": int(splits.get(f, 0)),
                         "price_logit_contribution_by_province": "; ".join(
                             f"{L.NAMES[p]} {sh.iloc[i][f]:+.3f}" for i, p in enumerate(L.PROVS)) if f in sh else "not an input",
                         "in_hunger_ridge": f in hm.cols, "hunger_H_points": round(hterms.get(f, 0.0), 3),
                         "hunger_ridge_alpha": fx["hc"]["alpha"]})
        # counterfactuals: the same fitted model, ENSO inputs replaced (other inputs as observed)
        for label, enso, enso_l2 in (("as observed", None, None), ("ENSO neutral (0, 0)", 0.0, 0.0),
                                     ("El Nino both lags (+1, +1)", 1.0, 1.0), ("La Nina both lags (-1, -1)", -1.0, -1.0)):
            te2, hte2 = te.copy(), hte.copy()
            if enso is not None:
                for z in (te2, hte2):
                    z["enso"], z["enso_l2"] = enso, enso_l2
                te2["enso_x_mom"] = te2["enso"] * te2["mom3"]
            for i, p in enumerate(L.PROVS):
                cf.append({"target": k, "scenario": label, "province": L.NAMES[p],
                           "P_price": float(fx["model"].predict(te2.iloc[[i]])[0]),
                           "P_hunger": T.p_hunger(fx["hc"], hte2), "P": p_of(fx, te2.iloc[[i]], hte2)})
        # CPI projection needed for P >= 0.5 (other inputs and trees as observed)
        m = fx["cfg"]["m"]
        ph = T.p_hunger(fx["hc"], hte)
        for i, p in enumerate(L.PROVS):
            row = te.iloc[[i]].copy()

            def gap_fn(x, col):
                r = row.copy()
                r[col] = x
                return float(fx["model"].predict(r)[0]) * ph - 0.5
            out = {"target": k, "province": L.NAMES[p], "P_hunger": ph,
                   "food_projection": float(row[f"base_{m}"].iloc[0]), "gap_projection": float(row[f"gbase_{m}"].iloc[0]),
                   "threshold_food": L.e40_spec()["food"][p], "threshold_gap": L.e40_spec()["gap"][p]}
            for col, key in ((f"base_{m}", "food_projection_needed"), (f"gbase_{m}", "gap_projection_needed")):
                try:
                    out[key] = brentq(lambda x: gap_fn(x, col), -20, 40) if gap_fn(40, col) > 0 > gap_fn(-20, col) or gap_fn(40, col) < 0 < gap_fn(-20, col) else np.nan
                except ValueError:
                    out[key] = np.nan
            need.append(out)
    A = pd.DataFrame(rows)
    C = pd.DataFrame(cf)
    N = pd.DataFrame(need)
    H.write_csv(A, H.TABLES / "r2_climate_feature_audit.csv")
    H.write_csv(C, H.TABLES / "r2_enso_counterfactuals.csv")
    H.write_csv(N, H.TABLES / "r2_cpi_needed_for_high.csv")
    pag = [{"issue_date": str(L.origin(t).date()), "target": k, "pagasa_status_code": H.official_status(t),
            "pagasa_status": H.PAGASA_STATUS[str(L.origin(t).date())][1],
            "model_enso_input": float(parts[k]["te"]["enso"].iloc[0]),
            "model_enso_l2_input": float(parts[k]["te"]["enso_l2"].iloc[0])} for k, t in T.ORIG.items()]
    H.dump({"protocol_sha256": H.verify_protocol(), "pagasa_vs_model": pag, "not_in_model": NOT_IN_MODEL},
           H.OUT / "r2_climate_audit.json")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    print(A[["target", "feature", "price_model_splits", "in_hunger_ridge", "hunger_H_points", "values_by_province"]].to_string(index=False))
    print(C.pivot_table(index=["target", "province"], columns="scenario", values="P").round(4).to_string())
    print(C.groupby(["target", "scenario"])["P_hunger"].first().round(4).to_string())
    print(N.round(2).to_string(index=False))
    print(pag)


if __name__ == "__main__":
    main()
