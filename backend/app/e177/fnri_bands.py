"""
E177: FNRI's official public-health-significance bands as an interpretation layer for E168 (investigation; no production change).

FNRI's Hunger and Malnutrition Heat Map (heatmap.fnri.dost.gov.ph, v1.0.0 2025) publishes "Cut-off values for public health
significance (Food Insecure Households)": Very Low <20, Low 20-39.9, Medium 40-59.9, High 60-79.9, Very High >=80, applied to
the share of households with ANY food insecurity (HFIAS mild + moderate + severe). E168 forecasts moderate + severe, so the
forecast must first be put on FNRI's measure:

  logit(any) = a + b * logit(moderate+severe)      fitted ONLY on FNRI rounds published before each forecast origin

Evaluated on E168's frozen as-of forecasts for the validation rows that have FNRI any-level values, against persistence
(the province's latest published FNRI any-level band).

    python -m app.e177.fnri_bands -> data/e177/out/{results.json, rows.csv, live_2027.csv}
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
OUT = D / "e177" / "out"
BANDS = [(80, "Very High"), (60, "High"), (40, "Medium"), (20, "Low"), (0, "Very Low")]
YEAR = {"NNS2013": 2013, "FNRI2015": 2015, "ENNS2018": 2018, "ENNS2019": 2019, "ENNS2021": 2021}
lg = lambda p: np.log(np.asarray(p, float) / (100 - np.asarray(p, float)))
ex = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))


def band(v: float) -> str:
    return next(lab for lo, lab in BANDS if v >= lo)


def fnri_table() -> pd.DataFrame:
    L = pd.concat([pd.read_csv(D / "e147" / "raw" / "dev_labels_2011_2019.csv"), pd.read_csv(D / "e147" / "raw" / "sealed_2021_labels.csv")])
    w = L.pivot_table(index=["key", "actual_year"], columns="fs_survey_category", values="pct", aggfunc="first").reset_index()
    w = w.rename(columns={"Food Insecure Households": "any", "Moderately Food Insecure Households": "mod", "Severely Food Insecure Households": "sev"})
    w["ms"] = w["mod"] + w["sev"]
    return w[["key", "actual_year", "any", "ms"]].dropna(subset=["any"])


def fit(w: pd.DataFrame, years: list[int]) -> tuple[float, float, float]:
    t = w[w["actual_year"].isin(years)].dropna(subset=["ms"])
    t = t[(t["ms"] > 0) & (t["ms"] < 100) & (t["any"] > 0) & (t["any"] < 100)]
    b, a = np.polyfit(lg(t["ms"]), lg(t["any"]), 1)
    res = lg(t["any"]) - (a + b * lg(t["ms"]))
    return float(a), float(b), float(res.std(ddof=2))


def released_years(survey: str, lead: int) -> list[int]:
    from app.e148 import model as M8
    from app.e150 import model as M
    from app.e151 import prov as Pv
    return [YEAR[s] for s in M.released(M8.RQ[survey] - lead, Pv.ROUNDS)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    w = fnri_table()
    A = pd.concat([pd.read_csv(D / "e168" / "out" / "all_rows.csv"), pd.read_csv(D / "e168" / "out" / "all_rows_l3_8.csv")])
    A = A[A["mode"] == "main"][["key", "survey", "lead", "mu"]]
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")[["key", "survey", "lead", "region"]]
    res = {"source": "FNRI Hunger and Malnutrition Heat Map, 'Cut-off values for public health significance (Food Insecure Households)'",
           "bands": {lab: lo for lo, lab in BANDS}, "leads": {}}
    all_rows = []
    for L in (1, 2, 3):
        x = G[G["lead"] == L].merge(A[A["lead"] == L], on=["key", "survey", "lead"])
        x["year"] = x["survey"].map(YEAR)
        x = x.merge(w.rename(columns={"actual_year": "year"})[["key", "year", "any"]], on=["key", "year"], how="inner")
        rows = []
        for s, g in x.groupby("survey"):
            yrs = released_years(s, L)
            a, b, sd = fit(w, yrs)
            for _, r in g.iterrows():
                prev = w[(w["key"] == r["key"]) & (w["actual_year"].isin(yrs))].sort_values("actual_year")
                rows.append({**r.to_dict(), "fit_years": "+".join(map(str, yrs)), "a": a, "b": b, "resid_sd": sd,
                             "any_forecast": float(ex(a + b * r["mu"])), "any_persist": float(prev["any"].iloc[-1]) if len(prev) else np.nan})
        X = pd.DataFrame(rows).dropna(subset=["any_persist"])
        X["band_true"], X["band_fc"], X["band_pers"] = X["any"].map(band), X["any_forecast"].map(band), X["any_persist"].map(band)
        order = {lab: i for i, (_, lab) in enumerate(BANDS[::-1])}
        def m(col):
            y, p = (X["any"] >= 60).astype(int), (X[col.replace("band", "any").replace("_fc", "_forecast").replace("_pers", "_persist")] >= 60).astype(int)
            return {"band_accuracy": round(float((X["band_true"] == X[col]).mean()), 3),
                    "within_one_band": round(float((X["band_true"].map(order) - X[col].map(order)).abs().le(1).mean()), 3),
                    "alert_high_or_above_accuracy": round(float((y == p).mean()), 3),
                    "alert_precision": round(float(precision_score(y, p, zero_division=0)), 3), "alert_recall": round(float(recall_score(y, p, zero_division=0)), 3),
                    "alert_f1": round(float(f1_score(y, p, zero_division=0)), 3)}
        res["leads"][L] = {"n": int(len(X)), "high_or_above_share": round(float((X["any"] >= 60).mean()), 3),
                           "mean_abs_error_any_pts": round(float((X["any_forecast"] - X["any"]).abs().mean()), 2),
                           "persistence_mean_abs_error_pts": round(float((X["any_persist"] - X["any"]).abs().mean()), 2),
                           "E168_on_FNRI_scale": m("band_fc"), "persistence": m("band_pers"),
                           "true_band_counts": X["band_true"].value_counts().to_dict()}
        all_rows.append(X.assign(lead=L))
    R = pd.concat(all_rows)
    R.to_csv(OUT / "rows.csv", index=False, lineterminator="\n")
    # live 2027: mapping fitted on every round published by the 2026-Q4 issue
    a, b, sd = fit(w, [2013, 2015, 2018, 2019, 2021])
    live = json.loads((D / "e168" / "out" / "live_2027.json").read_text())
    lv = pd.DataFrame([{"province": r["province"], "lead": r["lead"], "quarter": r["target_quarter"], "ms_forecast_pct": r["score_pct"],
                        "any_forecast_pct": round(float(ex(a + b * lg(r["score_pct"]))), 1),
                        "any_range90_pct": [round(float(ex(a + b * lg(r["score_pct"]) - 1.645 * sd)), 1), round(float(ex(a + b * lg(r["score_pct"]) + 1.645 * sd)), 1)]}
                       for r in live["provinces"]])
    lv["fnri_band"] = lv["any_forecast_pct"].map(band)
    lv.to_csv(OUT / "live_2027.csv", index=False, lineterminator="\n")
    res["live_mapping"] = {"a": round(a, 4), "b": round(b, 4), "resid_sd_logit": round(sd, 4), "fit_years": [2013, 2015, 2018, 2019, 2021]}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for L, r in res["leads"].items():
        print(L, {k: v for k, v in r.items() if k not in ("E168_on_FNRI_scale", "persistence")})
        print("   E168->FNRI", r["E168_on_FNRI_scale"]); print("   persistence", r["persistence"])
    print(res["live_mapping"]); print(lv[lv["lead"] == 1].to_string(index=False))


if __name__ == "__main__":
    main()
