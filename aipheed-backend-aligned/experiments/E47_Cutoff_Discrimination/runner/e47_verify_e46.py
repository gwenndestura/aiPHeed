"""E47: recompute the E46 headline metrics from the raw committed predictions and freshly recomputed T43 labels, with
sklearn only (independent of the E44/E46 metric code), and report how much of each accuracy comes from LOW calls.

    backend/venv/Scripts/python.exe -B runner/e47_verify_e46.py   -> runs/verify_e46_metrics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E47 = HERE.parent
EXP = E47.parent
sys.path.insert(0, str(EXP / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L, np, pd = K.L, K.np, K.pd
S44_Q = ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]


def metrics(y, yhat, p=None):
    from sklearn.metrics import confusion_matrix, roc_auc_score
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    rh = tp / (tp + fn) if tp + fn else None
    rl = tn / (tn + fp) if tn + fp else None
    pr = tp / (tp + fp) if tp + fp else None
    out = {"n": int(len(y)), "accuracy": float((y == yhat).mean()),
           "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2, "recall_HIGH": rh, "recall_LOW": rl,
           "precision_HIGH": pr, "f1_HIGH": (2 * pr * rh / (pr + rh)) if pr and rh else None,
           "confusion": {"TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)},
           "share_predicted_LOW": float((yhat == 0).mean()),
           "accuracy_from_LOW_calls": float(((yhat == 0) & (y == 0)).sum() / len(y))}
    if p is not None:
        out["brier"] = float(np.mean((p - y) ** 2))
        out["auc"] = float(roc_auc_score(y, p)) if len(set(y)) == 2 else None
    return out


def main():
    lab = K.label_frame(L.load())[["province_code", "q", "y"]].rename(columns={"q": "target_q", "y": "y_t43"})
    runs = EXP / "E46_Rice_Policy" / "runs"
    P7 = pd.read_csv(runs / "i7_20261017T000111Z" / "predictions_i7.csv", dtype={"province_code": str})
    P8 = pd.read_csv(runs / "i8_20261017T001227Z" / "predictions_i8.csv", dtype={"province_code": str})
    P1 = pd.read_csv(EXP / "E44_Five_Trigger_Optimization" / "runs" / "20261015T150213Z" / "predictions.csv",
                     dtype={"province_code": str})
    P = (P1[["t", "province_code", "target_q", "y", "I2_p", "I2_yhat", "B-persist_p", "B-persist_yhat"]]
         .merge(P7[["t", "province_code", "I7_p", "I7_yhat"]], on=["t", "province_code"])
         .merge(P8[["t", "province_code", "I8_p", "I8_yhat"]], on=["t", "province_code"])
         .merge(lab, on=["province_code", "target_q"], how="left"))
    out = {"label_check": None, "S44": {}, "EXT": {}}
    lb = P.dropna(subset=["y"])
    out["label_check"] = {"rows": int(len(lb)), "stored_equals_recomputed": bool((lb["y"] == lb["y_t43"]).all())}
    for nm, qs in (("S44", S44_Q), ("EXT", ["2024-Q2"] + S44_Q)):
        S = P[P["target_q"].map(L.qs).isin(qs) & P["y"].notna()]
        y = S["y"].astype(int).to_numpy()
        out[nm]["rows"], out[nm]["quarters"], out[nm]["HIGH"] = int(len(S)), int(S["target_q"].nunique()), int(y.sum())
        for a in ("I7", "I8", "I2", "B-persist"):
            out[nm][a] = metrics(y, S[f"{a}_yhat"].astype(int).to_numpy(), S[f"{a}_p"].to_numpy())
            out[nm][a]["by_quarter"] = {L.qs(int(q)): float((g[f"{a}_yhat"] == g["y"]).mean())
                                        for q, g in S.groupby("target_q")}
        out[nm]["always_LOW"] = metrics(y, np.zeros_like(y))
    (E47 / "runs" / "verify_e46_metrics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: (v if k == "label_check" else {a: (round(m["accuracy"], 3), m.get("balanced_accuracy"), m.get("recall_HIGH"),
                                                            m.get("brier"), m.get("auc"), m["confusion"]) if isinstance(m, dict) and "accuracy" in m else m
                                                        for a, m in v.items()}) for k, v in out.items()}, indent=0, default=str))


if __name__ == "__main__":
    main()
