"""E9 evaluation metrics (pure functions; no data access)."""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_PER_CLASS_FOR_AUC = 5


def _safe_div(a: float, b: float):
    return None if b == 0 else a / b


def classification(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """y_true / y_pred are booleans (True = HIGH). Rows must already exclude INSUFFICIENT_DATA."""
    y_true, y_pred = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp = int((y_true & y_pred).sum()); fn = int((y_true & ~y_pred).sum())
    fp = int((~y_true & y_pred).sum()); tn = int((~y_true & ~y_pred).sum())
    n = tp + fn + fp + tn
    rec_h, rec_l = _safe_div(tp, tp + fn), _safe_div(tn, tn + fp)
    prec_h, prec_l = _safe_div(tp, tp + fp), _safe_div(tn, tn + fn)
    f1 = lambda p, r: None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r)
    return {
        "n": n, "accuracy": _safe_div(tp + tn, n),
        "balanced_accuracy": None if rec_h is None or rec_l is None else (rec_h + rec_l) / 2,
        "balanced_accuracy_note": None if rec_h is not None and rec_l is not None else
        "undefined: one true class absent",
        "HIGH": {"precision": prec_h, "recall": rec_h, "f1": f1(prec_h, rec_h), "support": tp + fn},
        "LOW": {"precision": prec_l, "recall": rec_l, "f1": f1(prec_l, rec_l), "support": tn + fp},
        "confusion": {"true_HIGH_pred_HIGH": tp, "true_HIGH_pred_LOW": fn,
                      "true_LOW_pred_HIGH": fp, "true_LOW_pred_LOW": tn},
        "true_distribution": {"HIGH": tp + fn, "LOW": tn + fp},
        "pred_distribution": {"HIGH": tp + fp, "LOW": tn + fn},
    }


def ranking_auc(y_true: np.ndarray, score: np.ndarray) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score
    y = np.asarray(y_true, bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if min(npos, nneg) < MIN_PER_CLASS_FOR_AUC:
        return {"roc_auc": None, "pr_auc": None,
                "note": f"not meaningful: {nneg} LOW / {npos} HIGH (< {MIN_PER_CLASS_FOR_AUC} per class)"}
    return {"roc_auc": float(roc_auc_score(y, score)), "pr_auc": float(average_precision_score(y, score)),
            "note": None}


def brier(y_true: np.ndarray, p: np.ndarray) -> float:
    p = np.asarray(p, float)
    if np.any((p < 0) | (p > 1)):
        raise ValueError("Brier requires probabilities in [0, 1]")
    return float(np.mean((p - np.asarray(y_true, float)) ** 2))


def concordant_pairs(pred: np.ndarray, obs: np.ndarray) -> tuple[float, int]:
    """Concordant pairs between predicted and observed values; ties in prediction count 0.5;
    pairs tied in the observation are not evaluated. Returns (concordant, pairs evaluated)."""
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    c, n = 0.0, 0
    for i in range(len(obs)):
        for j in range(i + 1, len(obs)):
            if obs[i] == obs[j]:
                continue
            n += 1
            s = np.sign(pred[i] - pred[j]) * np.sign(obs[i] - obs[j])
            c += 1.0 if s > 0 else (0.5 if s == 0 else 0.0)
    return c, n


def stress_errors(df: pd.DataFrame) -> dict:
    """df columns: target_quarter, province_code, stress_pred, stress_true (complete rows only)."""
    e = df["stress_pred"] - df["stress_true"]
    per_q = []
    for q, g in df.groupby("target_quarter"):
        c, n = concordant_pairs(g["stress_pred"].values, g["stress_true"].values)
        per_q.append({"quarter": q, "n": int(len(g)), "mae": float((g["stress_pred"] - g["stress_true"]).abs().mean()),
                      "regional_level_error": float(abs(g["stress_pred"].mean() - g["stress_true"].mean())),
                      "concordant_pairs": c, "pairs": n,
                      "spearman": float(g["stress_pred"].rank().corr(g["stress_true"].rank())) if len(g) > 2 else None,
                      "pred_spread": float(g["stress_pred"].max() - g["stress_pred"].min()),
                      "true_spread": float(g["stress_true"].max() - g["stress_true"].min())})
    pq = pd.DataFrame(per_q)
    return {"n_rows": int(len(df)), "n_quarters": int(df["target_quarter"].nunique()),
            "mae": float(e.abs().mean()), "rmse": float(np.sqrt((e ** 2).mean())),
            "mean_regional_level_error": float(pq["regional_level_error"].mean()),
            "mean_concordant_share": float((pq["concordant_pairs"] / pq["pairs"].replace(0, np.nan)).mean()),
            "per_quarter": per_q}


def cluster_bootstrap_diff(per_q_a: dict, per_q_b: dict, quarters: list[str], n_boot: int = 2000,
                           seed: int = 42) -> dict:
    """Quarter-cluster bootstrap of mean(a) - mean(b) over quarters (one value per quarter)."""
    a = np.array([per_q_a[q] for q in quarters]); b = np.array([per_q_b[q] for q in quarters])
    d = a - b
    rng = np.random.default_rng(seed)
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)]
    return {"mean_diff": float(d.mean()), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "quarters": len(d), "quarters_a_lower": int((d < 0).sum()),
            "note": f"{len(d)} quarter clusters; the interval is unstable at this size"}
