"""
E131 provincial layer (protocol section 6).

X3a  Price-versus-income decomposition of the 2021->2023 change in provincial food deprivation (PFDR = subsistence
     incidence among the population), from the FIES 2023 public-use file and PSA's official food thresholds.
X3b  Stability of provincial patterns across PSA rounds (PFDR 2021/2023; poverty among the population 2021/2023/2025).
X3c  Provincial relative food deprivation (EB-shrunk PFDR 2023 / Region IV-A 2023) and its uncertainty, used to scale
     Balance Luzon hunger forecasts into labelled model-based provincial estimates.

    python -I runner/e131_provincial.py <FIES_PUF_2023_Volume1.dat>
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
sys.path.insert(0, str(ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
import e130_lib as L  # noqa: E402

CODES = {"1000": "Batangas", "2100": "Cavite", "3400": "Laguna", "5600": "Quezon", "5800": "Rizal"}   # RPROV; Lucena 5624 excluded
THRESH = ROOT / "data" / "raw" / "psa_food_threshold_subsistence_2021_2023.csv"
POV = ROOT / "data" / "raw" / "psa_poverty_population_2021_2023_2025.csv"
D5 = ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "out" / "d5_prices_vs_deprivation.csv"


def read_puf(path: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if line[0:2].strip() not in ("4", "04") or line[10:14] not in CODES:
                continue
            rows.append({"province": CODES[line[10:14]], "fsize": float(line[14:18]), "toinc": float(line[663:674]),
                         "rfact": float(line[722:737]), "mem_rfact": float(line[737:752])})
    d = pd.DataFrame(rows)
    d["pci"] = d["toinc"] / d["fsize"]
    return d


def thresholds() -> pd.DataFrame:
    t = pd.read_csv(THRESH, encoding="utf-8-sig")
    t.columns = [" ".join(c.split()) for c in t.columns]
    t["geo"] = t["Geolocation"].str.lstrip(". ").str.split(" ").str[0]
    t["geo"] = t["geo"].where(t["geo"] != "Region", "Region IV-A")
    return t.set_index("geo").rename(columns={
        "Annual Per Capita Food Threshold (in PhP) 2021": "t21", "Annual Per Capita Food Threshold (in PhP) 2023": "t23",
        "Subsistence Incidence among Population (%) 2021": "s21", "Subsistence Incidence among Population (%) 2023": "s23",
        "Coefficient of Variation 2021": "cv21", "Coefficient of Variation 2023": "cv23"})[["t21", "t23", "s21", "s23", "cv21", "cv23"]]


def incidence(d: pd.DataFrame, thr: float) -> float:
    return float(100 * d.loc[d["pci"] < thr, "mem_rfact"].sum() / d["mem_rfact"].sum())


def x3a(puf: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    d5 = pd.read_csv(D5).set_index("province")
    rows = []
    for p in L.PROVINCES:
        d = puf[puf.province == p]
        r = t.loc[p]
        cpi_g = d5.loc[p, "food_price_rise_2021_to_2023_pct"] / 100
        i23 = incidence(d, r.t23)
        i23_t21 = incidence(d, r.t21)
        i23_cpi = incidence(d, r.t21 * (1 + cpi_g))
        official_change = r.s23 - r.s21
        rows.append({"province": p, "records": len(d), "threshold_2021": r.t21, "threshold_2023": r.t23,
                     "threshold_growth_pct": 100 * (r.t23 / r.t21 - 1), "food_cpi_growth_pct": 100 * cpi_g,
                     "pfdr_2021_official": r.s21, "pfdr_2023_official": r.s23, "pfdr_2023_replicated_puf": i23,
                     "replication_gap_pp": i23 - r.s23, "pfdr_2023_at_2021_threshold": i23_t21,
                     "pfdr_2023_at_cpi_updated_threshold": i23_cpi,
                     "official_change_pp": official_change, "price_effect_pp": i23 - i23_t21,
                     "income_effect_pp": official_change - (i23 - i23_t21),
                     "cpi_threshold_error_pct": 100 * (r.t21 * (1 + cpi_g) / r.t23 - 1),
                     "pfdr_error_from_cpi_threshold_pp": i23_cpi - i23})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "x3a_price_income_decomposition.csv", index=False)
    return df


def x3b(t: pd.DataFrame) -> dict:
    pov = pd.read_csv(POV).set_index("geography")
    pv = pov.loc[list(L.PROVINCES)]
    out = {}
    a, b = t.loc[list(L.PROVINCES)], None
    se21, se23 = a.s21 * a.cv21 / 100, a.s23 * a.cv23 / 100
    out["pfdr_2021_2023"] = {"spearman": float(stats.spearmanr(a.s21, a.s23)[0]),
                             "stability_p": L.rank_stability_p(a.s21, se21, a.s23, se23)}
    for y0, y1 in ((2021, 2023), (2023, 2025), (2021, 2025)):
        v0, v1 = pv[f"pov_{y0}"].astype(float), pv[f"pov_{y1}"].astype(float)
        s0, s1 = v0 * pv[f"cv_{y0}"].astype(float) / 100, v1 * pv[f"cv_{y1}"].astype(float) / 100
        out[f"poverty_{y0}_{y1}"] = {"spearman": float(stats.spearmanr(v0, v1)[0]), "stability_p": L.rank_stability_p(v0, s0, v1, s1),
                                     "highest": [str(v0.idxmax()), str(v1.idxmax())]}
    out["poverty_values"] = pv[["pov_2021", "pov_2023", "pov_2025"]].astype(float).to_dict()
    out["note"] = "descriptive: 2025 family poverty was seen in E130 (exposure X2); poverty is a predictor, never a target"
    L.dump(out, OUT / "x3b_pattern_stability.json")
    return out


def x3c(t: pd.DataFrame) -> pd.DataFrame:
    """Relative food deprivation RR_p = EB-shrunk PFDR 2023 / Region IV-A PFDR 2023, with lognormal-approx uncertainty;
    poverty-based RR as a sensitivity."""
    a = t.loc[list(L.PROVINCES)]
    se = a.s23 * a.cv23 / 100
    tau2 = max(0.0, float(np.var(a.s23, ddof=1) - np.mean(se ** 2)))
    w = tau2 / (tau2 + se ** 2)
    m = float(a.s23.mean())
    eb = m + w * (a.s23 - m)
    eb_var = w * se ** 2
    reg, reg_se = float(t.loc["Region IV-A", "s23"]), float(t.loc["Region IV-A", "s23"] * t.loc["Region IV-A", "cv23"] / 100)
    rr = eb / reg
    rr_cv = np.sqrt(eb_var / eb ** 2 + (reg_se / reg) ** 2)
    pov = pd.read_csv(POV).set_index("geography")
    pov_rr = pov.loc[list(L.PROVINCES), "pov_2025"].astype(float) / float(pov.loc["Region IV-A (CALABARZON)", "pov_2025"])
    df = pd.DataFrame({"province": list(L.PROVINCES), "pfdr_2023": a.s23.values, "eb_pfdr_2023": eb.values, "eb_weight": w.values,
                       "rr_food_deprivation": rr.values, "rr_cv": rr_cv.values, "rr_poverty_2025_sensitivity": pov_rr.values})
    df.to_csv(OUT / "x3c_relative_risk.csv", index=False)
    return df


def provincial_estimates(bl: pd.DataFrame, rr: pd.DataFrame, n: int = 20000) -> pd.DataFrame:
    """Model-based provincial hunger estimates = Balance Luzon forecast x RR, with Monte Carlo 80 % intervals.
    bl: one row per target with columns target, f, lo80, hi80 (the E131 candidate)."""
    rng = np.random.default_rng(L.SEED)
    rows = []
    for r in bl.itertuples():
        sd = (r.hi80 - r.lo80) / (2 * 1.2815515655446004)
        f = np.clip(rng.normal(r.f, sd, n), 0, None)
        for p in rr.itertuples():
            k = rng.lognormal(np.log(p.rr_food_deprivation) - 0.5 * np.log1p(p.rr_cv ** 2), np.sqrt(np.log1p(p.rr_cv ** 2)), n)
            x = f * k
            rows.append({"province": p.province, "target": r.target, "lead": r.lead, "estimate": float(np.median(x)),
                         "lo80": float(np.quantile(x, 0.1)), "hi80": float(np.quantile(x, 0.9)),
                         "estimate_poverty_rr_sensitivity": float(r.f * p.rr_poverty_2025_sensitivity),
                         "label": "model-based: Balance Luzon hunger forecast x provincial relative food deprivation (PSA 2023); "
                                  "provincial dynamics inherited from Balance Luzon; validated only at PSA survey rounds"})
    return pd.DataFrame(rows)


def main(puf_path: str):
    OUT.mkdir(exist_ok=True)
    digest = hashlib.sha256(Path(puf_path).read_bytes()).hexdigest()
    puf = read_puf(puf_path)
    t = thresholds()
    a = x3a(puf, t)
    b = x3b(t)
    c = x3c(t)
    L.dump({"puf_file": Path(puf_path).name, "puf_sha256": digest, "puf_records_calabarzon_5_provinces": int(len(puf))},
           OUT / "x3_inputs.json")
    print(a.round(2).to_string(index=False))
    print({k: v for k, v in b.items() if k != "poverty_values"})
    print(c.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
