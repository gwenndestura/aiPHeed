"""
scripts/supplementary/model_b2_robustness.py

Robustness validation of the frozen MODEL-B2 candidate (2026-10-08).
Diagnostic only: nothing is tuned, nothing is served, MODEL-B2 is not changed.
Every model below uses the same timing-valid frame, the same k = 1 pairing, the
same 11 outer walk-forward folds (minimum 8 target quarters), seed 42, a 0.50
cut-off, and the MODEL-B2 rule scale_pos_weight = (1 - p) / p with p the HIGH
share of that fold's training rows. Diagnostic variants differ ONLY in the
feature columns they are given.

    python -m scripts.supplementary.model_b2_robustness

Writes evidence/2026-10-08_b2_robustness/.
"""

from __future__ import annotations

import hashlib
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import binomtest, spearmanr
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
OUT = Path("evidence/2026-10-08_b2_robustness")
OPT = Path("evidence/2026-10-08_optimization")
SEED = 42
OUTER_MIN = 8
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
         "PH040400000": "Rizal", "PH040500000": "Batangas"}

# Price variables, split into raw levels and the transformations Chapter III
# already specifies (YoY, lag/accel of Eq. 5's quarter-on-quarter change, CPI_dev,
# food-minus-headline gap). Nothing new is constructed.
FOOD_PRICE_LEVELS = ["rice_price_regular", "rice_price_regular_lag1", "food_cpi", "headline_cpi",
                     "commodity_fruit_veg", "commodity_leafy_veg", "commodity_livestock",
                     "commodity_poultry", "commodity_rootcrops"]
OTHER_PRICE_LEVELS = ["diesel_php_per_l", "diesel_php_per_l_lag1", "gasoline_php_per_l",
                      "brent_usd_per_bbl", "fx_usd_php_avg"]
PRICE_TRANSFORMS = ["food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "cpi_dev",
                    "food_minus_headline_yoy", "food_minus_headline_yoy_lag1",
                    "food_minus_headline_yoy_accel", "rice_price_regular_accel",
                    "diesel_php_per_l_accel"]
KEY_FEATURES = ["rice_price_regular", "commodity_rootcrops", "commodity_livestock", "FSSI_lag2",
                "headline_cpi", "unemployment_rate_lag1", "food_cpi_yoy", "sws_hunger", "enso_numeric"]


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ------------------------------------------------------------------ model
def walk(d, cols, rule="b2", keep_models=False):
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    rows, models = [], {}
    for i in range(OUTER_MIN, len(tq)):
        tr = d[d["target_quarter"].map(R.qi) < R.qi(tq[i])]
        te = d[d["target_quarter"] == tq[i]]
        params = {"objective": "binary", "verbosity": -1, "random_state": SEED}
        if rule == "b2":
            pos = tr["y"].mean()
            params["scale_pos_weight"] = float((1 - pos) / pos)
        m = LGBMClassifier(**params).fit(tr[cols], tr["y"])
        p = m.predict_proba(te[cols])[:, 1]
        rows.append(pd.DataFrame({"fold": i - OUTER_MIN + 1, "target_quarter": tq[i],
                                  "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": p, "pred": (p >= 0.5).astype(int),
                                  "last_label": te["last_label"].values,
                                  "n_train": len(tr), "train_high_share": round(float(tr["y"].mean()), 4)}))
        if keep_models:
            models[tq[i]] = (m, tr, te)
    out = pd.concat(rows, ignore_index=True)
    return (out, models) if keep_models else out


def summary(y, pred, prob=None, q=None):
    y, pred = np.asarray(y).astype(int), np.asarray(pred).astype(int)
    s = {"n": int(len(y)), "correct": int((y == pred).sum()), "incorrect": int((y != pred).sum()),
         "accuracy_pooled": round(float(accuracy_score(y, pred)), 4),
         "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
         "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
         "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
         "precision_high": round(float(precision_score(y, pred, zero_division=0)), 4),
         "recall_high": round(float(recall_score(y, pred, zero_division=0)), 4),
         "roc_auc": None if prob is None else round(float(roc_auc_score(y, prob)), 4)}
    if q is not None:
        df = pd.DataFrame({"q": q, "c": (y == pred).astype(float)})
        fold = df.groupby("q")["c"].mean()
        s["accuracy_mean_fold"] = round(float(fold.mean()), 4)
        s["accuracy_by_year"] = df.assign(yr=df["q"].str[:4]).groupby("yr")["c"].mean().round(4).to_dict()
        s["accuracy_by_fold"] = fold.round(4).to_dict()
    return s


def run_cols(d, cols, rule="b2"):
    r = walk(d, cols, rule)
    return r, summary(r["y"], r["pred"], r["p"], r["target_quarter"])


# ------------------------------------------------------------ statistics
def wilson(k, n, z=1.959964):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return round(c - h, 4), round(c + h, 4)


def cluster_bootstrap(correct_by_row, quarter, n_boot=10000, seed=SEED):
    """Resample the 11 test quarters (rows within a quarter share conditions)."""
    df = pd.DataFrame({"q": quarter, "c": correct_by_row})
    fold = df.groupby("q")["c"].mean().values
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fold), size=(n_boot, len(fold)))
    means = fold[idx].mean(axis=1)
    return round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)


def paired(a_correct, b_correct, quarter, n_boot=10000, seed=SEED):
    """Exact McNemar on discordant rows + quarter-cluster bootstrap of the mean-fold difference."""
    a, b = np.asarray(a_correct, bool), np.asarray(b_correct, bool)
    a_only, b_only = int((a & ~b).sum()), int((~a & b).sum())
    p = binomtest(a_only, a_only + b_only, 0.5).pvalue if a_only + b_only else 1.0
    df = pd.DataFrame({"q": quarter, "d": a.astype(float) - b.astype(float)})
    fold = df.groupby("q")["d"].mean().values
    rng = np.random.default_rng(seed)
    means = fold[rng.integers(0, len(fold), size=(n_boot, len(fold)))].mean(axis=1)
    return {"a_right_b_wrong": a_only, "b_right_a_wrong": b_only,
            "mcnemar_exact_p_two_sided": round(float(p), 4),
            "mean_fold_difference": round(float(fold.mean()), 4),
            "bootstrap_95ci_mean_fold_difference": [round(float(np.percentile(means, 2.5)), 4),
                                                     round(float(np.percentile(means, 97.5)), 4)],
            "bootstrap_share_difference_le_0": round(float((means <= 0).mean()), 4)}


# ----------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f, labels, cols = A.frame_t2()
    d = R.pairs(f, labels, 1)
    res = {}

    # ---------------------------------------------------------- 1. freeze
    saved_cfg = json.loads((OPT / "best_candidate_config.json").read_text())
    assert saved_cfg["features"] == cols, "feature list differs from the saved MODEL-B2 config"
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    frozen = {
        "model_id": "MODEL-B2 (frozen 2026-10-08; candidate under validation, not served)",
        "algorithm": "Algorithm 3, LightGBM LGBMClassifier, library defaults except scale_pos_weight",
        "lightgbm_params": {"objective": "binary", "verbosity": -1, "random_state": SEED},
        "scale_pos_weight_rule": "(1 - p) / p, p = HIGH share of the fold's training rows",
        "features": cols, "n_features": len(cols),
        "target": "label_stress (Eq. 3; HIGH if stress_score > global median 14.6)",
        "horizon": "k = 1: features of quarter t -> label of t+1",
        "timing": "strict Rule 3 (frame_t2): government series of t-1; news of t; SWS latest round "
                  "released before t+1; poverty incidence as published",
        "walk_forward": {"outer_min_target_quarters": OUTER_MIN, "test_quarters": tq[OUTER_MIN:],
                         "train_rule": "all rows whose target quarter precedes the test quarter"},
        "decision_threshold": 0.5, "seed": SEED,
    }
    frozen["config_sha256"] = sha({k: v for k, v in frozen.items()})
    frame = d[["province_code", "t", "target_quarter", "y"] + cols].sort_values(["target_quarter", "province_code"])
    frozen["input_frame_sha256"] = hashlib.sha256(
        pd.util.hash_pandas_object(frame.round(10), index=False).values.tobytes()).hexdigest()
    frozen["script_sha256"] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
        "scripts/supplementary/algorithm4_timing_valid.py",
        "scripts/supplementary/reliability_diagnostics.py",
        "scripts/supplementary/timing_audit.py",
        "scripts/supplementary/optimize_model_b.py",
        "scripts/supplementary/model_b2_robustness.py")}
    (OUT / "MODEL_B2_FROZEN_CONFIG.json").write_text(json.dumps(frozen, indent=2))

    # ---------------------------------------------------- 2. reproduce
    b2, models = walk(d, cols, "b2", keep_models=True)
    s_b2 = summary(b2["y"], b2["pred"], b2["p"], b2["target_quarter"])
    saved = pd.read_csv(OPT / "best_candidate_predictions.csv")
    key = ["target_quarter", "province_code"]
    mg = b2.merge(saved, on=key, suffixes=("", "_saved"))
    repro = {
        "rows_now": int(len(b2)), "rows_saved": int(len(saved)), "rows_matched": int(len(mg)),
        "identical_fold_assignment": bool(sorted(b2["target_quarter"].unique()) == sorted(saved["target_quarter"].unique())
                                          and len(mg) == len(saved) == len(b2)),
        "identical_labels": bool((mg["y"] == mg["y_saved"]).all()),
        "identical_predictions": bool((mg["pred"] == mg["pred_saved"]).all()),
        "max_abs_probability_difference": float((mg["p"] - mg["p_saved"]).abs().max()),
        "accuracy_mean_fold": s_b2["accuracy_mean_fold"], "f1_weighted": s_b2["f1_weighted"],
        "roc_auc": s_b2["roc_auc"], "correct": s_b2["correct"], "n": s_b2["n"],
        "predictions_sha256": hashlib.sha256(b2[key + ["y", "pred"]].to_csv(index=False).encode()).hexdigest(),
    }
    repro["expected_45_of_55"] = repro["correct"] == 45 and repro["n"] == 55
    repro["matches_saved_metrics"] = (s_b2["accuracy_mean_fold"] == 0.8182 and s_b2["f1_weighted"] == 0.82
                                      and s_b2["roc_auc"] == 0.8278)
    repro["PASS"] = bool(repro["identical_fold_assignment"] and repro["identical_predictions"]
                         and repro["max_abs_probability_difference"] < 1e-12
                         and repro["expected_45_of_55"] and repro["matches_saved_metrics"])
    res["reproduction"] = repro
    if not repro["PASS"]:
        (OUT / "robustness_results.json").write_text(json.dumps(res, indent=2, default=str))
        raise SystemExit("REPRODUCTION FAILED - stopping: " + json.dumps(repro, default=str))

    # --------------------------------------------- 3. row-by-row table
    b0 = walk(d, cols, "default")
    # Timing-valid persistence: the last label whose SWS round was released
    # before the forecast quarter t+1 began (the label of t needs SWS of t).
    rel = T.sws_release_dates()
    lab = labels[["province_code", "quarter", "label_stress"]].copy()
    def tv_last(row):
        cut = T.qstart(row["target_quarter"])
        known = lab[(lab["province_code"] == row["province_code"])
                    & lab["quarter"].map(lambda s: s in rel and rel[s] < cut and R.qi(s) < R.qi(row["target_quarter"]))]
        if known.empty:
            return np.nan, None
        last = known.loc[known["quarter"].map(R.qi).idxmax()]
        return int(last["label_stress"]), last["quarter"]
    tbl = b2.merge(b0[key + ["p", "pred"]].rename(columns={"p": "p_baseline", "pred": "pred_baseline"}), on=key)
    tv = tbl.apply(tv_last, axis=1, result_type="expand")
    tbl["persistence_naive"] = tbl["last_label"]
    tbl["persistence_timing_valid"], tbl["persistence_tv_source_quarter"] = tv[0], tv[1]
    feats = d[key + KEY_FEATURES]
    tbl = tbl.merge(feats, on=key)
    tbl = tbl.merge(labels[["province_code", "quarter", "stress_score", "sws_hunger_pct"]]
                    .rename(columns={"quarter": "target_quarter", "sws_hunger_pct": "target_sws"}), on=key)
    tbl["province"] = tbl["province_code"].map(NAMES)
    tbl["correct_b2"] = (tbl["pred"] == tbl["y"]).astype(int)
    tbl["correct_baseline"] = (tbl["pred_baseline"] == tbl["y"]).astype(int)
    tbl["status"] = np.select(
        [(tbl["correct_b2"] == 1) & (tbl["correct_baseline"] == 0),
         (tbl["correct_b2"] == 0) & (tbl["correct_baseline"] == 1)],
        ["B2 fixed", "B2 broke"], "same")
    order = ["fold", "target_quarter", "province", "province_code", "y", "pred", "p", "correct_b2",
             "pred_baseline", "p_baseline", "correct_baseline", "status", "persistence_naive",
             "persistence_timing_valid", "persistence_tv_source_quarter", "stress_score", "target_sws",
             "n_train", "train_high_share"] + KEY_FEATURES
    tbl = tbl[order].sort_values(["fold", "province_code"]).reset_index(drop=True)
    tbl.to_csv(OUT / "outer_test_rows_55.csv", index=False)
    fixed = tbl[tbl["status"] == "B2 fixed"]
    res["changed_rows"] = {
        "b2_fixed": fixed[["target_quarter", "province", "y", "p_baseline", "p", "stress_score"]].round(4).to_dict(orient="records"),
        "b2_broke": tbl[tbl["status"] == "B2 broke"][["target_quarter", "province", "y", "p_baseline", "p"]].round(4).to_dict(orient="records"),
        "fixed_distinct_quarters": int(fixed["target_quarter"].nunique()),
        "fixed_distinct_provinces": int(fixed["province"].nunique()),
        "all_fixed_are_high": bool((fixed["y"] == 1).all()),
        "rows_where_pred_changed": int((tbl["pred"] != tbl["pred_baseline"]).sum()),
        "b2_prob_minus_baseline_prob_mean": round(float((tbl["p"] - tbl["p_baseline"]).mean()), 4),
        "errors_by_province_b2": tbl.groupby("province")["correct_b2"].apply(lambda s: int((s == 0).sum())).to_dict(),
        "errors_by_province_baseline": tbl.groupby("province")["correct_baseline"].apply(lambda s: int((s == 0).sum())).to_dict(),
    }

    # --------------------------------------- 4. persistence comparison
    y = tbl["y"].values
    q = tbl["target_quarter"].values
    pn = tbl["persistence_naive"].values
    ptv = tbl["persistence_timing_valid"].values
    res["persistence_inputs"] = {"naive_missing": int(np.isnan(pn.astype(float)).sum()),
                                 "timing_valid_missing": int(np.isnan(ptv.astype(float)).sum()),
                                 "naive_vs_timing_valid_disagree": int((pn != ptv).sum())}
    comp = {"MODEL-B baseline": summary(y, tbl["pred_baseline"], tbl["p_baseline"], q),
            "MODEL-B2": summary(y, tbl["pred"], tbl["p"], q),
            "Persistence (naive: label of t, optimistic)": summary(y, np.nan_to_num(pn, nan=0), None, q),
            "Persistence (timing-valid: last label released before t+1)": summary(y, np.nan_to_num(ptv.astype(float), nan=0), None, q)}
    res["comparison_same_55_rows"] = comp
    cb2, cb0 = tbl["correct_b2"].values, tbl["correct_baseline"].values
    res["paired_tests"] = {
        "B2_vs_baseline": paired(cb2, cb0, q),
        "B2_vs_persistence_naive": paired(cb2, (pn == y), q),
        "B2_vs_persistence_timing_valid": paired(cb2, (ptv == y), q),
        "baseline_vs_persistence_naive": paired(cb0, (pn == y), q),
    }

    # -------------------------------------------- 9. uncertainty
    k, n = int(cb2.sum()), len(cb2)
    cp = binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
    res["uncertainty"] = {
        "point_estimate_pooled": round(k / n, 4), "point_estimate_mean_fold": s_b2["accuracy_mean_fold"],
        "correct": k, "n": n,
        "wilson_95": wilson(k, n),
        "clopper_pearson_95": [round(cp.low, 4), round(cp.high, 4)],
        "quarter_cluster_bootstrap_95_mean_fold": cluster_bootstrap(cb2, q),
        "one_sided_exact_p_accuracy_le_0.75": round(float(binomtest(k, n, 0.75, alternative="greater").pvalue), 4),
        "baseline_wilson_95": wilson(int(cb0.sum()), n),
    }

    # ------------------------------------------------ 10. fold table
    ft = (tbl.groupby(["fold", "target_quarter"])
          .agg(baseline=("correct_baseline", "mean"), model_b2=("correct_b2", "mean"),
               high_rows=("y", "sum")).reset_index())
    ft["change"] = (ft["model_b2"] - ft["baseline"]).round(2)
    ft.to_csv(OUT / "fold_comparison.csv", index=False)
    res["fold_comparison"] = ft.to_dict(orient="records")
    res["fold_gain_distribution"] = {"folds_improved": int((ft["change"] > 0).sum()),
                                     "folds_unchanged": int((ft["change"] == 0).sum()),
                                     "folds_worse": int((ft["change"] < 0).sum())}

    # ------------------------------------ 5. price-level stress test
    nonprice = [c for c in cols if c not in FOOD_PRICE_LEVELS + OTHER_PRICE_LEVELS + PRICE_TRANSFORMS]
    sets = {
        "A_all_47": cols,
        "B1_without_food_price_levels": [c for c in cols if c not in FOOD_PRICE_LEVELS],
        "B2_without_any_price_level": [c for c in cols if c not in FOOD_PRICE_LEVELS + OTHER_PRICE_LEVELS],
        "B3_without_any_price_variable": nonprice,
        "C_transformed_prices_only": nonprice + PRICE_TRANSFORMS,
    }
    stress, stress_rows = {}, []
    for name, cs in sets.items():
        r, s = run_cols(d, cs, "b2")
        r0, s0 = run_cols(d, cs, "default")
        stress[name] = {"n_features": len(cs), "dropped": [c for c in cols if c not in cs],
                        "b2_rule": s, "default_lightgbm": {k2: s0[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year")}}
        stress_rows.append(r.assign(variant=name))
    pd.concat(stress_rows).to_csv(OUT / "price_stress_predictions.csv", index=False)
    res["price_stress_test"] = stress

    # ---------------------------------------- 6. time-trend diagnostic
    tcorr = []
    for c in cols:
        rho = spearmanr(d["t"], d[c]).correlation if d[c].nunique() > 1 else np.nan
        tcorr.append({"feature": c, "spearman_with_time_index": None if np.isnan(rho) else round(float(rho), 3)})
    imp = pd.read_csv(OPT / "best_candidate_feature_importance.csv", index_col=0)["mean_gain_share"]
    tcorr = pd.DataFrame(tcorr).merge(imp.rename("b2_gain_share"), left_on="feature", right_index=True, how="left")
    tcorr = tcorr.sort_values("b2_gain_share", ascending=False)
    tcorr.to_csv(OUT / "time_trend_correlation.csv", index=False)
    top = tcorr.head(10)
    w = top["b2_gain_share"] / top["b2_gain_share"].sum()
    by_year = (d.assign(year=d["t"].map(lambda v: str(v // 4)))
               .groupby("year")[FOOD_PRICE_LEVELS + ["sws_hunger", "y"]].mean().round(3))
    by_year.to_csv(OUT / "price_levels_by_year.csv")
    r_t, s_t = run_cols(d.assign(time_index=d["t"]), ["time_index"], "b2")
    r_t2, s_t2 = run_cols(d.assign(time_index=d["t"]), ["time_index", "sws_hunger"], "b2")
    mm = b2.merge(r_t[key + ["pred"]].rename(columns={"pred": "pred_time"}), on=key)
    # Within-year signal: do the top price levels still separate HIGH from LOW
    # once each feature is centred on its target-year mean?
    within = {}
    for c in ["rice_price_regular", "commodity_rootcrops", "commodity_livestock", "headline_cpi", "food_cpi"]:
        x = d[c] - d.groupby(d["t"] // 4)[c].transform("mean")
        both = d.assign(x=x)
        within[c] = {"auc_raw_level": round(float(roc_auc_score(d["y"], d[c])), 3),
                     "auc_within_year_centred": round(float(roc_auc_score(both["y"], both["x"])), 3)}
    res["time_trend"] = {
        "top10_by_gain": top.to_dict(orient="records"),
        "gain_weighted_mean_abs_rho_top10": round(float((w * top["spearman_with_time_index"].abs()).sum()), 3),
        "time_index_only_model_b2_rule": {k2: s_t[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year", "accuracy_by_fold")},
        "time_index_plus_sws_hunger": {k2: s_t2[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year")},
        "b2_vs_time_only_prediction_agreement": round(float((mm["pred"] == mm["pred_time"]).mean()), 4),
        "label_high_share_by_target_year": by_year["y"].to_dict(),
        "within_year_signal": within,
    }

    # -------------------------------- 7. CPI-derived price construction
    comm = pd.read_parquet("data/processed/commodity_prices.parquet")
    cpi = pd.read_parquet("data/processed/cpi_full.parquet")
    cg = comm.groupby(["province_code", "quarter", "commodity_group"])["price_php_per_kg"].mean().unstack()
    post = cg[cg.index.get_level_values("quarter") >= "2022-Q1"].reset_index()
    post = post.merge(cpi[["province_code", "quarter", "cpi_food_yoy_pct"]], on=["province_code", "quarter"], how="left")
    corr = {}
    for g in ["fruit_veg", "leafy_veg", "livestock", "poultry", "rootcrops"]:
        per = [post[post["province_code"] == p][[g, "cpi_food_yoy_pct"]].corr().iloc[0, 1]
               for p in post["province_code"].unique() if post[post["province_code"] == p][g].notna().sum() > 2]
        corr[f"commodity_{g}"] = round(float(np.nanmin(per)), 6) if per else None
    note = comm.assign(derived=comm["source_note"].str.contains("forward-filled")).groupby("quarter")["derived"].mean()
    rice = pd.read_parquet("data/processed/psa_rice_prices.parquet")
    psa_ind = pd.read_parquet("data/processed/psa_indicators.parquet")
    fused = pd.read_parquet("data/processed/features_fused.parquet")
    # Compare to the fused matrix: is fused commodity_x equal to the derived values?
    res["cpi_derived"] = {
        "commodity_first_derived_quarter": str(note[note > 0].index.min()),
        "commodity_last_observed_quarter": str(note[note == 0].index.max()),
        "commodity_derivation": "price_q = price_2021Q4(province, item) x (1 + food_cpi_yoy_q / 100); "
                                "backend/fix_primary_data.py fix_commodity_prices(); NOT cumulative",
        "min_within_province_corr_with_food_cpi_yoy_2022plus": corr,
        "rice_psa_wholesale_quarters": [str(rice["quarter"].min()), str(rice["quarter"].max())],
        "rice_source_note": str(rice["source_note"].iloc[0])[:160],
        "psa_indicators_has_rice": "rice_price_regular" in psa_ind.columns,
        "fused_rice_by_year": fused.groupby(fused["quarter"].str[:4])["rice_price_regular"].mean().round(2).to_dict(),
        "fused_rootcrops_by_year": fused.groupby(fused["quarter"].str[:4])["commodity_rootcrops"].mean().round(2).to_dict(),
        "fused_livestock_by_year": fused.groupby(fused["quarter"].str[:4])["commodity_livestock"].mean().round(2).to_dict(),
    }

    # ------------------------------------------------ 8. 2024 analysis
    t24 = tbl[tbl["target_quarter"].str.startswith("2024")]
    contrib = []
    for tq_ in ["2024-Q1", "2024-Q2"]:
        m, tr, te = models[tq_]
        sh = m.booster_.predict(te[cols], pred_contrib=True)
        sh = pd.DataFrame(sh[:, :-1], columns=cols)
        for i, (_, row) in enumerate(te.iterrows()):
            s = sh.iloc[i].sort_values(key=lambda v: -v.abs())
            contrib.append({"target_quarter": tq_, "province": NAMES[row["province_code"]], "y": int(row["y"]),
                            "p": round(float(m.predict_proba(te[cols].iloc[[i]])[:, 1][0]), 3),
                            "top5_log_odds_contributions": {k2: round(float(v), 3) for k2, v in s.head(5).items()}})
    sws_avail = {}
    for tq_ in ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]:
        known = [s for s in rel if rel[s] < T.qstart(tq_)]
        sws_avail[tq_] = {"latest_sws_round_known_at_forecast": max(known, key=R.qi),
                          "sws_value_known": float(tbl[tbl["target_quarter"] == tq_]["sws_hunger"].iloc[0]),
                          "target_quarter_sws": float(tbl[tbl["target_quarter"] == tq_]["target_sws"].iloc[0])}
    tr24 = d[d["target_quarter"].map(R.qi) < R.qi("2024-Q1")]
    te24 = d[d["target_quarter"].str.startswith("2024")]
    rng_ = {}
    for c in ["enso_numeric", "rice_price_regular", "rice_price_regular_accel", "sws_hunger",
              "commodity_rootcrops", "commodity_livestock", "rainfall_anomaly_pct", "drought_alert", "food_cpi_yoy"]:
        a, b = tr24[c], te24[c]
        rng_[c] = {"train_min": round(float(a.min()), 2), "train_max": round(float(a.max()), 2),
                   "test2024_mean": round(float(b.mean()), 2), "train_mean": round(float(a.mean()), 2),
                   "smd": round(float((b.mean() - a.mean()) / (a.std() or 1)), 2),
                   "share_2024_outside_train_range": round(float(((b < a.min()) | (b > a.max())).mean()), 2)}
    res["y2024"] = {
        "class_distribution_by_quarter": t24.groupby("target_quarter")["y"].agg(["size", "sum"]).rename(
            columns={"size": "rows", "sum": "high"}).to_dict(orient="index"),
        "rows": t24[["target_quarter", "province", "y", "pred", "p", "p_baseline", "stress_score", "target_sws",
                     "sws_hunger", "train_high_share"]].round(3).to_dict(orient="records"),
        "accuracy_by_quarter_b2": t24.groupby("target_quarter")["correct_b2"].mean().to_dict(),
        "top_contributions_q1_q2": contrib,
        "sws_available_at_forecast": sws_avail,
        "distribution_shift_vs_pre2024_training": rng_,
        "pre2024_training_rows": int(len(tr24)), "pre2024_training_high": int(tr24["y"].sum()),
        "pre2024_training_rows_with_sws_hunger_ge_15": int((tr24["sws_hunger"] >= 15).sum()),
    }

    # ----------------------------------------- 11. Algorithm 4 diagnostic
    hold = tq[-4:]
    ho = tbl[tbl["target_quarter"].isin(hold)]
    a4 = json.loads((OPT / "algorithm4_diagnostic.json").read_text())
    low = ho[ho["y"] == 0]
    def manual_auc(yv, pv):
        pos, neg = pv[yv == 1], pv[yv == 0]
        return float(np.mean([(pp > nn) + 0.5 * (pp == nn) for pp in pos for nn in neg]))
    rng = np.random.default_rng(SEED)
    rand = [roc_auc_score(ho["y"], rng.random(len(ho))) for _ in range(20000)]
    sws_auc = roc_auc_score(ho["y"], ho["sws_hunger"]) if ho["sws_hunger"].nunique() > 1 else None
    res["algorithm4"] = {
        "holdout_quarters": hold, "n": int(len(ho)), "n_low": int((ho["y"] == 0).sum()),
        "n_high_low_pairs": int((ho["y"] == 1).sum() * (ho["y"] == 0).sum()),
        "auc_resolution": round(1 / ((ho["y"] == 1).sum() * (ho["y"] == 0).sum()), 4),
        "low_rows": low[["target_quarter", "province", "stress_score", "target_sws", "p"]].round(3).to_dict(orient="records"),
        "low_rows_margin_below_threshold_14.6": [round(14.6 - v, 3) for v in low["stress_score"]],
        "high_rows_stress_scores": sorted(ho[ho["y"] == 1]["stress_score"].round(2).tolist()),
        "saved_algorithm4_results": a4,
        "walkforward_b2_auc_on_same_20_rows": round(float(roc_auc_score(ho["y"], ho["p"])), 4),
        "walkforward_baseline_auc_on_same_20_rows": round(float(roc_auc_score(ho["y"], ho["p_baseline"])), 4),
        "manual_pair_count_auc_b2_matches_sklearn": abs(manual_auc(ho["y"].values, ho["p"].values) - roc_auc_score(ho["y"], ho["p"])) < 1e-12,
        "random_score_auc_sd": round(float(np.std(rand)), 4),
        "random_score_share_auc_ge_0.80": round(float(np.mean(np.array(rand) >= 0.8)), 4),
        "sws_hunger_feature_auc_on_holdout": None if sws_auc is None else round(float(sws_auc), 4),
        "train_high_share_cv_window": round(float(d[~d["target_quarter"].isin(hold)]["y"].mean()), 4),
    }

    # ---------------------------------------------- 12. 45 vs 12
    eq5 = [c for c in EQUATION5_FEATURES if c in d.columns]
    _, s12_b2 = run_cols(d, eq5, "b2")
    _, s12_0 = run_cols(d, eq5, "default")
    _, s12_sws = run_cols(d, eq5 + ["sws_hunger"], "b2")
    res["features_45_vs_12"] = {
        "equation5_features": eq5,
        "eq5_12_b2_rule": {k2: s12_b2[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year", "correct")},
        "eq5_12_default": {k2: s12_0[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year", "correct")},
        "eq5_12_plus_sws_b2_rule": {k2: s12_sws[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year", "correct")},
        "model_b2_47": {k2: s_b2[k2] for k2 in ("accuracy_mean_fold", "f1_weighted", "roc_auc", "accuracy_by_year", "correct")},
    }

    res["model_b2_summary"] = s_b2
    (OUT / "robustness_results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("reproduction", "fold_gain_distribution", "uncertainty")}, indent=1, default=str))
