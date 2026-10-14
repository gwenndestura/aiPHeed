"""E23 library (no file I/O). Frozen with E23_PROTOCOL.md; see that file for every rule used here.

Timing (strict, reused from E17): a row for feature quarter t is the information at forecast origin
O(t) = 00:00 PHT on the first day of quarter t+1:
    news features of quarter t (articles published in t), government features of quarter t-1,
    SWS hunger = mean of the production rounds of the latest fieldwork quarter published before O(t).
Target = composite label of quarter t+k (lead k). A training pair (t', t'+j) is usable at origin O(t)
only if its label was published before O(t) (CPI: label quarter <= t-1; SWS: every production round of
the label quarter published before O(t)).
"""
from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd

NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]
PSA = ["food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "rice_price_regular",
       "rice_price_regular_lag1", "rice_price_regular_accel", "unemployment_rate", "unemployment_rate_lag1",
       "unemployment_rate_accel", "food_minus_headline_yoy", "food_minus_headline_yoy_lag1",
       "food_minus_headline_yoy_accel", "headline_cpi", "commodity_fruit_veg", "commodity_leafy_veg",
       "commodity_livestock", "commodity_poultry", "commodity_rootcrops", "cpi_dev"]
FIRST_Q = "2021-Q1"
LAST_FEATURE_Q = "2025-Q4"          # news + government features exist (eligible) through 2025-Q4
LEADS = list(range(1, 9))           # Objective 2-V: 1..8 quarters
MIN_TRAIN_QUARTERS = 8
MIN_ORIGINS, MIN_PER_CLASS = 8, 5   # evaluability
FIXED_THRESHOLD = 14.6              # implemented label threshold (sensitivity only)
SEED = 20261013
N_BOOT = 4000
PERM_REPEATS = 200
TOP_K_STRONGEST = 5

PROPOSED = "PROPOSED_lgbm_combined"
BASELINES = ["B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only",
             "B5_lgbm_gov_only", "B6_lgbm_nlp_only"]
SUPPLEMENTARY = ["S_lr_psa_only"]   # Objective 4-II literal reading (PSA series only); descriptive
OBJ4_MAP = {"I Naive persistence": "B1_naive_persistence", "II PSA-only indicator": "B3_lr_gov_only",
            "III NLP-only sentiment": "B4_lr_nlp_only", "IV Logistic regression": "B2_lr_combined"}

# Predeclared LightGBM search space (identical for PROPOSED, B5, B6): 2 x 4 x 2 = 16 configurations.
LGBM_FIXED = dict(objective="binary", learning_rate=0.05, max_depth=3, reg_lambda=1.0, colsample_bytree=0.8,
                  subsample=1.0, random_state=42, n_jobs=1, deterministic=True, force_col_wise=True, verbosity=-1)
GRID = [dict(mode=m, num_leaves=nl, min_child_samples=mcs, n_estimators=ne)
        for m in ("single", "pooled") for nl, mcs in ((3, 5), (3, 10), (7, 5), (7, 10)) for ne in (50, 150)]
POOLED_LEADS = list(range(1, 9))


def qk(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def qstart(q: str) -> pd.Timestamp:
    y, n = q.split("-Q")
    return pd.Timestamp(int(y), 3 * (int(n) - 1) + 1, 1)


def origin_of(t: int) -> pd.Timestamp:
    return qstart(qs(t + 1))


# ------------------------------------------------------------------------------------------ frame
def sws_at_origin(rounds: pd.DataFrame, origin: pd.Timestamp) -> float:
    r = rounds[rounds["definition_A"]]
    pub = r[r["published"] < origin]
    if pub.empty:
        return np.nan
    lastq = max(pub["quarter"], key=qk)
    return float(pub.loc[pub["quarter"] == lastq, "H"].mean())


def build_frame(ff: pd.DataFrame, rounds: pd.DataFrame, gov_cols: list[str]) -> pd.DataFrame:
    f = ff.copy()
    f["t"] = f["quarter"].map(qk)
    news = f[["province_code", "t"] + NLP]
    g = f[["province_code", "t"] + gov_cols].copy()
    g["t"] = g["t"] + 1                     # quarter t-1's government values sit on row t
    X = news.merge(g, on=["province_code", "t"], how="left")
    X["sws_hunger"] = X["t"].map(lambda t: sws_at_origin(rounds, origin_of(t)))
    X["quarter"] = X["t"].map(qs)
    return X.sort_values(["t", "province_code"]).reset_index(drop=True)


def label_published(rounds: pd.DataFrame, q: str, t: int) -> bool:
    if qk(q) > t - 1:
        return False
    r = rounds[(rounds["quarter"] == q) & (rounds["definition_A"])]
    return bool(len(r)) and bool((r["published"] < origin_of(t)).all())


def threshold_at(S: pd.DataFrame, rounds: pd.DataFrame, t: int) -> tuple[float, int]:
    """Training-window-only threshold: median S1 over every province-quarter label published before O(t)."""
    ok = S[S["quarter"].map(lambda q: label_published(rounds, q, t))]
    return (float(ok["S1"].median()) if len(ok) else np.nan), int(len(ok))


def pairs_for(X: pd.DataFrame, S: pd.DataFrame, k: int) -> pd.DataFrame:
    L = S.assign(t=S["tq"] - k)[["province_code", "t", "S1", "quarter"]].rename(columns={"quarter": "target_quarter"})
    P = X.merge(L, on=["province_code", "t"], how="inner")
    P["lead"] = k
    P["target_q"] = P["target_quarter"].map(qk)
    return P


# ------------------------------------------------------------------------------------------ models
def _const(n, c):
    return np.full(n, float(c))


def usable_cols(tr: pd.DataFrame, cols: list[str]) -> list[str]:
    """Drop columns that are constant or entirely missing in the TRAINING rows (no effect on any model)."""
    out = []
    for c in cols:
        v = tr[c]
        if v.notna().any() and v.dropna().nunique() > 1:
            out.append(c)
    return out


def fit_lr(tr, cols, te):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    y = tr["y"].to_numpy(int)
    cols = usable_cols(tr, cols)
    if y.mean() in (0.0, 1.0) or not cols:
        return _const(len(te), y.mean())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(C=1.0, max_iter=5000))
        return m.fit(tr[cols], y).predict_proba(te[cols])[:, 1]


def _lgbm_fit(tr, cols, cfg):
    from lightgbm import LGBMClassifier
    y = tr["y"].to_numpy(int)
    p = y.mean()
    params = dict(LGBM_FIXED, num_leaves=cfg["num_leaves"], min_child_samples=cfg["min_child_samples"],
                  n_estimators=cfg["n_estimators"], scale_pos_weight=(1 - p) / p)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return LGBMClassifier(**params).fit(tr[cols], y)


def lgbm_predict(tr_single, tr_pooled, cols, cfg, te, k):
    """Fit one configuration; returns (prob, model, used_cols). Pooled mode adds 'lead' as a feature."""
    tr = tr_pooled if cfg["mode"] == "pooled" else tr_single
    use = usable_cols(tr, cols) + (["lead"] if cfg["mode"] == "pooled" else [])
    y = tr["y"].to_numpy(int)
    if y.mean() in (0.0, 1.0) or not [c for c in use if c != "lead"]:
        return _const(len(te), y.mean()), None, use
    m = _lgbm_fit(tr, use, cfg)
    te2 = te.assign(lead=k)
    return m.predict_proba(te2[use])[:, 1], m, use


def logloss(y, p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, int)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def inner_select(tr_single, tr_pooled, cols, k) -> dict:
    """Nested chronological selection on TRAINING pairs only. Validation targets = the last 3 distinct target
    quarters among the lead-k training pairs; inner training rows = pairs whose target quarter <= v - k - 1
    (labels plausibly known at the inner origin). Score = mean log loss. Ties -> earlier grid entry."""
    vq = sorted(tr_single["target_q"].unique())[-3:]
    best, best_s, scores = GRID[0], np.inf, []
    for cfg in GRID:
        lls = []
        for v in vq:
            a_s = tr_single[tr_single["target_q"] <= v - k - 1]
            a_p = tr_pooled[tr_pooled["target_q"] <= v - k - 1]
            b = tr_single[tr_single["target_q"] == v]
            a = a_p if cfg["mode"] == "pooled" else a_s
            if a["target_q"].nunique() < 4 or a["y"].nunique() < 2 or b.empty:
                continue
            p, _, _ = lgbm_predict(a_s, a_p, cols, cfg, b, k)
            lls.append(logloss(b["y"], p))
        s = float(np.mean(lls)) if lls else np.inf
        scores.append(s)
        if s < best_s - 1e-12:
            best, best_s = cfg, s
    return {"config": best, "inner_logloss": best_s if np.isfinite(best_s) else None,
            "n_inner_folds": len(vq), "fallback_to_grid0": not np.isfinite(best_s)}


def shap_abs(model, te, use, k):
    contrib = model.predict(te.assign(lead=k)[use], pred_contrib=True)[:, :-1]
    return pd.DataFrame(contrib, columns=use)


# ------------------------------------------------------------------------------------------ metrics
def auc(y, s):
    y, s = np.asarray(y, int), np.asarray(s, float)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return None
    r = pd.Series(s).rank(method="average").to_numpy()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def cls_metrics(y, s) -> dict:
    y, s = np.asarray(y, int), np.asarray(s, float)
    p = (s >= 0.5).astype(int)
    tp, tn = int(((y == 1) & (p == 1)).sum()), int(((y == 0) & (p == 0)).sum())
    fp, fn = int(((y == 0) & (p == 1)).sum()), int(((y == 1) & (p == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else (0.0 if prec is not None and rec is not None else None)
    rec0 = tn / (tn + fp) if tn + fp else None
    return {"n": int(len(y)), "HIGH": int(y.sum()), "LOW": int((1 - y).sum()), "TP": tp, "FP": fp, "FN": fn,
            "TN": tn, "accuracy": float((p == y).mean()) if len(y) else None, "precision": prec, "recall": rec,
            "F1": f1, "specificity": rec0, "ROC_AUC": auc(y, s), "Brier": float(np.mean((s - y) ** 2)) if len(y) else None,
            "predicted_HIGH_share": float(p.mean()) if len(y) else None}


EXACT_MAX_ORIGINS = 16      # exact enumeration of all 2^n sign/swap assignments up to n = 16
MC_ASSIGNMENTS = 50_000     # otherwise seeded Monte Carlo (n > 16 does not occur with this data)


def _signs(n, seed=SEED):
    if n <= EXACT_MAX_ORIGINS:
        return np.array(list(itertools.product([0, 1], repeat=n)), dtype=np.int8), True
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=(MC_ASSIGNMENTS, n)).astype(np.int8), False


def signflip_brier(d_origin: np.ndarray) -> dict:
    """One-sided sign-flip test of the mean per-origin Brier difference (proposed - baseline) < 0."""
    d_origin = np.asarray(d_origin, float)
    n = len(d_origin)
    F, exact = _signs(n)
    S = 1.0 - 2.0 * F
    obs = d_origin.mean()
    null = (S * d_origin[None, :]).mean(1)
    return {"n_origins": n, "exact": exact, "mean_diff": float(obs),
            "p_one_sided": float((null <= obs + 1e-12).mean()),
            "origins_better": int((d_origin < 0).sum()), "origins_worse": int((d_origin > 0).sum()),
            "origins_tied": int((d_origin == 0).sum())}


def _cmp(x, y):
    return (x[:, None] > y[None, :]).astype(float) + 0.5 * (x[:, None] == y[None, :])


def paired_auc_perm(groups: np.ndarray, y: np.ndarray, sa: np.ndarray, sb: np.ndarray) -> dict:
    """Paired permutation: swap the two models' scores within whole origins (all 2^n assignments when n <= 16).
    One-sided p for AUC(a) - AUC(b) > 0. Vectorised with the four pairwise comparison matrices."""
    y = np.asarray(y, int)
    ug, og = np.unique(groups, return_inverse=True)
    n = len(ug)
    obs_a, obs_b = auc(y, sa), auc(y, sb)
    if obs_a is None or obs_b is None:
        return {"n_origins": n, "auc_diff": None, "p_one_sided": None}
    P, N = np.where(y == 1)[0], np.where(y == 0)[0]
    Caa, Cab = _cmp(sa[P], sa[N]), _cmp(sa[P], sb[N])
    Cba, Cbb = _cmp(sb[P], sa[N]), _cmp(sb[P], sb[N])
    F, exact = _signs(n)
    F = F.astype(float)
    m = len(P) * len(N)
    diffs = []
    for lo in range(0, len(F), 8192):
        f = F[lo:lo + 8192]
        fi, fj = f[:, og[P]], f[:, og[N]]
        ui, uj = 1 - fi, 1 - fj

        def q(A, B, M):
            return ((A @ M) * B).sum(1)
        A_a = q(ui, uj, Caa) + q(ui, fj, Cab) + q(fi, uj, Cba) + q(fi, fj, Cbb)
        A_b = q(ui, uj, Cbb) + q(ui, fj, Cba) + q(fi, uj, Cab) + q(fi, fj, Caa)
        diffs.append((A_a - A_b) / m)
    diffs = np.concatenate(diffs)
    obs = obs_a - obs_b
    return {"n_origins": n, "exact": exact, "auc_a": obs_a, "auc_b": obs_b, "auc_diff": float(obs),
            "p_one_sided": float((diffs >= obs - 1e-12).mean())}


def cluster_boot_auc(groups, y, s, n_boot=N_BOOT, seed=SEED):
    ug = np.unique(groups)
    idx = [np.where(groups == g)[0] for g in ug]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = np.concatenate([idx[i] for i in rng.integers(0, len(ug), len(ug))])
        a = auc(y[pick], s[pick])
        if a is not None:
            vals.append(a)
    if len(vals) < n_boot * 0.9:
        return {"ci_low": None, "ci_high": None, "valid_resamples": len(vals)}
    return {"ci_low": float(np.quantile(vals, 0.025)), "ci_high": float(np.quantile(vals, 0.975)),
            "valid_resamples": len(vals)}


def holm(pvals: dict) -> dict:
    items = sorted([(p, k) for k, p in pvals.items() if p is not None])
    m, out, run = len(items), {}, 0.0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    for k, p in pvals.items():
        out.setdefault(k, None)
    return out
