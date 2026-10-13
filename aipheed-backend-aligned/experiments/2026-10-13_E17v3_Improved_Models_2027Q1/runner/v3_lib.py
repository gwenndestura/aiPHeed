"""E17 v3 library: horizon-h information sets, frozen candidates for H, F, D, and the frozen selection rule.
Information set for target T at horizon h = observations of quarters <= T - h. No file is opened here."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

ALPHA = 1.0
PHI = 0.8
MIN_TRAIN = 6
FIRST_Q = "2021-Q1"
H_SELECTABLE = ["C2_mean", "C3_drift", "C4_ridge_ar1", "C5_ridge_ar2", "C6_damped_theilsen", "C7_ridge_indicators"]
H_DIAG = ["C7a_ridge_H_F5", "C7b_ridge_H_U"]
H_ALL = ["C1_carry_forward"] + H_SELECTABLE + H_DIAG
F_BASE, F_FIT = ["F1_carry_forward", "F2_pooled_mean", "F3_province_mean"], ["F4_ridge_ar"]
D_BASE, D_FIT = ["D1_carry_forward", "D2_zero", "D3_province_mean"], ["D4_ridge_shrink", "D5_ridge_D_pmean"]


def qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float = ALPHA) -> dict:
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    b = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return {"mu": mu.tolist(), "sd": sd.tolist(), "beta_std": b.tolist(), "intercept": float(y.mean()), "n": int(len(y))}


def ridge_predict(m: dict, X: np.ndarray) -> np.ndarray:
    return m["intercept"] + ((X - np.array(m["mu"])) / np.array(m["sd"])) @ np.array(m["beta_std"])


def theil_sen(x: np.ndarray, y: np.ndarray) -> float:
    s = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    return float(np.median(s))


# ------------------------------------------------------------------------------------------- H
def h_quarterly(rounds: pd.DataFrame) -> pd.Series:
    """Quarterly H = mean of all eligible rounds of the quarter, indexed by quarter key."""
    s = rounds.groupby("quarter")["H"].mean()
    return pd.Series(s.values, index=[qk(q) for q in s.index]).sort_index()


def h_features(hs: pd.Series, f5: pd.Series, U: pd.Series, cutoff: int, kind: str):
    """Feature vector from the information set <= cutoff. Returns None if unavailable."""
    obs = hs[hs.index <= cutoff]
    if obs.empty:
        return None
    L, hL = obs.index[-1], obs.iloc[-1]
    if kind == "ar1":
        return [hL]
    if kind == "ar2":
        return None if len(obs) < 2 else [hL, obs.iloc[-2]]
    f, u = f5.get(cutoff, np.nan), U.get(cutoff, np.nan)
    if kind == "ind":
        return None if (f != f or u != u) else [hL, f, u]
    if kind == "hf":
        return None if f != f else [hL, f]
    if kind == "hu":
        return None if u != u else [hL, u]
    raise ValueError(kind)


def h_candidates(hs: pd.Series, f5: pd.Series, U: pd.Series, T: int, h: int) -> tuple[dict, dict]:
    """All H candidates for target T at horizon h, from observations <= T - h only."""
    cut = T - h
    obs = hs[hs.index <= cut]
    out, meta = {}, {"info_cutoff": qs(cut)}
    if obs.empty:
        return out, meta
    L, hL = obs.index[-1], float(obs.iloc[-1])
    meta.update({"latest_observed": qs(L), "steps_to_target": int(T - L)})
    out["C1_carry_forward"] = hL
    out["C2_mean"] = float(obs.mean())
    if len(obs) >= 2:
        g = (hL - obs.iloc[0]) / (L - obs.index[0])
        out["C3_drift"] = float(hL + g * (T - L))
    last = obs.iloc[-8:]
    if len(last) >= 4:
        s = theil_sen(last.index.to_numpy(float), last.to_numpy(float))
        out["C6_damped_theilsen"] = float(hL + s * sum(PHI ** i for i in range(1, T - L + 1)))
    for name, kind in [("C4_ridge_ar1", "ar1"), ("C5_ridge_ar2", "ar2"), ("C7_ridge_indicators", "ind"),
                       ("C7a_ridge_H_F5", "hf"), ("C7b_ridge_H_U", "hu")]:
        X, y = [], []
        for q in hs.index[hs.index <= cut]:
            x = h_features(hs, f5, U, q - h, kind)
            if x is not None:
                X.append(x)
                y.append(hs[q])
        xT = h_features(hs, f5, U, cut, kind)
        if len(y) >= MIN_TRAIN and xT is not None:
            m = ridge_fit(np.array(X, float), np.array(y, float))
            out[name] = float(ridge_predict(m, np.array([xT], float))[0])
            meta[f"{name}_n_train"] = len(y)
            meta[f"{name}_model"] = m
    return out, meta


# ------------------------------------------------------------------------------------------- F, D
def fd_candidates(comp: pd.DataFrame, var: str, T: int, h: int) -> tuple[pd.DataFrame, dict]:
    """Per-province candidates for F or D at target T, horizon h (observations <= T - h)."""
    c = comp.assign(k=comp["quarter"].map(qk))
    cut = T - h
    info = c[c["k"] <= cut]
    cur = info[info["k"] == cut].set_index("province_code")[var]
    if len(cur) < 5 or cur.isna().any():
        return pd.DataFrame(), {}
    prov = sorted(cur.index)
    pm = info.groupby("province_code")[var].mean()
    rows = {p: {} for p in prov}
    base = ["F1_carry_forward", "F2_pooled_mean", "F3_province_mean"] if var == "F" else \
        ["D1_carry_forward", "D2_zero", "D3_province_mean"]
    for p in prov:
        rows[p][base[0]] = float(cur[p])
        rows[p][base[1]] = float(info[var].mean()) if var == "F" else 0.0
        rows[p][base[2]] = float(pm[p])
    meta = {}
    X1, X2, Y, Q = [], [], [], []
    for q in range(qk(FIRST_Q) + h, cut + 1):
        xs = c[c["k"] == q - h].set_index("province_code")[var]
        ys = c[c["k"] == q].set_index("province_code")[var]
        pmq = c[c["k"] <= q - h].groupby("province_code")[var].mean()
        for p in prov:
            if p in xs.index and p in ys.index:
                X1.append([xs[p]]); X2.append([xs[p], pmq[p]]); Y.append(ys[p]); Q.append(q)
    if len(set(Q)) >= MIN_TRAIN:
        if var == "F":
            m = ridge_fit(np.array(X1), np.array(Y))
            pr = ridge_predict(m, np.array([[cur[p]] for p in prov]))
            for i, p in enumerate(prov):
                rows[p]["F4_ridge_ar"] = float(pr[i])
            meta["F4_ridge_ar_model"] = m
        else:
            m1 = ridge_fit(np.array(X1), np.array(Y))
            m2 = ridge_fit(np.array(X2), np.array(Y))
            p1 = ridge_predict(m1, np.array([[cur[p]] for p in prov]))
            p2 = ridge_predict(m2, np.array([[cur[p], pm[p]] for p in prov]))
            for i, p in enumerate(prov):
                rows[p]["D4_ridge_shrink"] = float(p1[i])
                rows[p]["D5_ridge_D_pmean"] = float(p2[i])
            meta["D4_ridge_shrink_model"], meta["D5_ridge_D_pmean_model"] = m1, m2
        meta["n_train_quarters"] = len(set(Q))
    df = pd.DataFrame.from_dict(rows, orient="index").rename_axis("province_code").reset_index()
    return df, meta


# ------------------------------------------------------------------------------------------- frozen selection rule
def rule_check(err_c: pd.Series, err_base: pd.Series) -> dict:
    """err_*: absolute error per origin (index = origin quarter key, time ordered). Conditions 1-4 of the frozen rule."""
    o = sorted(err_c.index)
    a, b = err_c.loc[o], err_base.loc[o]
    n = len(o)
    half = o[n - math.ceil(n / 2):]
    loo = [bool(a.drop(q).mean() < b.drop(q).mean()) for q in o] if n > 1 else [False]
    c1 = bool(a.mean() < b.mean())
    c2 = bool((a < b).sum() > n / 2)
    c3 = bool(a.loc[half].mean() <= b.loc[half].mean())
    c4 = all(loo)
    return {"n_origins": n, "MAE": float(a.mean()), "MAE_base": float(b.mean()), "wins": int((a < b).sum()),
            "later_half": [qs(q) for q in half], "later_half_MAE": float(a.loc[half].mean()),
            "later_half_MAE_base": float(b.loc[half].mean()), "loo_all_better": c4,
            "cond1": c1, "cond2": c2, "cond3": c3, "cond4": c4, "cond5_fixed_config": True,
            "passes": bool(c1 and c2 and c3 and c4)}
