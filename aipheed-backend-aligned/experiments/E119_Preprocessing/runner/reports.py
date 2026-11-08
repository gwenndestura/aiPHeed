"""E119 report tables from the preprocessing outputs (no new computation of features).

    python reports.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import preprocess as P

ROOT, OUT = P.ROOT, P.OUT
FI = P.FI
SKIP = {"origin", "t", "issue_date", "lead", "target_quarter", "target_q", "y_bl_hunger", "y_published", "H1_status", "H1_bl_latest_quarter",
        "province", "province_code", "A_status", "A_cpi_month"}
H1_FEATS = ["H1_bl_latest", "H1_bl_previous", "H1_bl_change", "H1_staleness_q"]
PROV_A = ["A1_food_projection_asof", "A1_gap_projection_asof", "A2_headline_above_usual_asof"]


def feature_cols(df):
    return [c for c in df.columns if c not in SKIP and not c.endswith(("__status", "__period"))]


def ind_of(f, meta):
    if f in H1_FEATS:
        return "H1"
    if f.startswith("A1_"):
        return "A1"
    if f.startswith("A2_"):
        return "A2"
    m = meta.get(f)
    return (m["indicator"] if isinstance(m["indicator"], str) else "UNASSIGNED") if m is not None else "UNASSIGNED"


def main():
    R = pd.read_csv(ROOT / "E119_REGIONAL_MODELING_DATASET.csv")
    Pv = pd.read_csv(ROOT / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv")
    A = pd.read_csv(ROOT / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv")
    meta = pd.read_csv(OUT / "feature_meta.csv").set_index("feature").to_dict("index")
    PIT = pd.read_csv(ROOT / "E119_POINT_IN_TIME_VALIDATION.csv")

    # ---------------- feature dictionary
    dic = []
    for f, m in meta.items():
        dic.append({"feature": f, "fiRI_indicator": m["indicator"] if isinstance(m["indicator"], str) else "UNASSIGNED", "role": m["role"],
                    "unit": m["unit_label"], "resolution": m["resolution"], "source": m["source"], "aggregation_or_formula": m["aggregation"],
                    "availability_rule": m["rule"], "units_present": m["units"]})
    dic += [{"feature": f, "fiRI_indicator": "H1", "role": "direct (latest published SWS Balance Luzon reading)", "unit": "%" if f != "H1_staleness_q" else "quarters",
             "resolution": "region (Balance Luzon)", "source": "SWS tables (E114, non-commissioned)", "aggregation_or_formula": {"H1_bl_latest": "mean of rounds of the newest quarter published before issue", "H1_bl_previous": "the quarter before that", "H1_bl_change": "latest - previous", "H1_staleness_q": "origin - quarter of latest reading"}[f],
             "availability_rule": "published < issue (verified)", "units_present": "Balance Luzon"} for f in H1_FEATS]
    dic += [{"feature": f, "fiRI_indicator": f[:2], "role": "direct (served A1/A2 definition, as-of thresholds)", "unit": "pp", "resolution": "province",
             "source": "corrected pipeline (provincial_profile)", "aggregation_or_formula": "projection minus P60 of quarters published before issue (2021+)",
             "availability_rule": "CPI to month 2 of t; release ledger status", "units_present": "5 provinces"} for f in PROV_A]
    pd.DataFrame(dic).to_csv(ROOT / "E119_FEATURE_ENGINEERING_DICTIONARY.csv", index=False, lineterminator="\n")

    # ---------------- missing data (per dataset x feature)
    miss = []
    for name, D in (("regional", R), ("provincial", Pv)):
        for f in feature_cols(D):
            st = D.get(f"{f}__status")
            n_miss = int(D[f].isna().sum())
            reasons = st[D[f].isna()].value_counts().to_dict() if st is not None else {}
            first = D.loc[D[f].notna(), "origin"].min() if D[f].notna().any() else None
            reason = "; ".join(f"{k}: {v}" for k, v in reasons.items()) if reasons else ""
            if f.endswith(("_yoy_pct", "_change_pp", "_drop", "_anomaly_mm", "_anomaly_c", "decline_pct")) and n_miss:
                reason += ("; " if reason else "") + "needs a 2021+ value one year earlier (no pre-2021 base)"
            if f.startswith(("chicken_production", "livestock_production")):
                reason += "; provincial series start 2023"
            if f.startswith(("rainfall", "temperature")):
                reason += "; NASA POWER monthly endpoint ends 2025-12"
            if f == "N1_fssi_v3":
                reason += "; fewer than 5 admitted articles (corpus collected every quarter)"
            if f.startswith("A1_") or f.startswith("A2_"):
                reason += "; as-of threshold needs >= 4 published quarters"
            miss.append({"dataset": name, "feature": f, "indicator": ind_of(f, meta), "rows": len(D), "missing": n_miss,
                         "missing_pct": round(100 * n_miss / len(D), 1), "first_origin_available": first, "reason": reason.strip("; "),
                         "usable_for_modeling": "yes" if n_miss / len(D) <= .35 else "limited (sparse)" if n_miss / len(D) < .8 else "no (too sparse)",
                         "verified_share_of_present": round(float((st[D[f].notna()] == "verified").mean()), 3) if st is not None and D[f].notna().any() else None})
    for f, g in A.groupby("feature"):
        miss.append({"dataset": "annual (provincial)", "feature": f, "indicator": g["indicator"].iloc[0], "rows": len(g), "missing": int(g["value"].isna().sum()),
                     "missing_pct": round(100 * g["value"].isna().mean(), 1), "first_origin_available": str(g["reference_year"].min()),
                     "reason": "annual / triennial / static; kept at its own frequency", "usable_for_modeling": "annual only (different frequency)",
                     "verified_share_of_present": round(float(g["status"].str.startswith("verified").mean()), 3)})
    M = pd.DataFrame(miss)
    M.to_csv(ROOT / "E119_MISSING_DATA_REPORT.csv", index=False, lineterminator="\n")

    # ---------------- temporal alignment (per feature: lag at issue)
    PIT["origin_q"] = PIT["origin"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    ta = []
    for (ds, f), g in PIT.groupby(["dataset", "feature"]):
        lag = (g["origin_q"] - g["obs_q"]).dropna()
        m = meta.get(f, {})
        ta.append({"dataset": ds, "feature": f, "indicator": ind_of(f, meta), "source_frequency": "monthly" if "month" in str(m.get("rule", "")) or "m+" in str(m.get("rule", "")) else "quarterly",
                   "aggregation": m.get("aggregation", "see dictionary"), "availability_rule": m.get("rule", "see dictionary"),
                   "obs_quarter_lag_at_issue_median": float(lag.median()) if len(lag) else None, "obs_quarter_lag_min": float(lag.min()) if len(lag) else None,
                   "obs_quarter_lag_max": float(lag.max()) if len(lag) else None, "values": int(len(g)), "verified_share": round(float((g["status"] == "verified").mean()), 3),
                   "all_available_before_issue": bool((g["avail_date"].astype(str) < g["issue_date"].astype(str)).all())})
    pd.DataFrame(ta).to_csv(ROOT / "E119_TEMPORAL_ALIGNMENT_REPORT.csv", index=False, lineterminator="\n")

    # ---------------- geography
    geo = []
    for f, m in meta.items():
        units = m["units"].split("; ")
        geo.append({"feature": f, "indicator": ind_of(f, meta), "source_resolution": m["resolution"], "units": m["units"],
                    "all_five_provinces": all(p in units for p in P.PROVS), "used_in_regional": f in R.columns, "used_in_provincial": f in Pv.columns,
                    "copied_across_provinces": False,
                    "note": "regional/national value kept at its own unit" if m["resolution"] in ("national", "region", "global/national", "region proxy") else
                            "point value at province centroid" if "centroid" in m["resolution"] else "provincial observation"})
    G = pd.DataFrame(geo)
    G.to_csv(ROOT / "E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv", index=False, lineterminator="\n")

    # ---------------- 12-indicator mapping (dataset -> indicator)
    mp = []
    for f, m in meta.items():
        ind = m["indicator"] if isinstance(m["indicator"], str) else "UNASSIGNED"
        mp.append({"indicator": ind, "indicator_label": FI.LABELS.get(ind, "(no matching FIRI indicator)"), "feature_or_dataset": f, "relationship": m["role"],
                   "source": m["source"], "resolution": m["resolution"], "frequency": "quarterly (from monthly)" if "quarter mean" in m["aggregation"] or "quarterly total" in m["aggregation"] or "quarterly mean" in m["aggregation"] else "quarterly",
                   "observation_period": "2021+", "publication_timing": m["rule"]})
    for f in H1_FEATS:
        mp.append({"indicator": "H1", "indicator_label": FI.LABELS["H1"], "feature_or_dataset": f, "relationship": "direct", "source": "SWS", "resolution": "region",
                   "frequency": "quarterly", "observation_period": "2021-Q2+", "publication_timing": "published date (verified)"})
    for f in PROV_A:
        mp.append({"indicator": f[:2], "indicator_label": FI.LABELS[f[:2]], "feature_or_dataset": f, "relationship": "direct (served definition)", "source": "corrected pipeline",
                   "resolution": "province", "frequency": "quarterly (as of issue)", "observation_period": "2021+ (bases >= 2021-01)", "publication_timing": "CPI ledger / day-10 rule"})
    for f, g in A.groupby("feature"):
        mp.append({"indicator": g["indicator"].iloc[0], "indicator_label": FI.LABELS[g["indicator"].iloc[0]], "feature_or_dataset": f,
                   "relationship": "direct (served V1)" if f == "V1_vulnerability_profile" else "supporting (annual)", "source": "PSA / owner file",
                   "resolution": g["resolution"].iloc[0], "frequency": "annual / triennial / static", "observation_period": f"{g['reference_year'].astype(str).min()}+",
                   "publication_timing": g["status"].iloc[0]})
    MP = pd.DataFrame(mp)
    # redundancy: correlations between supporting and direct features in the provincial dataset
    pairs = [("retail_rice_regular_yoy_pct", "rice_wholesale_yoy_pct"), ("cpi_bottom30_food_yoy_pct", "cpi_food_yoy_pct"),
             ("typhoons_local_100km", "C2_typhoons_300km"), ("aquaculture_production_yoy_pct", "C4_fisheries_drop"),
             ("retail_chicken_yoy_pct", "cpi_food_yoy_pct"), ("farmgate_palay_yoy_pct", "rice_wholesale_yoy_pct")]
    red = {}
    for a, b in pairs:
        d = Pv[[a, b]].dropna()
        red[f"{a} vs {b}"] = {"rows": int(len(d)), "corr": float(d[a].corr(d[b])) if len(d) > 5 else None}
    MP["redundancy_note"] = MP["feature_or_dataset"].map({a: f"r = {red[f'{a} vs {b}']['corr']:.2f} with {b}" for a, b in pairs if red[f"{a} vs {b}"]["corr"] is not None})
    MP.to_csv(ROOT / "E119_12_INDICATOR_DATA_MAPPING.csv", index=False, lineterminator="\n")

    # ---------------- indicator preprocessing + coverage
    ipr, cov = [], []
    for code, label in list(FI.LABELS.items()) + [("UNASSIGNED", "(domain support without a matching FIRI indicator)")]:
        obs_f = OUT / "indicators" / code / "observations_clean.csv"
        obs = pd.read_csv(obs_f) if obs_f.exists() else pd.DataFrame()
        mm = M[M["indicator"] == code]
        feats = sorted(MP.loc[MP["indicator"] == code, "feature_or_dataset"].unique())
        direct = MP.loc[(MP["indicator"] == code) & MP["relationship"].str.startswith("direct"), "feature_or_dataset"].tolist()
        ipr.append({"indicator": code, "label": label, "trigger_domain": P.TRIGGER.get(code, "unassigned"), "fao_dimensions": P.FAO.get(code, "availability / stability (support)"),
                    "direct_features": "; ".join(direct), "supporting_features": "; ".join(f for f in feats if f not in direct),
                    "clean_observations_2021plus": int(len(obs)), "units": "; ".join(sorted(obs["unit_label"].unique())) if len(obs) else "",
                    "geography": "; ".join(sorted(obs["resolution"].unique())) if len(obs) else ("province (annual)" if code == "V1" else ""),
                    "first_period": obs["period_label"].min() if len(obs) else "", "last_period": obs["period_label"].max() if len(obs) else "",
                    "verified_share_obs": round(float(obs["status"].astype(str).str.startswith("verified").mean()), 3) if len(obs) else None,
                    "max_missing_pct_in_datasets": float(mm["missing_pct"].max()) if len(mm) else None,
                    "eligibility": ("annual / static provincial profile (not quarterly)" if code == "V1" else "strict and provisional" if len(obs) and (obs["status"] == "verified").mean() > .9 else
                                    "provisional only (release dates unverified)" if len(obs) else "annual / static profile only" if code == "V1" else "")})
        for name, D in (("regional", R), ("provincial", Pv)):
            fs = [f for f in feature_cols(D) if ind_of(f, meta) == code]
            for f in fs:
                st = D.get(f"{f}__status")
                cov.append({"indicator": code, "dataset": name, "feature": f, "rows": len(D), "non_missing": int(D[f].notna().sum()),
                            "coverage_pct": round(100 * D[f].notna().mean(), 1),
                            "verified_rows": int((st == "verified").sum()) if st is not None else (int(D[f].notna().sum()) if f in H1_FEATS else 0),
                            "provinces": int(D.loc[D[f].notna(), "province"].nunique()) if name == "provincial" else None})
    IPR, COV = pd.DataFrame(ipr), pd.DataFrame(cov)
    IPR.to_csv(ROOT / "E119_INDICATOR_PREPROCESSING_REPORT.csv", index=False, lineterminator="\n")
    COV.to_csv(ROOT / "E119_INDICATOR_COVERAGE_REPORT.csv", index=False, lineterminator="\n")
    dom = []
    for d in ("market_prices", "fish_production", "climate", "employment", "ofw_remittances", "news_nlp (other input)", "poverty_vulnerability (other input)", "regional_hunger (target component)"):
        codes = [k for k, v in P.TRIGGER.items() if v == d]
        c = COV[COV["indicator"].isin(codes)]
        dom.append({"domain": d, "indicators": " ".join(codes), "features": int(c["feature"].nunique()),
                    "regional_coverage_pct_mean": round(float(c.loc[c["dataset"] == "regional", "coverage_pct"].mean()), 1) if (c["dataset"] == "regional").any() else None,
                    "provincial_coverage_pct_mean": round(float(c.loc[c["dataset"] == "provincial", "coverage_pct"].mean()), 1) if (c["dataset"] == "provincial").any() else None,
                    "verified_share": round(float(c["verified_rows"].sum() / max(1, c["non_missing"].sum())), 3),
                    "provincial_resolution": "yes (annual table only)" if codes == ["V1"] else "yes" if (c["dataset"] == "provincial").any() else "no (national/regional only)",
                    "annual_rows": int((A["indicator"].isin(codes)).sum())})
    pd.DataFrame(dom).to_csv(ROOT / "E119_DOMAIN_COVERAGE_REPORT.csv", index=False, lineterminator="\n")
    pd.DataFrame([{"indicator": k, "label": v, "trigger_domain": P.TRIGGER[k], "fao_dimensions": P.FAO[k],
                   "note": "secondary classification; FIRI v2 structure unchanged"} for k, v in FI.LABELS.items()]).to_csv(ROOT / "E119_FAO_DIMENSION_MAPPING.csv", index=False, lineterminator="\n")

    # ---------------- unified 12-indicator dataset (long; national / regional values once, under their own unit)
    uni = []
    for name, D, unitcol in (("provincial", Pv, "province"), ("regional", R[R["lead"] == 1], None)):
        for f in feature_cols(D):
            ind = ind_of(f, meta)
            res = "province" if name == "provincial" else meta.get(f, {}).get("resolution", "region (Balance Luzon)" if f in H1_FEATS else "region")
            unit = (lambda r: r[unitcol]) if unitcol else (lambda r, f=f: "Balance Luzon" if f in H1_FEATS else meta.get(f, {}).get("units", "Region IV-A"))
            st, per = D.get(f"{f}__status"), D.get(f"{f}__period")
            for i, r in D.iterrows():
                if pd.isna(r[f]):
                    continue
                uni.append({"unit": unit(r), "resolution": res, "origin": r["origin"], "issue_date": r["issue_date"], "indicator": ind,
                            "trigger_domain": P.TRIGGER.get(ind, "unassigned"), "feature": f, "value": r[f],
                            "obs_period": per[i] if per is not None else (r.get("H1_bl_latest_quarter") if f in H1_FEATS else r.get("A_cpi_month")),
                            "status": st[i] if st is not None else ("verified" if f in H1_FEATS else ("verified" if str(r.get("A_status", "")).startswith("verified") else "rule_unverified"))})
    for r in A.itertuples():
        uni.append({"unit": r.province, "resolution": r.resolution, "origin": None, "issue_date": None, "indicator": r.indicator, "trigger_domain": P.TRIGGER[r.indicator],
                    "feature": r.feature, "value": r.value, "obs_period": str(r.reference_year), "status": r.status})
    U = pd.DataFrame(uni)
    U.to_csv(ROOT / "E119_UNIFIED_12_INDICATOR_DATASET.csv", index=False, lineterminator="\n", float_format="%.10g")
    json.dump({"redundancy": red, "unified_rows": len(U), "indicators_in_unified": sorted(U["indicator"].unique())}, open(OUT / "reports_summary.json", "w"), indent=1, default=float)
    print(IPR[["indicator", "clean_observations_2021plus", "geography", "first_period", "last_period", "verified_share_obs", "eligibility"]].to_string())
    print(pd.read_csv(ROOT / "E119_DOMAIN_COVERAGE_REPORT.csv").to_string())
    print(json.dumps(red, indent=1, default=float), len(U), sorted(U["indicator"].unique()))


if __name__ == "__main__":
    main()
