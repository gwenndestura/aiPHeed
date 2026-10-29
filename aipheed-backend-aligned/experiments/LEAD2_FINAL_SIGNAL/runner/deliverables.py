"""Builds LEAD2_INDICATOR_AVAILABILITY.csv and LEAD2_DEVELOPMENT_RESULTS.csv from saved outputs only (no fitting).

    python deliverables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent / "LEAD2_FIVE_TRIGGER" / "runner"))
import lt_lib as T  # noqa: E402

F = T.F
OUT = ROOT / "out"

# code, columns, source, definition, lag rule, lag status, kind, five-group
IND = [
    ("A1", ["A1_food", "A1_gap", "A_mom"], "PSA CPI food and all-items index (OpenSTAT 0012M4ACP22), monthly, province",
     "base-effect projection of target-quarter food YoY and food-minus-headline, minus frozen 2021-22 P60; 3-month food momentum",
     "CPI through month 2 of t at O(t)", "verified: 35 of 36 archived m0 releases before issue (Batangas 2025-02 unverified)",
     "derived (final-vintage index; 3 of 29 archived headline rates differ by <= 0.4 pp; 2018=100 used before it was public for 375 training rows)", "market_prices"),
    ("A2", ["A2"], "PSA CPI all-items YoY, monthly, province", "headline YoY minus province 2021-22 headline P60",
     "months 1-2 of t", "verified as A1", "derived", "market_prices"),
    ("A3", ["A3"], "PSA wholesale rice prices, quarterly, province", "YoY % change t-1 vs t-5", "quarter t-1 at O(t)",
     "assumed (no dated releases saved); S-LAG sensitivity", "observed, derived YoY", "market_prices"),
    ("V1", ["V1"], "PSA SAE 2021 poverty, POPCEN 2024 population, land area", "0.6 x min-max poverty + 0.4 x min-max density",
     "static at every origin", "VIOLATION: figures published 2024-2025 used at all earlier origins; no earlier vintage in the repository",
     "static structural profile (5 distinct values); enters LightGBM only through province ordering", "poverty_vulnerability"),
    ("C1", ["C1"], "PAGASA ENSO alert items, national", "1 if El Nino Alert/Advisory in force", "items issued before O(t)",
     "verified (dated items)", "observed event flag", "climate_stress"),
    ("C2", ["C2"], "IBTrACS tracks", "typhoons within 300 km in quarter t", "quarter t complete at O(t)",
     "plausible; best-track revisions not checked", "observed count", "climate_stress"),
    ("C3", ["C3"], "PSA palay and corn production, quarterly, province", "-(lower of palay / corn YoY %), t-1 vs t-5",
     "quarter t-1 at O(t)", "assumed; S-LAG sensitivity", "observed, derived YoY", "climate_stress"),
    ("C4", ["C4"], "PSA fisheries production, quarterly, province", "-(fisheries YoY %), t-1 vs t-5", "quarter t-1 at O(t)",
     "assumed; S-LAG sensitivity", "observed, derived YoY", "separate (fish production; not in the five groups)"),
    ("E1", ["E1"], "PSA LFS, monthly, national", "quarter-mean unemployment t-1 minus t-5", "months of t-1 at O(t)",
     "assumed; S-LAG sensitivity", "observed, national (no provincial variation)", "employment_remittances"),
    ("E2", ["E2"], "BSP OFW cash remittances, national", "-(YoY %, t-1 vs t-5)", "quarter t-1 at O(t)",
     "assumed; S-LAG sensitivity; series ends 2025-Q4", "observed, national (no provincial variation)", "employment_remittances"),
    ("N1", ["N1", "G_pri_yoy", "NG_gap_price"], "RSS headlines scored by XLM-R (FSSI-v3); GDELT price-news volume",
     "bias-weighted mean intensity; NaN when < 5 admitted headlines (definition); GDELT YoY", "published before O(t)",
     "verified (1,575 dated rows)", "derived; NaN exactly when admitted headlines < 5 (coverage grows from 0% of 2021 origins to 35-40% in 2024-26)", "news_nlp"),
    ("H1", ["H1"], "SWS Balance Luzon involuntary hunger", "P(hunger > 11.3) from the latest posted round", "rounds posted before the issue",
     "verified", "derived, regional (no provincial variation)", "hunger outlook (target component; not in the five groups)"),
]


def main():
    S = T.stack()
    s2 = S[S["lead"] == 2]
    ab = json.loads((T.OUT / "asof_reeval.json").read_text())["ablation_B0"]
    gr = json.loads((OUT / "groups.json").read_text())
    rows = []
    for code, cols, src, defin, rule, status, kind, grp in IND:
        c = cols[0]
        x = s2[[c, "t", "province_code"]]
        tot = x[c].var()
        within = x.groupby("t")[c].var().mean()
        miss = {int(y): round(float(v), 3) for y, v in s2.groupby(s2["t"] // 4)[c].apply(lambda v: v.isna().mean()).items()}
        g5 = grp if grp in gr else None
        rows.append({"indicator": code, "columns": " ".join(cols), "source": src, "definition": defin, "availability_rule": rule,
                     "availability_status": status, "value_kind": kind,
                     "varies_by_province": bool(within > 1e-12) if pd.notna(within) else False,
                     "varies_by_quarter": bool(x.groupby("province_code")[c].nunique().max() > 1),
                     "distinct_values_lead2": int(x[c].nunique()), "missing_share_lead2_all": round(float(s2[c].isna().mean()), 3),
                     "missing_share_by_origin_year": json.dumps(miss), "trigger_group": grp,
                     "group_L2_delta_brier_all_rows_asof": round(ab[grp]["2"]["diff"], 4) if grp in ab else None,
                     "group_L2_DEV_delta_brier": round(gr[g5]["L2_DEV"]["diff"], 4) if g5 else None,
                     "group_L2_CONF_delta_brier": round(gr[g5]["L2_CONF"]["diff"], 4) if g5 else None,
                     "generalizes_DEV_to_CONF_same_sign": (np.sign(gr[g5]["L2_DEV"]["diff"]) == np.sign(gr[g5]["L2_CONF"]["diff"])) if g5 else None})
    pd.DataFrame(rows).to_csv(ROOT / "LEAD2_INDICATOR_AVAILABILITY.csv", index=False, lineterminator="\n")
    # development results: fold-by-fold methods/baselines + sensitivity runs summary
    D = pd.read_csv(OUT / "folds_methods.csv")
    sens = json.loads((OUT / "sensitivity.json").read_text())
    extra = [{"lead": int(k[1]), "origin": "all", "target": "all", "split": k[3:], "model": f"{m} {tag}", "rows": v["rows"], "high": None,
              "t43_brier": v["brier"], "price_brier": None, "reference_brier_same_rows": v["reference_brier_same_rows"]}
             for m, d in sens.items() for tag, r in d.items() for k, v in r.items()]
    cand = json.loads((OUT / "candidates.json").read_text())
    extra += [{"lead": 2, "origin": "gate", "target": "-", "split": "DEV", "model": c, "rows": None, "high": None, "t43_brier": None,
               "price_brier": None, "reference_brier_same_rows": None, "note": v.get("reason", "fitted")} for c, v in cand["cands"].items()]
    pd.concat([D, pd.DataFrame(extra)], ignore_index=True).to_csv(ROOT / "LEAD2_DEVELOPMENT_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")
    print(pd.DataFrame(rows)[["indicator", "varies_by_province", "varies_by_quarter", "distinct_values_lead2", "missing_share_lead2_all",
                              "group_L2_DEV_delta_brier", "group_L2_CONF_delta_brier"]].to_string())


if __name__ == "__main__":
    main()
