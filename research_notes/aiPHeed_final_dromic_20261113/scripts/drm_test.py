r"""PROTOCOL_DRM step 3: build D1-D6 per province and window, then the pre-registered confirmation test on T2 (2015->2018) and T3 (2015->2019).
T4 (2021) is reported descriptively and never used to select. Run: python -I drm_test.py"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, rankdata, mannwhitneyu
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
nk = lambda s: re.sub(r"[^a-z]", "", str(s).lower().replace("province", "").replace("city of ", ""))
V = pd.read_csv(EV / "DROMIC_province_values.csv")
pop = pd.read_csv("C:/Users/admin/aipheed_hcw/backend/data/e137/raw/psa/population_2010_2024.csv", dtype=str, encoding="latin-1")
pop = pop[pop.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
pop = pd.DataFrame({"k": pop.iloc[:, 0].str.replace("*", "", regex=False).map(nk), "pop2015": pd.to_numeric(pop.filter(like="2015)").iloc[:, 0], errors="coerce")})
pop = pop.drop_duplicates("k").set_index("k").pop2015
# 2015 Maguindanao = del Norte + del Sur - City of Cotabato (the 2024 table restates the 2022 split; 1,173,933 = 2015 census figure)
pop["maguindanao"] = pop.get("maguindanaodelnorte", np.nan) + pop.get("maguindanaodelsur", np.nan) - 299438.0
alias = {"northcotabato": "cotabato", "compostelavalley": "davaodeoro", "westernsamar": "samar"}
TR = pd.read_csv(RN / "aiPHeed_final_detection_20261113" / "evidence" / "TRANS_rows.csv")
TR = TR[TR["T"].isin(["T2", "T3", "T4"])].copy()
TR["pop2015"] = [pop.get(nk(k), pop.get(alias.get(nk(k), ""), np.nan)) for k in TR.key]
agg = V.groupby(["window", "province", "family", "measure"]).value.sum().unstack(["family", "measure"]).fillna(0.0)
get = lambda w, k, fam, m: float(agg.loc[(w, k), (fam, m)]) if (w, k) in agg.index and (fam, m) in agg.columns else 0.0
F = []
for _, r in TR.iterrows():
    w, k, P = r["T"], r["key"], r["pop2015"] / 1000.0
    aff, dmg = get(w, k, "hydromet", "affected"), get(w, k, "hydromet", "damaged")
    disp = get(w, k, "hydromet", "disp_in") + get(w, k, "hydromet", "disp_out")
    cost = get(w, k, "hydromet", "cost"); cdisp = get(w, k, "conflict", "disp_in") + get(w, k, "conflict", "disp_out")
    F.append({"D1_aff": np.log1p(aff / P), "D2_dmg": np.log1p(dmg / P), "D3_disp": np.log1p(disp / P), "D4_aid": np.log1p(cost / (P * 1000)),
              "D5_aid_aff": np.log1p(cost / aff) if aff > 0 else 0.0, "D6_conflict": np.log1p(cdisp / P),
              "raw_affected": aff, "raw_damaged_totally": dmg, "raw_displaced": disp, "raw_cost_php": cost, "raw_conflict_displaced": cdisp})
TR = pd.concat([TR.reset_index(drop=True), pd.DataFrame(F)], axis=1)
TR.to_csv(EV / "DRM_transition_features.csv", index=False, lineterminator="\n")
DIR = {"D1_aff": 1, "D2_dmg": 1, "D3_disp": 1, "D4_aid": -1, "D5_aid_aff": -1, "D6_conflict": 1}


def pcor(x, y, Z):
    m = np.isfinite(x) & np.isfinite(y) & np.all(np.isfinite(Z), axis=1)
    if m.sum() < 8 or np.std(x[m]) == 0:
        return np.nan, int(m.sum())
    R = lambda v: rankdata(v)
    Zr = np.column_stack([np.ones(m.sum())] + [R(z) for z in Z[m].T])
    ex = R(x[m]) - Zr @ np.linalg.lstsq(Zr, R(x[m]), rcond=None)[0]; ey = R(y[m]) - Zr @ np.linalg.lstsq(Zr, R(y[m]), rcond=None)[0]
    if np.std(ex) == 0:
        return np.nan, int(m.sum())
    return float(np.corrcoef(ex, ey)[0, 1]), int(m.sum())


rows = []
for f, sgn in DIR.items():
    r = {"feature": f, "predicted_sign": sgn}
    zs, ws = [], []
    for t in ("T2", "T3", "T4"):
        x = TR[TR["T"] == t]
        ctrl = ["z_a"] + (["D1_aff"] if f in ("D4_aid", "D5_aid_aff") else [])
        rho, n = pcor(x[f].values, x.dz.values, x[ctrl].values)
        r[f"{t}_rho"], r[f"{t}_n"], r[f"{t}_nonzero"] = (round(rho, 3) if rho == rho else np.nan), n, int((x[f] > 0).sum())
        if t != "T4" and rho == rho:
            dfree = n - 3 - (len(ctrl) - 1)
            zs.append(np.arctanh(np.clip(rho, -.999, .999)) * np.sqrt(dfree)); ws.append(dfree)
    if len(zs) == 2:
        zc = sum(zs) / np.sqrt(len(zs)); r["comb_z"] = round(float(zc), 3); r["comb_p"] = float(2 * norm.sf(abs(zc)))
        r["sign_ok_both"] = bool(all(np.sign(z) == sgn for z in zs))
    rows.append(r)
R = pd.DataFrame(rows)
ok = R.comb_p.notna()
order = R[ok].comb_p.sort_values().index; m = int(ok.sum()); holm = pd.Series(np.nan, index=R.index); run = 0
for j, i in enumerate(order):
    run = max(run, min(1.0, (m - j) * R.loc[i, "comb_p"])); holm[i] = run
R["holm_p"] = holm
R["CONFIRMED"] = (R.holm_p < .05) & R.sign_ok_both.fillna(False) & (np.sign(R.comb_z) == R.predicted_sign)
# secondary: absolute label among provinces starting >= 50 % (T2+T3), and descriptive T4
sec = {}
for scope, x in (("T2+T3", TR[TR["T"].isin(["T2", "T3"]) & (TR.pct_a >= 50)]), ("T4_descriptive", TR[(TR["T"] == "T4") & (TR.pct_a >= 50)])):
    stay = x.pct_T >= 50
    sec[scope] = {"n": int(len(x)), "stayed_high": int(stay.sum())}
    for f in DIR:
        a, b = x.loc[stay, f], x.loc[~stay, f]
        if len(a) and len(b) and (x[f] > 0).any():
            u = mannwhitneyu(a, b, alternative="two-sided"); sec[scope][f] = {"AUC_stay_vs_recover": round(float(u.statistic / (len(a) * len(b))), 3), "p": round(float(u.pvalue), 3)}
json.dump({"confirmation": R.to_dict(orient="records"), "absolute_secondary": sec,
           "coverage": {t: {"provinces": int((TR["T"] == t).sum()), "with_any_hydromet_event": int(((TR["T"] == t) & (TR.raw_affected > 0)).sum()),
                            "with_conflict_displacement": int(((TR["T"] == t) & (TR.raw_conflict_displaced > 0)).sum()),
                            "pop_missing": int(((TR["T"] == t) & TR.pop2015.isna()).sum())} for t in ("T2", "T3", "T4")}},
          open(EV / "DRM_confirmation.json", "w"), indent=1, default=str)
pd.set_option("display.width", 250); print(R.to_string(index=False)); print(json.dumps(sec, indent=1))
