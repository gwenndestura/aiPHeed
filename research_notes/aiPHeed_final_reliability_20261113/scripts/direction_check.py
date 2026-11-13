r"""Directional plausibility of FINAL's contributions: for each selected input, the Spearman correlation between the input's value
and its exact TreeSHAP contribution on the test rows (all 22 fold-leads, 5 seeds, hyp g), compared with the expected direction
(higher prices / poverty / unemployment / rain deficit -> higher risk; higher GRDP, income, production -> lower risk).
Reads inputs and contributions only (no outcome). Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=."""
import glob, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(RN / "aiPHeed_final_7of7_20261113" / "scripts"))
from ablation import PATHS  # noqa: E402
for p in PATHS:
    sys.path.insert(0, p)
import run_qs  # noqa: E402
# group definitions copied verbatim from contrib_final.py
DASH = {"market_prices": "1 Market and prices", "climate": "2 Climate stress", "employment": "3 Employment", "remittance": "4 OFW remittances",
        "poverty_vulnerability": "5 Poverty and social vulnerability", "regional_accounts": "(not on dashboard) Regional economy - GRDP/income, REGIONAL",
        "agri_fish_production": "(not on dashboard) Agriculture and fish production", "news_nlp": "(not on dashboard) News / NLP signals"}


def group(c):
    c = c[3:] if c.startswith("mi_") else c
    if c in ("gap_q", "lead"): return "timing"
    if c in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel"): return "regional_accounts"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density"): return "poverty_vulnerability"
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")): return "market_prices"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni": return "climate"
    if c.startswith("unemp"): return "employment"
    if c.startswith(("remit", "ofw")): return "remittance"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")): return "agri_fish_production"
    return "news_nlp"


EXPECT = {"market_prices": +1, "poverty_vulnerability": +1, "employment": +1, "regional_accounts": -1, "agri_fish_production": -1}
SH = pd.concat([pd.read_parquet(f) for f in glob.glob(str(RN / "aiPHeed_final_etmix_20261113" / "parts" / "SHAP__*.parquet"))])
SH = SH[(SH.hyp == "g") & (SH.input != "bias")]
rows = []
for (sv, L), s in SH.groupby(["survey", "lead"]):
    _, te, _ = run_qs.load(sv, L)
    for (inp, seed), x in s.groupby(["input", "seed"]):
        base = inp[3:] if inp.startswith("mi_") else inp
        if base not in te.columns:
            continue
        v = te.set_index("key")[base].reindex(x.key).values.astype(float)
        if inp.startswith("mi_"):
            v = np.isnan(v).astype(float)
        ok = ~np.isnan(v)
        if ok.sum() >= 6 and np.ptp(v[ok]) > 0 and np.ptp(x.contrib.values[ok]) > 0:
            rows.append({"input": inp, "survey": sv, "lead": L, "seed": seed, "rho": spearmanr(v[ok], x.contrib.values[ok])[0], "abs": float(np.abs(x.contrib).mean())})
D = pd.DataFrame(rows)
T = D.groupby("input").agg(fits=("rho", "size"), median_rho=("rho", "median"), share_positive=("rho", lambda r: float((r > 0).mean())), mean_abs=("abs", "mean")).reset_index()
T["group"] = T.input.map(group); T["dashboard"] = T.group.map(DASH)
T["expected_sign"] = [0 if i.startswith("mi_") else EXPECT.get(g, 0) for i, g in zip(T.input, T.group)]
T["observed_sign"] = np.sign(T.median_rho).astype(int)
T["plausible"] = np.where(T.expected_sign == 0, "no prior direction", np.where(T.observed_sign == T.expected_sign, "yes", "NO"))
T.sort_values("mean_abs", ascending=False).round(3).to_csv(HERE / "evidence" / "CONTRIB_direction_check.csv", index=False, lineterminator="\n")
print(T.sort_values("mean_abs", ascending=False).head(25).round(3).to_string(index=False))
