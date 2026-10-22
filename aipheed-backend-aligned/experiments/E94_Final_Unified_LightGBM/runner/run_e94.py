"""E94 (PROTOCOL.md): reliability of the unified news-informed LightGBM framework (E93 LINDIR) for K = 1..4.
Run from backend/:  python .../run_e94.py

Stage 1 runs the E93 LINDIR components (and an out-of-sample-uncertainty variant) at EVERY origin 2021-Q2..2026-Q3 for
K = 1..4, so each later origin has the model's own earlier out-of-sample forecasts. Stage 2 recalibrates or combines them
at origin t using only forecasts whose T43 label was published before O(t).
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E94 = HERE.parent
EXP = E94.parent
sys.path.insert(0, str(EXP / "E93_Lead2_Breakthrough" / "runner"))
import run_e93 as B  # noqa: E402

G, U, E, L, np, pd = B.G, B.U, B.E, B.L, B.np, B.pd
from scipy.stats import norm  # noqa: E402

KS = B.KS
TH = B.TH
E93_RUN = EXP / "E93_Lead2_Breakthrough" / "runs" / "20261022T060351Z"
NEWS_X = ["nx_market_rice", "nx_climate_enso", "nx_employment_ur", "nx_fssi_food"]
STK_GB = dict(objective="binary", num_leaves=4, max_depth=2, n_estimators=50, learning_rate=0.05, min_child_samples=5,
              reg_lambda=5.0, random_state=94, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
SHRINK_N = 20


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


def add_news_x(T):
    for k in KS:
        X = T[k]
        X["nx_market_rice"] = X["n3_market_rw"] * X["rice_acc"]
        X["nx_climate_enso"] = X["n3_climate_rw"] * X["enso_run3"]
        X["nx_employment_ur"] = X["n3_employment_rw"] * X["d_ur"]
        X["nx_fssi_food"] = X["n3_fssi"] * X["dF1"]
    return T


def hunger_lin_oos(tr, te_row, cols, d, t, k):
    """E93 hunger_lin with the uncertainty s = max(random-walk sd, in-sample RMSE, inner out-of-sample RMSE on the last
    3 training label quarters): in-sample tree residuals understate the forecast error."""
    from lightgbm import LGBMRegressor
    p0, f0, _ = B.hunger_lin(tr, te_row, cols, d, t, k, recency=False)
    if not f0:
        return p0, f0
    hs = L.h_quarters(d.cut(t)).sort_values("q")
    qq, hh = hs["q"].to_numpy(), hs["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_min = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    y = tr["H"] - (tr["H_rel"] + TH["H"])
    med = tr[cols].median()
    A, Bx = tr[cols].astype(float).fillna(med).fillna(0.0), te_row[cols].astype(float).fillna(med).fillna(0.0)
    m = LGBMRegressor(**B.REG).fit(A, y)
    rmse_in = float(np.sqrt(np.mean((y - m.predict(A)) ** 2)))
    qs = sorted(tr["q"].unique())
    rmse_oos = 0.0
    if len(qs) >= 7:
        inner, hold = tr["q"] < qs[-3], tr["q"] >= qs[-3]
        mi = LGBMRegressor(**B.REG).fit(A[inner], y[inner])
        rmse_oos = float(np.sqrt(np.mean((y[hold] - mi.predict(A[hold])) ** 2)))
    Hh = float(te_row["H_rel"].iloc[0]) + TH["H"] + float(m.predict(Bx)[0])
    return float(1 - norm.cdf((TH["H"] - Hh) / max(s_min, rmse_in, rmse_oos))), True


def components(d, T, news: bool, extra: list[str] | None = None) -> pd.DataFrame:
    """Stage 1: components at every origin and K (one fit per origin per part, pooled horizons)."""
    pc, hc = B.arm_cols(news, True)
    if extra:
        pc, hc = pc + extra, hc + extra
    rows = []
    for t in sorted(T[1]["t"].unique()):
        t = int(t)
        if len(L.h_quarters(d.cut(t))) < 3:                 # D1: no hunger history yet (earliest origins only)
            continue
        ptr = B.price_training(T, d, t)
        htr = B.hunger_rows(T, d, t, hc)
        for k in KS:
            te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
            te_row = te[[c for c in hc if c != "k"]].mean().to_frame().T.assign(k=k)
            pp, fp, _ = B.price_part(ptr, te, pc, weighted=False)
            ph, fh, _ = B.hunger_lin(htr, te_row, hc, d, t, k, recency=False)
            ph2, _ = hunger_lin_oos(htr, te_row, hc, d, t, k)
            for i, p in enumerate(L.PROVS):
                rows.append({"t": t, "k": k, "province_code": p, "q": t + k, "pp": float(pp[i]), "ph": ph, "ph_oos": ph2,
                             "fit_price": fp, "fit_hunger": fh})
    return pd.DataFrame(rows)


def past(C: pd.DataFrame, d, t: int) -> pd.DataFrame:
    """Earlier out-of-sample forecasts whose T43 label was complete and published before O(t)."""
    av = E.available(d, t)[["province_code", "q", "y"]]
    return C[C["t"] < t].merge(av, on=["province_code", "q"])


def platt(H: pd.DataFrame, col: str, x: np.ndarray) -> tuple[np.ndarray, bool]:
    """Logistic recalibration of logit(p) on past forecasts, shrunk toward the identity by n / (n + 20)."""
    if len(H) < 15 or H["y"].sum() < 3 or (1 - H["y"]).sum() < 3:
        return x, False
    from sklearn.linear_model import LogisticRegression
    z = lg(H[col]).reshape(-1, 1)
    m = LogisticRegression(C=1.0, max_iter=1000).fit(z, H["y"])
    a, b = float(m.intercept_[0]), float(m.coef_[0, 0])
    w = len(H) / (len(H) + SHRINK_N)
    a, b = a * w, 1 + (b - 1) * w
    return 1 / (1 + np.exp(-(a + b * lg(x)))), True


def stack(H: pd.DataFrame, te: pd.DataFrame, ph_col: str) -> tuple[np.ndarray, bool]:
    """Learned LightGBM combination of the two components (monotone increasing in both), K as input."""
    if len(H) < 20 or H["y"].sum() < 5 or (1 - H["y"]).sum() < 5:
        return (te[ph_col] * te["pp"]).to_numpy(), False
    from lightgbm import LGBMClassifier
    f = lambda D: pd.DataFrame({"lh": lg(D[ph_col]), "lp": lg(D["pp"]), "k": D["k"].astype(float)})  # noqa: E731
    m = LGBMClassifier(**STK_GB, monotone_constraints=[1, 1, 0]).fit(f(H), H["y"])
    return m.predict_proba(f(te))[:, 1], True


def stage2(C: pd.DataFrame, Ps: dict, d, prefix: str, ph_col: str, out: dict, arms: tuple):
    for k in KS:
        P = out[k]
        for a in arms:
            P[prefix + a] = np.nan
        for t in sorted(P["t"].unique()):
            m = P["t"] == t
            te = C[(C["t"] == t) & (C["k"] == k)].set_index("province_code").loc[P.loc[m, "province_code"]].reset_index()
            base = (te[ph_col] * te["pp"]).to_numpy()
            H = past(C, d, int(t)).assign(p=lambda f: f[ph_col] * f["pp"])
            if "" in arms:
                P.loc[m, prefix] = base
            if "-CAL" in arms:
                P.loc[m, prefix + "-CAL"], cf = platt(H, "p", base)
                if prefix == "M-U94-OOS":
                    P.loc[m, "cal_fitted"] = cf
            if "-STK" in arms:
                P.loc[m, prefix + "-STK"], sf = stack(H, te, ph_col)
                P.loc[m, "stk_fitted"] = sf
            if prefix == "M-U94":
                P.loc[m, "ph"], P.loc[m, "pp"], P.loc[m, "ph_oos"] = te["ph"].to_numpy(), te["pp"].to_numpy(), te["ph_oos"].to_numpy()
    return out


SELECTABLE = ["M-U94", "M-U94-CAL", "M-U94-STK", "M-U94-OOS", "M-U94-OOS-CAL"]


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E94 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    _, Ps = U.load_tables()
    T = add_news_x(B.tables())
    C = components(d, T, news=True)
    C0 = components(d, T, news=False)
    CX = components(d, T, news=True, extra=NEWS_X)
    C.to_csv(o / "components.csv", index=False)
    out = {k: Ps[k].copy() for k in KS}
    out = stage2(C, Ps, d, "M-U94", "ph", out, ("", "-CAL", "-STK"))
    out = stage2(C, Ps, d, "M-U94-OOS", "ph_oos", out, ("", "-CAL"))
    out = stage2(C0, Ps, d, "M-U94-OOS-NONEWS", "ph_oos", out, ("", "-CAL"))
    out = stage2(CX, Ps, d, "M-U94-OOS-NEWSX", "ph_oos", out, ("", "-CAL"))
    ablate = ["M-U94-OOS-NONEWS", "M-U94-OOS-NONEWS-CAL", "M-U94-OOS-NEWSX", "M-U94-OOS-NEWSX-CAL"]
    summ = {"stamp": stamp, "protocol_sha256": (E94 / "PROTOCOL.sha256").read_text().split()[0], "per_k": {}, "baselines": {}}
    for k in KS:
        P = out[k]
        P93 = pd.read_csv(E93_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["M-E93-LINDIR"] = P93["M-U93-LINDIR"].to_numpy()
        P["M-E92-DEC-S"] = P93["M-E92-DEC-S"].to_numpy()
        if k == 1:
            summ["e93_reproduced_max_abs_diff"] = float(np.nanmax(np.abs(P["M-U94"] - P["M-E93-LINDIR"])))
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        arms = SELECTABLE + ablate + ["M-E93-LINDIR", "M-E92-DEC-S", "S-COV"]
        summ["per_k"][k], summ["baselines"][k] = U.evaluate_k(P, arms)
        summ["per_k"][k]["_fitted"] = {c: float(P[c].mean()) for c in ("cal_fitted", "stk_fitted")}
    sel = {a: float(np.mean([summ["per_k"][k][a]["selection_block_brier"] for k in (1, 2, 3)])) for a in SELECTABLE}
    chosen = min(sel, key=sel.get)
    summ["selection_mean_brier"], summ["selected"] = sel, chosen
    summ["K"] = {a: U.k_validated(summ["per_k"], a) for a in SELECTABLE + ablate}
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("E93 reproduced (max |diff|, K=1):", summ["e93_reproduced_max_abs_diff"])
    print("selection (mean Brier K=1..3, targets <= 2024-Q4):", {a: round(v, 4) for a, v in sel.items()}, "->", chosen)
    for k in KS:
        print(f"K={k} fitted:", {c: round(v, 2) for c, v in summ["per_k"][k]["_fitted"].items()})
        for a in SELECTABLE + ablate + ["M-E93-LINDIR", "M-E92-DEC-S", "S-COV"]:
            r = summ["per_k"][k][a]
            m, g, ps = r["metrics"], r["generalization"], r["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r["tests"].items()}
            print(f"  {a:22s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} P/R={m['precision'] or 0:.2f}/"
                  f"{m['recall_HIGH'] or 0:.2f} TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} brier={m['brier']:.3f} "
                  f"citl={m.get('citl', 0):+.3f} PASS={ps['PASS']} {[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} "
                  f"holm={th} W/L={g['wins']}/{g['losses']} e/l={g['early_acc']:.2f}/{g['late_acc']:.2f}", flush=True)
    print("K:", {a: v["K"] for a, v in summ["K"].items()})
    print(o)
