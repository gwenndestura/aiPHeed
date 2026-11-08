"""Forecast-to-observation matching by survey reference year (never by publication year).

A model's score for (province, reference year Y, lead L) is the mean of its out-of-sample quarterly scores whose
target quarter lies in calendar year Y, each issued L quarters ahead. Rows are kept only when every contributing
forecast was issued before its target quarter began. Fewer than four quarters is flagged 'partial'.
Models whose output is one regional value (FI7, FI9, FI11) cannot rank provinces and are listed as not matchable.
"""
from __future__ import annotations

import json

import pandas as pd

from app.fi9 import quarters as Q
from app.fi12 import CODE, OUT
from app.paths import BACKEND_DIR

EXP = BACKEND_DIR.parent / "aipheed-backend-aligned" / "experiments"
FI10 = BACKEND_DIR / "data" / "fi10" / "out"
YEARS = (2015, 2018, 2019, 2021, 2023)

# model id -> (file, score column, target class, description)
QI_SOURCES = {
    "P0H4": (EXP / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", "P0H4_p", "B", "served P0H4 (T43c probability); file of LEAD2 as-of re-evaluation"),
    "P0H4_price": (EXP / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", "P0H4_price", "C", "P0H4 price part pi_P"),
    "CR": (EXP / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", "CR_p", "B", "CR candidate"),
    "CR-ANC": (EXP / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", "CRANC_p", "B", "CR-ANC candidate"),
    "P0H4-U": (EXP / "LEAD2_FIVE_TRIGGER/out/candidates.csv", "P0H4U_p", "B", "P0H4-U (schedule B)"),
    "UNI-FINAL": (EXP / "FINAL_UNIFIED_LGBM/out/predictions.csv", "UNI_p", "B", "unified LightGBM x hunger term"),
    "CH1-LGBM": (EXP / "FINAL_UNIFIED_LGBM/out/predictions.csv", "CH1-LEAD_p", "B", "per-lead LightGBM x hunger term"),
    "E108": (EXP / "E108_Best_Defensible_Forecasting/out/predictions_T43_lead1.csv", "F1_p", "B", "E108 factored LightGBM (Lead 1 only)"),
}
FI10_SOURCES = {
    "FI10_L1sel": ("LightGBM regression (tuned)", "C", "FI10 locked Lead-1 selection"),
    "FI10_L2sel": ("Ensemble: mean of ridge (partial pooling) and LightGBM regression", "C", "FI10 locked Lead-2 selection"),
    "FI10_damped": ("Damped persistence", "C", "FI10 damped persistence of price pressure"),
    "FI10_naive": ("Naive persistence", "C", "FI10 naive persistence of price pressure"),
}
NOT_MATCHABLE = {
    "FI7": "regional SWS Balance Luzon forecast: one value for all five provinces",
    "FI9 C0": "regional SWS Balance Luzon forecast: one value for all five provinces",
    "FI11": "regional SWS Balance Luzon forecast: one value for all five provinces",
    "FIRI v2 / FIRI3": "an index, not a forecast; no saved out-of-sample provincial history before 2021 (FIRI3 prospective only)",
    "E56-TUNED / E83 / E93": "T43 targets 2023-Q1+ only; superseded by the P0H4 family files above",
}


def _quarterly() -> pd.DataFrame:
    rows = []
    for mid, (f, col, cls, _) in QI_SOURCES.items():
        d = pd.read_csv(f)
        d = d[d[col].notna()]
        rows.append(pd.DataFrame({"model": mid, "target_class": cls, "province": d["province_code"].map(CODE), "lead": d["lead"],
                                  "target_qi": d["q"], "issue_qi": d["q"] - d["lead"], "score": d[col]}))
    P = pd.read_csv(FI10 / "predictions.csv")
    for mid, (cfg, cls, _) in FI10_SOURCES.items():
        d = P[P["config"] == cfg]
        rows.append(pd.DataFrame({"model": mid, "target_class": cls, "province": d["province"], "lead": d["lead"],
                                  "target_qi": d["target_quarter"].map(Q.index), "issue_qi": pd.to_datetime(d["issue_date"]).map(Q.qi_of),
                                  "score": d["p"]}))
    R = pd.concat(rows, ignore_index=True)
    R["year"] = R["target_qi"] // 4
    assert (R["issue_qi"] < R["target_qi"]).all(), "a forecast was issued inside or after its target quarter"
    return R


def realised_price_pressure() -> pd.DataFrame:
    """Construct check, not a forecast: the year's realised provincial food-price excess (mean of level - threshold)."""
    D = pd.read_csv(FI10 / "dataset.csv")
    D = D[(D["lead"] == 1) & D["y"].notna()].drop_duplicates(["province", "target_quarter"])
    D["year"] = D["target_quarter"].str[:4].astype(int)
    D["excess"] = D["level"] - D["threshold"]
    return D.groupby(["province", "year"]).agg(price_excess=("excess", "mean"), price_high_share=("y", "mean"), n_q=("y", "size")).reset_index()


def build() -> pd.DataFrame:
    R = _quarterly()
    R = R[R["year"].isin(YEARS)]
    A = (R.groupby(["model", "target_class", "province", "year", "lead"])
         .agg(score=("score", "mean"), n_quarters=("score", "size"), first_issue_qi=("issue_qi", "min"), last_issue_qi=("issue_qi", "max"))
         .reset_index())
    A["first_issue"] = A["first_issue_qi"].map(lambda q: Q.label(int(q)))
    A["last_issue"] = A["last_issue_qi"].map(lambda q: Q.label(int(q)))
    A["coverage"] = A["n_quarters"].map(lambda n: "full" if n == 4 else "partial")
    return A.drop(columns=["first_issue_qi", "last_issue_qi"])


def write() -> dict:
    A = build()
    A.to_csv(OUT / "model_scores_by_reference_year.csv", index=False)
    realised_price_pressure().to_csv(OUT / "realised_price_pressure_by_year.csv", index=False)
    cov = A.groupby(["model", "lead"])["year"].apply(lambda s: sorted(set(s))).to_dict()
    meta = {"coverage": {f"{m}|L{l}": v for (m, l), v in cov.items()}, "not_matchable": NOT_MATCHABLE,
            "sources": {k: [str(v[0].relative_to(BACKEND_DIR.parent)), v[1], v[3]] for k, v in QI_SOURCES.items()}
                       | {k: ["backend/data/fi10/out/predictions.csv", v[0], v[2]] for k, v in FI10_SOURCES.items()}}
    (OUT / "matching_meta.json").write_text(json.dumps(meta, indent=1, default=int))
    return meta
