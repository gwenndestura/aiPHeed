"""
Indicator audit (E7 part 1; leakage-safe). Writes to experiments/2026-10-11_devprotocol/indicator_audit_20261012/.

  * missingness, province variation (inputs only, 2021-Q2..2025-Q4 feature rows; no labels)
  * redundancy: Spearman correlation between inputs (no labels)
  * historical relationship with the outcome: ONLY labels published before 2023-10-01
    (the first evaluation origin; 8 quarters, 40 rows) - the 7 test quarters are not used.

    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/audit_indicators.py
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
import scripts.supplementary.devprotocol_rule_l as D
from app.ml.training import revised_trainer as RT

OUT = Path("experiments/2026-10-11_devprotocol/indicator_audit_20261012")
GROUPS = {
    "R": ["sws_hunger", "sws_change", "last_published_stress"],
    "GP": ["cpi_rel", "cpi_rel_lag1", "cpi_dev", "food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel",
           "rice_price_regular", "rice_price_regular_lag1", "rice_price_regular_accel", "poverty_incidence"],
    "GN": ["unemployment_rate", "unemployment_rate_lag1", "unemployment_rate_accel", "ofw_remit_yoy_pct",
           "ofw_remit_yoy_pct_lag1", "ofw_remit_yoy_pct_accel", "diesel_php_per_l", "diesel_php_per_l_lag1",
           "diesel_php_per_l_accel", "gasoline_php_per_l", "fx_usd_php_avg", "brent_usd_per_bbl", "headline_cpi",
           "food_minus_headline_yoy", "food_minus_headline_yoy_lag1", "food_minus_headline_yoy_accel", "enso_numeric",
           "drought_alert", "tc_count", "tc_severe_flag", "rainfall_anomaly_pct", "rainfall_anomaly_pct_lag1",
           "rainfall_anomaly_pct_accel"],
    "N": ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "fssi_article_count", "news_ph_fssi", "news_ph_count",
          "trigger_market", "trigger_climate", "trigger_fish_kill", "trigger_employment", "trigger_ofw_remittance"],
}


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    frame, _ = D.development_frame()
    fp = D.feature_protocol().set_index("feature")
    labels = RT.TrainingLabels(RT.load_stress())
    f = frame[(frame["target_quarter"] >= "2021-Q2") & (frame["target_quarter"] <= "2025-Q4")].copy()
    f = RT.with_last_published_stress(f, labels, "2026-Q1")          # anchors are all <= 2025-Q4 and published
    pre_q = D.eligible_training_quarters("2023-Q4", "development")   # labels published before 2023-10-01
    pre = f[f["target_quarter"].isin(pre_q)].merge(
        labels.for_target(pre_q, "2023-Q4"), left_on=["target_quarter", "province_code"],
        right_on=["quarter", "province_code"])
    pre["within"] = pre["stress"] - pre.groupby("target_quarter")["stress"].transform("mean")

    rows = []
    for g, cols in GROUPS.items():
        for c in cols:
            x = f[c]
            ok = f[["target_quarter", c]].dropna()
            tot = ok[c].var(ddof=0)
            wq = (ok[c] - ok.groupby("target_quarter")[c].transform("mean")).var(ddof=0)
            p = pre[[c, "stress", "within"]].dropna()
            r_all = spearmanr(p[c], p["stress"]).correlation if len(p) > 5 and p[c].nunique() > 1 else np.nan
            r_wq = spearmanr(p[c], p["within"]).correlation if len(p) > 5 and p[c].nunique() > 1 and wq > 0 else np.nan
            fam = fp.loc[c, "family"] if c in fp.index else "lagged outcome"
            rows.append({"group": g, "feature": c, "family": fam,
                         "availability_basis": fp.loc[c, "basis"] if c in fp.index else "Rule L label publication",
                         "missing_share": round(float(x.isna().mean()), 2),
                         "zero_share": round(float((x == 0).mean()), 2),
                         "province_specific_variance_share": round(float(wq / tot), 2) if tot > 0 else None,
                         "pre_eval_rows": len(p),
                         "pre_eval_spearman_with_stress": None if np.isnan(r_all) else round(float(r_all), 2),
                         "pre_eval_spearman_within_quarter": None if np.isnan(r_wq) else round(float(r_wq), 2)})
    audit = pd.DataFrame(rows)
    audit.to_csv(OUT / "indicator_audit.csv", index=False)

    cols = [c for cols in GROUPS.values() for c in cols]
    corr = f[cols].corr(method="spearman")
    pairs = [(a, b, round(float(corr.loc[a, b]), 2)) for i, a in enumerate(cols) for b in cols[i + 1:]
             if pd.notna(corr.loc[a, b]) and abs(corr.loc[a, b]) >= 0.9]
    pd.DataFrame(pairs, columns=["feature_a", "feature_b", "spearman"]).to_csv(OUT / "redundant_pairs.csv", index=False)
    print(audit.to_string(index=False))
    print(f"\nredundant pairs |rho| >= 0.9: {len(pairs)}")
    for a, b, r in pairs:
        print(f"  {a} ~ {b}: {r}")


if __name__ == "__main__":
    main()
