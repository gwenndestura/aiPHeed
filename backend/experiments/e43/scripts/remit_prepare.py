"""E43 OFW remittances. bsp.gov.ph returns HTTP 403 to scripts and to the fetch tool, so the BSP primary tables could not
be read. The 2026 monthly values below are BSP figures AS REPORTED by news outlets and the government news agency (web
search, 2026-10-15); each row carries its URL and verified_primary = 0 until checked against BSP's own release.
Nothing is estimated: September 2026 is not released (BSP publishes about 6 weeks after the month).

Writes to backend/experiments/e43/data/:
  remittance_monthly_2026.csv           reported monthly values Jan-Aug 2026 (+ Sep as missing)
  remittance_quarterly.csv/.parquet     quarterly USD and YoY with their basis
  remittance_manual_template.csv        months/quarters to confirm or fill from BSP by hand
  real_peso_inputs.csv/.parquet         inputs of the real-peso composite per province-quarter
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "experiments" / "e43" / "data"
FETCHED = datetime.now(timezone.utc).isoformat(timespec="seconds")
BW_FEB = "https://wealthinsights.metrobank.com.ph/news/cash-remittances-hit-9-month-low-in-february"
GMA_APR = "https://www.gmanetwork.com/news/money/economy/991477/remittances-hit-11-month-low-in-april-2026/story/"
SUN_MAY = "https://www.sunstar.com.ph/davao/cash-remittances-rise-to-us271b-in-may"
TRIB_JUN = "https://tribune.net.ph/2026/08/17/bsp-remittances-reach-half-year-high-in-june"
MIG_JUL = "https://migrantimes.com/remittance-finance/18-09-2026/philippine-cash-remittances-rise-to-324-billion-in-july-central-bank"
BW_AUG = "https://bworldonline.com/top-stories/2026/10/15/787129/philippine-cash-remittances-drop-to-3-month-low-in-august/"
PNA_FEB = "https://www.pna.gov.ph/articles/1272959"
PIA_MAR = "https://pia.gov.ph/press-release/cash-remittances-reach-us2-9b-in-march-2026/"
BW_FY25 = "https://www.bworldonline.com/top-stories/2026/02/16/730762/ofw-remittances-soar-to-all-time-high-35-63-billion-in-2025/"

# (month, USD bn, YoY % as reported or None, source, release/article date or None)
MONTHS = [
    ("2026-01", 3.02, 3.5, BW_FEB, None),
    ("2026-02", 2.79, 2.6, PNA_FEB, "2026-04-15"),
    ("2026-03", 2.874, None, GMA_APR, None),
    ("2026-04", 2.718, 2.0, GMA_APR, None),
    ("2026-05", 2.713, 2.0, SUN_MAY, None),
    ("2026-06", 3.04, 1.7, TRIB_JUN, "2026-08-17"),
    ("2026-07", 3.24, 1.9, MIG_JUL, "2026-09-18"),
    ("2026-08", 3.03, 1.9, BW_AUG, "2026-10-15"),
    ("2026-09", None, None, None, None),            # not released yet (expected about mid-November 2026)
]
# Cumulative totals reported with the same releases (used as cross-checks / quarterly YoY)
CUM = {"2026-Q1": (8.68, 2.8, PIA_MAR), "2026-H1": (17.15, 2.4, TRIB_JUN), "2025-FY": (35.634, 3.3, BW_FY25),
       "2026-Jan-Jul": (20.389, 2.3, MIG_JUL)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = pd.DataFrame(MONTHS, columns=["month", "value", "yoy_pct_reported", "source_url", "release_date"])
    m = m.assign(variable="ofw_cash_remittances_usd_bn", level="national", fetched_at=FETCHED,
                 observed=m["value"].notna().astype(int), verified_primary=0,
                 source_type=m["source_url"].map(lambda u: None if u is None else
                                                 ("government news agency" if ("pna.gov.ph" in u or "pia.gov.ph" in u)
                                                  else "news report of the BSP release")))
    m.to_csv(OUT / "remittance_monthly_2026.csv", index=False)

    q1 = m[m["month"].between("2026-01", "2026-03")]["value"].sum()
    q2 = m[m["month"].between("2026-04", "2026-06")]["value"].sum()
    assert abs(q1 - CUM["2026-Q1"][0]) < 0.02 and abs(q1 + q2 - CUM["2026-H1"][0]) < 0.02, (q1, q2)
    # Q2 YoY from the reported cumulative growth rates: Q2_2025 = H1_2025 - Q1_2025
    q1_25 = CUM["2026-Q1"][0] / (1 + CUM["2026-Q1"][1] / 100)
    h1_25 = CUM["2026-H1"][0] / (1 + CUM["2026-H1"][1] / 100)
    q2_yoy = 100 * (q2 / (h1_25 - q1_25) - 1)

    served = pd.read_parquet(ROOT / "data" / "processed" / "bsp_macro.parquet")
    s = served.drop_duplicates("quarter").set_index("quarter")
    rows = []
    for q, r in s.iterrows():
        if pd.notna(r["ofw_cash_remit_usd_bn"]):
            rows.append({"quarter": q, "value": r["ofw_cash_remit_usd_bn"], "yoy_pct": r["ofw_remit_yoy_pct"],
                         "basis": "served curated value (bsp_macro.parquet); quarterly split NOT consistent with BSP "
                                  "2026 releases, see DATA_REFRESH.md", "source_url": r["source_url"], "observed": 1,
                         "verified_primary": 0})
    rows += [
        {"quarter": "2026-Q1", "value": round(q1, 3), "yoy_pct": CUM["2026-Q1"][1],
         "basis": "sum of reported Jan-Mar 2026; YoY as reported for Jan-Mar", "source_url": PIA_MAR, "observed": 1,
         "verified_primary": 0},
        {"quarter": "2026-Q2", "value": round(q2, 3), "yoy_pct": round(q2_yoy, 2),
         "basis": "sum of reported Apr-Jun 2026; YoY derived from reported Jan-Mar (+2.8%) and Jan-Jun (+2.4%) growth",
         "source_url": TRIB_JUN, "observed": 1, "verified_primary": 0},
        {"quarter": "2026-Q3", "value": None, "yoy_pct": None,
         "basis": "Jul and Aug reported (3.24, 3.03); September not released yet", "source_url": BW_AUG, "observed": 0,
         "verified_primary": 0},
    ]
    qd = pd.DataFrame(rows).assign(variable="ofw_cash_remittances_usd_bn", level="national", release_date=None,
                                   fetched_at=FETCHED)
    qd.to_csv(OUT / "remittance_quarterly.csv", index=False)
    qd.to_parquet(OUT / "remittance_quarterly.parquet", index=False)

    curated_25 = s.loc[["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"], "ofw_cash_remit_usd_bn"]
    print("2026: Q1 =", round(q1, 3), "Q2 =", round(q2, 3), "Q2 YoY (derived) =", round(q2_yoy, 2))
    print("implied by BSP 2026 releases: Q1-2025 =", round(q1_25, 3), " H1-2025 =", round(h1_25, 3))
    print("served curated 2025: Q1 =", curated_25.iloc[0], " H1 =", round(curated_25.iloc[:2].sum(), 3),
          " FY =", round(curated_25.sum(), 3), " vs BSP FY 2025 =", CUM["2025-FY"][0])

    tmpl = [{"period": mo, "cash_remit_usd_bn": None, "candidate_value_from_news": v, "source_url": None,
             "release_date": None, "why": "confirm 2026 value against BSP primary table" if v is not None
             else "not released yet (expected about mid-November 2026)"} for mo, v, *_ in MONTHS]
    tmpl += [{"period": q, "cash_remit_usd_bn": None, "candidate_value_from_news": None, "source_url": None,
              "release_date": None, "why": "re-curate quarterly 2024-2025 from BSP monthly table (curated split "
                                           "disagrees with BSP-implied 2025 levels)"}
             for q in ("2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")]
    pd.DataFrame(tmpl).to_csv(OUT / "remittance_manual_template.csv", index=False)

    # real-peso composite inputs: g_real = (1+g_USD)(1+g_FX)/(1+pi_food) - 1, per province-quarter
    psa = pd.read_parquet(ROOT / "data" / "processed" / "psa_indicators.parquet")[["province_code", "quarter", "food_cpi_yoy"]]
    fx = s["fx_usd_php_yoy_pct"].rename("fx_usd_php_yoy_pct")
    g = qd.set_index("quarter")["yoy_pct"].rename("remit_usd_yoy_pct")
    ri = psa.join(g, on="quarter").join(fx, on="quarter")
    ri["g_real_pct"] = 100 * ((1 + ri["remit_usd_yoy_pct"] / 100) * (1 + ri["fx_usd_php_yoy_pct"] / 100)
                              / (1 + ri["food_cpi_yoy"] / 100) - 1)
    ri["observed"] = ri[["remit_usd_yoy_pct", "fx_usd_php_yoy_pct", "food_cpi_yoy"]].notna().all(axis=1).astype(int)
    ri = ri.assign(level="province", fetched_at=FETCHED,
                   source_url="bsp_macro.parquet (remittances curated, FX live ECB/Frankfurter) + 2026 reported BSP "
                              "values; psa_indicators.parquet (food CPI YoY)")
    ri = ri[ri["quarter"] >= "2021-Q1"].sort_values(["province_code", "quarter"])
    ri.to_csv(OUT / "real_peso_inputs.csv", index=False)
    ri.to_parquet(OUT / "real_peso_inputs.parquet", index=False)
    cov = ri.groupby("quarter")["observed"].min()
    print("real-peso composite complete for", int(cov.sum()), "quarters:", cov[cov == 1].index.min(), "..",
          cov[cov == 1].index.max(), "| FX YoY last:", fx.dropna().index.max(), "| food CPI YoY last:",
          psa.dropna(subset=["food_cpi_yoy"])["quarter"].max())


if __name__ == "__main__":
    main()
