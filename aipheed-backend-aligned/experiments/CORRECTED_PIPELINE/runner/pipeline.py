"""aiPHeed corrected experimental data pipeline (no training, no production change, raw files read-only).

Builds three separate products so that forecasting and vulnerability assessment are never confused:
  A. regional_forecast_panel.csv  - SWS hunger by area (1998-2026) x origin x lead, with area/national predictors
                                    (E114/E116 builders, unchanged values) plus per-feature availability status;
  B. provincial_profile.csv       - province x origin (2021-Q1..2026-Q3) vulnerability profile from the served stack,
                                    with corrected (origin-available) price thresholds, CPI vintage/revision flags,
                                    publication-status flags, local typhoon exposure, annual provincial employment at
                                    annual resolution, poverty as a dated structural profile; no outcome, no forecast;
  C. national_context.csv         - one row per origin for national/regional values (El Nino, unemployment,
                                    remittances, Balance Luzon hunger), never copied to provinces.
Every value carries a status: verified | rule_unverified | unavailable_at_issue | not_collected | insufficient_data.

    python pipeline.py      # ../out/*.csv, ../out/pipeline_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parents[2]
X = REPO / "aipheed-backend-aligned" / "experiments"
B = REPO / "backend"
sys.path.insert(0, str(B))
from app.ml.inference import firi as FI  # noqa: E402

PROV = FI.PROVINCES
NAME2CODE = {v: k for k, v in PROV.items()}
STACK = X / "LEAD2_FIVE_TRIGGER" / "data" / "stack_l2.csv"
LABELS = X / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv"
CPI_YOY = X / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
LABEL_SPEC = X / "E40_SWS_CPI_Tiers" / "label_spec.json"
LEDGER = X / "LEAD2_FIVE_TRIGGER" / "data" / "psa_cpi_availability_ledger_20261029.csv"
WAYBACK = X / "LEAD2_FIVE_TRIGGER" / "data" / "psa_release_evidence" / "wayback_catalog.csv"
VULN = B / "data" / "inputs" / "lgu_vulnerability.csv"
EMP = X / "E116_FIRI_Domains" / "data" / "owner" / "calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv"
REMIT = X / "FIRI_V2_DATA_AUDIT" / "data" / "bsp_cash_remittances_cumulative.csv"
REMIT_Q = X / "FIRI_V2_DATA_AUDIT" / "data" / "bsp_cash_remittances_quarterly.csv"
BSP_PANEL = X / "E107_Twelve_Indicator_LightGBM" / "data_inputs" / "bsp_macro.parquet"
IBTRACS = X / "E114_Final_Run" / "data" / "raw" / "ibtracs.WP.list.v04r01.csv"
SWS = B / "data" / "inputs" / "sws_rounds.csv"
INPUTS = [STACK, LABELS, CPI_YOY, LABEL_SPEC, LEDGER, WAYBACK, VULN, EMP, REMIT, REMIT_Q, BSP_PANEL, IBTRACS, SWS]

# trigger domains: the five FIRI domains (ADDENDUM_1, owner 2026-10-30) plus the three other required inputs
TRIGGER_DOMAIN = {"A1": "market_prices", "A2": "market_prices", "A3": "market_prices", "C4": "fish_production",
                  "C1": "climate", "C2": "climate", "C3": "climate", "E1": "employment", "E2": "ofw_remittances",
                  "N1": "news_nlp (other input)", "V1": "poverty_vulnerability (other input)", "H1": "regional_hunger (target component)"}
CPI_2018_PUBLIC = "2022-06-07"          # earliest archived 2018=100 provincial release in the repository (wayback catalog)
V1_PUBLIC = FI.V_AVAILABLE_FROM         # SAE 2021 + POPCEN 2024 both public (FIRI Amendment 1 strict rule)
LOCAL_KM = 100.0
MIN_THRESHOLD_QUARTERS = 4


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def qi(s):
    m = re.match(r"(\d{4})-?Q(\d)", str(s))
    return int(m.group(1)) * 4 + int(m.group(2)) - 1


def quarter_usable(q: int, issue: str) -> bool:
    """A quarterly CPI mean is complete once month 3 of the quarter is usable (day 10 of the following month)."""
    n = q * 3 + 3                                       # first month after quarter q (ym index)
    return date(n // 12, n % 12 + 1, 10).isoformat() < issue


# --------------------------------------------------------------------------------- price thresholds (as of issue)
def frozen_thresholds():
    spec = json.loads(LABEL_SPEC.read_text())
    return spec["thresholds"]["food"], spec["thresholds"]["gap"], FI.HEADLINE_P60


def cpi_quarterly() -> pd.DataFrame:
    """Quarterly means of PSA provincial food and all-items YoY (0012M4ACP23), every quarter with 3 published months."""
    y = pd.read_csv(CPI_YOY, dtype={"province_code": str})
    y["q"] = y["reference_month"].str[:4].astype(int) * 4 + (y["reference_month"].str[5:7].astype(int) - 1) // 3
    w = y.pivot_table(index=["province_code", "q"], columns="commodity", values="yoy_pct", aggfunc=["mean", "count"])
    w = w[(w[("count", "food")] == 3) & (w[("count", "all_items")] == 3)]
    return pd.DataFrame({"province_code": [i[0] for i in w.index], "q": [i[1] for i in w.index],
                         "F": w[("mean", "food")].to_numpy(), "HL": w[("mean", "all_items")].to_numpy()})


def asof_thresholds(L: pd.DataFrame, issue: str) -> dict:
    """P60 per province of quarterly food YoY, food-minus-headline and headline, over the quarters from 2021-Q1 that were
    complete and published before the issue (expanding window; at 2022-Q4 it equals the frozen 2021-22 definition)."""
    out = {}
    for p, g in L.groupby("province_code"):
        h = g[[quarter_usable(int(q), issue) for q in g["q"]]]
        if len(h) < MIN_THRESHOLD_QUARTERS:
            out[p] = {"food": np.nan, "gap": np.nan, "head": np.nan, "n": int(len(h))}
            continue
        out[p] = {"food": float(np.percentile(h["F"], 60)), "gap": float(np.percentile(h["F"] - h["HL"], 60)),
                  "head": float(np.percentile(h["HL"], 60)), "n": int(len(h))}
    return out


# --------------------------------------------------------------------------------------- local typhoon exposure
def local_typhoons():
    from app.ml.corpus import pagasa_climate_fetcher as PF
    t = pd.read_csv(IBTRACS, skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON"], low_memory=False)
    t["LAT"], t["LON"] = pd.to_numeric(t["LAT"], errors="coerce"), pd.to_numeric(t["LON"], errors="coerce")
    t = t[t["LAT"].between(10, 19) & t["LON"].between(116, 127)].copy()
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    t = t[t["ISO_TIME"].dt.year >= 2020]
    out = {}
    for code, (_, la, lo) in PF.PROVINCE_CENTROIDS.items():
        d = np.array([PF._haversine_km(la, lo, a, b) for a, b in zip(t["LAT"], t["LON"])])
        n = t[d <= LOCAL_KM]
        q = n["ISO_TIME"].dt.year * 4 + (n["ISO_TIME"].dt.month - 1) // 3
        out[code] = n.groupby(q)["SID"].nunique().to_dict()
    last = t["ISO_TIME"].max()
    return out, last


# ------------------------------------------------------------------------------------------------ status helpers
def cpi_status(prov: str, m0: int, issue: str, wb: pd.DataFrame) -> str:
    ref = f"{m0 // 12}-{m0 % 12 + 1:02d}"
    g = wb[(wb["reference_month"] == ref) & ((wb["subject"] == prov) | wb["provinces_with_figures"].fillna("").str.contains(prov))]
    if len(g) and (g["release_date_iso"] < issue).any():
        return "verified"
    if len(g):
        return "unavailable_at_issue"
    return "rule_unverified"


def remittance_series():
    """Quarterly national cash remittances with the first dated publication of each quarter's value."""
    c = pd.read_csv(REMIT)
    c["url_date"] = c["source_url"].str.extract(r"/(20\d\d)/(\d\d)/(\d\d)/").apply(
        lambda r: f"{r[0]}-{r[1]}-{r[2]}" if pd.notna(r[0]) else None, axis=1)
    q = pd.read_csv(REMIT_Q)
    rows = []
    for r in q.itertuples():
        y, qq = int(r.quarter[:4]), int(r.quarter[-1])
        need = {1: ["Q1"], 2: ["H1", "Q1"], 3: ["9M", "H1"], 4: ["FY", "9M"]}[qq]
        src = c[(c["year"] == y) & c["period"].isin(need)]
        derived = src["how_obtained"].str.startswith("derived").any()
        year_later = src["how_obtained"].str.contains("year-earlier").any()
        dates = src["url_date"].dropna()
        status = "rule_unverified"
        if len(src) == len(need) and not derived and not year_later and len(dates) == len(need):
            status = "verified"
        rows.append({"quarter": r.quarter, "q": int(r.q), "remit_usd_bn": float(r.cash_remit_usd_bn),
                     "first_dated_publication": dates.max() if len(dates) == len(need) else None,
                     "status": status, "evidence": "; ".join(src["how_obtained"].tolist()),
                     "note": ("value reported a year later (possibly revised)" if year_later else "") + ("; derived by subtraction" if derived else "")})
    return pd.DataFrame(rows)


def annual_employment():
    e = pd.read_csv(EMP)
    e = e[e["data_status"] != "Not yet available"].copy()
    e["unemployment_rate_pct_derived"] = e["unemployment_rate_pct"]
    miss = e["unemployment_rate_pct"].isna() & e["employment_rate_pct"].notna()
    e.loc[miss, "unemployment_rate_pct_derived"] = 100 - e.loc[miss, "employment_rate_pct"]
    e["unemployment_is_derived"] = miss
    return e


# ------------------------------------------------------------------------------------------------- products
def provincial_profile():
    S = pd.read_csv(STACK, dtype={"province_code": str})
    S = S[S["lead"] == 1].copy()                                   # origin-level features (lead-specific A1 at Lead 1)
    L = cpi_quarterly()
    THF, THG, THH = frozen_thresholds()
    wb = pd.read_csv(WAYBACK, dtype=str)
    wb = wb[wb["error"].isna() & wb["reference_month"].notna() & (wb["series"] == "all_income")]
    tc_local, tc_last = local_typhoons()
    emp = annual_employment()
    rows = []
    for r in S.itertuples():
        p, t, iss = r.province_code, int(r.t), r.issue_date
        th = asof_thresholds(L, iss)[p]
        proj_food, proj_gap = r.A1_food + THF[p], r.A1_gap + THG[p]
        headline = r.A2 + THH[p]
        m0 = int(r.psa_newest_month[:4]) * 12 + int(r.psa_newest_month[5:7]) - 1
        cst = cpi_status(PROV[p], m0, iss, wb)
        yq = [y for y in emp["year"].unique()]
        ey = emp[(emp["province"] == PROV[p]) & (emp["year"] <= int(iss[:4]) - 1)]           # annual value of an earlier year
        ey = ey.sort_values("year").iloc[-1] if len(ey) else None
        tl = tc_local[p].get(t, 0) if pd.Timestamp(qs(t + 1).replace("-Q", "-")[:4] + f"-{(t + 1) % 4 * 3 + 1:02d}-01") <= tc_last else np.nan
        rows.append({
            "province_code": p, "province": PROV[p], "origin": qs(t), "t": t, "issue_date": iss,
            # market: frozen-threshold values reproduce the served stack; as-of thresholds use only published quarters
            "A1_food_frozen": r.A1_food, "A1_gap_frozen": r.A1_gap, "A2_frozen": r.A2,
            "A1_food_asof": proj_food - th["food"], "A1_gap_asof": proj_gap - th["gap"], "A2_asof": headline - th["head"],
            "threshold_quarters_asof": th["n"],
            "threshold_status": "verified" if th["n"] >= MIN_THRESHOLD_QUARTERS else "insufficient_data",
            "cpi_newest_month": r.psa_newest_month, "cpi_release_status": cst,
            "A_status": "insufficient_data (threshold)" if th["n"] < MIN_THRESHOLD_QUARTERS else cst,
            "cpi_vintage_status": "2018=100 not shown public at issue" if iss < CPI_2018_PUBLIC else "2018=100 public",
            "A3_rice_yoy": r.A3, "A3_status": "rule_unverified" if pd.notna(r.A3) else "not_collected (no pre-2021 base)",
            # climate (local exposure kept separate from the 300 km count)
            "C2_tc_300km": r.C2, "C2_tc_local_100km": tl, "C2_status": "incomplete" if qs(t) in FI.INCOMPLETE_TYPHOON_QUARTERS else "verified",
            "C3_palay_corn_drop": r.C3, "C3_status": "rule_unverified" if pd.notna(r.C3) else "not_collected (no pre-2021 base)",
            # fish (provincial PSA rows)
            "C4_fish_drop": r.C4, "C4_status": "rule_unverified" if pd.notna(r.C4) else "not_collected (no pre-2021 base)",
            # employment at its real resolution: annual provincial (owner file, earlier year only)
            "E1_prov_unemployment_annual": None if ey is None else ey["unemployment_rate_pct_derived"],
            "E1_prov_underemployment_annual": None if ey is None else ey["underemployment_rate_pct"],
            "E1_prov_reference_year": None if ey is None else int(ey["year"]),
            "E1_prov_status": "not_collected" if ey is None else ("rule_unverified (derived 100 - employment rate)" if ey["unemployment_is_derived"] else "rule_unverified (no publication date)"),
            # news: no collected data vs too few admitted articles vs observed
            "N1_fssi": r.N1, "N1_admitted_articles": r.N1_articles,
            "N1_status": "observed" if pd.notna(r.N1) else ("insufficient_data (< 5 admitted articles)" if r.N1_articles > 0 else "insufficient_data (0 admitted articles; corpus collected)"),
            # poverty: dated structural profile, not a dynamic feature
            "V1_vulnerability_profile": r.V1, "V1_reference": "SAE 2021 poverty + POPCEN 2024 density",
            "V1_status": "verified" if iss >= V1_PUBLIC else "unavailable_at_issue (published 2024-2025)",
        })
    return pd.DataFrame(rows)


def national_context():
    S = pd.read_csv(STACK, dtype={"province_code": str})
    S = S[S["lead"] == 1].drop_duplicates("t").sort_values("t")
    rem = remittance_series().set_index("q")
    panel = pd.read_parquet(BSP_PANEL).drop_duplicates("quarter").set_index("quarter")
    rows = []
    for r in S.itertuples():
        t, iss = int(r.t), r.issue_date
        q_rem = t - 1                                             # quarter t-1 (rule, unverified)
        rr = rem.loc[q_rem] if q_rem in rem.index else None
        prev = rem.loc[q_rem - 4] if (q_rem - 4) in rem.index else None
        avail = rr is not None and (rr["first_dated_publication"] is None or rr["first_dated_publication"] < iss)
        rows.append({"origin": qs(t), "t": t, "issue_date": iss,
                     "C1_el_nino_in_force": r.C1, "C1_status": "verified", "C1_resolution": "national",
                     "E1_national_unemployment_change": r.E1, "E1_resolution": "national",
                     "E1_status": "rule_unverified" if pd.notna(r.E1) else "not_collected (no pre-2021 base)",
                     "E2_remit_decline_pct": (-100 * (rr["remit_usd_bn"] / prev["remit_usd_bn"] - 1)) if (rr is not None and prev is not None) else np.nan,
                     "E2_stack_value": r.E2, "E2_resolution": "national",
                     "E2_status": ("not_collected (no pre-2021 base)" if prev is None else
                                   "rule_unverified (earliest dated evidence after issue)" if not avail else rr["status"] if rr is not None else "not_collected"),
                     "E2_model_panel_value_usd_bn": panel["ofw_cash_remit_usd_bn"].get(qs(q_rem), np.nan),
                     "E2_audit_value_usd_bn": rr["remit_usd_bn"] if rr is not None else np.nan,
                     "H1_balance_luzon_outlook": r.H1, "H1_resolution": "region (Balance Luzon)", "H1_status": "verified" if pd.notna(r.H1) else "not_collected",
                     "sws_newest_quarter": r.sws_newest_q})
    return pd.DataFrame(rows)


def regional_panel():
    sys.path.insert(0, str(X / "E116_FIRI_Domains" / "runner"))
    import run_e116 as R16
    R = R16.rows()
    R["sws_release_status"] = np.where(R["q_last"] < qi("2021-Q1"), "rule_unverified (month end + 60 days)", "verified")
    R["cpi_vintage"] = np.where(R["issue"] < "2018-02-01", "2018=100 back-cast (not as published)", "2018=100")
    for c in ("F_yoy", "F_dyoy", "PAL_yoy", "P-UNEMP"):
        R[f"{c}_status"] = np.where(R[c].notna(), "rule_unverified", "not_collected")
    R["E2_status"] = "not_collected (no long national series; BSP blocks download)"
    R["N_status"] = np.where(R["N-SUP"].notna(), "verified", "not_collected (GDELT starts 2017)")
    R["resolution_note"] = "area: AF_*, F_*, PAL_*; national: P-RICE, C-ONI, C_nino, C-TC, P-UNEMP, N-*"
    keep = ["area", "t", "lead", "q", "issue", "y", "pub_target", "h_last", "q_last", "MR", "d_last", "stale", "mean_known",
            "AF_food", "AF_gap", "AF_dfood", "P-RICE", "F_yoy", "F_dyoy", "C-ONI", "C_nino", "C-TC", "PAL_yoy", "P-UNEMP",
            "N-SUP", "N-AST", "split", "sws_release_status", "cpi_vintage", "F_yoy_status", "F_dyoy_status", "PAL_yoy_status",
            "P-UNEMP_status", "E2_status", "N_status", "resolution_note"]
    return R[keep]


def registry():
    rows = []
    for k, lab in FI.LABELS.items():
        reg = {"A1": "area food CPI YoY / gap (E116)", "A2": "area food-minus-headline (E116)", "A3": "national rice CPI",
               "C1": "ONI / El Nino flag (national)", "C2": "typhoon change (national PAR)", "C3": "area palay YoY",
               "C4": "area fisheries YoY", "E1": "national unemployment change", "E2": "unavailable (no long series)",
               "N1": "GDELT supply/assistance (national, 2018+)", "V1": "unavailable (no dated series)", "H1": "SWS hunger history (the target series)"}[k]
        prov = {"A1": "province, as-of thresholds", "A2": "province, as-of thresholds", "A3": "province", "C1": "national context table",
                "C2": "province (300 km and 100 km)", "C3": "province", "C4": "province", "E1": "annual provincial (owner file) + national context",
                "E2": "national context table only", "N1": "province, with coverage status", "V1": "province profile (dated)", "H1": "regional context table only"}[k]
        rows.append({"indicator": k, "label": lab, "firi_domain": FI.DOMAIN_OF[k], "trigger_domain": TRIGGER_DOMAIN[k],
                     "regional_forecast_scope": reg, "provincial_profile_scope": prov,
                     "provincial_forecast_scope": "not validated (no provincial outcome)"})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    before = {str(p.relative_to(REPO)): sha(p) for p in INPUTS}
    P, N, R, G = provincial_profile(), national_context(), regional_panel(), registry()
    P.to_csv(OUT / "provincial_profile.csv", index=False, lineterminator="\n", float_format="%.10g")
    N.to_csv(OUT / "national_context.csv", index=False, lineterminator="\n", float_format="%.10g")
    R.to_csv(OUT / "regional_forecast_panel.csv", index=False, lineterminator="\n", float_format="%.10g")
    G.to_csv(OUT / "indicator_registry.csv", index=False, lineterminator="\n")
    remittance_series().to_csv(OUT / "remittances_quarterly_corrected.csv", index=False, lineterminator="\n")
    after = {str(p.relative_to(REPO)): sha(p) for p in INPUTS}
    assert before == after, "a raw input changed during the run"
    man = {"built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "inputs_sha256": before,
           "outputs_sha256": {f.name: sha(f) for f in sorted(OUT.glob("*.csv"))},
           "rows": {"provincial_profile": len(P), "national_context": len(N), "regional_forecast_panel": len(R)}}
    (OUT / "pipeline_manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(man["rows"]))


if __name__ == "__main__":
    main()
