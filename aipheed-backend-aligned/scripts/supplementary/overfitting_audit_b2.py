"""
scripts/supplementary/overfitting_audit_b2.py

Overfitting and reliability audit of the governing 45-candidate MODEL-B2
(config/governing_model.json). Supplementary only: it reads the frozen
configuration and evidence, never overwrites them, never tunes on the outer
test quarters, and serves nothing.

Fixed outer protocol (unchanged): strict-timing frame, k = 1, expanding
window, 11 outer test quarters (2022-Q4 .. 2025-Q4, 55 rows), seed 42,
cut-off 0.50. Anything chosen (configuration, feature subset) is chosen inside
each outer fold from its training quarters only, by an inner walk-forward with
at least 5 inner target quarters. Ties are broken by a fixed, pre-declared
order, never by outer results.

    python -m scripts.supplementary.overfitting_audit_b2

Writes evidence/2026-10-09_overfitting_audit/.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import binomtest
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             f1_score, log_loss, precision_score, recall_score, roc_auc_score)

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
CFG_PATH = Path("config/governing_model.json")
CFG = json.loads(CFG_PATH.read_text())
OUT = Path("evidence/2026-10-09_overfitting_audit")
ROWS55 = Path("evidence/2026-10-08_b2_robustness/outer_test_rows_55.csv")
SEED = CFG["seed"]
OUTER_MIN = CFG["walk_forward"]["outer_min_target_quarters"]
INNER_MIN = 5
THR = CFG["decision_threshold"]
KEY = ["target_quarter", "province_code"]
N_BOOT = 10000

GOV = CFG["feature_set"]["model_inputs"]
LIT45 = CFG["feature_set"]["candidates_section_3_3_2_6"]
EQ5 = list(EQUATION5_FEATURES)
FOOD_LEVELS = ["rice_price_regular", "rice_price_regular_lag1", "food_cpi", "headline_cpi",
               "commodity_fruit_veg", "commodity_leafy_veg", "commodity_livestock",
               "commodity_poultry", "commodity_rootcrops"]
OTHER_LEVELS = ["diesel_php_per_l", "diesel_php_per_l_lag1", "gasoline_php_per_l",
                "brent_usd_per_bbl", "fx_usd_php_avg"]
PRICE_TRANSFORMS = ["food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "cpi_dev",
                    "food_minus_headline_yoy", "food_minus_headline_yoy_lag1",
                    "food_minus_headline_yoy_accel", "rice_price_regular_accel", "diesel_php_per_l_accel"]
COMMODITY = [c for c in FOOD_LEVELS if c.startswith("commodity_")]
NEAR_CLOCK = ["headline_cpi", "food_cpi"]          # index levels; declared before running
# Pre-declared order for the nested configuration choice (Chapter III's
# documented 12-feature reading first); used only to break exact ties.
NESTED_ORDER = ["eq5_12_default", "eq5_12_weighted", "gov47_default", "gov47_weighted", "lit45_weighted"]
NESTED_SETS = {"eq5_12_default": (EQ5, False), "eq5_12_weighted": (EQ5, True),
               "gov47_default": (GOV, False), "gov47_weighted": (GOV, True),
               "lit45_weighted": (LIT45, True)}


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def qs(d):
    return sorted(d["target_quarter"].unique(), key=R.qi)


def fit(tr, cols, weighted=True):
    params = dict(CFG["lightgbm_params"])
    if weighted:
        pos = tr["y"].mean()
        params["scale_pos_weight"] = float((1 - pos) / pos)
    return LGBMClassifier(**params).fit(tr[cols], tr["y"])


def splits(d, start):
    tq = qs(d)
    for i in range(start, len(tq)):
        yield tq[i], d[d["target_quarter"].map(R.qi) < R.qi(tq[i])], d[d["target_quarter"] == tq[i]]


def walk(d, cols, weighted=True, start=OUTER_MIN):
    rows = []
    for q, tr, te in splits(d, start):
        if tr["y"].nunique() < 2:
            continue
        p = fit(tr, cols, weighted).predict_proba(te[cols])[:, 1]
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": p}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= THR).astype(int)
    return r


def inner_score(train, cols, weighted):
    r = walk(train, cols, weighted, start=INNER_MIN)
    return float(r.assign(c=(r["y"] == r["pred"]).astype(float)).groupby("target_quarter")["c"].mean().mean()), r


def m_all(y, pred, p=None, q=None):
    y, pred = np.asarray(y).astype(int), np.asarray(pred).astype(int)
    out = {"n": int(len(y)), "correct": int((y == pred).sum()),
           "accuracy": round(float(accuracy_score(y, pred)), 4),
           "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
           "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
           "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
           "precision_high": round(float(precision_score(y, pred, zero_division=0)), 4),
           "recall_high": round(float(recall_score(y, pred, zero_division=0)), 4)}
    if p is not None and len(set(y)) == 2:
        p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
        out.update({"roc_auc": round(float(roc_auc_score(y, p)), 4),
                    "pr_auc": round(float(average_precision_score(y, p)), 4),
                    "prevalence": round(float(y.mean()), 4),
                    "brier": round(float(brier_score_loss(y, p)), 4),
                    "log_loss": round(float(log_loss(y, p)), 4)})
    if q is not None:
        df = pd.DataFrame({"q": q, "c": (y == pred).astype(float)})
        fold = df.groupby("q")["c"].mean()
        out["accuracy_mean_fold"] = round(float(fold.mean()), 4)
        out["accuracy_by_year"] = df.assign(yr=df["q"].str[:4]).groupby("yr")["c"].mean().round(4).to_dict()
    return out


def summ(r):
    return m_all(r["y"], r["pred"], r["p"] if "p" in r and r["p"].notna().all() else None, r["target_quarter"])


def boot_quarters(values_by_q, n=N_BOOT, seed=SEED):
    v = np.asarray(values_by_q, float)
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(n, len(v)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)], means


def paired(a, b, q):
    """a, b: boolean correctness arrays on the same rows."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    x, z = int((a & ~b).sum()), int((~a & b).sum())
    df = pd.DataFrame({"q": q, "a": a.astype(float), "b": b.astype(float)}).groupby("q").mean()
    diff = (df["a"] - df["b"]).values
    ci, means = boot_quarters(diff)
    better, worse = int((diff > 0).sum()), int((diff < 0).sum())
    return {"a_right_b_wrong": x, "b_right_a_wrong": z,
            "mcnemar_exact_p": round(float(binomtest(x, x + z, 0.5).pvalue), 4) if x + z else 1.0,
            "mean_quarter_difference": round(float(diff.mean()), 4),
            "quarter_bootstrap_95ci": ci,
            "quarters_a_better_tie_worse": [better, int(len(diff) - better - worse), worse],
            "quarter_sign_test_p": round(float(binomtest(better, better + worse, 0.5).pvalue), 4) if better + worse else 1.0}


def calib_table(y, p, bins=5):
    y, p = np.asarray(y), np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    rows, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if m.sum():
            rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": int(m.sum()), "mean_p": round(float(p[m].mean()), 3),
                         "observed_high": round(float(y[m].mean()), 3)})
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    return rows, round(float(ece), 4)


# ===================================================================== main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    f, labels, cols = A.frame_t2()
    assert cols == GOV, "frame does not produce the governing inputs"
    d = R.pairs(f, labels, 1)
    d["time_index"] = d["t"]
    frame = d[["province_code", "t", "target_quarter", "y"] + GOV].sort_values(KEY)
    res["provenance"] = {
        "config_sha256": sha_file(CFG_PATH),
        "input_frame_sha256": hashlib.sha256(pd.util.hash_pandas_object(frame.round(10), index=False).values.tobytes()).hexdigest(),
        "frozen_input_frame_sha256": CFG["frozen_from"]["input_frame_sha256"],
        "data_sha256": {p: sha_file(p) for p in ("data/processed/features_fused.parquet", "data/processed/labels.parquet",
                                                 "data/processed/sws_hunger.parquet", "data/processed/commodity_prices.parquet",
                                                 "data/processed/cpi_full.parquet")},
        "rows55_file_sha256": sha_file(ROWS55),
        "script_sha256": sha_file(__file__),
        "features": GOV, "n_features": len(GOV), "seed": SEED, "outer_min": OUTER_MIN, "inner_min": INNER_MIN,
        "lightgbm_params": CFG["lightgbm_params"], "threshold": THR,
        "outer_test_quarters": qs(d)[OUTER_MIN:], "paired_rows_total": int(len(d)),
        "explicit_time_features_in_governing_set": [c for c in GOV if c in ("t", "time_index", "quarter", "year")],
    }

    # ------------------------------------------------- reference outer run
    gov = walk(d, GOV)
    ref = pd.read_csv("evidence/2026-10-08_optimization/best_candidate_predictions.csv")
    mg = gov.merge(ref, on=KEY, suffixes=("", "_ref"))
    res["outer_reproduction"] = {"rows": int(len(mg)), "identical_predictions": bool((mg["pred"] == mg["pred_ref"]).all()),
                                 "max_prob_diff": float((mg["p"] - mg["p_ref"]).abs().max()), "metrics": summ(gov)}
    gov.to_csv(OUT / "outer_predictions_governing.csv", index=False)

    # ---------------------------------- A. training / inner / outer gap
    gap_rows, inner_all = [], []
    for q, tr, te in splits(d, OUTER_MIN):
        m = fit(tr, GOV)
        ptr = m.predict_proba(tr[GOV])[:, 1]
        pte = m.predict_proba(te[GOV])[:, 1]
        isc, ir = inner_score(tr, GOV, True)
        inner_all.append(ir.assign(outer_fold=q))
        gap_rows.append({"outer_test_quarter": q, "n_train": len(tr), "train_quarters": tr["target_quarter"].nunique(),
                         "train_accuracy": round(float(((ptr >= THR) == tr["y"]).mean()), 4),
                         "train_auc": round(float(roc_auc_score(tr["y"], ptr)), 4),
                         "train_brier": round(float(brier_score_loss(tr["y"], ptr)), 4),
                         "inner_val_accuracy_mean_fold": round(isc, 4), "inner_val_rows": len(ir),
                         "inner_val_auc": round(float(roc_auc_score(ir["y"], ir["p"])), 4) if ir["y"].nunique() == 2 else None,
                         "outer_accuracy": round(float(((pte >= THR) == te["y"]).mean()), 4),
                         "n_trees": int(m.booster_.num_trees()),
                         "n_splits": int(m.booster_.feature_importance("split").sum())})
    gap = pd.DataFrame(gap_rows)
    gap.to_csv(OUT / "train_inner_outer_by_fold.csv", index=False)
    res["A_generalization_gap"] = {
        "mean_train_accuracy": round(float(gap["train_accuracy"].mean()), 4),
        "mean_train_auc": round(float(gap["train_auc"].mean()), 4),
        "mean_inner_val_accuracy": round(float(gap["inner_val_accuracy_mean_fold"].mean()), 4),
        "mean_outer_accuracy": round(float(gap["outer_accuracy"].mean()), 4),
        "train_minus_outer": round(float(gap["train_accuracy"].mean() - gap["outer_accuracy"].mean()), 4),
        "by_fold": gap.to_dict(orient="records"),
    }

    # ------------------------------------------- B. nested selection
    nested_rows, choices, sel_rows = [], [], []
    for q, tr, te in splits(d, OUTER_MIN):
        scores = {k: inner_score(tr, cs, w)[0] for k, (cs, w) in NESTED_SETS.items()}
        top = max(scores.values())
        chosen = next(k for k in NESTED_ORDER if abs(scores[k] - top) < 1e-12)
        cs, w = NESTED_SETS[chosen]
        p = fit(tr, cs, w).predict_proba(te[cs])[:, 1]
        nested_rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                         "y": te["y"].values, "p": p}))
        choices.append({"outer_test_quarter": q, "chosen": chosen, "inner_scores": {k: round(v, 4) for k, v in scores.items()}})
        # In-fold feature selection analogous to Section 3.3.2.7 (correlation
        # filter |r| > 0.85, then top 12 by training gain), training data only.
        X = tr[GOV]
        corr = X.corr().abs().fillna(0)
        keep = []
        for c in GOV:
            if X[c].nunique() <= 1:
                continue
            if all(corr.loc[c, k] <= 0.85 for k in keep):
                keep.append(c)
        g = pd.Series(fit(tr, keep).booster_.feature_importance("gain"), index=keep).sort_values(ascending=False)
        sel = list(g.index[:12])
        ps = fit(tr, sel).predict_proba(te[sel])[:, 1]
        sel_rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                      "y": te["y"].values, "p": ps, "selected": [",".join(sel)] * len(te)}))
    nested = pd.concat(nested_rows, ignore_index=True)
    nested["pred"] = (nested["p"] >= THR).astype(int)
    infold = pd.concat(sel_rows, ignore_index=True)
    infold["pred"] = (infold["p"] >= THR).astype(int)
    res["B_nested"] = {
        "nested_configuration_choice": {"metrics": summ(nested), "per_fold": choices,
                                        "times_chosen": pd.Series([c["chosen"] for c in choices]).value_counts().to_dict()},
        "infold_feature_selection_corr_then_top12": {"metrics": summ(infold),
                                                     "selected_by_fold": infold.groupby("target_quarter")["selected"].first().to_dict()},
        "governing_protocol_audit": {
            "feature_set": "fixed by configuration; not selected per fold",
            "hyperparameters": "LightGBM library defaults; none tuned",
            "class_weight": "scale_pos_weight from the fold's training HIGH share only",
            "threshold": "fixed 0.50",
            "imputation": "forward fill within province (past values only) then zero fill; no statistics fitted across folds",
            "cpi_dev": "province mean of prior 4 quarters only",
            "label_threshold": "global median of all 95 labelled stress scores (14.6), which includes the test quarters",
        },
    }

    # -------------------------- label-threshold sensitivity (diagnostic)
    lab = labels.set_index(["province_code", "quarter"])["stress_score"]
    d_ss = d.assign(stress=[lab.get((p, q)) for p, q in zip(d["province_code"], d["target_quarter"])])
    lt_rows = []
    for q, tr, te in splits(d_ss, OUTER_MIN):
        thr_q = float(tr["stress"].median())
        tr2, te2 = tr.assign(y=(tr["stress"] > thr_q).astype(int)), te.assign(y=(te["stress"] > thr_q).astype(int))
        if tr2["y"].nunique() < 2:
            continue
        p = fit(tr2, GOV).predict_proba(te2[GOV])[:, 1]
        lt_rows.append(pd.DataFrame({"target_quarter": q, "province_code": te2["province_code"].values,
                                     "y": te2["y"].values, "p": p, "threshold": thr_q,
                                     "y_global": te["y"].values}))
    lt = pd.concat(lt_rows, ignore_index=True)
    lt["pred"] = (lt["p"] >= THR).astype(int)
    res["label_threshold_sensitivity"] = {
        "note": "Diagnostic only; the approved target (global median 14.6) is unchanged.",
        "thresholds_by_fold": lt.groupby("target_quarter")["threshold"].first().round(2).to_dict(),
        "test_labels_changed": int((lt["y"] != lt["y_global"]).sum()),
        "metrics_training_median_labels": summ(lt),
    }

    # ------------------------------------------ C. quarter-level stability
    rows55 = pd.read_csv(ROWS55)
    g = gov.merge(rows55[KEY + ["province", "persistence_naive", "persistence_timing_valid", "pred_baseline", "p_baseline"]], on=KEY)
    g["correct"] = (g["y"] == g["pred"]).astype(int)
    qt = g.groupby("target_quarter").agg(rows=("y", "size"), high=("y", "sum"), correct=("correct", "sum"),
                                         predicted_high=("pred", "sum")).reset_index()
    qt["accuracy"] = qt["correct"] / qt["rows"]
    qt["quarter_single_class"] = qt["high"].isin([0, 5])
    qt["model_predicted_one_class"] = qt["predicted_high"].isin([0, 5])
    qt["majority_class_share"] = np.maximum(qt["high"], 5 - qt["high"]) / 5
    qt.to_csv(OUT / "quarter_level.csv", index=False)
    acc_q = qt.set_index("target_quarter")["accuracy"]
    ci_q, _ = boot_quarters(acc_q.values)
    loqo = {q: round(float(acc_q.drop(q).mean()), 4) for q in acc_q.index}
    years = sorted({q[:4] for q in acc_q.index})
    drop_year = {y: round(float(acc_q[[q for q in acc_q.index if not q.startswith(y)]].mean()), 4) for y in years}
    # Within-quarter (cross-province) discrimination: rows whose class is the
    # minority within their quarter, and AUC inside mixed quarters.
    g = g.merge(qt[["target_quarter", "high"]].rename(columns={"high": "q_high"}), on="target_quarter")
    g["q_majority"] = (g["q_high"] >= 3).astype(int)
    minority = g[g["y"] != g["q_majority"]]
    mixed = qt[~qt["quarter_single_class"]]["target_quarter"]
    within_auc = {q: round(float(roc_auc_score(g[g["target_quarter"] == q]["y"], g[g["target_quarter"] == q]["p"])), 3)
                  for q in mixed}
    res["C_quarter_level"] = {
        "table": qt.round(3).to_dict(orient="records"),
        "quarters_at_or_above_0.75": int((acc_q >= 0.75).sum()), "n_quarters": int(len(acc_q)),
        "quarter_bootstrap_95ci_mean_accuracy": ci_q,
        "leave_one_quarter_out_mean_accuracy": loqo,
        "loqo_range": [min(loqo.values()), max(loqo.values())],
        "drop_one_year_mean_accuracy": drop_year,
        "single_class_quarters": int(qt["quarter_single_class"].sum()),
        "quarters_model_predicted_one_class": int(qt["model_predicted_one_class"].sum()),
        "quarter_majority_oracle_accuracy": round(float(qt["majority_class_share"].mean()), 4),
        "minority_within_quarter_rows": int(len(minority)),
        "minority_within_quarter_correct": int((minority["y"] == minority["pred"]).sum()),
        "within_quarter_auc_mixed_quarters": within_auc,
        "mean_within_quarter_auc": round(float(np.mean(list(within_auc.values()))), 3) if within_auc else None,
        "effective_temporal_units": int(len(acc_q)),
    }
    sens = {}
    for mt in (6, 7, 8, 9, 10):
        r_ = walk(d, GOV, True, start=mt)
        s_ = summ(r_)
        sens[f"min_train={mt}"] = {"test_quarters": int(r_["target_quarter"].nunique()),
                                   "accuracy_mean_fold": s_["accuracy_mean_fold"], "roc_auc": s_.get("roc_auc")}
    sub = {"2023_onward": gov[gov["target_quarter"] >= "2023-Q1"], "2024_onward": gov[gov["target_quarter"] >= "2024-Q1"],
           "through_2023": gov[gov["target_quarter"] < "2024-Q1"]}
    for k, v in sub.items():
        s_ = summ(v)
        sens[k] = {"rows": int(len(v)), "accuracy_mean_fold": s_["accuracy_mean_fold"], "roc_auc": s_.get("roc_auc")}
    res["C_period_sensitivity"] = sens

    # ------------------------------------------- D. ablation (fixed outer)
    PRICE_ALL = FOOD_LEVELS + OTHER_LEVELS + PRICE_TRANSFORMS
    sets = {
        "gov47_all (MODEL-B2)": GOV,
        "lit45_candidates_only": LIT45,
        "eq5_12": EQ5,
        "no_food_price_levels": [c for c in GOV if c not in FOOD_LEVELS],
        "no_price_levels": [c for c in GOV if c not in FOOD_LEVELS + OTHER_LEVELS],
        "no_price_related": [c for c in GOV if c not in PRICE_ALL],
        "no_constructed_commodity": [c for c in GOV if c not in COMMODITY],
        "no_index_levels_near_clock": [c for c in GOV if c not in NEAR_CLOCK],
        "gov47_plus_time_index": GOV + ["time_index"],
        "clock_only (time_index)": ["time_index"],
    }
    abl, abl_preds = {}, []
    for name, cs in sets.items():
        rw, rd = walk(d, cs, True), walk(d, cs, False)
        abl[name] = {"n_features": len(cs), "weighted": summ(rw),
                     "default": {k: summ(rd)[k] for k in ("correct", "accuracy_mean_fold", "roc_auc", "accuracy_by_year")}}
        abl_preds.append(rw.assign(variant=name))
    abl["infold_selected_12 (Section 3.3.2.7 analogue)"] = {"n_features": 12, "weighted": summ(infold)}
    pd.concat(abl_preds).to_csv(OUT / "ablation_predictions.csv", index=False)
    res["D_ablation"] = abl

    # commodity construction check from the raw table
    comm = pd.read_parquet("data/processed/commodity_prices.parquet")
    cpi = pd.read_parquet("data/processed/cpi_full.parquet")
    anchor = comm[comm["quarter"] == "2021-Q4"].set_index(["province_code", "commodity_group", "commodity"])["price_php_per_kg"]
    post = comm[comm["quarter"] >= "2022-Q1"].merge(cpi[["province_code", "quarter", "cpi_food_yoy_pct"]],
                                                    on=["province_code", "quarter"], how="left")
    post["anchor"] = [anchor.get((a, b, c)) for a, b, c in zip(post["province_code"], post["commodity_group"], post["commodity"])]
    post["reconstructed"] = (post["anchor"] * (1 + post["cpi_food_yoy_pct"].fillna(0) / 100)).round(2)
    dev = (post["reconstructed"] - post["price_php_per_kg"]).abs()
    fused = pd.read_parquet("data/processed/features_fused.parquet")
    gain = pd.read_csv("evidence/2026-10-08_optimization/best_candidate_feature_importance.csv", index_col=0)["mean_gain_share"]
    res["D_commodity_construction"] = {
        "rows_2022_onward": int(len(post)),
        "rows_exactly_reconstructed_(abs_diff<=0.005)": int((dev <= 0.005).sum()),
        "max_abs_difference": round(float(dev.max()), 4),
        "formula": "price(q) = price(2021-Q4, province, item) x (1 + food CPI YoY(q, province)/100)",
        "fused_matrix_uses_these_rows": bool(fused[fused["quarter"] >= "2022-Q1"]["commodity_rootcrops"].notna().all()),
        "b2_gain_share_commodity_total": round(float(gain.reindex(COMMODITY).fillna(0).sum()), 4),
        "b2_gain_share_food_price_levels_total": round(float(gain.reindex(FOOD_LEVELS).fillna(0).sum()), 4),
    }

    # --------------------------------------------- E. baselines (paired)
    def majority_baseline():
        rows = []
        for q, tr, te in splits(d, OUTER_MIN):
            share = tr["y"].mean()
            rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                      "y": te["y"].values, "p": share, "pred": int(share > 0.5)}))
        return pd.concat(rows, ignore_index=True)
    maj = majority_baseline()
    clock = walk(d, ["time_index"], True)
    base = gov.merge(maj[KEY + ["pred", "p"]].rename(columns={"pred": "maj", "p": "p_maj"}), on=KEY) \
              .merge(clock[KEY + ["pred", "p"]].rename(columns={"pred": "clk", "p": "p_clk"}), on=KEY) \
              .merge(rows55[KEY + ["persistence_timing_valid", "persistence_naive", "pred_baseline", "p_baseline"]], on=KEY)
    q = base["target_quarter"].values
    y = base["y"].values
    preds = {"MODEL-B2": base["pred"], "MODEL-B (default weights)": base["pred_baseline"],
             "Persistence, timing-valid": base["persistence_timing_valid"].astype(int),
             "Persistence, naive (DIAGNOSTIC: uses unreleased labels)": base["persistence_naive"].astype(int),
             "Clock-only": base["clk"], "Training-majority class": base["maj"]}
    res["E_baselines"] = {"metrics": {k: m_all(y, v, None, q) for k, v in preds.items()},
                          "paired_vs_MODEL-B2": {k: paired(base["pred"].values == y, v.values == y, q)
                                                 for k, v in preds.items() if k != "MODEL-B2"}}

    # -------------------------------------------- F. calibration
    probs = {"MODEL-B2": base["p"], "MODEL-B (default)": base["p_baseline"], "Clock-only": base["p_clk"],
             "Training base rate": base["p_maj"]}
    cal = {}
    ref_brier = brier_score_loss(y, np.clip(base["p_maj"], 1e-6, 1 - 1e-6))
    for k, p in probs.items():
        tbl, ece = calib_table(y, p.values)
        b = brier_score_loss(y, np.clip(p, 1e-6, 1 - 1e-6))
        cal[k] = {"brier": round(float(b), 4), "brier_skill_vs_training_base_rate": round(float(1 - b / ref_brier), 4),
                  "log_loss": round(float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))), 4),
                  "ece_5_bins": ece, "mean_predicted": round(float(p.mean()), 4), "observed_rate": round(float(y.mean()), 4),
                  "pr_auc": round(float(average_precision_score(y, p)), 4) if p.nunique() > 1 else None,
                  "reliability_table": tbl}
    qb = base.assign(err=(base["p"] - base["y"]) ** 2).groupby("target_quarter")["err"].mean()
    cal["MODEL-B2"]["brier_quarter_bootstrap_95ci"] = boot_quarters(qb.values)[0]
    res["F_calibration"] = cal
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1)
    for k in ("MODEL-B2", "MODEL-B (default)", "Clock-only"):
        t = cal[k]["reliability_table"]
        ax.plot([r["mean_p"] for r in t], [r["observed_high"] for r in t], "o-", label=f"{k} (n per bin shown)")
        for r in t:
            ax.annotate(str(r["n"]), (r["mean_p"], r["observed_high"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Mean predicted P(HIGH)"); ax.set_ylabel("Observed HIGH share")
    ax.set_title("Reliability, 55 outer-test rows (5 bins)"); ax.legend(fontsize=7); fig.tight_layout()
    fig.savefig(OUT / "calibration_plot.png", dpi=130); plt.close(fig)

    # ------------------------------------------ G. future-period validity
    sws = pd.read_parquet("data/processed/sws_hunger.parquet")
    res["G_future"] = {
        "latest_label_quarter": str(labels["quarter"].max()),
        "latest_sws_round_on_file": str(max(sws["quarter"].unique(), key=R.qi)),
        "latest_cpi_quarter_on_file": str(pd.read_parquet("data/processed/cpi_full.parquet")["quarter"].max()),
        "untouched_labelled_future_quarters": 0,
        "statement": "No labelled quarter after 2025-Q4 exists, so no untouched future period is available.",
    }

    (OUT / "audit_results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("outer_reproduction", "A_generalization_gap")}, default=str)[:1500])
