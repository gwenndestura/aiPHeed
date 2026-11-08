"""How the Philippine food-insecurity labels enter the research: target validation, priority validation, and the
feasibility of direct, auxiliary, multi-task and small-area learning (measured, not asserted).

    python -m app.fi9x.labels         # writes data/fi9x/out/label_integration.json
"""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
from scipy import stats

from app.fi5.sources import sws_rounds
from app.fi9x import OUT
from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
SWS_AREA = {"National Capital Region (NCR)": "metro_manila", "Cordillera Administrative Region (CAR)": "balance_luzon",
            "Region I": "balance_luzon", "Region II": "balance_luzon", "Region III": "balance_luzon", "Region IV-A": "balance_luzon",
            "MIMAROPA Region": "balance_luzon", "Region V": "balance_luzon", "Region VI": "visayas", "Region VII": "visayas",
            "Region VIII": "visayas", "Region IX": "mindanao", "Region X": "mindanao", "Region XI": "mindanao", "Region XII": "mindanao",
            "Region XIII": "mindanao", "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)": "mindanao"}


def _sws_year(year: int) -> pd.Series:
    r = sws_rounds()
    r = r[r["quarter"].str[:4].astype(int) == year]
    return r[["national", "metro_manila", "balance_luzon", "visayas", "mindanao"]].astype(float).mean()


def target_validation() -> dict:
    """Does the SWS hunger series (the forecast target) move with the official FIES measurements?"""
    f = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    nat = f[f["level"] == "national"].set_index("year")["percent"]
    sws_nat = {int(y): float(_sws_year(int(y))["national"]) for y in nat.index}
    reg = f[(f["level"] == "region") & (f["year"] == 2023)].copy()
    reg["area"] = reg["geography"].map(SWS_AREA)
    area_fies = reg.groupby("area")["percent"].mean()
    s23 = _sws_year(2023)
    areas = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
    rho = stats.spearmanr([area_fies[a] for a in areas], [s23[a] for a in areas]).statistic
    hf = pd.read_csv(D / "fi_labels" / "clean" / "published_hfias_2015_calabarzon.csv")
    reg15 = hf[hf["geography"] == "CALABARZON"].set_index("category")["percent"]
    return {
        "national_fies_vs_sws": [{"year": int(y), "fies_mod_sev_pct": float(nat[y]), "sws_national_hunger_pct": round(sws_nat[int(y)], 2)} for y in nat.index],
        "national_direction_agreement": {"fies_2019_to_2021": float(np.sign(nat[2021] - nat[2019])), "sws_2019_to_2021": float(np.sign(sws_nat[2021] - sws_nat[2019])),
                                         "fies_2021_to_2023": float(np.sign(nat[2023] - nat[2021])), "sws_2021_to_2023": float(np.sign(sws_nat[2023] - sws_nat[2021]))},
        "area_2023": [{"sws_area": a, "fies_mean_of_regions_pct": round(float(area_fies[a]), 1), "sws_hunger_2023_pct": round(float(s23[a]), 2)} for a in areas],
        "area_2023_spearman_n4": float(rho),
        "calabarzon_fies_2023": float(reg.loc[reg["geography"] == "Region IV-A", "percent"].iloc[0]),
        "balance_luzon_fies_2023_mean_of_7_regions": round(float(area_fies["balance_luzon"]), 1),
        "balance_luzon_sws_2023": round(float(s23["balance_luzon"]), 2),
        "calabarzon_hfias_2015_mod_sev": float(reg15["moderately_food_insecure"] + reg15["severely_food_insecure"]),
        "balance_luzon_sws_2015": round(float(_sws_year(2015)["balance_luzon"]), 2),
    }


def _poverty_2015() -> pd.Series:
    a = pd.read_csv(D / "fi5" / "raw" / "psa" / "psa_poverty_2006_2015.csv", encoding="latin-1")
    a = a[a.iloc[:, 0].str.contains("|".join(PROV), na=False)]
    return pd.Series({next(p for p in PROV if p in g): float(v) for g, v in zip(a.iloc[:, 0], a["Poverty Incidence among Population Estimate (%) 2015"])})


def provincial() -> dict:
    hf = pd.read_csv(D / "fi_labels" / "clean" / "published_hfias_2015_calabarzon.csv")
    hf = hf[hf["geography"].isin(PROV)]
    ms = hf[hf["category"].isin(["moderately_food_insecure", "severely_food_insecure"])].groupby("geography")["percent"].sum()
    sev = hf[hf["category"] == "severely_food_insecure"].set_index("geography")["percent"]
    se = hf[hf["category"] == "severely_food_insecure"].set_index("geography")["se"]
    wb = pd.read_csv(D / "fi_labels" / "clean" / "owner_workbook_records_verified.csv")
    sub = wb[(wb["label_name"] == "Subsistence incidence among families") & (wb["reference_year"] == 2018)].set_index("province")["label_value"]
    pov15 = _poverty_2015()
    pp = pd.read_csv(D / "fi9" / "out" / "province_priority.csv").set_index("province_name")["priority_score"]
    T = pd.DataFrame({"hfias2015_mod_sev": ms, "hfias2015_severe": sev, "hfias2015_severe_se": se, "poverty2015": pov15,
                      "subsistence_families_2018": sub, "lgu_priority_fi9": pp}).loc[PROV]
    rho = {c: float(stats.spearmanr(T["hfias2015_mod_sev"], T[c]).statistic) for c in ["poverty2015", "subsistence_families_2018", "lgu_priority_fi9"]}
    # auxiliary supervised task, measured: leave-one-province-out regression of HFIAS on poverty (n = 5)
    x, y = T["poverty2015"].to_numpy(float), T["hfias2015_mod_sev"].to_numpy(float)
    loo, mean_err = [], []
    for k in range(5):
        m = np.ones(5, bool)
        m[k] = False
        b = np.polyfit(x[m], y[m], 1)
        loo.append(abs(np.polyval(b, x[k]) - y[k]))
        mean_err.append(abs(y[m].mean() - y[k]))
    spread = float(T["hfias2015_mod_sev"].max() - T["hfias2015_mod_sev"].min())
    enns = wb[wb["record_id"].str.startswith("ENNS")][["province", "reference_year", "label_name", "label_value", "verification_status_aipheed"]]
    return {"table": json.loads(T.reset_index(names="province").to_json(orient="records")), "spearman_vs_hfias2015_mod_sev": rho,
            "auxiliary_loo_mae_poverty_model": float(np.mean(loo)), "auxiliary_loo_mae_mean_only": float(np.mean(mean_err)),
            "hfias2015_mod_sev_range_pp": spread, "hfias2015_typical_ci_halfwidth_pp": float(1.96 * T["hfias2015_severe_se"].mean() * np.sqrt(2)),
            "enns_unverified": json.loads(enns.to_json(orient="records"))}


def run() -> dict:
    res = {"target_validation": target_validation(), "provincial": provincial(),
           "feasibility": {
               "direct_supervised_quarterly": "no: no label is quarterly; the provincial labels give 1 HFIAS wave (2015) + 1 unverified ENNS year per province",
               "auxiliary_provincial_task": "measured below: n = 5 per wave; leave-one-out cannot beat the mean reliably",
               "multi_task_shared_representation": "no: SWS (Balance Luzon, quarterly) and FNRI (provinces, one wave per instrument) share no geography-period cell; a linking function cannot be identified",
               "measurement_linking_sws_fies": "3 national FIES years and 1 regional FIES year overlap SWS years; enough for a directional check, not to estimate a link with uncertainty",
               "small_area_estimation": "not possible now: needs household FIES/HFIAS microdata with weights, strata, PSUs and province codes (FNRI PUFs unreachable from this network)",
           }}
    (OUT / "label_integration.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1)[:4000])
