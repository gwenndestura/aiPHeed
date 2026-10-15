"""E36 library: feature groups, the LightGBM grid, the six Chapter I baselines and the nested (honest) selection rule.

Inputs, origins, labels and the as-of feature construction are E32's (`E32_New_Model/runner/e32_lib.py`), reused
unchanged. Only the arms and the selection rule are new (PROTOCOL.md sections 3-5).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

E36 = Path(__file__).resolve().parents[1]
EXPS = E36.parent
E32R = EXPS / "E32_New_Model" / "runner"
for p in (str(Path(__file__).resolve().parent), str(E32R), str(EXPS / "E31_Chapter1_Completion" / "runner")):
    if p not in sys.path:
        sys.path.insert(0, p)

import guard32  # noqa: E402

guard32.EXP = E36            # E32's read rules, but writes confined to E36 (and the OS temp directory)
import e32_common as C  # noqa: E402
import e32_lib as L32  # noqa: E402

np, pd, P = C.np, C.pd, C.P
qk, qs, PROVS, NAMES = C.qk, C.qs, C.PROVS, C.NAMES

GOV = ["H_last", "H_gap", "H_trend", "H_margin", "D_last", "Dnow", "rice_rel", "y_last"]
NLP = ["news_n", "news_reg", "news_direct_share", "fssi_v2", "fssi_missing"]
COMB = GOV[:7] + NLP + ["y_last"]                      # same 13 columns as E32 FEATURES (order kept)
COMPACT = ["H_margin", "H_trend", "D_last", "Dnow", "news_reg", "fssi_v2"]
COMB_NOY = [f for f in COMB if f != "y_last"]
FEATURE_SETS = {"GOV": GOV, "NLP": NLP, "COMB": COMB, "COMPACT": COMPACT, "COMB_NOY": COMB_NOY}
assert sorted(COMB) == sorted(L32.FEATURES)

_BASE = dict(objective="binary", n_jobs=1, seed=36, deterministic=True, force_col_wise=True, bagging_fraction=1.0,
             bagging_freq=0, verbose=-1)
GRID = {
    "G1": dict(num_leaves=2, max_depth=1, min_data_in_leaf=5, n_estimators=100, learning_rate=0.05, reg_lambda=1.0,
               colsample_bytree=1.0),
    "G4": dict(num_leaves=2, max_depth=1, min_data_in_leaf=5, n_estimators=100, learning_rate=0.05, reg_lambda=1.0,
               colsample_bytree=1.0, class_weight="balanced"),
    "G3": dict(num_leaves=3, max_depth=2, min_data_in_leaf=8, n_estimators=80, learning_rate=0.05, reg_lambda=5.0,
               colsample_bytree=0.8),
    "G2": dict(num_leaves=4, max_depth=-1, min_data_in_leaf=5, n_estimators=150, learning_rate=0.05, reg_lambda=0.0,
               colsample_bytree=0.8),
}
COMPLEXITY = ["G1", "G4", "G3", "G2"]
POOLS = {   # arm -> (configurations in simplicity order, default)
    "E36-LGBM": ([("COMPACT", g) for g in COMPLEXITY] + [("COMB", g) for g in COMPLEXITY], ("COMB", "G1")),
    "B5_LGBM_GOV": ([("GOV", g) for g in COMPLEXITY], ("GOV", "G1")),
    "B6_LGBM_NLP": ([("NLP", g) for g in COMPLEXITY], ("NLP", "G1")),
}
TIE = 0.002
MIN_PRIOR = 3
LR_SETS = {"B2_LR_COMB": COMB, "B3_LR_GOV": GOV, "B4_LR_NLP": NLP}
FIRST_TARGET, LAST_TARGET = qk("2022-Q4"), qk("2026-Q3")   # 2022-Q4 drops out by the 10-row rule (D-1)
EARLY_LAST = qk("2023-Q3")
OPERATIONAL_T = qk("2026-Q3")                           # origin 2026-10-01, lead-1 target 2026-Q4
origin = L32.origin


def cfg_name(fs: str, g: str) -> str:
    return f"{fs}x{g}"


class Data(L32.Data):
    """E32 data with the E36 training-row rule (rows with a missing COMB value dropped, identical for every arm)."""

    def train(self, t: int) -> pd.DataFrame:
        tr = self.training_pairs(t, 1)
        if tr.empty:
            return tr
        return tr.dropna(subset=COMB).reset_index(drop=True)

    def test(self, t: int) -> pd.DataFrame:
        return self.features(t, 1)


# ------------------------------------------------------------------ model fitting
def _const(te: pd.DataFrame, y) -> dict:
    r = (np.sum(y) + 1) / (len(y) + 2)
    return {p: float(r) for p in te["province_code"]}


def fit_lgbm(tr: pd.DataFrame, feats: list[str], g: str):
    import lightgbm as lgb

    y = tr["y"].to_numpy(int)
    if len(set(y)) < 2:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return lgb.LGBMClassifier(**_BASE, **GRID[g]).fit(tr[feats].astype(float), y)


def lgbm_predict(tr: pd.DataFrame, te: pd.DataFrame, feats: list[str], g: str) -> dict:
    m = fit_lgbm(tr, feats, g)
    if m is None:
        return _const(te, tr["y"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pr = m.predict_proba(te[feats].astype(float))[:, 1]
    return dict(zip(te["province_code"], pr.astype(float)))


def lr_predict(tr: pd.DataFrame, te: pd.DataFrame, feats: list[str]) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    y = tr["y"].to_numpy(int)
    if len(set(y)) < 2:
        return _const(te, y)
    X = tr[feats].to_numpy(float)
    sc = StandardScaler().fit(X)
    Z = sc.transform(X)
    m = LogisticRegression(C=1.0, max_iter=5000).fit(Z, y)
    Zt = np.nan_to_num(sc.transform(te[feats].to_numpy(float)), nan=0.0)   # training-mean imputation
    return dict(zip(te["province_code"], m.predict_proba(Zt)[:, 1].astype(float)))


def references(d: Data, t: int) -> dict:
    """always-HIGH, climatology (training HIGH rate, Laplace) and B1/B1p persistence, publication-aware."""
    te, tr = d.test(t), d.train(t)
    clim = (tr["y"].sum() + 1) / (len(tr) + 2)
    out = {"B1_PERSISTENCE": {}, "B1p_CAL_PERSISTENCE": {}, "CLIMATOLOGY": {}, "ALWAYS_HIGH": {}}
    for r in te.itertuples():
        yl = r.y_last
        out["B1_PERSISTENCE"][r.province_code] = float(yl) if yl == yl else 0.5
        g = tr[tr["y_last"] == yl] if yl == yl else tr.iloc[0:0]
        out["B1p_CAL_PERSISTENCE"][r.province_code] = float((g["y"].sum() + 1) / (len(g) + 2)) if len(g) else 0.5
        out["CLIMATOLOGY"][r.province_code] = float(clim)
        out["ALWAYS_HIGH"][r.province_code] = 1.0
    return out


# ------------------------------------------------------------------ fixed arms per origin
def fixed_arms(d: Data, t: int) -> dict[str, dict]:
    """Every fixed configuration needed by the nested pools, the LR baselines and the diagnostics at origin O(t)."""
    tr, te = d.train(t), d.test(t)
    out = {}
    for pool, _default in POOLS.values():
        for fs, g in pool:
            name = cfg_name(fs, g)
            if name not in out:
                out[name] = lgbm_predict(tr, te, FEATURE_SETS[fs], g)
    out[cfg_name("COMB_NOY", "G1")] = lgbm_predict(tr, te, COMB_NOY, "G1")
    for arm, feats in LR_SETS.items():
        out[arm] = lr_predict(tr, te, feats)
    out.update(references(d, t))
    try:                                                # diagnostic only; needs >= 40 published D pairs
        out["PCF21"] = L32.pcf21(d, t, 1)
    except ValueError:
        pass
    return out


# ------------------------------------------------------------------ nested selection
def eligible_prior_dates(d: Data, t: int, dates: list[int]) -> list[int]:
    """Development dates (lead-1 origins t_j) whose TARGET label t_j+1 was posted before O(t)."""
    posted = set(d.posted_quarters(origin(t)))
    return [tj for tj in dates if tj < t and (tj + 1) in posted and (tj + 1) <= t - 1]


def per_date_brier(preds: dict, labels: dict, name: str, tj: int) -> float:
    return float(np.mean([(preds[tj][name][p] - labels[tj][p]) ** 2 for p in PROVS]))


def select(pool_key: str, prior: list[int], preds: dict, labels: dict) -> tuple[tuple[str, str], dict]:
    """Return the chosen (feature set, grid id) and the score table, by PROTOCOL.md section 5."""
    pool, default = POOLS[pool_key]
    if len(prior) < MIN_PRIOR:
        return default, {"rule": "default (fewer than 3 eligible prior dates)", "prior_dates": [qs(x + 1) for x in prior]}
    scores = {cfg_name(*c): float(np.mean([per_date_brier(preds, labels, cfg_name(*c), tj) for tj in prior]))
              for c in pool}
    best = min(scores.values())
    chosen = next(c for c in pool if scores[cfg_name(*c)] <= best + TIE)   # pool is listed in simplicity order
    return chosen, {"rule": "lowest mean per-date Brier on eligible prior dates (tie 0.002 -> simpler)",
                    "prior_dates": [qs(x + 1) for x in prior], "scores": scores}


def walk_forward(d: Data) -> tuple[pd.DataFrame, dict]:
    """All arms at all development origins, with the nested arms filled in chronologically."""
    origins = [tg - 1 for tg in range(FIRST_TARGET, LAST_TARGET + 1)]
    preds, labels, dates = {}, {}, []
    for t in origins:
        lab = {p: d.label(p, t + 1, t) for p in PROVS}
        if any(v is None for v in lab.values()):
            continue
        tr = d.train(t)
        if len(tr) < 10 or tr["y"].nunique() < 2:
            continue
        preds[t], labels[t] = fixed_arms(d, t), lab
        dates.append(t)
    selections = {}
    for t in dates:
        prior = eligible_prior_dates(d, t, dates)
        for arm in POOLS:
            (fs, g), info = select(arm, prior, preds, labels)
            preds[t][arm] = dict(preds[t][cfg_name(fs, g)])
            selections.setdefault(arm, {})[qs(t + 1)] = {"chosen": cfg_name(fs, g), **info}
    rows = []
    for t in dates:
        for arm, pr in preds[t].items():
            for p in PROVS:
                rows.append({"lead": 1, "t": qs(t), "origin": str(origin(t).date()), "target_quarter": qs(t + 1),
                             "province_code": p, "arm": arm, "p": float(pr[p]), "y": int(labels[t][p]),
                             "period": "P-early" if t + 1 <= EARLY_LAST else "P-late"})
    return pd.DataFrame(rows), {"dates": [qs(t + 1) for t in dates], "selections": selections}


# ------------------------------------------------------------------ the operational model
def operational_choice(d: Data, preds_df: pd.DataFrame, pool_key: str = "E36-LGBM") -> tuple[tuple[str, str], dict]:
    """The configuration the nested rule picks at O(2026-Q3) = 2026-10-01 (only targets posted before then)."""
    dates = sorted({qk(x) for x in preds_df["t"].unique()})
    prior = eligible_prior_dates(d, OPERATIONAL_T, dates)
    preds, labels = {}, {}
    for tj in prior:
        s = preds_df[preds_df["t"] == qs(tj)]
        preds[tj] = {a: dict(zip(g["province_code"], g["p"])) for a, g in s.groupby("arm")}
        labels[tj] = dict(zip(s[s["arm"] == "ALWAYS_HIGH"]["province_code"], s[s["arm"] == "ALWAYS_HIGH"]["y"]))
    return select(pool_key, prior, preds, labels)


def shap_contributions(model, X: pd.DataFrame) -> pd.DataFrame:
    """Exact TreeSHAP in log-odds (LightGBM pred_contrib); the last column is the expected value."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = model.booster_.predict(X.astype(float), pred_contrib=True)
    return pd.DataFrame(c, columns=list(X.columns) + ["expected_value"], index=X.index)


DISPLAY = {
    "H_last": "Latest regional hunger rate (SWS Balance Luzon)",
    "H_gap": "Quarters between the latest hunger survey and the forecast quarter",
    "H_trend": "Change in regional hunger between the two latest surveys",
    "H_margin": "Latest regional hunger relative to the HIGH threshold",
    "D_last": "Province food-price pressure last quarter (PSA food CPI)",
    "Dnow": "Province food-price pressure in the first two months of this quarter",
    "rice_rel": "Province rice-price inflation relative to the regional mean",
    "y_last": "Latest published risk label for the province",
    "news_n": "Relevant food-insecurity news about the province (count)",
    "news_reg": "Relevant food-insecurity news in the region (count)",
    "news_direct_share": "Share of the province's news directly about food",
    "fssi_v2": "Food Stress Sentiment Index (FSSI-v2)",
    "fssi_missing": "No FSSI evidence for the province this quarter",
}
SOURCE = {f: "government" for f in GOV} | {f: "news" for f in NLP}
