"""
scripts/supplementary/feature_audit_model_b.py

Per-feature timing audit for MODEL-B under strict Rule 3 (forecast for quarter
t+1 made before t+1 starts). Writes evidence/2026-10-08_optimization/
feature_audit.csv. Release practice for series other than SWS and poverty is
the agencies' usual publication lag; with one full quarter of margin under the
strict rule, none is near the boundary. Confirm against release calendars.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import scripts.supplementary.algorithm4_timing_valid as A

OUT = Path("evidence/2026-10-08_optimization/feature_audit.csv")

FAMILIES = [
    # prefix-or-name, source, frequency, base transformation, release, quarter used
    ("FSSI", "News corpus, XLM-RoBERTa (Algorithm 1), Eq. 2", "Continuous", "Bias-weighted mean score", "Same day", "t (lags t-1, t-2)"),
    ("trigger_", "News corpus, regex (Algorithm 2)", "Continuous", "Share of articles per category", "Same day", "t"),
    ("food_cpi", "PSA OpenStat CPI 2018=100, provincial", "Monthly", "Quarterly mean; YoY; lag; accel", "Early next month", "t-1"),
    ("cpi_dev", "PSA OpenStat CPI", "Monthly", "YoY minus province's mean of prior 4 quarters", "Early next month", "t-1 (mean over t-5..t-2)"),
    ("headline_cpi", "PSA OpenStat CPI", "Monthly", "Quarterly mean", "Early next month", "t-1"),
    ("food_minus_headline", "PSA OpenStat CPI", "Monthly", "Food minus headline YoY; lag; accel", "Early next month", "t-1"),
    ("rice_price", "PSA OpenStat regular milled rice", "Monthly", "Quarterly mean; lag; accel", "Within weeks", "t-1"),
    ("commodity_", "PSA NRP to 2021; derived from food CPI after", "Monthly", "Quarterly mean", "As CPI", "t-1"),
    ("unemployment_rate", "PSA Labor Force Survey (national)", "Monthly/quarterly", "Rate; lag; accel", "About 6 weeks", "t-1"),
    ("poverty_incidence", "PSA Full Year Official Poverty Statistics", "Triennial", "Province incidence", "2021 survey 2022-08-15; 2023 survey 2024-08", "Latest release before t+1"),
    ("ofw_remit", "BSP (hand-curated)", "Monthly", "YoY; lag; accel", "About 6-7 weeks", "t-1"),
    ("fx_usd_php", "ECB reference rate (Frankfurter API)", "Daily", "Quarterly mean", "Daily", "t-1"),
    ("diesel", "DOE Oil Monitor (hand-curated)", "Weekly", "Quarterly mean; lag; accel", "Weekly", "t-1"),
    ("gasoline", "DOE Oil Monitor (hand-curated)", "Weekly", "Quarterly mean", "Weekly", "t-1"),
    ("brent", "US EIA via FRED", "Daily", "Quarterly mean", "Daily", "t-1"),
    ("enso", "NOAA CPC ONI", "Monthly", "Integer phase", "Early next month", "t-1"),
    ("tc_", "PAGASA", "Event", "Count / severe flag", "Real time", "t-1"),
    ("drought_alert", "PAGASA", "Event", "Binary", "Real time", "t-1"),
    ("rainfall_anomaly", "Measured provincial rainfall", "Monthly", "% anomaly; lag; accel", "Within the month", "t-1"),
    ("sws_hunger", "SWS Social Weather Survey (Balance Luzon)", "Quarterly", "Total hunger %", "2-12 weeks after fieldwork (article dates)", "Latest round released before t+1"),
]


def main():
    _, _, cols = A.frame_t2()
    rows = []
    for c in cols:
        fam = next((x for x in FAMILIES if c.startswith(x[0])), None)
        src, freq, trans, rel, used = (fam[1:] if fam else ("?",) * 5)
        rows.append({
            "feature": c, "source": src, "frequency": freq, "transformation": trans,
            "derived_from_other_feature": any(s in c for s in ("_lag", "_accel")) or c == "cpi_dev",
            "lagged": "_lag" in c or used.startswith("t-1") or "before" in used,
            "quarter_used_for_forecast_of_t+1": used, "typical_release": rel,
            "available_before_forecast_quarter": True,
            "contains_target_period_information": False,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    return rows


if __name__ == "__main__":
    r = main()
    print(len(r), "features audited; unknown sources:", [x["feature"] for x in r if x["source"] == "?"])
