"""
Construct check: PSA Family Income and Expenditure Survey 2023 against measured food insecurity. Descriptive only.

PSA FIES has no hunger or food-insecurity item, so it is never a target. It postdates the 2013-2019 survey rows, so it is
never an E145 input (look-ahead). Rule fixed before computing: it may be called a vulnerability context variable only if
its correlation with 2023 regional Food Insecurity Experience Scale prevalence has a bootstrap 95 % lower bound above 0.

    python -m app.e145.psa_fies_check "<folder with the PSA PUF>"   -> data/e145/out/psa_fies_check.json, psa_fies_province.csv

The microdata stay outside the repository; only weighted aggregates are written.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e141 import panel as P
from app.e145 import OUT
from app.hfias.panel import norm as key
from app.paths import BACKEND_DIR

SEED = 145
REGION_NAME = {13: "National Capital Region (NCR)", 14: "Cordillera Administrative Region (CAR)", 1: "Region I", 2: "Region II", 3: "Region III",
               4: "Region IV-A", 17: "MIMAROPA Region", 5: "Region V", 6: "Region VI", 7: "Region VII", 8: "Region VIII", 9: "Region IX",
               10: "Region X", 11: "Region XI", 12: "Region XII", 16: "Region XIII", 15: "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)",
               18: "Negros Island Region (NIR)", 19: "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)"}
ALIAS = {"davao de oro": "compostela valley", "cotabato": "north cotabato", "samar": "western samar", "mountain province": "mountain",
         "tawi-tawi": "tawi tawi", "davao de oro (compostela valley)": "compostela valley"}


def labels(folder: Path) -> dict:
    t = (folder / "FIES_PUF_2023_Volume1.dcf").read_text(encoding="utf-8-sig", errors="replace")
    block = t[t.index("Name=W_PROV_VS1"):]
    block = block[:block.index("[Item]")]
    return {int(a): b.strip() for a, b in re.findall(r"Value=(\d+);([^\r\n]+)", block)}


def aggregate(d: pd.DataFrame) -> pd.Series:
    w, m = d["RFACT"], d["MEM_RFACT"]
    return pd.Series({"food_share_pct": 100 * (d["FOOD"] * w).sum() / (d["TOTEX"] * w).sum(),
                      "bottom30_pop_pct": 100 * (m * (d["NPCINC"] <= 3)).sum() / m.sum(), "n_families": len(d)})


def boot_rho(a, b, n=4000):
    rng = np.random.default_rng(SEED)
    a, b = np.asarray(a, float), np.asarray(b, float)
    v = []
    for _ in range(n):
        i = rng.integers(0, len(a), len(a))
        if np.ptp(a[i]) > 0 and np.ptp(b[i]) > 0:
            v.append(spearmanr(a[i], b[i]).statistic)
    return {"rho": float(spearmanr(a, b).statistic), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], "n": int(len(a))}


def run(folder: Path) -> dict:
    cols = ["W_REGN", "W_PROV", "RPROV", "FOOD", "TOTEX", "RFACT", "MEM_RFACT", "NPCINC"]
    d = pd.read_csv(folder / "FIES PUF 2023 Volume1.CSV", usecols=cols, encoding="utf-8-sig", low_memory=False)
    prov = d.groupby("W_PROV").apply(aggregate, include_groups=False).reset_index()
    names = labels(folder)
    prov["name"] = prov["W_PROV"].map(names)
    prov["key"] = prov["name"].map(lambda s: ALIAS.get(str(s).strip().lower(), key(str(s))))
    reg = d.groupby("W_REGN").apply(aggregate, include_groups=False).reset_index()
    reg["region"] = reg["W_REGN"].map(REGION_NAME)
    f = pd.read_csv(BACKEND_DIR / "data" / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    f = f[(f["year"] == 2023) & (f["level"] == "region")][["geography", "percent"]]
    R = reg.merge(f, left_on="region", right_on="geography")
    out = {"regional_2023_fies": {"food_share": boot_rho(R["food_share_pct"], R["percent"]),
                                  "bottom30": boot_rho(R["bottom30_pop_pct"], R["percent"]), "unmatched": sorted(set(f["geography"]) - set(R["geography"]))}}
    X = P.outcomes().sort_values("round").groupby("key").tail(1)[["key", "province", "survey", "p", "y"]]
    M = X.merge(prov, on="key")
    out["latest_hfias_rows"] = {"n_panel_provinces": int(X["key"].nunique()), "matched": int(len(M)), "unmatched": sorted(set(X["key"]) - set(M["key"])),
                                "note": "HFIAS 2015-2019 against PSA 2023: rows are years apart, so this is ordering, not same-year agreement",
                                "food_share": boot_rho(M["food_share_pct"], M["y"]), "bottom30": boot_rho(M["bottom30_pop_pct"], M["y"])}
    cal = M[M["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])][["province", "survey", "p", "food_share_pct", "bottom30_pop_pct", "n_families"]]
    out["calabarzon_province_level_as_coded_by_PSA"] = cal.round(2).to_dict(orient="records")
    a, b = out["regional_2023_fies"]["food_share"], out["regional_2023_fies"]["bottom30"]
    out["decision"] = {"food_share_is_context_variable": bool(a["ci95"][0] > 0), "bottom30_is_context_variable": bool(b["ci95"][0] > 0),
                       "is_food_insecurity_label": False, "used_in_E145": False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "psa_fies_check.json").write_text(json.dumps(out, indent=1), newline="\n")
    prov.drop(columns=["key"]).round(3).to_csv(OUT / "psa_fies_province.csv", index=False, lineterminator="\n")
    return out


if __name__ == "__main__":
    print(json.dumps(run(Path(sys.argv[1])), indent=1))
