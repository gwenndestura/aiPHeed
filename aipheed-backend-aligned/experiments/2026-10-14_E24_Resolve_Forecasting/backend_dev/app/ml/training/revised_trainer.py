"""
app/ml/training/revised_trainer.py
----------------------------------
Revised LightGBM forecaster for the S1 target (isolated development backend).

What it forecasts
    P( stress(p,T) > tau_ref ), where stress = SWS_T + 2 x (provincial food inflation - five-province
    mean) (app/ml/features/risk_score_v2.py) and tau_ref is a frozen, point-in-time reference
    (median stress of labels published before a stated date). The probability is LightGBM's own
    output; no rule-based score is blended into it.

What changed relative to the served model (models/lgbm_best.pkl, app/ml/inference/predictor.py)
    * Time-valid: for target quarter T, training uses only labels published before T's origin
      (Rule L), and inputs only as published before that origin (development frame, strict timing).
      The served model is fitted on every quarter it is later asked to "forecast".
    * Missing inputs stay NaN (LightGBM native handling). The served feature matrix forward-fills
      and zero-fills (app/ml/features/feature_matrix.py l.532, l.619).
    * Inputs include the regional hunger level the target depends on (latest published SWS) and the
      province's last published stress. The served model has no SWS input.
    * Compact, fixed configuration sized for 40-75 training rows (E3); no hyperparameter search.
    * NO class weighting: class weights multiply the odds of HIGH by (1-p)/p and so move
      probabilities away from observed frequencies; the fixed 0.50 rule should apply to a
      probability on the base-rate scale.
    * Calibration (Platt) is applied only if a training-only inner walk-forward yields enough
      out-of-fold evidence (CAL_MIN_QUARTERS quarters and CAL_MIN_PER_CLASS rows per class).
      Otherwise the raw probability is used and the decision is recorded.
    * INSUFFICIENT_DATA when a required input is missing or stale, or training history is too short.

Depends on the experimental timing modules in scripts/supplementary/ (Rule L dates, development frame).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T
from app.ml.features import risk_score_v2 as R

LABELS_PATH = Path("data/processed/labels.parquet")
PSA_PATH = Path("data/processed/psa_indicators.parquet")
WINDOW = ("2021-Q1", "2025-Q4")                 # approved window; no 2026 label is ever loaded

INPUTS = ["last_published_stress", "sws_hunger", "sws_change", "cpi_rel", "food_cpi_yoy",
          "rice_price_regular_accel", "unemployment_rate"]
MONOTONE = [1, 1, 0, 0, 0, 0, 0]                # higher regional hunger / last stress never lowers P(HIGH)
REQUIRED_INPUTS = ["last_published_stress", "sws_hunger", "cpi_rel", "food_cpi_yoy"]
LGBM_PARAMS = {"objective": "binary", "num_leaves": 4, "min_child_samples": 5, "n_estimators": 100,
               "learning_rate": 0.05, "random_state": 42, "verbosity": -1}
MIN_TRAIN_QUARTERS = R.MIN_REFERENCE_QUARTERS
CAL_MIN_QUARTERS = 8
CAL_MIN_PER_CLASS = 10
RETROSPECTIVE_AS_OF = pd.Timestamp("2023-10-01")   # first evaluation origin -> tau0 = 10.843
PROSPECTIVE_AS_OF = pd.Timestamp("2026-07-01")     # first protected origin  -> 14.345 (approved)


# ---------------------------------------------------------------- labels (training access only)
def load_stress() -> pd.DataFrame:
    lab = pd.read_parquet(LABELS_PATH)
    lab = lab[(lab["quarter"] >= WINDOW[0]) & (lab["quarter"] <= WINDOW[1])]
    return lab[["province_code", "quarter", "stress_score"]].rename(columns={"stress_score": "stress"})


class TrainingLabels:
    """Gives a forecast for quarter T access only to labels of quarters < T published before T's origin."""

    def __init__(self, stress: pd.DataFrame):
        if (stress["quarter"] > WINDOW[1]).any():
            raise RuntimeError("a label after the approved window is present")
        self._s = stress.copy()

    def for_target(self, quarters: list[str], target: str) -> pd.DataFrame:
        origin = T.qstart(target)
        for q in quarters:
            pub = D.label_published(q, "development")[0]
            if q >= target or pub is None or pub >= origin:
                raise PermissionError(f"label {q} is not available at the origin of {target}")
        return self._s[self._s["quarter"].isin(quarters)].copy()

    def reference(self, as_of: pd.Timestamp) -> tuple[float, list[str]]:
        return R.reference_threshold(self._s, lambda q: D.label_published(q, "development")[0], as_of)


# ---------------------------------------------------------------- inputs
def anchor_quarter(q: str) -> str | None:
    e = D.eligible_training_quarters(q, "development")
    return max(e) if e else None


def with_last_published_stress(rows: pd.DataFrame, labels: TrainingLabels, target: str) -> pd.DataFrame:
    rows = rows.copy()
    anchors = rows["target_quarter"].map(anchor_quarter)
    need = sorted({a for a in anchors.dropna()})
    s = labels.for_target(need, target).set_index(["quarter", "province_code"])["stress"] if need else pd.Series(dtype=float)
    rows["anchor_quarter"] = anchors
    rows["last_published_stress"] = [s.get((a, p), np.nan) if isinstance(a, str) else np.nan
                                     for a, p in zip(anchors, rows["province_code"])]
    return rows


def insufficiency(row: pd.Series) -> list[str]:
    reasons = [f"missing input: {c}" for c in REQUIRED_INPUTS if pd.isna(row.get(c))]
    age = row.get("sws_age")
    if pd.notna(age) and age > R.SWS_MAX_AGE_QUARTERS:
        reasons.append(f"stale regional hunger input: latest published SWS round is {int(age)} quarters old")
    return reasons


# ---------------------------------------------------------------- model
def fit(X: pd.DataFrame, y: np.ndarray):
    from lightgbm import LGBMClassifier
    if list(X.columns) != INPUTS:
        raise RuntimeError("feature order differs from INPUTS")
    return LGBMClassifier(**LGBM_PARAMS, monotone_constraints=MONOTONE).fit(X, y)


def calibration_check(train: pd.DataFrame, y: np.ndarray) -> dict:
    """Inner walk-forward over the TRAINING quarters only; decides whether Platt scaling is supportable."""
    qs = sorted(train["target_quarter"].unique())
    oof = []
    for i in range(MIN_TRAIN_QUARTERS, len(qs)):
        inner_tr = train["target_quarter"].isin(qs[:i]).values
        inner_te = (train["target_quarter"] == qs[i]).values
        if len(set(y[inner_tr])) < 2:
            continue
        m = fit(train.loc[inner_tr, INPUTS], y[inner_tr])
        oof.append(pd.DataFrame({"q": qs[i], "p": m.predict_proba(train.loc[inner_te, INPUTS])[:, 1],
                                 "y": y[inner_te]}))
    if not oof:
        return {"applied": False, "reason": "no inner out-of-fold quarters", "oof_quarters": 0}
    o = pd.concat(oof)
    n_q, n_pos, n_neg = o["q"].nunique(), int(o["y"].sum()), int((o["y"] == 0).sum())
    ok = n_q >= CAL_MIN_QUARTERS and min(n_pos, n_neg) >= CAL_MIN_PER_CLASS
    out = {"applied": bool(ok), "oof_quarters": int(n_q), "oof_high": n_pos, "oof_low": n_neg,
           "oof_brier": round(float(np.mean((o["p"] - o["y"]) ** 2)), 4),
           "reason": "sufficient inner evidence" if ok else
                     f"insufficient inner evidence (need >= {CAL_MIN_QUARTERS} quarters and >= {CAL_MIN_PER_CLASS} rows per class)"}
    if ok:
        from sklearn.linear_model import LogisticRegression
        logit = np.log(np.clip(o["p"], 1e-6, 1 - 1e-6) / (1 - np.clip(o["p"], 1e-6, 1 - 1e-6)))
        out["platt"] = LogisticRegression().fit(logit.values.reshape(-1, 1), o["y"].values)
    return out


@dataclass
class Forecast:
    target: str
    tau: float
    rows: pd.DataFrame
    n_train_quarters: int
    calibration: dict = field(default_factory=dict)


def forecast_quarter(frame: pd.DataFrame, labels: TrainingLabels, target: str, tau: float) -> Forecast:
    """Label-free forecast for one target quarter. Never reads the target quarter's label."""
    train_q = D.eligible_training_quarters(target, "development")
    te = frame[frame["target_quarter"] == target].sort_values("province_code")
    te = with_last_published_stress(te, labels, target)
    base = te[["province_code", "target_quarter", "origin", "sws_hunger", "sws_age", "sws_round",
               "sws_round_quarter", "sws_published", "sws_date_type", "anchor_quarter",
               "last_published_stress"] + [c for c in INPUTS if c not in ("last_published_stress", "sws_hunger")]].copy()
    base["probability_raw"] = np.nan
    base["probability"] = np.nan
    base["top_factors"] = ""
    reasons = [insufficiency(r) for _, r in te.iterrows()]
    if len(train_q) < MIN_TRAIN_QUARTERS:
        reasons = [rs + [f"training history: {len(train_q)} eligible labelled quarters (< {MIN_TRAIN_QUARTERS})"]
                   for rs in reasons]
        base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
        base["classification"] = R.INSUFFICIENT_DATA
        return Forecast(target, tau, base, len(train_q), {"applied": False, "reason": "no model fitted"})

    lab = labels.for_target(train_q, target)
    tr = frame[frame["target_quarter"].isin(train_q)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"], how="inner")
    tr = with_last_published_stress(tr, labels, target)
    y = (tr["stress"] > tau).astype(int).values
    if len(set(y)) < 2:
        reasons = [rs + ["training labels contain one class only"] for rs in reasons]
        base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
        base["classification"] = R.INSUFFICIENT_DATA
        return Forecast(target, tau, base, len(train_q), {"applied": False, "reason": "no model fitted"})

    model = fit(tr[INPUTS], y)
    p_raw = model.predict_proba(te[INPUTS])[:, 1]
    cal = calibration_check(tr, y)
    if cal.get("applied"):
        lg = np.log(np.clip(p_raw, 1e-6, 1 - 1e-6) / (1 - np.clip(p_raw, 1e-6, 1 - 1e-6)))
        p = cal["platt"].predict_proba(lg.reshape(-1, 1))[:, 1]
    else:
        p = p_raw
    contrib = model.booster_.predict(te[INPUTS], pred_contrib=True)[:, :-1]
    base["probability_raw"] = p_raw
    base["probability"] = p
    base["top_factors"] = ["; ".join(f"{INPUTS[j]} {'+' if c[j] > 0 else '-'}{abs(c[j]):.2f}"
                                     for j in np.argsort(-np.abs(c))[:3]) for c in contrib]
    base["insufficient_reasons"] = ["; ".join(r) for r in reasons]
    base["classification"] = [R.final_classification(pp, rs) for pp, rs in zip(p, reasons)]
    base.loc[base["classification"] == R.INSUFFICIENT_DATA, ["probability"]] = np.nan
    cal = {k: v for k, v in cal.items() if k != "platt"}
    return Forecast(target, tau, base, len(train_q), cal)


def price_evidence(target: str) -> pd.DataFrame:
    """Provincial food-price evidence as published before the origin of `target` (reference quarter T-2)."""
    ref = T.prev(T.prev(target))
    pub, kind = D.cpi_published(ref, provincial=True)
    ind = pd.read_parquet(PSA_PATH)
    ind = ind[(ind["quarter"] >= WINDOW[0]) & (ind["quarter"] <= WINDOW[1])]
    pi = R.price_pressure_indicators(ind)
    out = pi[pi["quarter"] == ref].copy()
    available = pub is not None and pub < T.qstart(target)
    if not available:
        out[["price_index_level", "inflation_rate", "inflation_change", "relative_pressure"]] = np.nan
    out["cpi_reference_quarter"] = ref
    out["cpi_published"] = pub.date().isoformat() if pub is not None else None
    out["cpi_date_type"] = kind
    return out.drop(columns=["quarter"])
