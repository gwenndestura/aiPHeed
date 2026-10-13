"""E11 pure functions: extra lagged-label features, model structures, configurations, nested selection.
No data access here; the runner passes data in."""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- configurations (prespecified)
COMMON = dict(random_state=42, verbosity=-1, deterministic=True, force_row_wise=True, n_jobs=1)
CONFIGS = {   # listed from simplest to most flexible; ties in nested selection go to the simpler one
    "C2_stumps":      dict(max_depth=1, num_leaves=2, min_child_samples=10, n_estimators=100, learning_rate=0.03, reg_lambda=10.0),
    "C1_shallow_reg": dict(max_depth=2, num_leaves=3, min_child_samples=10, n_estimators=50, learning_rate=0.05, reg_lambda=5.0),
    "C0_e9_default":  dict(num_leaves=4, min_child_samples=5, n_estimators=100, learning_rate=0.05),
    "C3_moderate":    dict(max_depth=3, num_leaves=4, min_child_samples=8, n_estimators=200, learning_rate=0.02,
                           reg_alpha=1.0, reg_lambda=5.0),
}
ORDER = list(CONFIGS)
MIN_INNER_TRAIN_Q = 6
MONO_UP = {"last_published_stress", "sws_hunger"}

FS = {
    "core":      ["last_published_stress", "sws_hunger", "sws_change"],
    "core_plus": ["last_published_stress", "sws_hunger", "sws_change", "lps_change", "anchor_dev"],
    "compact":   ["last_published_stress", "sws_hunger", "sws_change", "cpi_rel", "cpi_rel_lag1", "food_cpi_yoy",
                  "food_cpi_yoy_lag1", "cpi_dev"],
    "expanded":  ["last_published_stress", "sws_hunger", "sws_change", "cpi_rel", "cpi_rel_lag1", "food_cpi_yoy",
                  "food_cpi_yoy_lag1", "cpi_dev", "poverty_incidence", "headline_cpi", "food_minus_headline_yoy",
                  "food_minus_headline_yoy_lag1", "unemployment_rate"],
    "provincial": ["cpi_rel", "cpi_rel_lag1", "anchor_dev", "dev_change", "cpi_dev", "food_cpi_yoy", "food_cpi_yoy_lag1"],
    "residual":  ["last_published_stress", "sws_hunger", "sws_change", "lps_change", "anchor_dev", "cpi_rel",
                  "cpi_rel_lag1", "cpi_dev"],
}
REGIONAL_FEATURES = {"sws_hunger", "sws_change", "headline_cpi", "food_minus_headline_yoy",
                     "food_minus_headline_yoy_lag1", "unemployment_rate"}


# ---------------------------------------------------------------- extra features from published labels
def label_history_features(frame: pd.DataFrame, stress: pd.DataFrame, published, qi, qstart) -> pd.DataFrame:
    """For each (target, province): components of the latest and second-latest labels published before the origin.
    stress: rows (province_code, quarter, stress, sws_hunger_pct, deviation) for complete labelled quarters."""
    st = stress.set_index(["quarter", "province_code"])
    quarters = sorted(stress["quarter"].unique(), key=qi)
    out = []
    for t in sorted(frame["target_quarter"].unique(), key=qi):
        origin = qstart(t)
        avail = [q for q in quarters if qi(q) < qi(t) and published(q) is not None and published(q) < origin]
        a = avail[-1] if avail else None
        b = avail[-2] if len(avail) > 1 else None
        for p in frame.loc[frame["target_quarter"] == t, "province_code"]:
            r = {"target_quarter": t, "province_code": p, "anchor_check": a, "prev_anchor": b,
                 "anchor_sws": np.nan, "anchor_dev": np.nan, "lps_change": np.nan, "dev_change": np.nan}
            if a is not None:
                r["anchor_sws"] = float(st.at[(a, p), "sws_hunger_pct"])
                r["anchor_dev"] = float(st.at[(a, p), "deviation"])
                if b is not None:
                    r["lps_change"] = float(st.at[(a, p), "stress"] - st.at[(b, p), "stress"])
                    r["dev_change"] = float(st.at[(a, p), "deviation"] - st.at[(b, p), "deviation"])
            out.append(r)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- structures
def target_for(structure: str, rows: pd.DataFrame) -> np.ndarray:
    if structure == "direct":
        return rows["stress"].values
    if structure == "decomp":
        return rows["deviation"].values
    if structure == "resid":
        return (rows["stress"] - rows["s1rule"]).values
    raise ValueError(structure)


def combine(structure: str, rows: pd.DataFrame, yhat: np.ndarray) -> np.ndarray:
    if structure == "direct":
        return yhat
    if structure == "decomp":
        return rows["sws_hunger"].values + 2.0 * yhat
    if structure == "resid":
        return rows["s1rule"].values + yhat
    raise ValueError(structure)


def mono_for(structure: str, cols: list[str]) -> list[int]:
    return [1 if (structure == "direct" and c in MONO_UP) else 0 for c in cols]


def train_filter(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if not (X[c].isna().mean() > 0.5 or X[c].dropna().nunique() < 2)]


def fit_predict_reg(structure, tr, te, feats, cfg):
    from lightgbm import LGBMRegressor
    y = target_for(structure, tr)
    ok = ~np.isnan(y)
    tr = tr[ok]
    y = y[ok]
    keep = train_filter(tr[feats])
    if not keep or len(tr) < 10:
        return np.full(len(te), np.nan), keep, None, None
    m = LGBMRegressor(objective="regression", **CONFIGS[cfg], **COMMON, monotone_constraints=mono_for(structure, keep))
    m.fit(tr[keep], y)
    pred = combine(structure, te, m.predict(te[keep]))
    fit_in = combine(structure, tr, m.predict(tr[keep]))
    train_mae = float(np.nanmean(np.abs(fit_in - tr["stress"].values)))
    gain = dict(zip(keep, map(float, m.booster_.feature_importance("gain"))))
    return pred, keep, train_mae, gain


def fit_predict_clf(tr, te, feats, cfg, tau):
    from lightgbm import LGBMClassifier
    y = (tr["stress"].values > tau).astype(int)
    keep = train_filter(tr[feats])
    if not keep or len(set(y)) < 2:
        return np.full(len(te), np.nan), keep
    m = LGBMClassifier(objective="binary", **CONFIGS[cfg], **COMMON, monotone_constraints=mono_for("direct", keep))
    m.fit(tr[keep], y)
    return m.predict_proba(te[keep])[:, 1], keep


def inner_quarters(train_q: list[str], published, qi, qstart) -> list[tuple[str, list[str]]]:
    """Inner walk-forward over the outer training quarters only (Rule L1 within the inner folds)."""
    out = []
    for qt in train_q:
        inner_tr = [q for q in train_q if qi(q) < qi(qt) and published(q) is not None and published(q) < qstart(qt)]
        if len(inner_tr) >= MIN_INNER_TRAIN_Q:
            out.append((qt, inner_tr))
    return out


def choose(scores: dict[str, list[float]]) -> tuple[str, dict]:
    """Lowest mean inner loss; ties (within 1e-9) go to the simpler configuration; no inner evidence -> simplest."""
    means = {c: (float(np.mean(v)) if v else np.inf) for c, v in scores.items()}
    if all(np.isinf(v) for v in means.values()):
        return ORDER[0], means
    best = min(means.values())
    for c in ORDER:
        if means[c] <= best + 1e-9:
            return c, means
    return ORDER[0], means


def signflip_p(x) -> float:
    """Exact two-sided sign-flip p for the mean of per-quarter differences (descriptive)."""
    x = np.asarray(x, float)
    n = len(x)
    obs = abs(x.mean())
    pats = np.array([[1 if (k >> i) & 1 else -1 for i in range(n)] for k in range(2 ** n)])
    return float((np.abs((pats * x).mean(axis=1)) >= obs - 1e-12).mean())


def within_quarter_share(frame: pd.DataFrame, cols: list[str]) -> dict[str, float | None]:
    """Share of a feature's variance that lies WITHIN quarters (provincial variation) rather than between them."""
    out = {}
    for c in cols:
        d = frame[["target_quarter", c]].dropna()
        if d[c].var() == 0 or len(d) < 3:
            out[c] = None
            continue
        within = (d[c] - d.groupby("target_quarter")[c].transform("mean")).pow(2).sum()
        total = (d[c] - d[c].mean()).pow(2).sum()
        out[c] = float(within / total)
    return out
