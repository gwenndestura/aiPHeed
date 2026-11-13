r"""Exploratory transition analysis (no model is fitted or tuned). One row per province transition at Lead 1:
T1 2013->2015 (78), T2 2015->2018 (22), T3 2015->2019 (25)  = CONFIRMATION set (never involves 2021);  T4 2015->2021 (25) = shown, never used to select.
Outcome: dz = change in position relative to national (logit), i.e. the part of change not shared nationally. For each input: partial Spearman
correlation with dz controlling for the starting relative position, per transition; Fisher-z meta-analysis over T1-T3.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import rankdata, norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
sys.path.insert(0, str(RN / "aiPHeed_objective_completion_20261111" / "scripts"))
import run_qs
from app.hcw import engine as Hh
lg = lambda p: np.log(p / (1 - p))
NAT = {"NNS2013": 0.2432467540453589, "FNRI2015": lg(.538), "ENNS2018": lg(.416), "ENNS2019": lg(.469), "ENNS2021": lg(.410)}
ANCH = {"FNRI2015": "NNS2013", "ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015", "ENNS2021": "FNRI2015"}


def build():
    tr, te, _ = run_qs.load("ENNS2021", 1)
    tr = tr[tr.lead == 1].copy()
    gt = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")
    gt = gt[gt.survey == "ENNS2021"][["key", "p"]]
    te = te.merge(gt, on="key"); te["y_true"] = lg(te.p / 100)
    d = pd.concat([tr.assign(T="T1" if False else None), te], ignore_index=True)
    d["T"] = d.survey.map({"FNRI2015": "T1", "ENNS2018": "T2", "ENNS2019": "T3", "ENNS2021": "T4"})
    d["z_a"] = d.y_anchor - d.survey.map(ANCH).map(NAT)
    d["z_T"] = d.y_true - d.survey.map(NAT)
    d["dz"] = d.z_T - d.z_a
    d["pct_a"] = 100 / (1 + np.exp(-d.y_anchor)); d["pct_T"] = 100 / (1 + np.exp(-d.y_true))
    return d


def pcor(x, y, z):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if m.sum() < 8 or np.nanstd(x[m]) == 0:
        return np.nan, int(m.sum())
    rx, ry, rz = rankdata(x[m]), rankdata(y[m]), rankdata(z[m])
    Z = np.column_stack([np.ones(m.sum()), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1]), int(m.sum())


if __name__ == "__main__":
    EV.mkdir(parents=True, exist_ok=True)
    d = build()
    FS = sorted({c for v in Hh.feature_sets().values() for c in v} | {"tc_rate_since", "soil_since", "rain_since", "agri_since", "c_tc_4q", "p_poverty",
                                                                      "p_subsistence", "p_poverty_gap"})
    FS = [c for c in FS if c in d.columns and pd.api.types.is_numeric_dtype(d[c]) and c != "gap_q"]
    rows = []
    for c in FS:
        r = {"input": c}
        zs, ws = [], []
        for t in ("T1", "T2", "T3", "T4"):
            x = d[d["T"] == t]
            rho, n = pcor(x[c].values.astype(float), x.dz.values, x.z_a.values)
            r[f"{t}_rho"], r[f"{t}_n"] = (round(rho, 3) if rho == rho else np.nan), n
            if t != "T4" and rho == rho and n > 3:
                zs.append(np.arctanh(np.clip(rho, -.999, .999))); ws.append(n - 3)
        if ws:
            zbar = float(np.average(zs, weights=ws)); se = 1 / np.sqrt(sum(ws))
            r["meta_T1_T3_rho"], r["meta_p"] = round(float(np.tanh(zbar)), 3), float(2 * norm.sf(abs(zbar / se)))
            r["sign_consistent_T1_T3"] = bool(len(set(np.sign([v for v in zs if v != 0]))) == 1 and len(zs) == 3)
        rows.append(r)
    R = pd.DataFrame(rows).sort_values("meta_p")
    m = len(R.dropna(subset=["meta_p"])); R["holm_p"] = np.minimum(1, (R.meta_p.rank(method="first") .rsub(m + 1)) * R.meta_p)
    R["holm_p"] = R.sort_values("meta_p").holm_p.cummax()
    R.to_csv(EV / "TRANS_partial_correlations.csv", index=False, lineterminator="\n")
    d[["key", "province", "region", "survey", "T", "pct_a", "pct_T", "z_a", "z_T", "dz"] + FS].to_csv(EV / "TRANS_rows.csv", index=False, lineterminator="\n")
    desc = d.groupby("T").agg(n=("key", "size"), mean_dz=("dz", "mean"), sd_dz=("dz", "std"),
                              rmr=("z_a", lambda s: float(np.polyfit(s, d.loc[s.index, "z_T"], 1)[0]))).round(3)
    print(desc.to_string()); json.dump(desc.to_dict(orient="index"), open(EV / "TRANS_summary.json", "w"), indent=1)
    pd.set_option("display.width", 250); print(R.head(25).to_string(index=False))
