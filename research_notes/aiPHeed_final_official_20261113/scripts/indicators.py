r"""Indicator-level contributor assessment for FINAL (hyp g) from the existing fold fits (110 fits: exact TreeSHAP, withholding and
permutation of each SELECTED input, 10 permutation repeats) and the 18 single-input retrains. Classification rule fixed here before
scoring (Section 6C of the 11-13 brief):
  predictive   : permutation dBrier at Lead 1 has 95 % CI > 0 (out-of-sample loss when the input's information is destroyed) AND the
                 input is selected in >= 50 of 110 fits AND its direction is plausible or has no fixed prior
  contextual   : selected at least once, no significant out-of-sample loss
  not recommended : never selected / zero effect, or implausible direction with no OOS support
  requires data : no usable public series at provincial level for the period (OFW remittances; provincial unemployment before 2022)
Run: python -I indicators.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
P = RN / "aiPHeed_final_etmix_20261113" / "parts"; REL = RN / "aiPHeed_final_reliability_20261113" / "evidence"
K = ["key", "survey", "lead"]; rng = np.random.default_rng(13)
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["y_high"]]
F = pd.concat([pd.read_parquet(f) for f in glob.glob(str(P / "FOLD__*.parquet"))]); F = F[F.hyp == "g"]
E = F.groupby(K + ["kind", "what", "rep"], as_index=False)["p"].mean().merge(LAB, on=K)
base = E[E.kind == "base"][K + ["p"]].rename(columns={"p": "p0"}); E = E.merge(base, on=K)
rows = []
for kind in ("permute_input", "withhold_input"):
    for inp, g in E[(E.kind == kind) & (E.lead == 1)].groupby("what"):
        z = g.groupby(K, as_index=False).agg(p=("p", "mean"), p0=("p0", "first"), y=("y_high", "first"))
        d = ((z.p - z.y) ** 2 - (z.p0 - z.y) ** 2).values
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(3000)]
        rnd = {s[-4:]: round(float(((x.p - x.y) ** 2 - (x.p0 - x.y) ** 2).mean()), 4) for s, x in z.groupby("survey")}
        fl = g[g.rep == 0] if kind == "withhold_input" else g
        rows.append({"input": inp, "kind": kind, "dBrier_L1": round(float(d.mean()), 4), "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                     "by_round": rnd, "rounds_worse": int(sum(v > 0 for v in rnd.values())), "rows_L1": len(z),
                     "flips_L1": int(((fl.p >= .5) != (fl.p0 >= .5)).sum() / (1 if kind == "withhold_input" else 10)),
                     "high_recall_change_L1": round(float(((z.p >= .5) & (z.y == 1)).sum() - ((z.p0 >= .5) & (z.y == 1)).sum()), 2)})
O = pd.DataFrame(rows)
imp = pd.read_csv(REL / "CONTRIB_input_importance.csv"); dirn = pd.read_csv(REL / "CONTRIB_direction_check.csv")[["input", "median_rho", "plausible"]]
pm = O[O.kind == "permute_input"].drop(columns="kind").add_prefix("perm_").rename(columns={"perm_input": "input"})
wh = O[O.kind == "withhold_input"][["input", "dBrier_L1", "ci95", "flips_L1"]].add_prefix("withhold_").rename(columns={"withhold_input": "input"})
T = imp.merge(pm, on="input", how="left").merge(wh, on="input", how="left").merge(dirn, on="input", how="left")
SRC = {"cpi_": "PSA CPI (provincial, monthly)", "l_": "PSA/BAS provincial wholesale & farmgate prices", "p_poverty": "PSA poverty statistics (provincial, 2015/2018/2021)",
       "p_subsistence": "PSA subsistence incidence (provincial)", "p_density": "PSA census population / land area", "hh_grdp": "PSA regional accounts (REGIONAL)",
       "income_": "PSA FIES household income (REGIONAL)", "ag_": "PSA palay/corn production (provincial, quarterly)", "c_agri": "PSA palay/corn production (provincial, quarterly)",
       "agri_since": "PSA palay/corn production (provincial, quarterly)", "vu_": "NASA POWER rainfall / IBTrACS typhoon tracks (province centroid)",
       "c_rain": "NASA POWER rainfall", "c_soil": "NASA POWER soil moisture", "c_tc": "IBTrACS typhoon tracks", "oni": "NOAA ONI (global ENSO index)",
       "unemp": "PSA LFS unemployment (national/regional before 2022)", "a_": "News corpus (NLP, regional/area level)", "n_": "News corpus (NLP, national)",
       "p_e": "News corpus (NLP, provincial)", "r_e": "News corpus (NLP, regional)", "mi_": "MIND missing-value flag"}
src = lambda c: next((v for k, v in SRC.items() if c.startswith(k)), "")
T["public_source"] = T.input.map(lambda c: src(c[3:]) + " [missing flag]" if c.startswith("mi_") else src(c))
def rec(r):
    sel = r.fits_selected_of_110
    if r.input.startswith("unemp") and sel < 20: return "requires additional data (no provincial LFS series before 2022)"
    if sel == 0 or r.mean_abs_contrib == 0: return "not recommended (never used)"
    sig = isinstance(r.perm_ci95, list) and r.perm_ci95[0] > 0
    if sig and sel >= 50 and r.plausible in ("yes", "no prior direction"): return "predictive (retain; show)"
    if r.plausible == "NO" and not sig: return "contextual only (implausible direction, no OOS support)"
    return "contextual (retain as input; no demonstrated OOS gain)"
T["recommendation"] = T.apply(rec, axis=1)
T = T.sort_values("mean_abs_contrib", ascending=False)
T.to_csv(EV / "IND_assessment.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 60)
print(T[["input", "group", "fits_selected_of_110", "mean_abs_contrib", "perm_dBrier_L1", "perm_ci95", "perm_rounds_worse", "withhold_flips_L1", "plausible", "recommendation"]].head(40).to_string(index=False))
