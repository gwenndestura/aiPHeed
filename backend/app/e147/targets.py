"""
Compare candidate target definitions on development rounds (2013 to 2019). Reads no 2021 label.

    python -m app.e147.targets -> data/e147/out/target_comparison.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e141 import panel as P
from app.e147 import OUT

CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
BANDS = [(-1, 20, "Very Low"), (20, 40, "Low"), (40, 60, "Medium"), (60, 80, "High"), (80, 101, "Very High")]


def band(p):
    return next(n for a, b, n in BANDS if a <= p < b)


def main():
    a, m = P.outcomes("insecure"), P.outcomes("mod_sev")
    d = a[["key", "province", "region", "survey", "p", "se_p"]].rename(columns={"p": "any", "se_p": "se_any"}).merge(m[["key", "survey", "p", "se_p", "ref", "status"]].rename(columns={"p": "modsev", "se_p": "se_ms"}), on=["key", "survey"])
    d["A_above_national"] = d["status"] == "ELEVATED"
    d["B_modsev_ge_42_8"] = d["modsev"] >= 42.8
    d["C_any_ge_60_fnri_high"] = d["any"] >= 60
    d["D_band"] = d["any"].map(band)
    rm = d.groupby(["survey", "region"])["any"].transform("mean")
    n_r = d.groupby(["survey", "region"])["any"].transform("size")
    d["E_above_region_mean"] = d["any"] > rm
    d["region_provinces_measured"] = n_r
    c = d[d["province"].isin(CAL)]
    defs = ["A_above_national", "B_modsev_ge_42_8", "C_any_ge_60_fnri_high", "E_above_region_mean"]
    out = {"nationwide_share_by_round": {k: d.groupby("survey")[k].mean().round(3).to_dict() for k in defs},
           "calabarzon_positive_rows_of_13": {k: int(c[k].sum()) for k in defs},
           "calabarzon_by_province": {k: c[c[k]].groupby("province").size().to_dict() for k in defs},
           "bands_all_rows": d["D_band"].value_counts().to_dict(), "bands_calabarzon": c["D_band"].value_counts().to_dict(),
           "calabarzon_rows": c.sort_values(["province", "survey"])[["province", "survey", "any", "se_any", "modsev", "D_band", "C_any_ge_60_fnri_high"]].round(2).to_dict(orient="records"),
           "class_certainty_C": {"rows_within_1_645_se_of_60": float((np.abs(d["any"] - 60) <= 1.645 * d["se_any"]).mean())},
           "continuous": {"sd_between_provinces_within_round": d.groupby("survey")["any"].std().round(2).to_dict(), "mean_survey_se": d.groupby("survey")["se_any"].mean().round(2).to_dict()}}
    (OUT / "target_comparison.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
