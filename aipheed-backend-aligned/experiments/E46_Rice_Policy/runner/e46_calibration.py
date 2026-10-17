"""E46 calibration and ranking checks for I7 and I8 on S44 and EXT (diagnostics; nothing selected).

Reliability table, calibration-in-the-large, logistic calibration slope/intercept, AUC with a date-cluster bootstrap
interval, and the AUC split into within-quarter pairs (provinces ranked against each other in the same quarter) and
between-quarter pairs (which mostly measures the timing of HIGH periods).

    backend/venv/Scripts/python.exe -B runner/e46_calibration.py  -> runs/calibration_i7_i8.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_lib as M  # noqa: E402

L, np, pd = M.L, M.np, M.pd
RUNS = M.E46 / "runs"
RUN1 = M.E46.parent / "E44_Five_Trigger_Optimization" / "runs" / "20261015T150213Z"


def auc_pairs(g, col, same):
    pos, neg = g[g["y"] == 1], g[g["y"] == 0]
    num = den = 0.0
    for _, a in pos.iterrows():
        b = neg[(neg["target_q"] == a["target_q"]) == same]
        if len(b):
            num += float((a[col] > b[col]).sum() + 0.5 * (a[col] == b[col]).sum())
            den += len(b)
    return (num / den if den else None), int(den)


def calib(g, col):
    from sklearn.linear_model import LogisticRegression
    p = g[col].clip(1e-4, 1 - 1e-4)
    z = np.log(p / (1 - p)).to_numpy().reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z, g["y"].astype(int))
    bins = pd.cut(g[col], [0, 0.1, 0.25, 0.5, 0.75, 1.0], include_lowest=True)
    rel = g.groupby(bins, observed=True).agg(n=("y", "size"), mean_p=(col, "mean"), observed=("y", "mean"))
    return {"citl_observed_minus_mean_p": float(g["y"].mean() - g[col].mean()),
            "calibration_slope": float(lr.coef_[0][0]), "calibration_intercept": float(lr.intercept_[0]),
            "reliability": {str(k): {kk: (round(float(vv), 3) if kk != "n" else int(vv)) for kk, vv in r.items()}
                            for k, r in rel.iterrows()}}


def auc_boot(g, col, n=2000, seed=46):
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    qs = g["target_q"].unique()
    vals = []
    for _ in range(n):
        s = pd.concat([g[g["target_q"] == q] for q in rng.choice(qs, len(qs))])
        if s["y"].nunique() == 2:
            vals.append(roc_auc_score(s["y"], s[col]))
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def main():
    from sklearn.metrics import roc_auc_score
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(RUNS / "i7_20261017T000111Z" / "predictions_i7.csv", dtype={"province_code": str})
    P8 = pd.read_csv(RUNS / "i8_20261017T001227Z" / "predictions_i8.csv", dtype={"province_code": str})
    P = P1.merge(P7[["t", "province_code", "I7_p"]], on=["t", "province_code"]).merge(
        P8[["t", "province_code", "I8_p"]], on=["t", "province_code"])
    import e44_evaluate as E4  # noqa: E402  (path set by e46_lib's import chain)
    lab = P[P["y"].notna() & (P["target_q"] <= L.qi("2026-Q3"))]
    S44 = lab.dropna(subset=[f"{a}_p" for a in E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS])
    EXT = lab.dropna(subset=["I7_p", "I8_p", "I2_p"])
    out = {}
    for nm, D in (("S44", S44), ("EXT", EXT)):
        out[nm] = {}
        for col in ("I2_p", "I7_p", "I8_p"):
            D2 = D.dropna(subset=[col])
            w, nw = auc_pairs(D2, col, True)
            b, nb = auc_pairs(D2, col, False)
            out[nm][col[:-2]] = {"rows": int(len(D2)), "auc": float(roc_auc_score(D2["y"], D2[col])),
                                 "auc_ci95_date_bootstrap": auc_boot(D2, col),
                                 "auc_within_quarter": w, "within_pairs": nw, "auc_between_quarter": b, "between_pairs": nb,
                                 **calib(D2, col)}
    (RUNS / "calibration_i7_i8.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
