"""
scripts/supplementary/experiment_reliability.py

Diagnostic for the 75% reliability question (not served, not part of the
approved pipeline). Walk-forward, one quarter ahead (features at t, label at
t+1, Rule 3), minimum 8 training quarters, default LightGBM as Algorithm 3
specifies. Every design is compared with the trivial references on the SAME
test rows, because on this label a model with no skill can clear 75%.

Designs
  E0  Equation 5 as approved
  E1  E0 + last published SWS hunger and its change (past data only)
  E2  E1 + the province's last observed label (autoregressive term)
  E3  E1 with logistic regression instead of LightGBM (size check)
References
  always_high, training_majority, persistence (label at t -> label at t+1),
  sws_persistence (stress at t above the global threshold)
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
K = 1
MIN_TRAIN = 8


def qi(q: str) -> int:
    y, p = q.split("-Q")
    return int(y) * 4 + int(p) - 1


def build() -> pd.DataFrame:
    f = pd.read_parquet("data/processed/features_fused.parquet")
    l = pd.read_parquet("data/processed/labels.parquet")
    sws = pd.read_parquet("data/processed/sws_hunger.parquet")
    scol = next(c for c in sws.columns if "hunger" in c.lower() and "pct" in c.lower())
    sws = sws.groupby("quarter")[scol].first().rename("sws").reset_index()
    f["t"] = f["quarter"].map(qi)
    sws["t"] = sws["quarter"].map(qi)
    # Last PUBLISHED SWS at t: carried forward only from earlier/equal quarters.
    grid = pd.DataFrame({"t": sorted(f["t"].unique())}).merge(sws[["t", "sws"]], on="t", how="left")
    grid["sws_last"] = grid["sws"].ffill()
    grid["sws_change"] = grid["sws_last"] - grid["sws_last"].shift(1)
    f = f.merge(grid[["t", "sws_last", "sws_change"]], on="t", how="left")
    lab = l[["province_code", "quarter", "label_stress", "stress_score"]].copy()
    lab["t"] = lab["quarter"].map(qi)
    f = f.merge(lab[["province_code", "t", "label_stress", "stress_score"]], on=["province_code", "t"], how="left")
    f = f.sort_values(["province_code", "t"])
    f["label_last"] = f.groupby("province_code")["label_stress"].transform(lambda s: s.ffill())
    f["stress_last"] = f.groupby("province_code")["stress_score"].transform(lambda s: s.ffill())
    tgt = lab[["province_code", "t", "label_stress"]].rename(columns={"label_stress": "y"})
    tgt["t"] -= K
    return f.merge(tgt, on=["province_code", "t"], how="inner")  # features(t) -> y(t+1)


def walk(d: pd.DataFrame, cols: list[str], model: str = "lgbm") -> pd.DataFrame:
    out = []
    ts = sorted(d["t"].unique())
    for i in range(MIN_TRAIN, len(ts)):
        tr, te = d[d["t"] < ts[i]], d[d["t"] == ts[i]]
        if tr["y"].nunique() < 2:
            continue
        X, Xt = tr[cols].fillna(0.0), te[cols].fillna(0.0)
        if model == "lgbm":
            m = LGBMClassifier(objective="binary", verbosity=-1, random_state=42, class_weight="balanced")
        else:
            m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
        m.fit(X, tr["y"])
        p = m.predict_proba(Xt)[:, 1]
        out.append(pd.DataFrame({"t": ts[i], "y": te["y"].values, "p": p,
                                 "majority": float(tr["y"].mean() >= 0.5),
                                 "persist": te["label_last"].values,
                                 "stress_last": te["stress_last"].values}))
    return pd.concat(out, ignore_index=True)


def score(r: pd.DataFrame, pred: np.ndarray, prob: np.ndarray | None = None) -> dict:
    fold_acc = r.assign(c=(pred == r["y"]).astype(float)).groupby("t")["c"].mean()
    auc = roc_auc_score(r["y"], prob) if prob is not None and r["y"].nunique() > 1 else float("nan")
    return {"mean_fold_acc": round(float(fold_acc.mean()), 4),
            "pooled_acc": round(float(accuracy_score(r["y"], pred)), 4), "auc": round(float(auc), 4)}


def main() -> None:
    d = build()
    thr = pd.read_parquet("data/processed/labels.parquet")["global_threshold"].iloc[0]
    eq5 = list(EQUATION5_FEATURES)
    designs = {
        "E0 Eq5 (approved)": (eq5, "lgbm"),
        "E1 Eq5 + lagged SWS": (eq5 + ["sws_last", "sws_change"], "lgbm"),
        "E2 E1 + last label": (eq5 + ["sws_last", "sws_change", "label_last"], "lgbm"),
        "E3 E1, logistic": (eq5 + ["sws_last", "sws_change"], "logit"),
        "E4 lagged SWS only, logistic": (["sws_last", "sws_change"], "logit"),
    }
    ref = None
    for name, (cols, model) in designs.items():
        r = walk(d, cols, model)
        if ref is None:
            ref = r
            n = len(r)
            print(f"test rows {n}, test quarters {r['t'].nunique()}, share HIGH {r['y'].mean():.3f}")
            print(f"  {'always_high':32s}", score(r, np.ones(n, int)))
            print(f"  {'training majority':32s}", score(r, r['majority'].astype(int).values))
            pm = r["persist"].fillna(r["majority"]).astype(int).values
            print(f"  {'persistence (label t)':32s}", score(r, pm))
            sp = (r["stress_last"] > thr).astype(int).values
            print(f"  {'stress_t > threshold':32s}", score(r, sp, r["stress_last"].fillna(thr).values))
        print(f"  {name:32s}", score(r, (r["p"] >= 0.5).astype(int).values, r["p"].values))


if __name__ == "__main__" and __import__("sys").argv[-1] != "more":
    main()


def more() -> None:
    """Round 2: autoregressive stress term, regularization, small models."""
    d = build()
    d = d.sort_values(["province_code", "t"])
    d["cpi_dev_last"] = d["cpi_dev"]
    eq5 = list(EQUATION5_FEATURES)
    reg = dict(objective="binary", verbosity=-1, random_state=42,
               n_estimators=200, learning_rate=0.03, num_leaves=4, min_child_samples=10)
    designs = {
        "E5 Eq5 + stress_last + SWS (default)": (eq5 + ["stress_last", "sws_last", "sws_change"], None, "lgbm"),
        "E6 E5, regularized": (eq5 + ["stress_last", "sws_last", "sws_change"], reg, "lgbm"),
        "E7 E5, regularized, no class weight": (eq5 + ["stress_last", "sws_last", "sws_change"], {**reg, "nocw": 1}, "lgbm"),
        "E8 logistic: stress_last + sws_change + cpi_dev + FSSI": (["stress_last", "sws_change", "cpi_dev", "FSSI"], None, "logit"),
        "E9 logistic: stress_last + sws_change": (["stress_last", "sws_change"], None, "logit"),
    }
    for name, (cols, params, kind) in designs.items():
        out = []
        ts = sorted(d["t"].unique())
        for i in range(MIN_TRAIN, len(ts)):
            tr, te = d[d["t"] < ts[i]], d[d["t"] == ts[i]]
            tr = tr.dropna(subset=["stress_last"]) if "stress_last" in cols else tr
            X, Xt = tr[cols].fillna(0.0), te[cols].fillna(0.0)
            if kind == "lgbm":
                p_ = dict(params or {"objective": "binary", "verbosity": -1, "random_state": 42})
                nocw = p_.pop("nocw", 0)
                if not nocw:
                    p_["class_weight"] = "balanced"
                m = LGBMClassifier(**p_)
            else:
                m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
            m.fit(X, tr["y"])
            p = m.predict_proba(Xt)[:, 1]
            out.append(pd.DataFrame({"t": ts[i], "y": te["y"].values, "p": p}))
        r = pd.concat(out, ignore_index=True)
        print(f"  {name:52s}", score(r, (r['p'] >= 0.5).astype(int).values, r['p'].values))


if __name__ == "__main__" and __import__("sys").argv[-1] == "more":
    more()
