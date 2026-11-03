"""Survey-design vs seasonality, bias, and interval audits (read data and saved predictions only).

    python -m app.fi9x.audits          # writes data/fi9x/out/audits.json (run after app.fi9x.study run)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from app.fi5.sources import sws_rounds
from app.fi6.target import quarterly
from app.fi9x import OUT
from app.paths import BACKEND_DIR


def seasonality_vs_design() -> dict:
    q = quarterly().sort_values("qi").reset_index(drop=True)
    trail = q["hunger"].rolling(9, center=True, min_periods=5).mean()
    q["dev"] = q["hunger"] - trail
    q["qoy"] = q["quarter"].str[-1].astype(int)
    pre = q[(q["quarter"] < "2021") & q["dev"].notna()]
    by = pre.groupby("qoy")["dev"].agg(["mean", "sem", "count"])
    f = stats.f_oneway(*[g["dev"].to_numpy() for _, g in pre.groupby("qoy")])
    r = sws_rounds()
    r = r[r["bl_n"].notna() & (r["quarter"] >= "2023-Q2")].copy()
    r["t"] = (pd.to_datetime(r["fieldwork"].str[:10]) - pd.Timestamp("2023-01-01")).dt.days / 365.25
    r["small"] = (r["bl_n"] <= 300).astype(float)
    r["month"] = pd.to_datetime(r["fieldwork"].str[:10]).dt.month
    r["qoy"] = r["quarter"].str[-1].astype(int)
    w = 1 / (r["area_moe_bl"] / 1.96) ** 2

    def wls(cols):
        X = np.column_stack([np.ones(len(r))] + [r[c].to_numpy(float) for c in cols])
        W = np.diag(w)
        b = np.linalg.solve(X.T @ W @ X, X.T @ W @ r["balance_luzon"].to_numpy(float))
        res = r["balance_luzon"].to_numpy(float) - X @ b
        dof = len(r) - X.shape[1]
        s2 = max(float(res @ W @ res / dof), 1.0)
        se = np.sqrt(np.diag(np.linalg.inv(X.T @ W @ X)) * s2)
        return {"dof": dof, "small_effect": float(b[1]), "se": float(se[1]), "p": float(2 * stats.t.sf(abs(b[1] / se[1]), dof))}

    for k in (2, 3, 4):
        r[f"q{k}"] = (r["qoy"] == k).astype(float)
    same_q = r[r["quarter"] == "2025-Q2"][["fieldwork", "bl_n", "balance_luzon"]]
    return {"pre2021_quarter_of_year_deviation": json.loads(by.reset_index().to_json(orient="records")),
            "pre2021_anova_p": float(f.pvalue),
            "rounds_2023Q2_plus": json.loads(r[["quarter", "fieldwork", "month", "bl_n", "balance_luzon", "respondent_base"]].to_json(orient="records")),
            "design_effect_trend_only": wls(["small", "t"]),
            "design_effect_with_quarter_of_year": wls(["small", "t", "q2", "q3", "q4"]),
            "same_quarter_pair_2025Q2": json.loads(same_q.to_json(orient="records")),
            "small_rounds_quarters": sorted(r.loc[r["small"] == 1, "quarter"]), "large_rounds_quarters": sorted(r.loc[r["small"] == 0, "quarter"])}


def bias(W: pd.DataFrame, configs: list[str]) -> dict:
    r = sws_rounds()
    n_by_q = r.groupby("quarter")["bl_n"].min()
    out = {}
    for origin, G in W.groupby("origin"):
        G = G.copy()
        G["target_n"] = G["target_quarter"].map(n_by_q)
        D = {}
        for c in configs:
            g = G[G["config"] == c]
            if g.empty:
                continue
            k = g[g["target_n"].notna()]
            D[c] = {"share_predicted_high": float(g["cls"].mean()), "base_rate": float(g["y"].mean()),
                    "false_negatives": int(((g["cls"] == 0) & (g["y"] == 1)).sum()), "false_positives": int(((g["cls"] == 1) & (g["y"] == 0)).sum()),
                    "accuracy_target_round_300": float((k[k["target_n"] <= 300]["cls"] == k[k["target_n"] <= 300]["y"]).mean()) if (k["target_n"] <= 300).any() else None,
                    "accuracy_target_round_600plus": float((k[k["target_n"] > 300]["cls"] == k[k["target_n"] > 300]["y"]).mean()) if (k["target_n"] > 300).any() else None,
                    "n_target_300": int((k["target_n"] <= 300).sum()), "n_target_600plus": int((k["target_n"] > 300).sum())}
        out[origin] = D
    return out


def attention_vs_conditions() -> dict:
    out = {}
    for origin in ("OP1", "QE1"):
        X = pd.read_csv(OUT / f"design_{origin}.csv")
        X = X[X["y"].notna() & X["nidx_QTD"].notna()]
        out[origin] = {"n": int(len(X)),
                       "spearman_y_vs_volume": float(stats.spearmanr(X["z_vol_QTD"], X["y"], nan_policy="omit").statistic),
                       "spearman_y_vs_stress_index": float(stats.spearmanr(X["nidx_QTD"], X["y"], nan_policy="omit").statistic),
                       "spearman_delta_vs_stress_index": float(stats.spearmanr(X["nidx_QTD"], X["delta_target"], nan_policy="omit").statistic),
                       "spearman_volume_vs_stress_index": float(stats.spearmanr(X["z_vol_QTD"], X["nidx_QTD"], nan_policy="omit").statistic)}
    a = pd.read_parquet(BACKEND_DIR / "data" / "fi6" / "news_archive" / "articles.parquet", columns=["site"])
    out["source_shares"] = a["site"].value_counts(normalize=True).round(4).to_dict()
    return out


def interval_coverage() -> dict:
    W = pd.read_csv(BACKEND_DIR / "data" / "fi9r" / "out" / "wf_predictions.csv")
    g = W[W["tag"] == "C0 damped persistence (FI9)"]
    out = {}
    for meth, lo, hi in [("conformal", "cpi95_lo", "cpi95_hi"), ("gaussian", "pi95_lo", "pi95_hi")]:
        inside = ((g["hunger_target"] >= g[lo]) & (g["hunger_target"] <= g[hi]))
        k, n = int(inside.sum()), int(len(g))
        ci = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
        yr = g["target_quarter"].str[:4].astype(int)
        out[meth] = {"covered": k, "n": n, "coverage": k / n, "clopper_pearson_95": [float(ci.low), float(ci.high)],
                     "coverage_2010_2017": float(inside[yr <= 2017].mean()), "coverage_2018_plus": float(inside[yr >= 2018].mean()),
                     "mean_width_pp": float((g[hi] - g[lo]).mean())}
    return out


def run() -> dict:
    W = pd.read_csv(OUT / "predictions.csv")
    A = json.loads((OUT / "adoption.json").read_text())
    E = json.loads((OUT / "evaluation.json").read_text())
    best = {}
    for o in ("OP1", "QE1"):
        F = E[o]["full"]["models"]
        best[o] = sorted([c for c in F if c not in ("Always LOW", "Always HIGH", "Climatology")], key=lambda c: F[c]["brier"])[:3]
    configs = sorted(set(sum(best.values(), [])) | {"C0 damped persistence (production)", "Naive persistence"})
    res = {"seasonality_vs_design": seasonality_vs_design(), "bias": bias(W, configs), "attention_vs_conditions": attention_vs_conditions(),
           "interval_coverage_production": interval_coverage(), "best_by_brier": best, "adopted": A["adopted"]}
    (OUT / "audits.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: r[k] for k in ["best_by_brier", "interval_coverage_production"]}, indent=1))
    s = r["seasonality_vs_design"]
    print(s["pre2021_quarter_of_year_deviation"], s["pre2021_anova_p"], s["design_effect_trend_only"], s["design_effect_with_quarter_of_year"], s["same_quarter_pair_2025Q2"])
    print(json.dumps(r["attention_vs_conditions"], indent=1))
