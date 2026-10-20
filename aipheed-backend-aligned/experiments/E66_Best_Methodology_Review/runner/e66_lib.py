"""E66 shared library: protocol and seal checks, one scorer for every arm, paired quarter-cluster tests.

E66 reads the sealed files of E55-E65 and never writes into them; every output goes under E66/out and E66/tables.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

sys.dont_write_bytecode = True
E66 = Path(__file__).resolve().parents[1]
EXP = E66.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
OUT, TABLES = E66 / "out", E66 / "tables"

SEALED = {
    "E57": EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv",
    "E58": EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv",
    "E60": EXP / "E60_E58_Accuracy_Optimization" / "sealed" / "candidates.csv",
    "E61": EXP / "E61_E58_Low_Forecast_Investigation" / "sealed" / "candidates.csv",
    "E63": EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv",
    "E64": EXP / "E64_Objectives_1_3_Completion" / "sealed" / "candidates.csv",
}
EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
E55_BASELINES = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "baselines_20261017T154832Z" / "rows_baselines.csv"
E65_ROWS = EXP / "E65_El_Nino_Risk_Drop_Audit" / "tables" / "r3_rows50.csv"
E61_HUNGER = EXP / "E61_E58_Low_Forecast_Investigation" / "tables" / "d2_hunger_variants.csv"
LABELS = EXP / "E64_Objectives_1_3_Completion" / "tables" / "r4_target_labels.csv"
LATE_FROM = "2025-Q4"   # late regime: targets 2025-Q4..2026-Q3 (1 HIGH in 20 rows)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_protocol() -> str:
    want = (E66 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E66 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("E66 PROTOCOL.md changed after freezing")
    return got


def verify_sealed() -> dict:
    out = {}
    for k, p in SEALED.items():
        want = (p.parent / (p.name + ".sha256")).read_text().split()[0]
        if sha(p) != want:
            raise SystemExit(f"{p} changed after sealing")
        out[k] = want
    return out


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(obj, indent=1, default=float).encode("utf-8"))


def write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(df.to_csv(index=False, float_format="%.6g").encode("utf-8"))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(max(0, c - h)), float(min(1, c + h))]


def auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else float("nan")


def cal_slope(y, p):
    """Logistic recalibration slope of y on logit(p) (1 = well spread; < 1 over-confident)."""
    from sklearn.linear_model import LogisticRegression
    if not 0 < y.sum() < len(y):
        return float("nan")
    z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
    if np.ptp(z) < 1e-9:
        return float("nan")
    return float(LogisticRegression(C=1e6, max_iter=1000).fit(z, y).coef_[0, 0])


def metrics(R: pd.DataFrame, col: str, ycol: str = "HIGH", dec: str | None = None) -> dict:
    """Unified scorer. dec: optional column holding a 0/1 decision (warning rules); default p >= 0.5."""
    y = R[ycol].to_numpy(int)
    p = R[col].to_numpy(float)
    yh = R[dec].to_numpy(int) if dec else (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    out = {"n": int(len(R)), "quarters": int(R["target"].nunique()), "positives": int(y.sum()),
           "accuracy": (tp + tn) / len(y), "acc_wilson_lo": wilson(tp + tn, len(y))[0],
           "acc_wilson_hi": wilson(tp + tn, len(y))[1],
           "balanced_accuracy": 0.5 * (tp / max(tp + fn, 1) + tn / max(tn + fp, 1)),
           "precision_HIGH": tp / (tp + fp) if tp + fp else float("nan"), "recall_HIGH": tp / max(tp + fn, 1),
           "recall_LOW": tn / max(tn + fp, 1), "f1_HIGH": (2 * tp / (2 * tp + fp + fn)) if tp else 0.0,
           "false_alarms": fp, "missed_HIGH": fn, "brier": float(np.mean((p - y) ** 2)), "auc": auc(y, p),
           "cal_slope": cal_slope(y, p), "citl": float(y.mean() - p.mean())}
    if "ONSET" in R and ycol == "HIGH":
        on = R["ONSET"].to_numpy(int) == 1
        out["onsets_detected"] = f"{int(yh[on].sum())}/{int(on.sum())}"
    q = R.assign(c=(yh == y)).groupby("target")["c"].mean()
    out["quarters_acc_ge_0.75"] = int((q >= 0.75).sum())
    out["worst_quarter_acc"] = float(q.min())
    return out


def paired(R: pd.DataFrame, ref: str, arm: str, ycol: str = "HIGH", n_boot: int = 2000, seed: int = 66) -> dict:
    """Brier(arm) - Brier(ref) on the same rows: quarter-cluster bootstrap CI and quarter sign test (arm wins)."""
    y = R[ycol].to_numpy(float)
    d = (R[arm].to_numpy(float) - y) ** 2 - (R[ref].to_numpy(float) - y) ** 2
    d = pd.Series(d, index=R.index)
    dq = d.groupby(R["target"]).mean()
    nq = R.groupby("target").size()
    rng = np.random.default_rng(seed)
    qs = dq.index.to_numpy()
    boots = []
    for _ in range(n_boot):
        pick = rng.choice(qs, len(qs))
        boots.append(float((dq[pick] * nq[pick]).sum() / nq[pick].sum()))
    wins, losses = int((dq < -1e-12).sum()), int((dq > 1e-12).sum())
    p = binomtest(wins, wins + losses, 0.5, alternative="greater").pvalue if wins + losses else 1.0
    lo, hi = float(np.quantile(boots, .025)), float(np.quantile(boots, .975))
    return {"arm": arm, "reference": ref, "target_label": ycol, "mean_brier_diff": float(d.mean()), "ci95_lo": lo,
            "ci95_hi": hi, "quarter_wins": wins, "quarter_losses": losses, "sign_p": float(p),
            "better_by_rule": bool(hi < 0 and p < 0.05)}


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * ps[i])
        adj[i] = min(1.0, run)
    return adj.tolist()
