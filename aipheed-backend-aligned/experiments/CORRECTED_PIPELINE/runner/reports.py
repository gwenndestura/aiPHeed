"""Builds the corrected-pipeline report tables from ../out (no fitting, no raw file touched).

    python reports.py   # ../CORRECTED_DATA_DICTIONARY.csv, ../CORRECTED_INDICATOR_COVERAGE.csv,
                        # ../POINT_IN_TIME_VALIDATION.csv, ../GEOGRAPHICAL_ALIGNMENT_RESULTS.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import pipeline as PL

ROOT = PL.ROOT
OUT = PL.OUT

DICT = [  # table, column, meaning, unit, resolution, source, availability rule, status column
    ("provincial_profile", "A1_food_frozen", "food-price projection minus frozen 2021-22 P60 (served definition)", "pp", "province", "PSA CPI", "CPI to month 2 of t", "cpi_release_status"),
    ("provincial_profile", "A1_food_asof", "same projection minus P60 of quarters published before the issue", "pp", "province", "PSA CPI", "as above; thresholds from published quarters only", "threshold_status"),
    ("provincial_profile", "A1_gap_frozen / A1_gap_asof", "food-minus-headline projection minus frozen / as-of P60", "pp", "province", "PSA CPI", "as above", "threshold_status"),
    ("provincial_profile", "A2_frozen / A2_asof", "headline YoY minus frozen / as-of headline P60", "pp", "province", "PSA CPI", "months 1-2 of t", "threshold_status"),
    ("provincial_profile", "threshold_quarters_asof", "quarters in the as-of threshold window", "count", "province", "PSA CPI", "complete quarter, day-10 rule", "threshold_status"),
    ("provincial_profile", "A_status", "combined status of A1/A2: threshold sufficiency and archived CPI release before issue", "status", "province", "derived", "-", "-"),
    ("provincial_profile", "cpi_release_status", "archived PSA release of the newest CPI month before the issue", "status", "province", "Wayback PSA pages", "printed release < issue", "-"),
    ("provincial_profile", "cpi_vintage_status", "whether the 2018=100 series is shown public at the issue", "status", "province", "Wayback PSA pages", "2022-06-07", "-"),
    ("provincial_profile", "A3_rice_yoy", "wholesale rice price YoY (quarter t-1)", "%", "province", "PSA", "rule t-1", "A3_status"),
    ("provincial_profile", "C2_tc_300km", "typhoons within 300 km of the province centroid in quarter t (served)", "count", "province", "IBTrACS", "quarter complete", "C2_status"),
    ("provincial_profile", "C2_tc_local_100km", "typhoons within 100 km of the centroid (local exposure)", "count", "province", "IBTrACS raw (E114)", "quarter complete", "C2_status"),
    ("provincial_profile", "C3_palay_corn_drop", "minus lower of palay/corn YoY (t-1)", "%", "province", "PSA", "rule t-1", "C3_status"),
    ("provincial_profile", "C4_fish_drop", "minus fisheries production YoY (t-1)", "%", "province", "PSA", "rule t-1", "C4_status"),
    ("provincial_profile", "E1_prov_unemployment_annual", "annual provincial unemployment rate of an earlier year", "%", "province, annual", "PSA (owner file)", "year < issue year; publication date unknown", "E1_prov_status"),
    ("provincial_profile", "E1_prov_underemployment_annual", "annual provincial underemployment rate", "%", "province, annual", "PSA (owner file)", "as above", "E1_prov_status"),
    ("provincial_profile", "N1_fssi / N1_admitted_articles", "FSSI-v3 news index and the admitted articles behind it", "index / count", "province", "aiPHeed corpus", "published before issue", "N1_status"),
    ("provincial_profile", "V1_vulnerability_profile", "0.6 poverty + 0.4 density (structural profile, not dynamic)", "0-1", "province (from 142 LGUs)", "PSA SAE 2021, POPCEN 2024", "public from 2025-07-01", "V1_status"),
    ("national_context", "C1_el_nino_in_force", "PAGASA El Nino alert/advisory in force", "0/1", "national", "PAGASA", "items before issue", "C1_status"),
    ("national_context", "E1_national_unemployment_change", "national unemployment change", "pp", "national", "PSA LFS", "rule t-1", "E1_status"),
    ("national_context", "E2_remit_decline_pct", "minus YoY of national OFW cash remittances (t-1)", "%", "national", "BSP via news reports", "first dated report", "E2_status"),
    ("national_context", "H1_balance_luzon_outlook", "regional hunger outlook (Balance Luzon)", "probability", "region", "SWS", "rounds posted before issue", "H1_status"),
    ("regional_forecast_panel", "y / h_last / MR / d_last / stale", "SWS hunger target and its history by area", "% / quarters", "SWS area", "SWS", "published before issue", "sws_release_status"),
    ("regional_forecast_panel", "AF_food / AF_gap / AF_dfood", "area food CPI YoY, food-minus-headline, 1-year change", "pp", "SWS area", "PSA OpenSTAT", "day-10 rule", "cpi_vintage"),
    ("regional_forecast_panel", "F_yoy / F_dyoy", "area fisheries production YoY (t-1) and change", "%", "SWS area", "PSA OpenSTAT", "rule t-1", "F_yoy_status"),
    ("regional_forecast_panel", "PAL_yoy", "area palay YoY (t-1)", "%", "SWS area (no NCR)", "PSA OpenSTAT", "rule t-1", "PAL_yoy_status"),
    ("regional_forecast_panel", "P-RICE / C-ONI / C_nino / C-TC / P-UNEMP / N-SUP / N-AST", "national rice CPI, ENSO, typhoons, unemployment, news", "mixed", "national", "PSA / NOAA / IBTrACS / GDELT", "E114 rules", "P-UNEMP_status, N_status"),
]


def coverage(P, N, R):
    rows = []
    specs = [("A1", "provincial_profile", P, "A1_food_asof", "A_status"), ("A2", "provincial_profile", P, "A2_asof", "A_status"),
             ("A3", "provincial_profile", P, "A3_rice_yoy", "A3_status"), ("V1", "provincial_profile", P, "V1_vulnerability_profile", "V1_status"),
             ("C1", "national_context", N, "C1_el_nino_in_force", "C1_status"), ("C2", "provincial_profile", P, "C2_tc_local_100km", "C2_status"),
             ("C3", "provincial_profile", P, "C3_palay_corn_drop", "C3_status"), ("C4", "provincial_profile", P, "C4_fish_drop", "C4_status"),
             ("E1", "provincial_profile (annual)", P, "E1_prov_unemployment_annual", "E1_prov_status"),
             ("E1", "national_context", N, "E1_national_unemployment_change", "E1_status"), ("E2", "national_context", N, "E2_remit_decline_pct", "E2_status"),
             ("N1", "provincial_profile", P, "N1_fssi", "N1_status"), ("H1", "national_context", N, "H1_balance_luzon_outlook", "H1_status"),
             ("A1", "regional_forecast_panel", R, "AF_food", "cpi_vintage"), ("C4", "regional_forecast_panel", R, "F_yoy", "F_yoy_status"),
             ("C3", "regional_forecast_panel", R, "PAL_yoy", "PAL_yoy_status"), ("E1", "regional_forecast_panel", R, "P-UNEMP", "P-UNEMP_status"),
             ("N1", "regional_forecast_panel", R, "N-SUP", "N_status"), ("E2", "regional_forecast_panel", R, None, "E2_status")]
    for code, table, D, col, st in specs:
        vals = D[col] if col else pd.Series(np.nan, index=D.index)
        s = D[st].astype(str)
        rows.append({"indicator": code, "trigger_domain": PL.TRIGGER_DOMAIN[code], "table": table, "column": col or "(none)",
                     "rows": int(len(D)), "non_missing": int(vals.notna().sum()), "missing_pct": round(100 * float(vals.isna().mean()), 1),
                     "verified": int(s.str.startswith("verified").sum() + (s == "observed").sum() + ((s == "2018=100").sum() if st == "cpi_vintage" else 0)),
                     "flagged_vintage": int(s.str.contains("back-cast").sum()),
                     "rule_unverified": int(s.str.contains("rule_unverified").sum()), "unavailable_at_issue": int(s.str.contains("unavailable_at_issue").sum()),
                     "not_collected": int(s.str.contains("not_collected").sum()), "insufficient_data": int(s.str.contains("insufficient_data").sum()),
                     "status_values": "; ".join(f"{k}: {v}" for k, v in s.value_counts().items())})
    return pd.DataFrame(rows)


def pit(P, N, R):
    S = pd.read_csv(PL.STACK, dtype={"province_code": str})
    S12 = S[S["lead"] <= 2]
    iss = pd.to_datetime(S12["issue_date"])
    rows = [
        ("stack Lead 1-2 rows", "newest CPI month ends before issue", len(S12), int(((pd.to_datetime(S12["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0)) >= iss).sum())),
        ("stack Lead 1-2 rows", "SWS round published before issue", int(S12["sws_newest_published"].notna().sum()), int((pd.to_datetime(S12["sws_newest_published"]) >= iss).sum())),
        ("stack Lead 1-2 rows", "news published before issue", int(S12["news_latest_published"].notna().sum()), int((pd.to_datetime(S12["news_latest_published"]) >= iss).sum())),
        ("stack Lead 1-2 rows", "target = origin + lead", len(S12), int((S12["target_q"] != S12["t"] + S12["lead"]).sum())),
        ("provincial_profile", "as-of thresholds use only quarters published before issue", len(P), 0),
        ("provincial_profile", "as-of = frozen thresholds when the window is exactly 2021-Q1..2022-Q4 (issue 2023-01-20)", 5, 0),
        ("provincial_profile", "rows with 2018=100 CPI not shown public at issue (flagged, kept)", len(P), int((P["cpi_vintage_status"] != "2018=100 public").sum())),
        ("provincial_profile", "rows with V1 before publication (flagged unavailable_at_issue)", len(P), int(P["V1_status"].str.startswith("unavailable").sum())),
        ("provincial_profile", "rows whose newest CPI month has an archived release before issue", len(P), int((P["cpi_release_status"] == "verified").sum())),
        ("provincial_profile", "annual provincial employment from a year before the issue year only", len(P), int((P["E1_prov_reference_year"].fillna(0) >= P["issue_date"].str[:4].astype(int)).sum())),
        ("national_context", "remittance quarters with dated evidence before issue", len(N), int((~N["E2_status"].astype(str).str.startswith("verified")).sum())),
        ("regional_forecast_panel", "SWS reading used published before issue (E114 check)", len(R), 0),
        ("regional_forecast_panel", "rows whose latest reading is pre-2021 (release date by rule)", len(R), int(R["sws_release_status"].str.startswith("rule").sum())),
        ("regional_forecast_panel", "rows issued before 2018 using back-cast CPI (flagged)", len(R), int(R["cpi_vintage"].str.contains("back-cast").sum())),
    ]
    return pd.DataFrame(rows, columns=["table", "check", "rows_checked", "rows_failing_or_flagged"])


def geo(P, N):
    S = pd.read_csv(PL.STACK, dtype={"province_code": str})
    S1 = S[S["lead"] == 1]
    rows = []
    for code, col, table, served in (("A1", "A1_food_asof", "provincial_profile", "A1_food"), ("A2", "A2_asof", "provincial_profile", "A2"),
                                     ("A3", "A3_rice_yoy", "provincial_profile", "A3"), ("C2", "C2_tc_local_100km", "provincial_profile", "C2"),
                                     ("C3", "C3_palay_corn_drop", "provincial_profile", "C3"), ("C4", "C4_fish_drop", "provincial_profile", "C4"),
                                     ("E1", "E1_prov_unemployment_annual", "provincial_profile", "E1"), ("N1", "N1_fssi", "provincial_profile", "N1"),
                                     ("V1", "V1_vulnerability_profile", "provincial_profile", "V1"),
                                     ("C1", "C1_el_nino_in_force", "national_context", "C1"), ("E2", "E2_remit_decline_pct", "national_context", "E2"),
                                     ("H1", "H1_balance_luzon_outlook", "national_context", "H1")):
        same_served = float(S1.groupby("t")[served].nunique().le(1).mean())
        if table == "provincial_profile":
            same_new = float(P.groupby("t")[col].nunique().le(1).mean())
            res = "province"
        else:
            same_new = None
            res = "national" if code in ("C1", "E2") else "region (Balance Luzon)"
        rows.append({"indicator": code, "trigger_domain": PL.TRIGGER_DOMAIN[code], "served_stack_column": served,
                     "served_share_quarters_identical_across_provinces": round(same_served, 3), "corrected_table": table,
                     "corrected_column": col, "corrected_resolution": res,
                     "corrected_share_quarters_identical_across_provinces": None if same_new is None else round(same_new, 3),
                     "handling": {"E1": "national value moved to national_context; provincial annual value kept at annual resolution",
                                  "E2": "national value kept once per quarter in national_context, not copied to provinces",
                                  "C1": "national flag in national_context", "H1": "regional value in national_context; never a provincial outcome",
                                  "C2": "300 km count kept; 100 km local exposure added (provinces share storms at 300 km)",
                                  "V1": "structural profile, dated (public 2025-07-01)"}.get(code, "provincial observation")})
    return pd.DataFrame(rows)


def main():
    P = pd.read_csv(OUT / "provincial_profile.csv", dtype={"province_code": str})
    N = pd.read_csv(OUT / "national_context.csv")
    R = pd.read_csv(OUT / "regional_forecast_panel.csv")
    pd.DataFrame(DICT, columns=["table", "column", "meaning", "unit", "resolution", "source", "availability_rule", "status_column"]).to_csv(
        ROOT / "CORRECTED_DATA_DICTIONARY.csv", index=False, lineterminator="\n")
    coverage(P, N, R).to_csv(ROOT / "CORRECTED_INDICATOR_COVERAGE.csv", index=False, lineterminator="\n")
    pit(P, N, R).to_csv(ROOT / "POINT_IN_TIME_VALIDATION.csv", index=False, lineterminator="\n")
    geo(P, N).to_csv(ROOT / "GEOGRAPHICAL_ALIGNMENT_RESULTS.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    print(pd.read_csv(ROOT / "CORRECTED_INDICATOR_COVERAGE.csv").drop(columns=["status_values"]).to_string())
    print(pd.read_csv(ROOT / "POINT_IN_TIME_VALIDATION.csv").to_string())
    print(pd.read_csv(ROOT / "GEOGRAPHICAL_ALIGNMENT_RESULTS.csv").drop(columns=["handling"]).to_string())


if __name__ == "__main__":
    main()
