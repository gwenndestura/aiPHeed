"""
scripts/supplementary/reliability_diagnostics.py

Phases 2-8 of the 2026-10-08 reliability review. Diagnostic only: it reads the
pipeline's artifacts, changes nothing that is served, and writes
data/supplementary/reliability_diagnostics.json.

Evaluation protocol (identical for every design and reference)
  * Algorithm 3 as approved: one quarter ahead, features at quarter t paired
    with the label at t+1 within province (Rule 3), walk-forward expanding
    window, minimum 8 training quarters, one test quarter per fold.
  * The model sees only rows whose TARGET quarter precedes the test quarter.
  * No threshold, hyperparameter, scaling or feature is chosen from test data.
    The 0.50 decision cut-off is fixed. LightGBM runs with library defaults
    (Algorithm 3 specifies "a default LightGBM classifier"), so there is no
    random search to re-run until a split passes.
  * Equation 3's HIGH/LOW threshold is the label's definition and is never a
    model input.

    python -m scripts.supplementary.reliability_diagnostics
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
OUT = Path("data/supplementary/reliability_diagnostics.json")
MIN_TRAIN = 8
VINTAGE_POVERTY = True
P = Path("data/processed")


def qi(q: str) -> int:
    y, p = q.split("-Q")
    return int(y) * 4 + int(p) - 1


# --------------------------------------------------------------------- data
def load() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    f = pd.read_parquet(P / "features_fused.parquet")
    labels = pd.read_parquet(P / "labels.parquet")
    sws = pd.read_parquet(P / "sws_hunger.parquet")
    sws = sws.groupby("quarter")["pct_total_hunger"].first()

    f["t"] = f["quarter"].map(qi)
    # SWS hunger as Section 3.3.2.6 joins it: one value per quarter, sparse
    # quarters forward-filled from the last published round (never back-filled).
    grid = pd.DataFrame({"quarter": sorted(f["quarter"].unique())})
    grid["sws_hunger"] = grid["quarter"].map(sws).ffill()
    f = f.merge(grid, on="quarter", how="left")
    f["sws_hunger"] = f["sws_hunger"].fillna(0.0)

    # Rule 3 / Level 1: poverty incidence enters only once PSA has published
    # it. The matrix carries each survey year's figure from that same year,
    # but PSA released the 2021 provincial figures on 15 August 2022 and the
    # 2023 figures in August 2024. Each quarter here uses the latest release
    # available before it: 2018 survey through 2022-Q3, 2021 survey from
    # 2022-Q4, 2023 survey from 2024-Q4.
    if VINTAGE_POVERTY:
        def _vintage(g):
            by = g.assign(yr=g["quarter"].str[:4].astype(int)).groupby("yr")["poverty_incidence"].first()
            v18, v21, v23 = by.get(2020), by.get(2021), by.get(2023)
            return pd.Series([v18 if q <= "2022-Q3" else (v21 if q <= "2024-Q3" else v23)
                              for q in g["quarter"]], index=g.index)
        f["poverty_incidence"] = f.groupby("province_code", group_keys=False).apply(_vintage)

    candidates = [c for c in f.columns
                  if c not in ("province_code", "quarter", "t", "cpi_dev", "sws_hunger")
                  and pd.api.types.is_numeric_dtype(f[c])]
    return f, labels, candidates


def pairs(f: pd.DataFrame, labels: pd.DataFrame, k: int = 1) -> pd.DataFrame:
    lab = labels[["province_code", "quarter", "label_stress"]].copy()
    lab["t"] = lab["quarter"].map(qi) - k
    lab = lab.rename(columns={"label_stress": "y", "quarter": "target_quarter"})
    d = f.merge(lab, on=["province_code", "t"], how="inner")
    # Persistence reference: the province's last OBSERVED label at or before t.
    obs = labels[["province_code", "quarter", "label_stress"]].copy()
    obs["t"] = obs["quarter"].map(qi)
    full = f[["province_code", "t"]].merge(obs[["province_code", "t", "label_stress"]],
                                           on=["province_code", "t"], how="left")
    full = full.sort_values(["province_code", "t"])
    full["last_label"] = full.groupby("province_code")["label_stress"].ffill()
    return d.merge(full[["province_code", "t", "last_label"]], on=["province_code", "t"], how="left")


# --------------------------------------------------------------- evaluation
def walk(d: pd.DataFrame, cols: list[str], class_weight=None) -> pd.DataFrame:
    tq = sorted(d["target_quarter"].unique(), key=qi)
    rows = []
    for i in range(MIN_TRAIN, len(tq)):
        tr, te = d[d["target_quarter"].map(qi) < qi(tq[i])], d[d["target_quarter"] == tq[i]]
        if tr["y"].nunique() < 2:
            continue
        params = {"objective": "binary", "verbosity": -1, "random_state": 42}
        if class_weight:
            params["class_weight"] = class_weight
        m = LGBMClassifier(**params).fit(tr[cols], tr["y"])
        p = m.predict_proba(te[cols])[:, 1]
        rows.append(pd.DataFrame({"target_quarter": tq[i], "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": p, "last_label": te["last_label"].values}))
    return pd.concat(rows, ignore_index=True)


def metrics(y, pred, prob=None, by=None) -> dict:
    y, pred = np.asarray(y), np.asarray(pred)
    out = {
        "accuracy_pooled": round(float(accuracy_score(y, pred)), 4),
        "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
        "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
        "precision_high": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall_high": round(float(recall_score(y, pred, zero_division=0)), 4),
        "roc_auc": (round(float(roc_auc_score(y, prob)), 4)
                    if prob is not None and len(set(y)) > 1 and len(set(np.round(prob, 6))) > 1 else None),
        "confusion_matrix_[[TN,FP],[FN,TP]]": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }
    if by is not None:
        df = pd.DataFrame({"q": by, "c": (y == pred).astype(float)})
        fold = df.groupby("q")["c"].mean()
        out["accuracy_mean_fold"] = round(float(fold.mean()), 4)   # Algorithm 3's criterion
        year = df.assign(yr=df["q"].str[:4]).groupby("yr")["c"].mean().round(4).to_dict()
        out["accuracy_by_year"] = year
        out["accuracy_by_fold"] = fold.round(4).to_dict()
    return out


# ------------------------------------------------------------- diagnostics
def diagnostics(f: pd.DataFrame, labels: pd.DataFrame, candidates: list[str]) -> dict:
    l = labels.copy()
    per_q = l.groupby("quarter").agg(sws=("sws_hunger_pct", "first"), n=("label_stress", "size"),
                                     high=("label_stress", "sum")).reset_index()
    per_q = per_q.sort_values("quarter", key=lambda s: s.map(qi))

    # B. SWS contribution: Equation 3 decomposed into its two additive terms.
    s = l["stress_score"]
    term_sws = l["sws_hunger_pct"]
    term_cpi = s - term_sws
    between = l.groupby("quarter")["stress_score"].transform("mean")
    lab_by_sws = (l["sws_hunger_pct"] > l["global_threshold"]).astype(int)

    # C. Persistence of the label between consecutive observed quarters.
    o = l[["province_code", "quarter", "label_stress", "stress_score"]].copy()
    o["t"] = o["quarter"].map(qi)
    nxt = o.copy()
    nxt["t"] -= 1
    pp = o.merge(nxt, on=["province_code", "t"], suffixes=("", "_next"))

    # D/E. Feature variation across provinces and quarters.
    def variation(c):
        within_q = f.groupby("quarter")[c].nunique().gt(1).mean()
        within_p = f.groupby("province_code")[c].nunique().gt(1).mean()
        return {"varies_across_provinces_share_of_quarters": round(float(within_q), 3),
                "varies_across_quarters_share_of_provinces": round(float(within_p), 3)}
    eq5 = {c: variation(c) for c in EQUATION5_FEATURES}

    # H. Threshold stability: the median the label would have if set from the
    # quarters available up to each point.
    sq = per_q.dropna(subset=["sws"])
    expanding = []
    for i in range(4, len(per_q) + 1):
        seen = per_q.iloc[:i]["quarter"]
        med = float(l[l["quarter"].isin(seen)]["stress_score"].median())
        expanding.append({"through": per_q.iloc[i - 1]["quarter"], "median_stress": round(med, 2)})

    return {
        "A_label_by_quarter": per_q.assign(low=lambda x: x["n"] - x["high"]).to_dict(orient="records"),
        "B_sws_contribution": {
            "share_of_stress_variance_between_quarters": round(float(between.var() / s.var()), 4),
            "var_sws_term": round(float(term_sws.var()), 3),
            "var_cpi_term": round(float(term_cpi.var()), 3),
            "cov_terms_x2": round(float(2 * np.cov(term_sws, term_cpi)[0, 1]), 3),
            "label_agreement_with_sws_alone": round(float((lab_by_sws == l["label_stress"]).mean()), 4),
            "quarters_entirely_one_class": int(((per_q["high"] == 0) | (per_q["high"] == per_q["n"])).sum()),
        },
        "C_persistence": {
            "consecutive_pairs": int(len(pp)),
            "label_same_next_quarter": round(float((pp["label_stress"] == pp["label_stress_next"]).mean()), 4),
            "stress_autocorrelation": round(float(pp["stress_score"].corr(pp["stress_score_next"])), 4),
        },
        "D_E_equation5_feature_variation": eq5,
        "D_candidates_constant_within_every_quarter": [
            c for c in candidates if f.groupby("quarter")[c].nunique().max() <= 1],
        "G_sample_size": {"labelled_province_quarters": int(len(l)),
                          "labelled_quarters": int(l["quarter"].nunique()),
                          "quarters_without_sws": 24 - int(l["quarter"].nunique()),
                          "candidate_features": len(candidates)},
        "H_threshold": {"global_threshold": float(l["global_threshold"].iloc[0]),
                        "expanding_median": expanding},
    }


# --------------------------------------------------------------------- main
def main() -> dict:
    global MIN_TRAIN
    f, labels, candidates = load()
    d = pairs(f, labels, k=1)
    eq5 = list(EQUATION5_FEATURES)
    matrix_sws = candidates + ["cpi_dev", "sws_hunger"]

    designs = {
        "D0 current implementation: Eq.5, class_weight=balanced": (eq5, "balanced"),
        "D1 Algorithm 3 as written: Eq.5, default LightGBM": (eq5, None),
        "D2 Algorithm 3 input as written, SWS still excluded: 45-candidate matrix, default": (candidates + ["cpi_dev"], None),
        "D3 Algorithm 3 input as Section 3.3.2.6 builds it (incl. SWS hunger), default": (matrix_sws, None),
        "D4 Smallest correction: Eq.5 + SWS hunger at t, default": (eq5 + ["sws_hunger"], None),
    }
    results, ref = {}, None
    for name, (cols, cw) in designs.items():
        r = walk(d, cols, cw)
        if ref is None:
            ref = r
        pred = (r["p"] >= 0.5).astype(int)
        results[name] = metrics(r["y"], pred, r["p"].values, r["target_quarter"].values)

    y, q = ref["y"].values, ref["target_quarter"].values
    persist = ref["last_label"].fillna(0).astype(int).values
    baselines = {
        "always_HIGH": metrics(y, np.ones_like(y), None, q),
        "always_LOW": metrics(y, np.zeros_like(y), None, q),
        "persistence_last_observed_label": metrics(y, persist, None, q),
    }
    # F. class balance in each fold's training window vs test quarter
    tq = sorted(d["target_quarter"].unique(), key=qi)
    balance = []
    for i in range(MIN_TRAIN, len(tq)):
        tr = d[d["target_quarter"].map(qi) < qi(tq[i])]
        te = d[d["target_quarter"] == tq[i]]
        balance.append({"test_quarter": tq[i], "train_rows": int(len(tr)),
                        "train_high_share": round(float(tr["y"].mean()), 3),
                        "test_high": int(te["y"].sum()), "test_rows": int(len(te))})

    # Robustness of the two leading designs: training-window size and horizon.
    robust = {}
    for name in ("D2 Algorithm 3 input as written, SWS still excluded: 45-candidate matrix, default",
                 "D3 Algorithm 3 input as Section 3.3.2.6 builds it (incl. SWS hunger), default"):
        cols, cw = designs[name]
        rows = {}
        for mt in (6, 7, 8, 9, 10):
            MIN_TRAIN = mt
            rr = walk(pairs(f, labels, 1), cols, cw)
            rows[f"min_train={mt}"] = metrics(rr["y"], (rr["p"] >= 0.5).astype(int), rr["p"].values,
                                              rr["target_quarter"].values)["accuracy_mean_fold"]
        MIN_TRAIN = 8
        for k in (1, 2, 3, 4):
            rr = walk(pairs(f, labels, k), cols, cw)
            rows[f"k={k}"] = metrics(rr["y"], (rr["p"] >= 0.5).astype(int), rr["p"].values,
                                     rr["target_quarter"].values)["accuracy_mean_fold"]
        robust[name] = rows

    out = {
        "robustness": robust,
        "vintage_poverty": VINTAGE_POVERTY,
        "protocol": "k=1 forward pairing, walk-forward, min 8 training quarters, default LightGBM, cut-off 0.50",
        "n_test_rows": int(len(ref)), "n_test_quarters": int(ref["target_quarter"].nunique()),
        "diagnostics": diagnostics(f, labels, candidates),
        "F_class_balance_by_fold": balance,
        "designs": results,
        "baselines": baselines,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    o = main()
    print("test rows", o["n_test_rows"], "quarters", o["n_test_quarters"])
    for k, v in {**o["baselines"], **o["designs"]}.items():
        print(f"{k[:78]:78s} meanfold={v.get('accuracy_mean_fold')} pooled={v['accuracy_pooled']} "
              f"F1w={v['f1_weighted']} AUC={v['roc_auc']} byyear={v.get('accuracy_by_year')}")
    print(json.dumps(o["diagnostics"]["B_sws_contribution"], indent=1))
    print(json.dumps(o["diagnostics"]["C_persistence"], indent=1))
