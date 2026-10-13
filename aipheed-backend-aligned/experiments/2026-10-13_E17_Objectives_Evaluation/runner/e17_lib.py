"""E17 library: timing-valid frame, label publication rule, fold construction, arms and metrics.
No file is opened here."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]
SENTIMENT = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]
PSA = ["food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "rice_price_regular",
       "rice_price_regular_lag1", "rice_price_regular_accel", "unemployment_rate", "unemployment_rate_lag1",
       "unemployment_rate_accel", "food_minus_headline_yoy", "food_minus_headline_yoy_lag1",
       "food_minus_headline_yoy_accel", "headline_cpi", "commodity_fruit_veg", "commodity_leafy_veg",
       "commodity_livestock", "commodity_poultry", "commodity_rootcrops", "cpi_dev"]
FIRST_Q = "2021-Q1"
LAST_Q = "2025-Q4"
MIN_TRAIN_QUARTERS = 8
SEED = 20261013
N_BOOT = 10_000
ARMS = ["M_lgbm", "B1_persistence", "B2_psa_lr", "B3_nlp_sentiment_lr", "B4_lr_all", "REF_majority"]


def qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def qstart(q: str) -> pd.Timestamp:
    y, n = q.split("-Q")
    return pd.Timestamp(int(y), 3 * (int(n) - 1) + 1, 1)


def gov_columns(all_features: list[str], include_poverty: bool) -> list[str]:
    g = [c for c in all_features if c not in NLP and c != "poverty_incidence"]
    return g + (["poverty_incidence"] if include_poverty else [])


# ---------------------------------------------------------------------------------- inputs at origin
def sws_at_origin(rounds: pd.DataFrame, origin: pd.Timestamp, production_only: bool = True) -> float:
    r = rounds[rounds["definition_A"]] if production_only else rounds
    pub = r[r["published"] < origin]
    if pub.empty:
        return np.nan
    lastq = max(pub["quarter"], key=qk)
    return float(pub.loc[pub["quarter"] == lastq, "H"].mean())


def build_frame(f: pd.DataFrame, rounds: pd.DataFrame, features: list[str], include_poverty: bool = False) -> pd.DataFrame:
    """One row per (province, feature quarter t): news of t, government of t-1, SWS before start of t+1.
    `features` = the 45 candidates + cpi_dev. Poverty (row t, as stored) only when include_poverty."""
    f = f.copy()
    f["t"] = f["quarter"].map(qk)
    gov = gov_columns(features, include_poverty=False)
    news = f[["province_code", "t"] + NLP]
    g = f[["province_code", "t"] + gov].copy()
    g["t"] = g["t"] + 1                                   # value of t-1 placed on row t
    X = news.merge(g, on=["province_code", "t"], how="left")
    if include_poverty:
        X = X.merge(f[["province_code", "t", "poverty_incidence"]], on=["province_code", "t"], how="left")
    X["quarter"] = X["t"].map(qs)
    X["sws_hunger"] = X["quarter"].map(lambda q: sws_at_origin(rounds, qstart(qs(qk(q) + 1))))
    return X.sort_values(["t", "province_code"]).reset_index(drop=True)


def label_table(comp: pd.DataFrame, thr: float) -> pd.DataFrame:
    lab = comp[comp["S1"].notna()][["province_code", "quarter", "S1"]].copy()
    lab["y"] = (lab["S1"] > thr).astype(int)
    lab["tq"] = lab["quarter"].map(qk)
    return lab


def label_published(rounds: pd.DataFrame, q: str, t: int) -> bool:
    """Label of quarter q is known at origin start(t+1): q <= t-1 and all production rounds of q published before."""
    if qk(q) > t - 1:
        return False
    r = rounds[(rounds["quarter"] == q) & (rounds["definition_A"])]
    return bool(len(r)) and bool((r["published"] < qstart(qs(t + 1))).all())


def fold_data(X: pd.DataFrame, lab: pd.DataFrame, rounds: pd.DataFrame, k: int, t: int, rule: str = "strict"):
    """Training and test rows for lead time k at feature quarter t (origin = start of t+1)."""
    pairs = X.merge(lab.assign(t=lab["tq"] - k)[["province_code", "t", "y", "quarter"]]
                    .rename(columns={"quarter": "target_quarter"}), on=["province_code", "t"], how="inner")
    test = pairs[pairs["t"] == t]
    if rule == "strict":
        ok = {q: label_published(rounds, q, t) for q in pairs["target_quarter"].unique()}
        train = pairs[(pairs["t"] >= qk(FIRST_Q)) & pairs["target_quarter"].map(ok)]
    else:                                                  # R0: the implementation's recorded rule
        train = pairs[(pairs["t"] >= qk(FIRST_Q)) & (pairs["t"] < t)]
    return train, test


def persistence(lab: pd.DataFrame, rounds: pd.DataFrame, t: int, provinces) -> dict:
    out = {}
    for pc in provinces:
        L = lab[lab["province_code"] == pc].sort_values("tq")
        known = [r for r in L.itertuples() if label_published(rounds, r.quarter, t)]
        out[pc] = known[-1].y if known else np.nan
    return out


# ---------------------------------------------------------------------------------- arms
def _const(n, c):
    return np.full(n, float(c))


def fit_lgbm(Xtr, ytr, Xte):
    from lightgbm import LGBMClassifier
    p = ytr.mean()
    if p in (0.0, 1.0):
        return _const(len(Xte), p), True
    m = LGBMClassifier(objective="binary", verbosity=-1, random_state=42, scale_pos_weight=(1 - p) / p)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1], False


def fit_lr(Xtr, ytr, Xte):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    p = ytr.mean()
    if p in (0.0, 1.0):
        return _const(len(Xte), p), True
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
        m.fit(Xtr, ytr)
        return m.predict_proba(Xte)[:, 1], False


def predict_fold(train, test, cols, lab, rounds, t):
    ytr = train["y"].to_numpy(int)
    te = test.sort_values("province_code")
    res = {}
    res["M_lgbm"], s1 = fit_lgbm(train[cols], ytr, te[cols])
    res["B2_psa_lr"], s2 = fit_lr(train[PSA], ytr, te[PSA])
    res["B3_nlp_sentiment_lr"], s3 = fit_lr(train[SENTIMENT], ytr, te[SENTIMENT])
    res["B4_lr_all"], s4 = fit_lr(train[cols], ytr, te[cols])
    pers = persistence(lab, rounds, t, te["province_code"])
    res["B1_persistence"] = te["province_code"].map(pers).to_numpy(float)
    maj = 1.0 if ytr.mean() >= 0.5 else 0.0
    res["REF_majority"] = _const(len(te), maj)
    meta = {"single_class_training": bool(s1), "n_train_rows": int(len(train)),
            "n_train_quarters": int(train["target_quarter"].nunique()), "train_high_share": float(ytr.mean())}
    return te, res, meta


# ---------------------------------------------------------------------------------- metrics
def cls_metrics(y, p, score=None) -> dict:
    y = np.asarray(y, int)
    p = np.asarray(p, int)
    tp, tn = int(((y == 1) & (p == 1)).sum()), int(((y == 0) & (p == 0)).sum())
    fp, fn = int(((y == 0) & (p == 1)).sum()), int(((y == 1) & (p == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    rec0 = tn / (tn + fp) if tn + fp else None
    prec0 = tn / (tn + fn) if tn + fn else None
    f1 = (2 * prec * rec / (prec + rec)) if prec and rec else (0.0 if (prec is not None and rec is not None) else None)
    f10 = (2 * prec0 * rec0 / (prec0 + rec0)) if prec0 and rec0 else (0.0 if (prec0 is not None and rec0 is not None) else None)
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    f1w = None if f1 is None and f10 is None else ((f1 or 0) * n1 + (f10 or 0) * n0) / len(y)
    ba = (rec + rec0) / 2 if rec is not None and rec0 is not None else None
    out = {"n": int(len(y)), "HIGH": n1, "LOW": n0, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
           "accuracy": float((y == p).mean()), "precision_HIGH": prec, "recall_HIGH": rec, "F1_HIGH": f1,
           "F1_weighted": f1w, "recall_LOW": rec0, "balanced_accuracy": ba, "ROC_AUC": None, "PR_AUC": None}
    if score is not None and n1 and n0:
        s = np.asarray(score, float)
        pos, neg = s[y == 1], s[y == 0]
        out["ROC_AUC"] = float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                               / (len(pos) * len(neg)))
        order = np.argsort(-s, kind="mergesort")
        ys, ss = y[order], s[order]
        ap, tpc, i = 0.0, 0, 0
        while i < len(ys):
            j = i
            while j < len(ys) and ss[j] == ss[i]:
                j += 1
            add = ys[i:j].sum()
            if add:
                ap += (add / n1) * ((tpc + add) / j)
            tpc += add
            i = j
        out["PR_AUC"] = float(ap)
        out["score_distinct_values"] = int(len(np.unique(s)))
    return out


def boot_acc_diff(correct_a: np.ndarray, correct_b: np.ndarray, quarters: np.ndarray,
                  n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Quarter-cluster bootstrap of accuracy(a) - accuracy(b)."""
    qu = np.unique(quarters)
    ca = np.array([correct_a[quarters == q].sum() for q in qu], float)
    cb = np.array([correct_b[quarters == q].sum() for q in qu], float)
    nq = np.array([(quarters == q).sum() for q in qu], float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(qu), size=(n_boot, len(qu)))
    d = (ca[idx].sum(1) - cb[idx].sum(1)) / nq[idx].sum(1)
    return {"diff": float((ca.sum() - cb.sum()) / nq.sum()), "ci_low": float(np.quantile(d, 0.025)),
            "ci_high": float(np.quantile(d, 0.975)), "quarters": int(len(qu))}
