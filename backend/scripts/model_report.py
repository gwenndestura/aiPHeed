"""
Phase 5-6: apply docs/aipheed/SELECTION_RULE.md mechanically and produce docs/aipheed/results/*.csv.

PERSIST, TREND-D and SEAS-LLM are recomputed walk-forward with the backend code (app.forecasting) and checked against
the research predictions (E136 out/e136_predictions.csv, max |diff| < 1e-9). HFM-X, RIDGE-ALL, X-RED and SIMPLE come
from those research predictions (reproduced exactly in E134-E136). Reliability N1-N7 uses the frozen
e130_lib.numeric_reliability (protocol lock R2).

    python -I backend/scripts/model_report.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import models as M  # noqa: E402
from app.forecasting import sws as T  # noqa: E402

EXP = REPO / "aipheed-backend-aligned" / "experiments"
OUT = REPO / "docs" / "aipheed" / "results"
PRED = EXP / "E136_Methodology_Review" / "out" / "e136_predictions.csv"
SEED, NBOOT = 2026, 10000
ORDER = ["PERSIST", "TREND-D", "SEAS-LLM", "HFM-X"]            # eligible, simplest first (SELECTION_RULE.md)
REPORTED = ["RIDGE-ALL", "X-RED", "SIMPLE"]                     # reported only
PARAMS = {"PERSIST": 0, "TREND-D": 0, "SEAS-LLM": 3, "HFM-X": 10, "RIDGE-ALL": 23, "X-RED": 10, "SIMPLE": 8}


def lib():
    p = EXP / "E130_Provincial_Risk_Score_Forecasting" / "runner" / "e130_lib.py"
    spec = importlib.util.spec_from_file_location("e130_lib_report", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["e130_lib_report"] = m
    spec.loader.exec_module(m)
    return m


def backend_walk_forward(P: pd.DataFrame) -> pd.DataFrame:
    rr = T.load_rounds()
    for c in ("bk_PERSIST", "bk_TREND-D", "bk_SEAS-LLM", "bk_lo80_SEAS-LLM", "bk_hi80_SEAS-LLM"):
        P[c] = np.nan
    for issue, g in P.groupby("issue"):
        qt = T.known_at(rr, date.fromisoformat(issue))
        par = M.fit_seas(qt)
        pe, tr = M.persistence(qt), M.trend_d(qt)
        for (tq), gg in g.groupby("target"):
            fc = M.forecast_seas(qt, par, T.qi(tq))
            P.loc[gg.index, "bk_PERSIST"] = [pe[a] for a in gg["area"]]
            P.loc[gg.index, "bk_TREND-D"] = [tr[a] for a in gg["area"]]
            P.loc[gg.index, "bk_SEAS-LLM"] = [fc[a]["f"] for a in gg["area"]]
            P.loc[gg.index, "bk_lo80_SEAS-LLM"] = [fc[a]["lo80"] for a in gg["area"]]
            P.loc[gg.index, "bk_hi80_SEAS-LLM"] = [fc[a]["hi80"] for a in gg["area"]]
    for m in ("PERSIST", "TREND-D", "SEAS-LLM"):
        d = float(np.nanmax(np.abs(P[f"bk_{m}"] - P[f"f_{m}"])))
        assert d < 1e-9, f"backend {m} differs from the research predictions by {d}"
        P[f"f_{m}"] = P[f"bk_{m}"]
    return P


def boot_index(tq: np.ndarray, rng) -> list[np.ndarray]:
    qs = np.unique(tq)
    pos = {q: np.where(tq == q)[0] for q in qs}
    return [np.concatenate([pos[q] for q in rng.choice(qs, size=len(qs), replace=True)]) for _ in range(NBOOT)]


def metrics(g: pd.DataFrame, m: str, boots) -> dict:
    y, f, tol = g["y_true"].to_numpy(), g[f"f_{m}"].to_numpy(), g["tol"].to_numpy()
    w = np.abs(f - y) <= tol
    e = f - y
    shares = np.array([w[b].mean() for b in boots])
    high = (pd.qcut(g["y_true"], 3, labels=False) == 2).to_numpy()
    sharp = ((g["y_true"] - g["y_latest"]) > 2 * g["se"]).to_numpy()
    lo, hi = (g.get(f"lo80_{m}"), g.get(f"hi80_{m}"))
    cov = float(np.mean((y >= lo) & (y <= hi))) if lo is not None and lo.notna().all() else np.nan
    gap = np.nan
    if f"train_mae_{m}" in g and g[f"train_mae_{m}"].notna().all():
        gap = float(np.abs(e).mean() - g[f"train_mae_{m}"].mean())
    return {"n_eligible": int(len(g)), "n_quarters": int(g["target"].nunique()), "n_within": int(w.sum()),
            "pct_within": float(w.mean()), "ci95_lo": float(np.quantile(shares, 0.025)), "ci95_hi": float(np.quantile(shares, 0.975)),
            "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
            "high_tercile_bias": float(e[high].mean()), "sharp_n": int(sharp.sum()), "sharp_within": int(w[sharp].sum()),
            "pred_var_over_target_var": float(np.var(f) / np.var(y)), "corr": float(np.corrcoef(f, y)[0, 1]),
            "coverage80": cov, "train_test_mae_gap": gap}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    L = lib()
    P = pd.read_csv(PRED)
    P = P[P.policy == "P-DASH"].copy()
    P = backend_walk_forward(P)
    P["lo80_SEAS-LLM_kalman"], P["hi80_SEAS-LLM_kalman"] = P["bk_lo80_SEAS-LLM"], P["bk_hi80_SEAS-LLM"]
    # the backend serves the Kalman predictive interval (app.forecasting.models.forecast_seas); score that one
    P["lo80_SEAS-LLM"], P["hi80_SEAS-LLM"] = P["bk_lo80_SEAS-LLM"], P["bk_hi80_SEAS-LLM"]
    shared = P[["f_RIDGE-ALL", "f_PSA-ONLY", "f_NLP-ONLY", "f_LGBM-ALL", "f_HYB-LGBM"]].notna().all(axis=1)
    sets = {"S-U": P.n_obs >= 8, "S-E132": shared}
    rng = np.random.default_rng(SEED)
    rows, rel, sel = [], [], []
    for sname, mask in sets.items():
        for k in (1, 2, 3, 4):
            g = P[mask & (P.lead == k)].reset_index(drop=True)
            boots = boot_index(g["target"].to_numpy(), rng)
            for m in ORDER + REPORTED:
                if g[f"f_{m}"].isna().any():
                    continue
                rec = metrics(g, m, boots)
                rec.update(set=sname, lead=k, model=m, params=PARAMS[m], eligible=m in ORDER and sname == "S-U")
                rows.append(rec)
                d = g.rename(columns={"y_true": "y", "area": "province"}).assign(
                    target_q=g["target"].map(T.qi), f_persistence=g["f_PERSIST"], f_climatology=g["f_CLIM"])
                base = ["persistence", "climatology"] if m != "PERSIST" else ["climatology"]
                r = L.numeric_reliability(d, m, base)
                rel.append({"set": sname, "lead": k, "model": m, **{n: bool(v) for n, v in r["rules"].items()},
                            "all_pass": bool(r["passed"]), "n_rows": r["n_rows"], "n_quarters": r["n_target_quarters"]})
            if sname == "S-U" and k == 2:
                inc = "PERSIST"
                w = {m: (np.abs(g[f"f_{m}"] - g["y_true"]) <= g["tol"]).to_numpy() for m in ORDER}
                for m in ORDER[1:]:
                    diffs = np.array([w[m][b].mean() - w[inc][b].mean() for b in boots])
                    lo_, hi_ = np.quantile(diffs, [0.025, 0.975])
                    replaced = bool(lo_ > 0)
                    sel.append({"candidate": m, "incumbent": inc, "diff_within": float(w[m].mean() - w[inc].mean()),
                                "ci95_lo": float(lo_), "ci95_hi": float(hi_), "replaces_incumbent": replaced})
                    if replaced:
                        inc = m
                sel.append({"candidate": "SELECTED", "incumbent": inc})
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(rel).to_csv(OUT / "reliability.csv", index=False)
    S = pd.DataFrame(sel)
    S.to_csv(OUT / "selection.csv", index=False)
    chosen = S.iloc[-1]["incumbent"]
    V = pd.DataFrame(rel)
    V = V[(V.set == "S-U") & (V.model == chosen)].sort_values("lead")
    passed = dict(zip(V["lead"], V["all_pass"]))
    V.to_csv(OUT / "reliability_verdict.csv", index=False)
    cfg = {"selection_rule_sha256": hashlib.sha256((REPO / "docs/aipheed/SELECTION_RULE.md").read_bytes()).hexdigest(),
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "predictions_sha256": hashlib.sha256(PRED.read_bytes()).hexdigest(),
           "sws_rounds_sha256": hashlib.sha256(T.SWS_ROUNDS.read_bytes()).hexdigest(),
           "seed": SEED, "n_boot": NBOOT, "selected": chosen,
           "maximum_reliable_lead": L.maximum_reliable_lead({int(k): bool(v) for k, v in passed.items()})}
    (OUT / "run_config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    cov = P[(P.n_obs >= 8) & (P.lead == 2)]
    kal = float(((cov.y_true >= cov["lo80_SEAS-LLM_kalman"]) & (cov.y_true <= cov["hi80_SEAS-LLM_kalman"])).mean())
    (OUT / "seas_llm_kalman_interval_coverage_lead2_SU.txt").write_text(f"{kal:.4f} over {len(cov)} rows\n", encoding="utf-8")
    print(S.to_string(index=False))
    print(R[(R.set == "S-U") & (R.lead == 2)][["model", "n_eligible", "n_within", "pct_within", "ci95_lo", "ci95_hi", "mae", "rmse"]].round(3).to_string(index=False))
    print(json.dumps(cfg, indent=1))


if __name__ == "__main__":
    main()
