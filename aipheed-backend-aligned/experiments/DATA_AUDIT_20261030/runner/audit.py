"""aiPHeed data audit (read-only; no source file is modified, nothing is repaired, no model is trained).

Profiles every dataset that feeds the 12 FIRI v2 indicators (backend/app/ml/inference/firi.py), the target and the
long-history studies (E114, E116): coverage, completeness, quality, geography and timing; checks the served training
stack against the issue-date rules; counts usable, independent training examples.

    python audit.py     # ../DATASET_COVERAGE.csv, ../INDICATOR_COMPLETENESS.csv, ../TEMPORAL_ALIGNMENT_REPORT.csv,
                        # ../GEOGRAPHICAL_COVERAGE_REPORT.csv, ../DATA_QUALITY_REPORT.csv, ../out/audit.json
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUTD = HERE.parent
REPO = OUTD.parents[2]
X = REPO / "aipheed-backend-aligned" / "experiments"
B = REPO / "backend"
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
NAME2CODE = {v.upper(): k for k, v in PROV.items()}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def qi(s):
    s = str(s)
    m = re.match(r"(\d{4})-?Q(\d)", s)
    return int(m.group(1)) * 4 + int(m.group(2)) - 1 if m else None


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def ym_s(m):
    return f"{m // 12}-{m % 12 + 1:02d}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------------- dataset loaders
# Each loader returns a tidy frame: unit (geography), period (int; month index ym or quarter index q), variable, value
def l_cpi_index():
    d = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv")
    d = d[d["Period"].isin(MON)]
    return pd.DataFrame({"unit": d["Geolocation"].str.strip(". "), "period": d["Year"] * 12 + d["Period"].map(MON.index),
                         "variable": d["Commodity Description"], "value": pd.to_numeric(d["value"], errors="coerce")}), "M"


def l_cpi_yoy():
    d = pd.read_csv(X / "E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv", dtype=str)
    return pd.DataFrame({"unit": d["province_code"].map(PROV), "period": d["reference_month"].str[:4].astype(int) * 12 + d["reference_month"].str[5:7].astype(int) - 1,
                         "variable": d["commodity"], "value": pd.to_numeric(d["yoy_pct"], errors="coerce")}), "M"


def l_rice():
    d = pd.read_parquet(X / "E107_Twelve_Indicator_LightGBM/data_inputs/psa_rice_prices.parquet")
    return pd.DataFrame({"unit": d["province_name"], "period": d["quarter"].map(qi), "variable": d["rice_class"],
                         "value": d["price_php_per_kg"]}), "Q"


def l_vuln():
    d = pd.read_csv(B / "data/inputs/lgu_vulnerability.csv")
    return pd.DataFrame({"unit": d["lgu_name"] + " (" + d["province"] + ")", "period": 2021, "variable": "poverty_lgu_estimate",
                         "value": d["poverty_lgu_estimate"], "province": d["province"], "code": d["lgu_code"].astype(str)}), "static"


def l_subsistence():
    d = pd.read_csv(B / "data/inputs/psa_subsistence_population_2021_2023.csv", dtype={"province_code": str})
    return pd.DataFrame({"unit": d["province_code"].map(PROV), "period": d["reference_year"], "variable": "subsistence_incidence_pct",
                         "value": d["subsistence_incidence_pct"]}), "A"


def l_climate():
    d = pd.read_parquet(X / "E107_Twelve_Indicator_LightGBM/data_inputs/pagasa_climate.parquet")
    q = d["year"].astype(int) * 4 + d["quarter"].astype(str).str[-1].astype(int) - 1 if d["quarter"].dtype != object or not str(d["quarter"].iloc[0]).startswith("20") else d["quarter"].map(qi)
    rows = []
    for v in ("tc_count", "tc_max_signal", "drought_alert", "rainfall_anomaly_pct"):
        rows.append(pd.DataFrame({"unit": d["province_name"], "period": q, "variable": v, "value": pd.to_numeric(d[v], errors="coerce")}))
    return pd.concat(rows), "Q"


def l_palay():
    d = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/palay_corn_production.csv")
    d = d[d["Period"].str.startswith("Quarter")]
    return pd.DataFrame({"unit": d["Geolocation"].str.strip(". "), "period": d["Year"] * 4 + d["Period"].str[-1].astype(int) - 1,
                         "variable": d["Ecosystem/Croptype"], "value": pd.to_numeric(d["value"], errors="coerce")}), "Q"


def l_fish():
    d = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/fisheries_production.csv")
    d = d[d["Quarter"].str.startswith("Quarter")]
    return pd.DataFrame({"unit": d["Geolocation"].str.strip(". "), "period": d["Year"] * 4 + d["Quarter"].str[-1].astype(int) - 1,
                         "variable": d["Subsector"].str.strip(". "), "value": pd.to_numeric(d["value"], errors="coerce")}), "Q"


def l_lfs():
    d = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/lfs_rates_national.csv")
    d = d[d["Month"].isin(MONL) & (d["Sex"] == "Both sexes")]
    return pd.DataFrame({"unit": "PHILIPPINES", "period": d["Year"] * 12 + d["Month"].map(MONL.index), "variable": d["Rates"],
                         "value": pd.to_numeric(d["value"], errors="coerce")}), "M"


def l_bsp():
    d = pd.read_parquet(X / "E107_Twelve_Indicator_LightGBM/data_inputs/bsp_macro.parquet")
    q = d["quarter"].map(qi) if str(d["quarter"].iloc[0]).startswith("20") else d["year"].astype(int) * 4 + d["quarter"].astype(int) - 1
    return pd.DataFrame({"unit": d["province_name"], "period": q, "variable": "ofw_cash_remit_usd_bn", "value": d["ofw_cash_remit_usd_bn"]}), "Q"


def l_fssi():
    d = pd.read_csv(B / "data/news_e31/fssi_v2_panel.csv", dtype={"province_code": str})
    return pd.DataFrame({"unit": d["province"], "period": d["quarter"].map(qi), "variable": "FSSI_v2", "value": d["FSSI_v2"],
                         "n_admitted": d["n_admitted"]}), "Q"


def l_sws():
    d = pd.read_csv(B / "data/inputs/sws_rounds.csv")
    return pd.DataFrame({"unit": "Balance Luzon", "period": d["quarter"].map(qi), "variable": "H", "value": d["H"],
                         "published": d["published"]}), "Q"


def l_sws_long():
    d = pd.read_csv(X / "E114_Final_Run/data/sws_area_rounds_full.csv")
    rows = []
    for a, c in (("NCR", "metro_manila"), ("Balance Luzon", "balance_luzon"), ("Visayas", "visayas"), ("Mindanao", "mindanao")):
        rows.append(pd.DataFrame({"unit": a, "period": d["quarter"].map(qi), "variable": "total_hunger", "value": d[c], "published": d["published"]}))
    return pd.concat(rows), "Q"


def l_area(name):
    d = pd.read_csv(X / f"E116_FIRI_Domains/data/{name}")
    if "ym" in d:
        return pd.concat([pd.DataFrame({"unit": d["area"], "period": d["ym"], "variable": v, "value": d[v]}) for v in ("food_yoy", "all_yoy")]), "M"
    return pd.DataFrame({"unit": d["area"], "period": d["q"], "variable": "yoy", "value": d["yoy"]}), "Q"


def l_remit_q():
    d = pd.read_csv(X / "FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_quarterly.csv")
    return pd.DataFrame({"unit": "PHILIPPINES", "period": d["q"], "variable": "cash_remit_usd_bn", "value": d["cash_remit_usd_bn"]}), "Q"


def l_fies():
    d = pd.read_csv(X / "E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv")
    return pd.DataFrame({"unit": d["geography"], "period": d["year"], "variable": d["indicator"], "value": d["value_pct"]}), "A"


def l_owner_emp():
    d = pd.read_csv(X / "E116_FIRI_Domains/data/owner/calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv")
    return pd.concat([pd.DataFrame({"unit": d["province"], "period": d["year"], "variable": v, "value": d[v]})
                      for v in ("unemployment_rate_pct", "underemployment_rate_pct", "employment_rate_pct")]), "A"


def l_stack():
    d = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/data/stack_l2.csv", dtype={"province_code": str})
    cols = ["A1_food", "A1_gap", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"]
    d = d[d["lead"] <= 2]
    return pd.concat([pd.DataFrame({"unit": d["province_code"].map(PROV), "period": d["t"] * 10 + d["lead"], "variable": c, "value": d[c]}) for c in cols]), "stack"


DATASETS = [
    # name, path, loader, agency/source, indicators, processing state, publication-date evidence
    ("PSA CPI index by province (OpenSTAT 0012M4ACP22)", "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv", l_cpi_index, "PSA (OpenSTAT)", "A1, A2", "raw (final vintage, retrieved 2026-10-15)", "retrieval timestamp only; per-month release dates: 32 verified, 61 owner-reported, 79 unresolved (refresh months)"),
    ("PSA CPI YoY by province (0012M4ACP23)", "aipheed-backend-aligned/experiments/E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv", l_cpi_yoy, "PSA (OpenSTAT)", "A1, A2 (labels)", "raw (final vintage)", "retrieval timestamp only"),
    ("PSA wholesale rice prices by province", "aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/data_inputs/psa_rice_prices.parquet", l_rice, "PSA", "A3", "processed (quarterly)", "none (rule: quarter t-1 at O(t))"),
    ("LGU vulnerability (SAE 2021 poverty, POPCEN 2024)", "backend/data/inputs/lgu_vulnerability.csv", l_vuln, "PSA", "V1", "processed (one substitute: Lucena)", "published 2024-2025; no per-origin vintage"),
    ("PSA subsistence incidence by province", "backend/data/inputs/psa_subsistence_population_2021_2023.csv", l_subsistence, "PSA", "target candidate / V", "raw", "publication_date column (2024-08-15)"),
    ("PAGASA ENSO alert items (in code)", "backend/app/ml/inference/enso_context.py", None, "PAGASA", "C1", "raw (hand-entered dated items, 2023-2026)", "each item dated"),
    ("Climate panel (typhoons, ENSO, rainfall)", "aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/data_inputs/pagasa_climate.parquet", l_climate, "PAGASA / IBTrACS", "C2 (C1 context)", "processed", "fetched_at only"),
    ("PSA palay and corn production (region)", "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/palay_corn_production.csv", l_palay, "PSA (OpenSTAT)", "C3", "raw (final revisions)", "none (rule: t-1)"),
    ("PSA fisheries production (region)", "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/fisheries_production.csv", l_fish, "PSA (OpenSTAT)", "C4", "raw (final revisions)", "none (rule: t-1)"),
    ("PSA LFS rates (national, monthly)", "aipheed-backend-aligned/experiments/E41_Lead2_Audit/data_acquired/lfs_rates_national.csv", l_lfs, "PSA (OpenSTAT)", "E1", "raw", "none (rule: t-1)"),
    ("BSP OFW cash remittances (macro panel)", "aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/data_inputs/bsp_macro.parquet", l_bsp, "BSP", "E2", "processed (national value per province row)", "fetched_at only"),
    ("BSP cash remittances quarterly (national)", "aipheed-backend-aligned/experiments/FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_quarterly.csv", l_remit_q, "BSP", "E2 (audit copy)", "processed", "none"),
    ("FSSI news panel (province x quarter)", "backend/data/news_e31/fssi_v2_panel.csv", l_fssi, "aiPHeed news pipeline (RSS + XLM-R)", "N1", "derived", "article publication timestamps (in corpus)"),
    ("SWS hunger rounds, Balance Luzon (2021+)", "backend/data/inputs/sws_rounds.csv", l_sws, "Social Weather Stations", "H1 + target", "raw", "published column (verified)"),
    ("SWS hunger by area, 1998-2026", "aipheed-backend-aligned/experiments/E114_Final_Run/data/sws_area_rounds_full.csv", l_sws_long, "Social Weather Stations", "target (long history)", "raw (from SWS tables)", "published column; pre-2021 = month end + 60 days (rule)"),
    ("Area food / all-items CPI (E116)", "aipheed-backend-aligned/experiments/E116_FIRI_Domains/data/area_cpi.csv", lambda: l_area("area_cpi.csv"), "PSA (OpenSTAT)", "A1, A2 (area level)", "derived (unweighted regional mean; 1994-2017 back-cast)", "none (rule: day 10)"),
    ("Area fisheries production YoY (E116)", "aipheed-backend-aligned/experiments/E116_FIRI_Domains/data/area_fish.csv", lambda: l_area("area_fish.csv"), "PSA (OpenSTAT)", "C4 (area level)", "derived (sum of regions)", "none (rule: t-1)"),
    ("Area palay production YoY (E116)", "aipheed-backend-aligned/experiments/E116_FIRI_Domains/data/area_palay.csv", lambda: l_area("area_palay.csv"), "PSA (OpenSTAT)", "C3 (area level)", "derived (sum of regions)", "none (rule: t-1)"),
    ("FNRI FIES observations", "aipheed-backend-aligned/experiments/E87_Outcome_Gap/data_acquired/fnri_fies_observations.csv", l_fies, "DOST-FNRI", "target candidate", "raw (transcribed from reports)", "report year"),
    ("Owner provincial employment (annual)", "aipheed-backend-aligned/experiments/E116_FIRI_Domains/data/owner/calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv", l_owner_emp, "PSA (owner-collected)", "E1 (provincial)", "raw (owner-collected)", "none"),
    ("Served training stack (LEAD2 stack_l2)", "aipheed-backend-aligned/experiments/LEAD2_FIVE_TRIGGER/data/stack_l2.csv", l_stack, "aiPHeed", "all 12 (model features)", "derived", "issue_date, psa_newest_month, sws_newest_published, news_latest_published"),
]


def profile(name, path, loader, agency, inds, state, pub):
    p = REPO / path
    row = {"dataset": name, "path": path, "agency_source": agency, "indicators": inds, "processing_state": state,
           "publication_date_evidence": pub, "exists": p.exists(), "sha256": sha(p) if p.exists() else None}
    if loader is None or not p.exists():
        return row, None
    d, freq = loader()
    d = d[d["unit"].notna()]
    row.update({"frequency": freq, "rows": int(len(d)), "units": int(d["unit"].nunique()), "variables": int(d["variable"].nunique()),
                "period_min": None, "period_max": None})
    per = d["period"].dropna().astype(int)
    fmt = {"M": ym_s, "Q": qs}.get(freq, str)
    row["period_min"], row["period_max"] = fmt(int(per.min())), fmt(int(per.max()))
    obs = d[d["value"].notna()]
    row["latest_non_missing"] = fmt(int(obs["period"].max())) if len(obs) else None
    if freq in ("M", "Q", "A"):
        # expected = every unit x variable x period between the first and the last non-missing period of the dataset
        lo, hi = int(obs["period"].min()), int(obs["period"].max())
        exp = d.groupby(["unit", "variable"]).ngroups * (hi - lo + 1)
        got = obs[(obs["period"] >= lo) & (obs["period"] <= hi)].drop_duplicates(["unit", "variable", "period"]).shape[0]
        row.update({"expected_obs": int(exp), "actual_obs": int(got), "missing_obs": int(exp - got), "missing_pct": round(100 * (exp - got) / exp, 2)})
        gaps = []
        for _, g in obs.groupby(["unit", "variable"]):
            s = sorted(set(g["period"].astype(int)))
            gaps.append(max([b - a - 1 for a, b in zip(s, s[1:])] + [0]))
        row["longest_gap_periods"] = int(max(gaps)) if gaps else None
    else:
        row.update({"expected_obs": int(len(d)), "actual_obs": int(d["value"].notna().sum()), "missing_obs": int(d["value"].isna().sum()),
                    "missing_pct": round(100 * d["value"].isna().mean(), 2), "longest_gap_periods": None})
    row["duplicate_keys"] = int(d.duplicated(["unit", "variable", "period"]).sum())
    row["negative_values"] = int((obs["value"] < 0).sum())
    row["zero_values"] = int((obs["value"] == 0).sum())
    # identical values across units in the same period = a coarser-geography value copied to every unit
    if d["unit"].nunique() > 1 and freq in ("Q", "M", "stack"):
        g = obs.groupby(["variable", "period"])["value"].agg(["nunique", "size"])
        g = g[g["size"] > 1]
        row["share_periods_identical_across_units"] = round(float((g["nunique"] == 1).mean()), 3) if len(g) else None
    else:
        row["share_periods_identical_across_units"] = None
    # abrupt change: |change| > 6 robust SDs of the unit-variable series
    jumps = 0
    if freq in ("M", "Q"):
        for _, g in obs.sort_values("period").groupby(["unit", "variable"]):
            dv = g["value"].diff().dropna()
            if len(dv) > 8:
                mad = (dv - dv.median()).abs().median() * 1.4826
                if mad > 0:
                    jumps += int(((dv - dv.median()).abs() > 6 * mad).sum())
    row["abrupt_changes_gt6_robust_sd"] = jumps
    return row, d


# --------------------------------------------------------------------------------------------- indicator audit
IND = [  # code, label, domain (FIRI v2 DOMAIN_OF), user domain, stack columns, source, geography, frequency, rule, timing status
    ("A1", "Food-price-pressure forecast (LightGBM, Lead-2)", "A Affordability", "Market and food prices", ["A1_food", "A1_gap"], "PSA CPI index (ACP22)", "province", "monthly", "CPI through month 2 of t at O(t)", "base month verified 35/36; refresh months partly unresolved"),
    ("A2", "Headline inflation above the usual level", "A Affordability", "Market and food prices", ["A2"], "PSA CPI YoY", "province", "monthly", "months 1-2 of t", "as A1"),
    ("A3", "Wholesale rice price change", "A Affordability", "Market and food prices", ["A3"], "PSA wholesale rice prices", "province", "quarterly", "quarter t-1", "assumed lag, unverified"),
    ("V1", "Poverty and population density", "V Household vulnerability", "(other input: poverty)", ["V1"], "PSA SAE 2021, POPCEN 2024", "LGU -> province", "static", "static at every origin", "VIOLATION: published 2024-25, used at all origins"),
    ("C1", "PAGASA El Nino alert/advisory in force", "C Climate and food production", "Climate", ["C1"], "PAGASA ENSO items (code)", "national", "event", "items before O(t)", "verified (dated items)"),
    ("C2", "Typhoons within 300 km", "C Climate and food production", "Climate", ["C2"], "IBTrACS / PAGASA", "province (identical across provinces in 61% of quarters)", "quarterly", "quarter t (complete)", "plausible; 2026-Q3 incomplete; best-track revisions unchecked; rainfall anomaly column 100% empty"),
    ("C3", "Palay/corn production drop", "C Climate and food production", "Climate", ["C3"], "PSA palay/corn (province rows)", "province", "quarterly", "quarter t-1", "assumed lag, unverified; revisions unchecked"),
    ("C4", "Fisheries production drop", "C Climate and food production", "Fish production", ["C4"], "PSA fisheries (province rows)", "province", "quarterly", "quarter t-1", "assumed lag, unverified; revisions unchecked"),
    ("E1", "Unemployment change (national)", "E Household economy (national)", "Employment", ["E1"], "PSA LFS (national)", "national copied to provinces", "monthly", "months of t-1", "assumed lag, unverified"),
    ("E2", "Remittance decline (national)", "E Household economy (national)", "OFW remittances", ["E2"], "BSP cash remittances", "national copied to provinces", "quarterly", "quarter t-1", "assumed lag; series ends 2025-Q4 in stack"),
    ("N1", "Food Stress Sentiment Index (FSSI-v3)", "N News warning signals", "(other input: news)", ["N1"], "aiPHeed news corpus", "province", "quarterly", "headlines before O(t)", "verified (dated articles)"),
    ("H1", "Regional hunger outlook above 11.3%", "H Regional hunger (Balance Luzon)", "(target component)", ["H1"], "SWS rounds", "region copied to provinces", "quarterly", "rounds posted before issue", "verified"),
]


def indicator_rows(stack):
    S = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/data/stack_l2.csv", dtype={"province_code": str})
    S = S[S["lead"] <= 2]
    out = []
    for code, label, dom, udom, cols, src, geo, freq, rule, timing in IND:
        c = cols[0]
        x = S[["t", "lead", "province_code", c]]
        per_q = x.groupby(["t", "lead"])[c].nunique()
        varies = bool((per_q > 1).mean() > .5)
        by_year = x.groupby(x["t"] // 4)[c].apply(lambda v: round(float(v.isna().mean()), 3)).to_dict()
        by_prov = x.groupby("province_code")[c].apply(lambda v: round(float(v.isna().mean()), 3)).to_dict()
        miss_years = [int(y) for y, m in by_year.items() if m == 1.0]
        status = {"A1": "B", "A2": "B", "A3": "B", "V1": "D", "C1": "B", "C2": "B", "C3": "B", "C4": "B", "E1": "C", "E2": "C", "N1": "C", "H1": "B"}[code]
        out.append({"indicator": code, "label": label, "firi_domain": dom, "trigger_domain": udom, "stack_columns": " ".join(cols),
                    "input_dataset": src, "geographic_resolution": geo, "varies_between_provinces_in_stack": varies,
                    "temporal_resolution": freq, "stack_origins": f"{qs(int(S['t'].min()))}..{qs(int(S['t'].max()))}",
                    "missing_share_leads_1_2": round(float(x[c].isna().mean()), 3), "missing_by_origin_year": json.dumps(by_year),
                    "missing_by_province": json.dumps({PROV[k]: v for k, v in by_prov.items()}),
                    "fully_missing_origin_years": " ".join(map(str, miss_years)), "distinct_values": int(x[c].nunique()),
                    "availability_rule": rule, "availability_status": timing,
                    "classification": status})
    return pd.DataFrame(out)


def temporal_rows():
    S = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/data/stack_l2.csv", dtype={"province_code": str})
    S = S[S["lead"] <= 2].copy()
    iss = pd.to_datetime(S["issue_date"])
    psa_end = pd.to_datetime(S["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0)
    rows = []
    for k in (1, 2):
        g = S[S["lead"] == k]
        ig = pd.to_datetime(g["issue_date"])
        ex = g.iloc[len(g) // 2]
        rows.append({"check": f"Lead {k}: issue, latest CPI month, latest SWS round, target",
                     "example": f"origin {qs(int(ex.t))}, issue {ex.issue_date}, CPI through {ex.psa_newest_month}, SWS {ex.sws_newest_q} (published {str(ex.sws_newest_published)[:10]}), target {qs(int(ex.target_q))}",
                     "rows": int(len(g)), "violations": int((g["target_q"] != g["t"] + k).sum()),
                     "rule": "target quarter = origin + lead; issue = day 1 of quarter t+1 (schedule A; Lead-2 re-issue schedule B is later)"})
        rows.append({"check": f"Lead {k}: newest CPI month ends before issue", "example": "", "rows": int(len(g)),
                     "violations": int(((pd.to_datetime(g["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0)) >= ig).sum()),
                     "rule": "CPI month m used only if m ends before the issue (release dates: see release ledger)"})
        m = g["sws_newest_published"].notna()
        rows.append({"check": f"Lead {k}: SWS round published before issue", "example": "", "rows": int(m.sum()),
                     "violations": int((pd.to_datetime(g.loc[m, "sws_newest_published"]) >= ig[m]).sum()), "rule": "published < issue"})
        m = g["news_latest_published"].notna()
        rows.append({"check": f"Lead {k}: news articles published before issue", "example": "", "rows": int(m.sum()),
                     "violations": int((pd.to_datetime(g.loc[m, "news_latest_published"]) >= ig[m]).sum()), "rule": "published < issue"})
    for code, label, _, _, _, _, _, freq, rule, timing in IND:
        rows.append({"check": f"{code} availability rule", "example": label, "rows": None, "violations": None,
                     "rule": f"{freq}; {rule}; status: {timing}"})
    rows.append({"check": "Lead-2 CPI refresh months (CR/CR-ANC research only)", "example": "180 province-months", "rows": 180,
                 "violations": None, "rule": "32 verified, 61 owner-reported, 79 unresolved, 8 not before issue (psa_cpi_availability_ledger_20261029.csv)"})
    rows.append({"check": "Price thresholds (2021-22 P60) vs issue dates", "example": "600 training rows issued before 2023-01-06", "rows": 600,
                 "violations": 600, "rule": "label constant computed from 2021-22 data; not computable at those issue dates (no evaluation row affected)"})
    rows.append({"check": "CPI base year (2018=100 public from 2022)", "example": "375 training rows issued before 2022-06-07", "rows": 375,
                 "violations": 375, "rule": "values in a series not yet public at issue (no evaluation row affected)"})
    rows.append({"check": "Archived headline CPI vs final vintage", "example": "Cavite 2025-03 1.5 vs 1.1; Batangas 2025-06 1.4 vs 1.3; Quezon 2025-06 1.8 vs 1.7",
                 "rows": 29, "violations": 3, "rule": "as-released values differ from the final vintage the model reads"})
    return pd.DataFrame(rows)


def geo_rows(profiles):
    rows = []
    for name, d in profiles.items():
        if d is None:
            continue
        units = sorted(map(str, d["unit"].dropna().unique()))
        prov = [u for u in units if u.upper() in NAME2CODE]
        rows.append({"dataset": name, "units": len(units), "unit_examples": "; ".join(units[:6]),
                     "calabarzon_provinces_present": len(prov), "missing_provinces": "; ".join(sorted(set(PROV.values()) - set(prov))) if prov else "n/a (not provincial)",
                     "names_standardized": all(u == u.strip() for u in units),
                     "resolution": "LGU" if name.startswith("LGU") else "province" if len(prov) == 5 else "region/area/national"})
    v = pd.read_csv(B / "data/inputs/lgu_vulnerability.csv")
    rows.append({"dataset": "LGU vulnerability (municipal check)", "units": int(v["lgu_code"].nunique()),
                 "unit_examples": f"{(v['poverty_source'].str.contains('substitute', case=False, na=False)).sum()} substituted poverty value(s)",
                 "calabarzon_provinces_present": int(v["province"].nunique()), "missing_provinces": "",
                 "names_standardized": bool(v["lgu_name"].str.strip().eq(v["lgu_name"]).all()), "resolution": f"LGU ({len(v)} of 142 expected)"})
    return pd.DataFrame(rows)


def training_readiness():
    L = pd.read_csv(X / "FORECAST_RESEARCH/data/labels_t43c.csv", dtype={"province_code": str})
    E = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", dtype={"province_code": str})
    sws = pd.read_csv(X / "E114_Final_Run/data/sws_area_rounds_full.csv")
    out = {}
    for k in (1, 2):
        g = E[E["lead"] == k]
        out[f"provincial_T43c_lead{k}"] = {"rows": int(len(g)), "target_quarters": int(g["q"].nunique()), "high_rows": int(g["y"].sum()),
                                           "high_quarters": int(g.loc[g["y"] == 1, "q"].nunique()),
                                           "independent_hunger_observations": int(g["q"].nunique())}
    out["t43c_labels"] = {"rows": int(len(L)), "quarters": int(L["q"].nunique()), "provinces": int(L["province_code"].nunique()),
                          "hunger_values_per_quarter": int(L.groupby("q")["H"].nunique().max())}
    q = sws.groupby("quarter")[["metro_manila", "balance_luzon", "visayas", "mindanao"]].mean()
    out["regional_sws_long"] = {"quarters": int(len(q)), "first": q.index.min(), "last": q.index.max(), "areas": 4,
                                "area_quarters": int(q.notna().sum().sum()),
                                "missing_quarters_1998Q3_2026Q3": int((qi("2026-Q3") - qi("1998-Q3") + 1) - len(q))}
    return out


def main():
    (OUTD / "out").mkdir(exist_ok=True)
    rows, profiles = [], {}
    for spec in DATASETS:
        r, d = profile(*spec)
        rows.append(r)
        profiles[spec[0]] = d
    cov = pd.DataFrame(rows)
    cov.to_csv(OUTD / "DATASET_COVERAGE.csv", index=False, lineterminator="\n")
    q = cov[["dataset", "frequency", "expected_obs", "actual_obs", "missing_obs", "missing_pct", "duplicate_keys", "negative_values",
             "zero_values", "abrupt_changes_gt6_robust_sd", "longest_gap_periods", "share_periods_identical_across_units", "latest_non_missing"]]
    q.to_csv(OUTD / "DATA_QUALITY_REPORT.csv", index=False, lineterminator="\n")
    ind = indicator_rows(profiles)
    ind.to_csv(OUTD / "INDICATOR_COMPLETENESS.csv", index=False, lineterminator="\n")
    temporal_rows().to_csv(OUTD / "TEMPORAL_ALIGNMENT_REPORT.csv", index=False, lineterminator="\n")
    geo_rows(profiles).to_csv(OUTD / "GEOGRAPHICAL_COVERAGE_REPORT.csv", index=False, lineterminator="\n")
    res = {"training_readiness": training_readiness(), "datasets": len(cov),
           "source_sha256": {r["path"]: r["sha256"] for r in rows}}
    (OUTD / "out" / "audit.json").write_text(json.dumps(res, indent=1, default=str))
    pd.set_option("display.width", 250)
    print(cov[["dataset", "frequency", "rows", "units", "period_min", "period_max", "missing_pct", "duplicate_keys", "share_periods_identical_across_units", "longest_gap_periods", "abrupt_changes_gt6_robust_sd"]].to_string())
    print(ind[["indicator", "trigger_domain", "geographic_resolution", "varies_between_provinces_in_stack", "missing_share_leads_1_2", "fully_missing_origin_years", "distinct_values", "classification"]].to_string())
    print(json.dumps(res["training_readiness"], indent=1, default=str))


if __name__ == "__main__":
    main()
