"""E18 library (no file I/O): data assembly, classification arms (incl. structural candidates N1-N4), metrics,
selection rule, extra continuous candidates C8/C9."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import e17v3_frozen_lib as V

THR = 14.6
FIRST = "2021-Q1"
MIN_TRAIN_Q = 8
NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]
SENT = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]
PSA = ["food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "rice_price_regular",
       "rice_price_regular_lag1", "rice_price_regular_accel", "unemployment_rate", "unemployment_rate_lag1",
       "unemployment_rate_accel", "food_minus_headline_yoy", "food_minus_headline_yoy_lag1",
       "food_minus_headline_yoy_accel", "headline_cpi", "commodity_fruit_veg", "commodity_leafy_veg",
       "commodity_livestock", "commodity_poultry", "commodity_rootcrops", "cpi_dev"]
N4_FEATS = ["H_last", "D_c", "F_c", "F5_c", "FSSI", "FSSI_lag1", "cpi_dev", "unemployment_rate"]
CH1 = ["B2_psa_lr", "B3_nlp_sentiment_lr", "B4_lr_all"]
NEW = ["N1_structural_rule", "N2_structural_shrink", "N3_structural_lr", "N4_lgbm_constrained_tuned"]
NO_NEWS = ["P_persistence", "MAJ_majority", "N1_structural_rule", "N2_structural_shrink", "N3_structural_lr"]
ARMS = ["P_persistence", "MAJ_majority"] + CH1 + ["S5_lgbm_gov_only", "S6_lgbm_nlp_only", "M_governing_lgbm"] + NEW
qk, qs = V.qk, V.qs


# ------------------------------------------------------------------ data
def extend_components(comp: pd.DataFrame, cpi26: pd.DataFrame, sws26: pd.DataFrame) -> pd.DataFrame:
    """Append 2026-Q1/Q2: F = mean of monthly YoY; D = F - five-province mean (only if all five); S1 = H + 2D."""
    c = cpi26.copy()
    c["quarter"] = c["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    F = c.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index(name="F")
    H = sws26.drop_duplicates("quarter").set_index("quarter")["pct_total_hunger"]
    rows = []
    for q, g in F.groupby("quarter"):
        complete = len(g) == 5 and g["F"].notna().all()
        m5 = g["F"].mean() if complete else np.nan
        for r in g.itertuples():
            D = r.F - m5 if complete else np.nan
            h = float(H.get(q, np.nan))
            rows.append({"province_code": r.province_code, "quarter": q, "F": r.F, "mean5": m5, "D": D, "H": h,
                         "S1": h + 2 * D if (h == h and D == D) else np.nan})
    new = pd.DataFrame(rows)
    cols = ["province_code", "quarter", "F", "mean5", "D", "H", "S1"]
    return pd.concat([comp[cols], new[cols]], ignore_index=True)


def h_series(rounds: pd.DataFrame, sws26: pd.DataFrame, production_only: bool) -> pd.Series:
    r = rounds[rounds["definition_A"]] if production_only else rounds
    s = r.groupby("quarter")["H"].mean()
    s26 = sws26.drop_duplicates("quarter").set_index("quarter")["pct_total_hunger"]
    s = pd.concat([s, s26])
    return pd.Series(s.values, index=[qk(q) for q in s.index]).sort_index()


def feature_frame(ff: pd.DataFrame, comp_x: pd.DataFrame, hprod: pd.Series, gov_cols: list[str]) -> pd.DataFrame:
    """Row per (province, cutoff c): news+gov of row c (2021-2025 only), H_last <= c, D/F/F5 of c."""
    base = comp_x[["province_code", "quarter", "F", "mean5", "D"]].rename(columns={"F": "F_c", "mean5": "F5_c", "D": "D_c"})
    X = base.merge(ff[["province_code", "quarter"] + NLP + gov_cols], on=["province_code", "quarter"], how="left")
    X["c"] = X["quarter"].map(qk)
    X["H_last"] = X["c"].map(lambda c: float(hprod[hprod.index <= c].iloc[-1]) if (hprod.index <= c).any() else np.nan)
    X["has_news"] = X["FSSI"].notna()
    return X


def labels(comp_x: pd.DataFrame) -> pd.DataFrame:
    l = comp_x[comp_x["S1"].notna()][["province_code", "quarter", "S1"]].copy()
    l["y"] = (l["S1"] > THR).astype(int)
    l["q"] = l["quarter"].map(qk)
    return l


# ------------------------------------------------------------------ models
def _const(n, p):
    return np.full(n, float(p))


def lr(Xtr, y, Xte):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if y.mean() in (0.0, 1.0):
        return _const(len(Xte), y.mean())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
        return m.fit(Xtr, y).predict_proba(Xte)[:, 1]


def lgbm(Xtr, y, Xte, **kw):
    from lightgbm import LGBMClassifier
    p = y.mean()
    if p in (0.0, 1.0):
        return _const(len(Xte), p), None
    params = dict(objective="binary", verbosity=-1, random_state=42, scale_pos_weight=(1 - p) / p)
    params.update(kw)
    m = LGBMClassifier(**params).fit(Xtr, y)
    return m.predict_proba(Xte)[:, 1], m


N4_GRID = [dict(min_child_samples=a, n_estimators=b) for a in (5, 10) for b in (50, 150)]
N4_FIXED = dict(max_depth=2, num_leaves=3, learning_rate=0.05)


def n4_tune(tr: pd.DataFrame) -> dict:
    qsorted = sorted(tr["q_target"].unique())
    folds = qsorted[-3:]
    best, best_ll = N4_GRID[0], np.inf
    for g in N4_GRID:
        lls = []
        for qf in folds:
            a, b = tr[tr["q_target"] < qf], tr[tr["q_target"] == qf]
            if a.empty or b.empty:
                continue
            p, _ = lgbm(a[N4_FEATS], a["y"].to_numpy(), b[N4_FEATS], **N4_FIXED, **g)
            p = np.clip(p, 1e-3, 1 - 1e-3)
            yb = b["y"].to_numpy()
            lls.append(float(-np.mean(yb * np.log(p) + (1 - yb) * np.log(1 - p))))
        ll = np.mean(lls) if lls else np.inf
        if ll < best_ll - 1e-12:
            best, best_ll = g, ll
    return {**N4_FIXED, **best, "inner_logloss": best_ll}


def ridge_shrink_D(comp_x: pd.DataFrame, c: int, h: int, Dc: np.ndarray) -> np.ndarray:
    k = comp_x.assign(k=comp_x["quarter"].map(qk))
    X, Y = [], []
    for q in range(qk(FIRST) + h, c + 1):
        a = k[k["k"] == q - h].set_index("province_code")["D"]
        b = k[k["k"] == q].set_index("province_code")["D"]
        for p in a.index:
            if p in b.index and a[p] == a[p] and b[p] == b[p]:
                X.append([a[p]]); Y.append(b[p])
    m = V.ridge_fit(np.array(X), np.array(Y))
    return V.ridge_predict(m, Dc[:, None])


def fold(X, L, comp_x, T: int, h: int, gov_cols: list[str]):
    """All arms for target quarter T at horizon h. Returns (test frame, scores dict, meta) or None."""
    c = T - h
    test = X[X["c"] == c].sort_values("province_code").reset_index(drop=True)
    if len(test) != 5:
        return None
    lt = L.assign(c_feat=L["q"] - h)
    tr = X.merge(lt[["province_code", "c_feat", "y", "q"]].rename(columns={"c_feat": "c", "q": "q_target"}),
                 on=["province_code", "c"], how="inner")
    tr = tr[(tr["q_target"] <= c) & (tr["c"] >= qk(FIRST))]
    ntq = tr["q_target"].nunique()
    if ntq < MIN_TRAIN_Q:
        return None
    y = tr["y"].to_numpy()
    allf = NLP + gov_cols + ["H_last"]
    news_ok = bool(test["has_news"].all()) and bool(tr["has_news"].all())
    s, meta = {}, {"n_train_quarters": int(ntq), "n_train_rows": int(len(tr)), "train_high_share": float(y.mean()),
                   "news_available": news_ok}
    lastq = L[L["q"] <= c].groupby("province_code")["q"].max()
    lab = L.set_index(["province_code", "q"])["y"]
    s["P_persistence"] = np.array([float(lab[(p, lastq[p])]) for p in test["province_code"]])
    s["MAJ_majority"] = _const(5, 1.0 if y.mean() >= 0.5 else 0.0)
    s["N1_structural_rule"] = (test["H_last"] + 2 * test["D_c"] > THR).astype(float).to_numpy()
    dh = ridge_shrink_D(comp_x, c, h, test["D_c"].to_numpy(float))
    s["N2_structural_shrink"] = (test["H_last"].to_numpy() + 2 * dh > THR).astype(float)
    s["N3_structural_lr"] = lr(tr[["H_last", "D_c"]], y, test[["H_last", "D_c"]])
    if news_ok:
        s["B2_psa_lr"] = lr(tr[PSA], y, test[PSA])
        s["B3_nlp_sentiment_lr"] = lr(tr[SENT], y, test[SENT])
        s["B4_lr_all"] = lr(tr[allf], y, test[allf])
        s["S5_lgbm_gov_only"], _ = lgbm(tr[gov_cols], y, test[gov_cols])
        s["S6_lgbm_nlp_only"], _ = lgbm(tr[NLP], y, test[NLP])
        s["M_governing_lgbm"], mM = lgbm(tr[allf], y, test[allf])
        cfg = n4_tune(tr)
        s["N4_lgbm_constrained_tuned"], mN = lgbm(tr[N4_FEATS], y, test[N4_FEATS],
                                                  **{k: v for k, v in cfg.items() if k != "inner_logloss"})
        meta["N4_config"] = cfg
        meta["shap"] = {}
        for nm, mdl, cols in (("M_governing_lgbm", mM, allf), ("N4_lgbm_constrained_tuned", mN, N4_FEATS)):
            if mdl is not None:
                contrib = mdl.predict(test[cols], pred_contrib=True)[:, :-1]
                meta["shap"][nm] = dict(zip(cols, np.abs(contrib).mean(0).tolist()))
    return test, s, meta


# ------------------------------------------------------------------ metrics
def cls_metrics(y, p, score=None):
    y, p = np.asarray(y, int), np.asarray(p, int)
    tp, tn = int(((y == 1) & (p == 1)).sum()), int(((y == 0) & (p == 0)).sum())
    fp, fn = int(((y == 0) & (p == 1)).sum()), int(((y == 1) & (p == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    rec0 = tn / (tn + fp) if tn + fp else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else (0.0 if prec is not None and rec is not None else None)
    ba = (rec + rec0) / 2 if rec is not None and rec0 is not None else None
    out = {"n": int(len(y)), "HIGH": int(y.sum()), "LOW": int((1 - y).sum()), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
           "accuracy": float((y == p).mean()), "precision_HIGH": prec, "recall_HIGH": rec, "F1_HIGH": f1,
           "recall_LOW": rec0, "balanced_accuracy": ba, "ROC_AUC": None, "PR_AUC": None}
    if score is not None and y.sum() and (1 - y).sum() and len(np.unique(score)) > 2:
        s = np.asarray(score, float)
        pos, neg = s[y == 1], s[y == 0]
        out["ROC_AUC"] = float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                               / (len(pos) * len(neg)))
        o = np.argsort(-s, kind="mergesort"); ys = y[o]
        out["PR_AUC"] = float(sum(ys[i] * ys[:i + 1].sum() / (i + 1) for i in range(len(ys))) / y.sum())
    return out


def select(per_q: pd.DataFrame, overall: dict, cand: str) -> dict:
    """Frozen classification rule vs persistence (and Chapter I baselines for condition 1)."""
    m, P = overall[cand], overall["P_persistence"]
    c1 = all(m["accuracy"] >= overall[b]["accuracy"] for b in ["P_persistence"] + CH1 if b in overall) and \
        all((overall[b]["balanced_accuracy"] is None) or (m["balanced_accuracy"] is not None and
                                                          m["balanced_accuracy"] >= overall[b]["balanced_accuracy"])
            for b in ["P_persistence"] + CH1 if b in overall)
    a, b = per_q[cand], per_q["P_persistence"]
    c2 = bool((a > b).sum() > (a < b).sum())
    qsrt = sorted(per_q.index)
    half = qsrt[len(qsrt) // 2:]
    c3 = bool(a.loc[half].mean() >= b.loc[half].mean())
    n = per_q["n"] if "n" in per_q else None
    c4 = all(a.drop(q).mean() >= b.drop(q).mean() for q in qsrt) if len(qsrt) > 1 else False
    return {"cond1": bool(c1), "cond2": c2, "cond3": c3, "cond4": bool(c4), "passes": bool(c1 and c2 and c3 and c4)}


# ------------------------------------------------------------------ extra continuous candidates
def c8_recent_mean(hs, T, h):
    o = hs[hs.index <= T - h]
    return float(o.iloc[-4:].mean()) if len(o) else np.nan


def c9_ewma(hs, T, h, alpha=0.5):
    o = hs[hs.index <= T - h]
    if o.empty:
        return np.nan
    v = o.iloc[0]
    for x in o.iloc[1:]:
        v = alpha * x + (1 - alpha) * v
    return float(v)
