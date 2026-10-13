"""
app/ml/training/datadriven_trainer.py
-------------------------------------
Evidence-based indicator influence for the LightGBM forecaster (protocol:
experiments/2026-10-11_devprotocol/E7_INDICATOR_EVIDENCE_PROTOCOL.md).

Target: unchanged (app/ml/training/revised_trainer.py): P( stress(p,T) > tau ). Equation 3's own
weights cannot be learned (no independent outcome exists); what is learned here is how much each
PREDICTOR group contributes:
  * LightGBM learns nonlinear contributions within the chosen groups;
  * which groups enter is decided per forecast origin by a TRAINING-ONLY inner walk-forward
    (lowest inner out-of-fold log loss over R + every subset of {GP, GN, N}; ties -> fewer groups;
    fewer than 3 inner quarters -> R alone);
  * features missing in > 50% of the fold's training rows, or constant in them, are dropped (training-only).
Each forecast records the selected groups and each group's summed log-odds contribution, so the
API can separate regional hunger evidence, provincial economic stress, national context, news and
the final forecast. Contributions describe the fitted model; they are not causal effects.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T
from app.ml.features import risk_score_v2 as R
from app.ml.training import revised_trainer as RT

GROUPS = {
    "R": ["sws_hunger", "sws_change", "last_published_stress"],
    "GP": ["cpi_rel", "cpi_rel_lag1", "cpi_dev", "food_cpi", "food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel",
           "rice_price_regular", "rice_price_regular_lag1", "rice_price_regular_accel", "poverty_incidence"],
    "GN": ["unemployment_rate", "unemployment_rate_lag1", "unemployment_rate_accel", "ofw_remit_yoy_pct",
           "ofw_remit_yoy_pct_lag1", "ofw_remit_yoy_pct_accel", "diesel_php_per_l", "diesel_php_per_l_lag1",
           "diesel_php_per_l_accel", "gasoline_php_per_l", "fx_usd_php_avg", "brent_usd_per_bbl", "headline_cpi",
           "food_minus_headline_yoy", "food_minus_headline_yoy_lag1", "food_minus_headline_yoy_accel", "enso_numeric",
           "drought_alert", "tc_count", "tc_severe_flag", "rainfall_anomaly_pct", "rainfall_anomaly_pct_lag1",
           "rainfall_anomaly_pct_accel"],
    "N": ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "fssi_article_count", "news_ph_fssi", "news_ph_count",
          "trigger_market", "trigger_climate", "trigger_fish_kill", "trigger_employment", "trigger_ofw_remittance"],
}
GROUP_LABELS = {"R": "regional hunger and persistence", "GP": "provincial government indicators",
                "GN": "national/regional government indicators", "N": "news-derived indicators"}
CANDIDATES = [("R",) + tuple(c) for k in range(4) for c in combinations(("GP", "GN", "N"), k)]
MONOTONE_UP = {"sws_hunger", "last_published_stress"}
MAX_MISSING_SHARE = 0.50
INNER_MIN_TRAIN_QUARTERS = 6
INNER_MIN_OOF_QUARTERS = 3
TIE_TOLERANCE = 0.005
PARAMS = dict(RT.LGBM_PARAMS)


def columns_for(groups: tuple[str, ...]) -> list[str]:
    return [c for g in ("R", "GP", "GN", "N") if g in groups for c in GROUPS[g]]


def usable_columns(train: pd.DataFrame, cols: list[str]) -> list[str]:
    """Training-only filter: drop columns missing in > 50% of training rows or constant there."""
    keep = []
    for c in cols:
        x = train[c]
        if x.isna().mean() > MAX_MISSING_SHARE or x.dropna().nunique() < 2:
            continue
        keep.append(c)
    return keep


def fit(X: pd.DataFrame, y: np.ndarray, kind: str = "classifier"):
    from lightgbm import LGBMClassifier, LGBMRegressor
    mono = [1 if c in MONOTONE_UP else 0 for c in X.columns]
    if kind == "classifier":
        return LGBMClassifier(**PARAMS, monotone_constraints=mono).fit(X, y)
    p = {**PARAMS, "objective": "regression"}
    return LGBMRegressor(**p, monotone_constraints=mono).fit(X, y)


def _log_loss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def select_groups(train: pd.DataFrame, y: np.ndarray) -> dict:
    """Training-only inner walk-forward over the outer TRAINING quarters (rows carry target_quarter)."""
    qs = sorted(train["target_quarter"].unique())
    scores = {c: [] for c in CANDIDATES}
    inner_qs = []
    for q in qs:
        origin = T.qstart(q)
        tr_q = [x for x in qs if x < q and D.label_published(x, "development")[0] < origin]
        if len(tr_q) < INNER_MIN_TRAIN_QUARTERS:
            continue
        m_tr = train["target_quarter"].isin(tr_q).values
        m_te = (train["target_quarter"] == q).values
        if len(set(y[m_tr])) < 2:
            continue
        inner_qs.append(q)
        for cand in CANDIDATES:
            cols = usable_columns(train.loc[m_tr], columns_for(cand))
            m = fit(train.loc[m_tr, cols], y[m_tr])
            scores[cand].append(_log_loss(y[m_te], m.predict_proba(train.loc[m_te, cols])[:, 1]))
    if len(inner_qs) < INNER_MIN_OOF_QUARTERS:
        return {"selected": ("R",), "reason": f"{len(inner_qs)} inner quarters (< {INNER_MIN_OOF_QUARTERS}); fallback R",
                "inner_quarters": inner_qs, "inner_log_loss": {}}
    mean = {"+".join(c): round(float(np.mean(v)), 4) for c, v in scores.items()}
    best = min(mean.values())
    tied = [c for c in CANDIDATES if mean["+".join(c)] <= best + TIE_TOLERANCE]
    chosen = min(tied, key=len)
    return {"selected": chosen, "reason": "lowest inner out-of-fold log loss (ties -> fewer groups)",
            "inner_quarters": inner_qs, "inner_log_loss": mean}


def group_contributions(model, X: pd.DataFrame) -> pd.DataFrame:
    contrib = model.booster_.predict(X, pred_contrib=True)[:, :-1]
    out = pd.DataFrame(0.0, index=range(len(X)), columns=list(GROUPS))
    for j, c in enumerate(X.columns):
        g = next(k for k, v in GROUPS.items() if c in v)
        out[g] += contrib[:, j]
    return out


def forecast_quarter(frame: pd.DataFrame, labels: RT.TrainingLabels, target: str, tau: float,
                     groups: tuple[str, ...] | None = None) -> RT.Forecast:
    """Label-free forecast; `groups=None` -> training-only selection (M6), else a fixed configuration."""
    train_q = D.eligible_training_quarters(target, "development")
    te = RT.with_last_published_stress(frame[frame["target_quarter"] == target].sort_values("province_code"),
                                       labels, target)
    base = te[["province_code", "target_quarter", "origin", "sws_hunger", "sws_age", "sws_round", "sws_round_quarter",
               "sws_published", "sws_date_type", "anchor_quarter", "last_published_stress", "cpi_rel", "food_cpi_yoy"]].copy()
    for k in ("probability", "contrib_R", "contrib_GP", "contrib_GN", "contrib_N"):
        base[k] = np.nan
    base["selected_groups"], base["features_used"], base["top_factors"] = "", "", ""
    reasons = [RT.insufficiency(r) for _, r in te.iterrows()]
    if len(train_q) < RT.MIN_TRAIN_QUARTERS:
        reasons = [r + [f"training history: {len(train_q)} eligible labelled quarters (< {RT.MIN_TRAIN_QUARTERS})"]
                   for r in reasons]
        base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
        base["classification"] = R.INSUFFICIENT_DATA
        return RT.Forecast(target, tau, base, len(train_q), {"selected": None})
    lab = labels.for_target(train_q, target)
    tr = frame[frame["target_quarter"].isin(train_q)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
    tr = RT.with_last_published_stress(tr, labels, target)
    y = (tr["stress"] > tau).astype(int).values
    if len(set(y)) < 2:
        reasons = [r + ["training labels contain one class only"] for r in reasons]
        base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
        base["classification"] = R.INSUFFICIENT_DATA
        return RT.Forecast(target, tau, base, len(train_q), {"selected": None})
    sel = select_groups(tr, y) if groups is None else {"selected": tuple(groups), "reason": "fixed configuration"}
    cols = usable_columns(tr, columns_for(sel["selected"]))
    if not cols:                       # every column filtered out: no evidence-based forecast is possible
        reasons = [r + ["no usable indicator in the selected groups (missing or constant in training)"] for r in reasons]
        base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
        base["classification"] = R.INSUFFICIENT_DATA
        base["selected_groups"] = "+".join(sel["selected"])
        return RT.Forecast(target, tau, base, len(train_q), {k: (list(v) if isinstance(v, tuple) else v)
                                                              for k, v in sel.items()})
    model = fit(tr[cols], y)
    p = model.predict_proba(te[cols])[:, 1]
    gc = group_contributions(model, te[cols])
    contrib = model.booster_.predict(te[cols], pred_contrib=True)[:, :-1]
    base["probability"] = p
    for g in GROUPS:
        base[f"contrib_{g}"] = gc[g].values
    base["selected_groups"] = "+".join(sel["selected"])
    base["features_used"] = ",".join(cols)
    base["top_factors"] = ["; ".join(f"{cols[j]} {'+' if c[j] > 0 else '-'}{abs(c[j]):.2f}"
                                     for j in np.argsort(-np.abs(c))[:3]) for c in contrib]
    base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
    base["classification"] = [R.final_classification(pp, rs) for pp, rs in zip(p, reasons)]
    base.loc[base["classification"] == R.INSUFFICIENT_DATA, "probability"] = np.nan
    return RT.Forecast(target, tau, base, len(train_q), {k: (list(v) if isinstance(v, tuple) else v)
                                                          for k, v in sel.items()})


def regress_quarter(frame: pd.DataFrame, labels: RT.TrainingLabels, target: str, groups: tuple[str, ...]) -> pd.DataFrame:
    """Label-free continuous stress forecast with fixed groups (E7 tertiary analysis)."""
    train_q = D.eligible_training_quarters(target, "development")
    te = RT.with_last_published_stress(frame[frame["target_quarter"] == target].sort_values("province_code"),
                                       labels, target)
    lab = labels.for_target(train_q, target)
    tr = frame[frame["target_quarter"].isin(train_q)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
    tr = RT.with_last_published_stress(tr, labels, target)
    cols = usable_columns(tr, columns_for(groups))
    m = fit(tr[cols], tr["stress"].values, kind="regressor")
    return pd.DataFrame({"target_quarter": target, "province_code": te["province_code"].values,
                         "pred_stress": m.predict(te[cols])})
