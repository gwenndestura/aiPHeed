r"""Deliverable 7: external plausibility checks for FINAL (contextual; never treated as provincial HFIAS ground truth).
 A. PSA/FNRI FIES 2023 by region (12-month recall, different instrument) vs FINAL's sealed ENNS2022 regional mean probability.
 B. PSA provincial poverty incidence 2023 (published after the 2022 seal origin; not a model input at that origin) vs FINAL
    sealed 2022 Lead-1 probabilities, and vs the observed HFIAS of the evaluation rounds (to show what a perfect model would score).
 C. SWS hunger, Balance Luzon (household heads, 3-month recall, area level) vs FINAL Luzon means and observed HFIAS Luzon means.
Run: python -I ext_checks.py"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
D = Path("C:/Users/admin/aipheed_e145/backend/data")
norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", re.split(r",|\s(?:\d+/|[a-z]/|r\d)", str(s).lower().lstrip("."))[0])).strip()
seal = json.load(open(RN / "aiPHeed_final_7of7_20261113" / "evidence" / "sealed_enns2022_final_mix.json"))
S = pd.DataFrame(seal["rows"]); S = S[S.arm == "FINAL"]
REL = pd.read_csv(EV / "REL_rows_L1to5.csv")
live = pd.read_csv("C:/Users/admin/aipheed_hcw/backend/data/etmix/out/rows.csv")
out = {}

# ---------- A: regional FIES 2023
F = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
F = F[(F.year == 2023) & (F.level == "region")].copy()
RMAP = {"National Capital Region (NCR)": "NCR", "Cordillera Administrative Region (CAR)": "CAR", "Region I": "Ilocos", "Region II": "Cagayan Valley",
        "Region III": "Central Luzon", "Region IV-A": "CALABARZON", "MIMAROPA Region": "MIMAROPA", "Region V": "Bicol", "Region VI": "Western Visayas",
        "Region VII": "Central Visayas", "Region VIII": "Eastern Visayas", "Region IX": "Zamboanga Peninsula", "Region X": "Northern Mindanao",
        "Region XI": "Davao", "Region XII": "SOCCSKSARGEN", "Region XIII": "Caraga"}
F["region"] = F.geography.map(RMAP)
reg = S[S.lead == 1].groupby("region").agg(final_mean_p=("p", "mean"), final_HIGH=("cls", lambda c: int((c == "HIGH").sum())), provinces=("p", "size")).reset_index()
A = F[["geography", "region", "percent"]].rename(columns={"percent": "fies_2023_mod_sev_pct"}).merge(reg, on="region", how="left")
A.to_csv(EV / "EXT_A_region_fies2023_vs_final2022.csv", index=False, lineterminator="\n")
a = A.dropna()
out["A_regions_compared"] = int(len(a)); out["A_spearman_fies2023_vs_final2022_mean_p"] = round(float(spearmanr(a.fies_2023_mod_sev_pct, a.final_mean_p)[0]), 3)
out["A_spearman_p"] = round(float(spearmanr(a.fies_2023_mod_sev_pct, a.final_mean_p)[1]), 4)
out["A_unmatched_regions"] = sorted(set(reg.region) - set(a.region))
cz = A[A.region == "CALABARZON"].iloc[0]
out["A_CALABARZON"] = {"fies_2023": 19.1, "fies_ci95": [17.0, 21.1], "fies_rank_lowest_of_regions": int((a.fies_2023_mod_sev_pct < cz.fies_2023_mod_sev_pct).sum()) + 1,
                       "final_2022_mean_p": round(float(cz.final_mean_p), 4), "final_rank_lowest_of_regions": int((a.final_mean_p < cz.final_mean_p).sum()) + 1, "regions": int(len(a))}
CZ = ["batangas", "cavite", "laguna", "quezon", "rizal"]
cz_rows = []
for k in CZ:
    s1 = S[(S.key == k) & (S.lead == 1)].p
    rr = REL[(REL.key == k) & (REL.lead == 1)]
    lv = live[(live.province.str.lower() == k)]
    cz_rows.append({"province": k.title(), "retro_rounds": ";".join(f"{s[-4:]}: obs {100 / (1 + np.exp(-y)):.1f}% p={p:.3f}" for s, y, p in zip(rr.survey, rr.y_true, rr.FINAL)),
                    "sealed_2022_L1_p": round(float(s1.iloc[0]), 4) if len(s1) else None,
                    "live_2027Q1_p": round(float(lv[lv.lead == 1].p_own_survey_gap.iloc[0]), 4) if len(lv) else None,
                    "live_2027Q2_p": round(float(lv[lv.lead == 2].p_own_survey_gap.iloc[0]), 4) if len(lv) else None})
pd.DataFrame(cz_rows).to_csv(EV / "EXT_A_calabarzon_provinces.csv", index=False, lineterminator="\n")

# ---------- B: provincial poverty 2023 (post-origin)
P = pd.read_csv(D / "fi5" / "raw" / "psa" / "psa_poverty_incidence_all_regions_2018_2023.csv", encoding="latin-1")
P["key"] = P.Geolocation.map(norm)
pc = [c for c in P.columns if c.startswith("Poverty Incidence among Population (%)")]
P = P[["key"] + pc].rename(columns={c: "pov_" + c[-4:] for c in pc})
for c in ("pov_2018", "pov_2021", "pov_2023"):
    P[c] = pd.to_numeric(P[c], errors="coerce")
alias = {"cotabato": "north cotabato", "mountain province": "mountain", "davao de oro": "compostela valley", "samar": "western samar", "tawitawi": "tawi tawi"}
P["key"] = P.key.map(lambda k: alias.get(k, k))
s1 = S[S.lead == 1][["key", "p"]].merge(P, on="key", how="inner")
out["B_provinces_matched"] = int(len(s1)); out["B_provinces_sealed"] = int((S.lead == 1).sum())
out["B_spearman_final2022_vs_poverty2023"] = round(float(spearmanr(s1.p, s1.pov_2023, nan_policy="omit")[0]), 3)
out["B_spearman_final2022_vs_poverty2021"] = round(float(spearmanr(s1.p, s1.pov_2021, nan_policy="omit")[0]), 3)
s1["d_pov_2021_2023"] = s1.pov_2023 - s1.pov_2021
s1.to_csv(EV / "EXT_B_province_final2022_vs_poverty.csv", index=False, lineterminator="\n")
# reference: the observed HFIAS (2021 round) vs poverty 2021 -- how strongly the measured outcome itself tracks poverty
r21 = REL[(REL.lead == 1) & (REL.survey == "ENNS2021")][["key", "y_true", "FINAL"]].merge(P, on="key")
out["B_ref_observed_hfias2021_vs_poverty2021"] = round(float(spearmanr(r21.y_true, r21.pov_2021, nan_policy="omit")[0]), 3)
out["B_ref_final_2021L1_vs_poverty2021"] = round(float(spearmanr(r21.FINAL, r21.pov_2021, nan_policy="omit")[0]), 3)
out["B_ref_n_2021"] = int(len(r21))

# ---------- C: SWS Balance Luzon (context only)
W = pd.read_csv(D / "fi5" / "raw" / "sws" / "sws_area_rounds_full.csv")
W["year"] = W.quarter.str[:4].astype(int)
wb = W.groupby("year").balance_luzon.mean().round(1)
LUZ = {"CAR", "Ilocos", "Cagayan Valley", "Central Luzon", "CALABARZON", "MIMAROPA", "Bicol"}
rows = []
for s, yr in (("ENNS2018", 2018), ("ENNS2019", 2019), ("ENNS2021", 2021)):
    x = REL[(REL.lead == 1) & (REL.survey == s) & REL.region.isin(LUZ)]
    rows.append({"year": yr, "sws_BL_hunger_mean_pct": float(wb.get(yr, np.nan)), "luzon_test_provinces": int(len(x)),
                 "observed_hfias_mod_sev_mean_pct": round(float((100 / (1 + np.exp(-x.y_true))).mean()), 1), "final_L1_mean_p": round(float(x.FINAL.mean()), 3)})
rows.append({"year": 2022, "sws_BL_hunger_mean_pct": float(wb.get(2022, np.nan)), "luzon_test_provinces": int(S[(S.lead == 1) & S.region.isin(LUZ)].shape[0]),
             "observed_hfias_mod_sev_mean_pct": None, "final_L1_mean_p": round(float(S[(S.lead == 1) & S.region.isin(LUZ)].p.mean()), 3), "note": "sealed forecast; outcome not available"})
lv1 = live[live.lead == 1]
rows.append({"year": 2026, "sws_BL_hunger_mean_pct": float(wb.get(2026, np.nan)), "luzon_test_provinces": int(len(lv1)), "observed_hfias_mod_sev_mean_pct": None,
             "final_L1_mean_p": round(float(lv1.p_own_survey_gap.mean()), 3), "note": "live 2027-Q1 issue covers CALABARZON only"})
C = pd.DataFrame(rows); C.to_csv(EV / "EXT_C_sws_balance_luzon_context.csv", index=False, lineterminator="\n")
json.dump(out, open(EV / "EXT_summary.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)); print(pd.DataFrame(cz_rows).to_string(index=False)); print(C.to_string(index=False)); print(A.to_string(index=False))
