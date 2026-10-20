"""Diagnostics before any FIRI v2 design (final optimization task, 2026-10-20). Describes; changes nothing.

D1 indicator coverage, geographic resolution, missingness (all origins in the feature table)
D2 Spearman correlations between indicators (pooled; and within-quarter for province-varying ones)
D3 FIRI v1 score saturation on the evaluated Lead-2 rows
D4 regional food-insecurity outcome: H1 alone vs FIRI v1 vs FIRI v1 without H vs always-elevated
D5 LightGBM (E57 Lead-2) error analysis: misses by quarter, calibration (bins, Murphy decomposition, slope)

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/firi2_diagnostics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import final_evaluation as FE  # noqa: E402
import firi_evaluate as FV  # noqa: E402

H, F, L, np, pd = FE.H, FE.F, FE.L, FE.np, FE.pd
E = FE.G.E
from app.ml.inference import climate_watch as CW  # noqa: E402
from app.ml.inference import firi as FI  # noqa: E402
from app.ml.inference import thesis_system as TS  # noqa: E402
from app.news import pipeline_v3 as P3  # noqa: E402

OUT = HERE.parent / "out" / "firi2_diagnostics"


def panel(X, S57):
    """Raw indicators for every province at every origin in the feature table (A1 only where sealed)."""
    pp = {(int(r.t), r.province_code): float(r.E56_p_price) for r in S57.itertuples()}
    rows = []
    for t in sorted(X["t"].unique()):
        issue = str(L.origin(int(t)).date())
        haz = CW.hazard(issue)[0]
        rh = TS.regional_hunger(int(t), 2)
        for code in FI.PROVINCES:
            r = X[(X["t"] == t) & (X["province_code"] == code)]
            if r.empty:
                continue
            raw = FI.raw_indicators(code, r.iloc[0].to_dict(), pp.get((int(t), code)), issue, L.qs(int(t)), haz,
                                    rh.get("probabilityAbove11_3"), P3.fssi_v3(code, int(t)))
            rows.append({"t": int(t), "origin": L.qs(int(t)), "issue": issue, "province_code": code,
                         **{k: v["x"] for k, v in raw.items()}, **{f"st_{k}": v["status"] for k, v in raw.items()}})
    return pd.DataFrame(rows)


def coverage(P):
    out = []
    for k in FI.LABELS:
        s = P[k]
        obs = P[s.notna()]
        per_q = obs.groupby("t")[k].nunique()
        out.append({"indicator": k, "label": FI.LABELS[k], "origins": int(P["t"].nunique()),
                    "rows_observed": int(s.notna().sum()), "rows_missing": int(s.isna().sum()),
                    "first_observed": obs["origin"].min() if len(obs) else None,
                    "last_observed": obs["origin"].max() if len(obs) else None,
                    "distinct_values_per_quarter_median": float(per_q.median()) if len(per_q) else None,
                    "resolution": ("province" if len(per_q) and per_q.median() > 1 else "national/regional (same for all provinces)"),
                    "statuses": json.dumps(P[f"st_{k}"].value_counts().to_dict())})
    return pd.DataFrame(out)


def correlations(P):
    ks = [k for k in FI.LABELS if P[k].notna().sum() >= 10 and P[k].nunique() > 2]
    pooled = P[ks].corr(method="spearman")
    prov = [k for k in ks if P.groupby("t")[k].nunique().median() > 1]
    # within-quarter: rank within each origin, then correlate the demeaned ranks
    W = P[["t"] + prov].copy()
    for k in prov:
        W[k] = W.groupby("t")[k].rank() - W.groupby("t")[k].transform(lambda s: s.rank().mean())
    within = W[prov].corr()
    return pooled, within


def saturation(R):
    g = R[R["lead"] == 2]
    anc = FI.anchors()
    out = []
    for r in g.itertuples():
        pass
    return None


def regional(RG_path, R):
    RG = pd.read_csv(RG_path)
    allr = pd.read_csv(L.SWS_FILE)
    # H1 alone (the regional hunger outlook at the same origins)
    h1 = []
    for q in RG["origin_quarter"]:
        rh = TS.regional_hunger(L.qi(q), 2)
        h1.append(rh.get("probabilityAbove11_3"))
    RG["H1"] = h1
    res = {}
    for name, col in (("H1 alone (regional hunger outlook)", "H1"), ("FIRI v1 regional mean", "FIRI_region"),
                      ("FIRI v1 without H", "FIRI_region_noH")):
        g = RG.dropna(subset=[col])
        pred = (g[col] >= 0.5).astype(int)
        res[name] = {"quarters": int(len(g)), "accuracy": float((pred == g["E1"]).mean()),
                     "auc": H.auc(g["E1"].to_numpy(), g[col].to_numpy()),
                     "brier": float(((g[col] - g["E1"]) ** 2).mean()),
                     "spearman_with_hunger_level": float(g[[col, "H_observed"]].corr(method="spearman").iloc[0, 1])}
    res["always elevated"] = {"quarters": int(len(RG)), "accuracy": float(RG["E1"].mean())}
    return RG, res


def lgbm_errors(S57, Y):
    D = S57.merge(Y, on=["province_code", "target"], how="left")
    D["y"] = D["T43"].astype(int)
    D["pred"] = (D["E56_p"] >= 0.5).astype(int)
    byq = D.groupby("target").agg(rows=("y", "size"), HIGH=("y", "sum"), predicted_HIGH=("pred", "sum"),
                                  correct=("pred", lambda s: int((s == D.loc[s.index, "y"]).sum())),
                                  mean_p=("E56_p", "mean"), mean_p_price=("E56_p_price", "mean"),
                                  mean_p_hunger=("E56_p_hunger", "mean")).reset_index()
    fn = D[(D["y"] == 1) & (D["pred"] == 0)][["target", "province", "E56_p", "E56_p_price", "E56_p_hunger", "PS"]]
    fp = D[(D["y"] == 0) & (D["pred"] == 1)][["target", "province", "E56_p", "E56_p_price", "E56_p_hunger", "PS"]]
    # calibration: 5 bins, Murphy decomposition, calibration-in-the-large and slope
    p, y = D["E56_p"].clip(1e-4, 1 - 1e-4), D["y"]
    bins = pd.cut(p, [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    rel = D.assign(bin=bins).groupby("bin", observed=True).agg(n=("y", "size"), mean_p=("E56_p", "mean"), freq=("y", "mean")).reset_index()
    ybar = y.mean()
    reliability = float(((rel["mean_p"] - rel["freq"]) ** 2 * rel["n"]).sum() / len(D))
    resolution = float(((rel["freq"] - ybar) ** 2 * rel["n"]).sum() / len(D))
    from sklearn.linear_model import LogisticRegression
    lo = np.log(p / (1 - p)).to_numpy().reshape(-1, 1)
    slope = float(LogisticRegression(C=1e6).fit(lo, y).coef_[0][0])
    cal = {"rows": int(len(D)), "base_rate": float(ybar), "mean_p": float(D["E56_p"].mean()),
           "brier": float(((D["E56_p"] - y) ** 2).mean()), "murphy_reliability": reliability,
           "murphy_resolution": resolution, "murphy_uncertainty": float(ybar * (1 - ybar)), "calibration_slope": slope,
           "missed_HIGH": int(len(fn)), "false_alarms": int(len(fp))}
    return byq, fn, fp, rel, cal


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, X, B = E.load()
    S57 = pd.read_csv(FE.E57, dtype={"province_code": str})
    Y = F.t43_labels(L.load())[["province_code", "quarter", "T43", "PS"]].rename(columns={"quarter": "target"})
    P = panel(X, S57)
    H.write_csv(P, OUT / "indicator_panel.csv")
    C = coverage(P)
    H.write_csv(C, OUT / "coverage.csv")
    pooled, within = correlations(P)
    pooled.round(3).to_csv(OUT / "spearman_pooled.csv")
    within.round(3).to_csv(OUT / "spearman_within_quarter.csv")
    # D3 saturation of v1 scores on evaluated lead-2 rows
    R = pd.read_csv(HERE.parent / "out" / "firi_rows_all_leads.csv", dtype={"province_code": str})
    l2 = R[R["lead"] == 2][["t", "province_code"]]
    Pl2 = P.merge(l2, on=["t", "province_code"])
    anc = FI.anchors()["indicators"]
    sat = []
    for k in FI.CONTINUOUS:
        a = anc[k]
        x = Pl2[k].dropna()
        if not a["usable"] or x.empty:
            sat.append({"indicator": k, "rows": int(len(x)), "usable": a["usable"]})
            continue
        s = ((x - a["p10"]) / (a["p90"] - a["p10"])).clip(0, 1)
        sat.append({"indicator": k, "rows": int(len(x)), "usable": True, "share_at_1": float((s >= 0.999).mean()),
                    "share_at_0": float((s <= 0.001).mean()), "mean_score": float(s.mean())})
    S = pd.DataFrame(sat)
    H.write_csv(S, OUT / "v1_saturation_lead2.csv")
    dom = R[R["lead"] == 2][[c for c in R.columns if c.startswith("dom_")]].describe().T
    dom.round(3).to_csv(OUT / "v1_domain_scores_lead2.csv")
    RG, reg = regional(HERE.parent / "out" / "firi_regional_outcome.csv", R)
    H.write_csv(RG, OUT / "regional_outcome_with_H1.csv")
    byq, fn, fp, rel, cal = lgbm_errors(S57, Y)
    for name, df in (("lgbm_by_quarter", byq), ("lgbm_missed_HIGH", fn), ("lgbm_false_alarms", fp), ("lgbm_reliability_bins", rel)):
        H.write_csv(df.astype({c: str for c in df.columns if str(df[c].dtype) == "category"}), OUT / f"{name}.csv")
    summary = {"regional": reg, "lgbm_calibration": cal}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
    print(C[["indicator", "rows_observed", "rows_missing", "first_observed", "last_observed", "resolution", "statuses"]].to_string())
    print(pooled.round(2).to_string())
    print(within.round(2).to_string())
    print(S.to_string())
    print(dom.round(3).to_string())
    print(json.dumps(summary, indent=1, default=float))
    print(byq.round(3).to_string())
    print(fn.round(3).to_string())
    print(rel.round(3).to_string())
    print(RG.round(3).to_string())


if __name__ == "__main__":
    main()
