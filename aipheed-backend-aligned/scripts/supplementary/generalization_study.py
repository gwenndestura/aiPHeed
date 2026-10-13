"""
scripts/supplementary/generalization_study.py

Leakage-safe generalization study for aiPHeed, run under the protocol fixed in
experiments/2026-10-09_generalization/PREREGISTRATION.json (hash checked at
start). Supplementary only: no production file, model artifact, earlier
evidence or thesis text is touched.

Primary estimate: the nested procedure P. Inside every outer fold it picks one
configuration from a fixed pool using inner walk-forward validation on that
fold's training quarters only, then forecasts the outer quarter. Every other
model in this file is descriptive and is never used to choose anything.

    python -m scripts.supplementary.generalization_study
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (brier_score_loss, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
EXP = Path("experiments/2026-10-09_generalization")
PREREG = EXP / "PREREGISTRATION.json"
PREREG_SHA = "3183c4232e308be86fad77dfe2076e64f23c8050098d3272834d99b3485fc453"
GOVCFG = json.loads(Path("config/governing_model.json").read_text())
ROWS55 = Path("evidence/2026-10-08_b2_robustness/outer_test_rows_55.csv")
SEED, OUTER_MIN, INNER_MIN, THR, N_BOOT = 42, 8, 5, 0.5, 10000
KEY = ["target_quarter", "province_code"]

GOV = GOVCFG["feature_set"]["model_inputs"]
EQ5 = list(EQUATION5_FEATURES)
COMMODITY = ["commodity_fruit_veg", "commodity_leafy_veg", "commodity_livestock", "commodity_poultry", "commodity_rootcrops"]
FOOD_LEVELS = ["rice_price_regular", "rice_price_regular_lag1", "food_cpi", "headline_cpi"] + COMMODITY
OTHER_LEVELS = ["diesel_php_per_l", "diesel_php_per_l_lag1", "gasoline_php_per_l", "brent_usd_per_bbl", "fx_usd_php_avg"]
PRICE_TRANSFORMS = ["food_cpi_yoy", "food_cpi_yoy_lag1", "food_cpi_yoy_accel", "cpi_dev", "food_minus_headline_yoy",
                    "food_minus_headline_yoy_lag1", "food_minus_headline_yoy_accel", "rice_price_regular_accel",
                    "diesel_php_per_l_accel"]
FEATURE_SETS = {"eq5_12": EQ5, "gov47_no_commodity": [c for c in GOV if c not in COMMODITY], "gov47": GOV}


# ------------------------------------------------------------- the pool
def pool():
    """Fixed pool in pre-registered order (simplest first)."""
    out = []
    for fs in FEATURE_SETS:
        for C in (0.01, 0.1, 1.0, 10.0):
            for w in (None, "balanced"):
                out.append({"id": f"{fs}|logistic|C={C}|w={w}", "fs": fs, "family": "logistic", "C": C, "w": w})
        for depth in (1, 2, 3):
            for w in (None, "balanced"):
                out.append({"id": f"{fs}|tree|depth={depth}|w={w}", "fs": fs, "family": "tree", "depth": depth, "w": w})
        for small in (True, False):
            for w in (None, "spw"):
                out.append({"id": f"{fs}|lgbm|{'small' if small else 'default'}|w={w}", "fs": fs, "family": "lgbm",
                            "small": small, "w": w})
    return out


def make(cfg, ytr):
    if cfg["family"] == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(C=cfg["C"], class_weight=cfg["w"], max_iter=5000,
                                                                  random_state=SEED))
    if cfg["family"] == "tree":
        return DecisionTreeClassifier(max_depth=cfg["depth"], min_samples_leaf=5, class_weight=cfg["w"], random_state=SEED)
    p = {"objective": "binary", "verbosity": -1, "random_state": SEED}
    if cfg.get("small"):
        p.update(num_leaves=4, min_child_samples=10, n_estimators=100, learning_rate=0.05)
    if cfg["w"] == "spw":
        pos = float(np.mean(ytr))
        p["scale_pos_weight"] = (1 - pos) / pos
    return LGBMClassifier(**p)


def cols_of(cfg):
    return cfg.get("cols") or FEATURE_SETS[cfg["fs"]]


def qs(d):
    return sorted(d["target_quarter"].unique(), key=R.qi)


def splits(d, start):
    tq = qs(d)
    for i in range(start, len(tq)):
        yield tq[i], d[d["target_quarter"].map(R.qi) < R.qi(tq[i])], d[d["target_quarter"] == tq[i]]


def fit_predict(cfg, tr, te):
    c = cols_of(cfg)
    m = make(cfg, tr["y"].values).fit(tr[c], tr["y"])
    return m.predict_proba(te[c])[:, 1]


def walk(d, cfg, start=OUTER_MIN):
    rows = []
    for q, tr, te in splits(d, start):
        if tr["y"].nunique() < 2:
            continue
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(cfg, tr, te)}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= THR).astype(int)
    return r


def qacc(r):
    return float(r.assign(c=(r["y"] == r["pred"]).astype(float)).groupby("target_quarter")["c"].mean().mean())


# ------------------------------------------------------------- metrics
def within_quarter_auc(r):
    v = []
    for _, g in r.groupby("target_quarter"):
        if g["y"].nunique() == 2 and g["p"].nunique() > 1:
            v.append(roc_auc_score(g["y"], g["p"]))
    return round(float(np.mean(v)), 3) if v else None


def metrics(r):
    y, pred = r["y"].values.astype(int), r["pred"].values.astype(int)
    byq = r.assign(c=(r["y"] == r["pred"]).astype(float)).groupby("target_quarter")["c"].mean()
    has_p = "p" in r and r["p"].notna().all() and r["p"].nunique() > 1
    return {"n": int(len(y)), "correct": int((y == pred).sum()), "incorrect": int((y != pred).sum()),
            "accuracy_mean_quarter": round(float(byq.mean()), 4),
            "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
            "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y, r["p"])), 4) if has_p else None,
            "brier": round(float(brier_score_loss(y, r["p"])), 4) if has_p else None,
            "within_quarter_auc_mean": within_quarter_auc(r) if has_p else None,
            "confusion_[[TN,FP],[FN,TP]]": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
            "accuracy_by_year": r.assign(c=(r["y"] == r["pred"]).astype(float), yr=r["target_quarter"].str[:4])
                                 .groupby("yr")["c"].mean().round(4).to_dict(),
            "accuracy_by_quarter": byq.round(2).to_dict()}


def boot(v, seed=SEED):
    v = np.asarray(v, float)
    rng = np.random.default_rng(seed)
    return v[rng.integers(0, len(v), size=(N_BOOT, len(v)))].mean(axis=1)


def acceptance(r, refs):
    byq = r.assign(c=(r["y"] == r["pred"]).astype(float)).groupby("target_quarter")["c"].mean()
    k, n = int((r["y"] == r["pred"]).sum()), len(r)
    b = boot(byq.values)
    cp_low = binomtest(k, n).proportion_ci(0.90, "exact").low
    out = {"C1_observed": {"value": round(float(byq.mean()), 4), "pass": bool(byq.mean() >= 0.75)},
           "C2_statistical": {"quarter_bootstrap_p5": round(float(np.percentile(b, 5)), 4),
                              "clopper_pearson_one_sided_95_low": round(float(cp_low), 4),
                              "pass": bool(np.percentile(b, 5) >= 0.75 and cp_low >= 0.75)}}
    c3 = {}
    for name, ref in refs.items():
        m = r.merge(ref[KEY + ["pred"]].rename(columns={"pred": "ref"}), on=KEY)
        diff = m.assign(d=(m["y"] == m["pred"]).astype(float) - (m["y"] == m["ref"]).astype(float)) \
                .groupby("target_quarter")["d"].mean()
        bd = boot(diff.values)
        a, z = int(((m["y"] == m["pred"]) & (m["y"] != m["ref"])).sum()), int(((m["y"] != m["pred"]) & (m["y"] == m["ref"])).sum())
        c3[name] = {"mean_quarter_difference": round(float(diff.mean()), 4),
                    "bootstrap_p5": round(float(np.percentile(bd, 5)), 4),
                    "bootstrap_95ci": [round(float(np.percentile(bd, 2.5)), 4), round(float(np.percentile(bd, 97.5)), 4)],
                    "rows_model_only_right": a, "rows_ref_only_right": z,
                    "mcnemar_p": round(float(binomtest(a, a + z, 0.5).pvalue), 4) if a + z else 1.0,
                    "pass": bool(diff.mean() > 0 and np.percentile(bd, 5) > 0)}
    out["C3_beats_baselines"] = {"comparisons": c3, "pass": all(v["pass"] for v in c3.values())}
    years = sorted({q[:4] for q in byq.index})
    loyo = {y: round(float(byq[[q for q in byq.index if not q.startswith(y)]].mean()), 4) for y in years}
    out["C4_stability"] = {"leave_one_year_out": loyo, "pass": all(v >= 0.75 for v in loyo.values())}
    out["C5_prospective"] = {"pass": None, "status": "not evaluable: no labelled quarter after 2025-Q4"}
    c = [out[k]["pass"] for k in ("C1_observed", "C2_statistical", "C3_beats_baselines", "C4_stability")]
    out["verdict"] = ("MEETS_WITHIN_PERIOD" if all(c) else "OBSERVED_ONLY" if c[0] else "FAILS")
    return out


# --------------------------------------------------------- nested P
def nested(d, members, start=OUTER_MIN):
    rows, choices = [], []
    for q, tr, te in splits(d, start):
        scores = {}
        for cfg in members:
            r_in = walk(tr, cfg, start=INNER_MIN)
            scores[cfg["id"]] = qacc(r_in)
        top = max(scores.values())
        chosen = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(chosen, tr, te)}))
        top5 = sorted(scores.items(), key=lambda kv: -kv[1])[:5]
        choices.append({"outer_quarter": q, "chosen": chosen["id"], "inner_score": round(top, 4),
                        "n_tied_at_top": sum(abs(v - top) < 1e-12 for v in scores.values()),
                        "top5": [[k, round(v, 4)] for k, v in top5]})
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= THR).astype(int)
    return r, choices


# ----------------------------------------------------------- data audit
def data_audit(f, d, labels):
    out = {}
    fused = pd.read_parquet("data/processed/features_fused.parquet")
    feats = [c for c in fused.columns if c not in ("province_code", "quarter")]
    common = [c for c in feats if fused.groupby("quarter")[c].nunique().max() <= 1]
    out["quarter_common_features"] = common
    out["province_varying_features"] = [c for c in feats if c not in common]
    lab = labels.copy()
    s = lab["stress_score"]
    out["label_structure"] = {
        "share_of_stress_variance_between_quarters": round(float(lab.groupby("quarter")["stress_score"].transform("mean").var() / s.var()), 4),
        "sws_is_one_value_per_quarter": bool(lab.groupby("quarter")["sws_hunger_pct"].nunique().max() == 1),
        "label_equals_sws_above_threshold_share": round(float(((lab["sws_hunger_pct"] > 14.6).astype(int) == lab["label_stress"]).mean()), 4),
        "quarters_single_class": int(lab.groupby("quarter")["label_stress"].agg(lambda v: v.nunique() == 1).sum()),
        "n_labelled_quarters": int(lab["quarter"].nunique()),
        "global_threshold": float(lab["global_threshold"].iloc[0]),
        "rows_from_outer_test_period_in_threshold": int((lab["quarter"].map(R.qi) >= R.qi("2022-Q4")).sum()),
        "rows_total_in_threshold": int(len(lab)),
    }
    cpi = pd.read_parquet("data/processed/cpi_full.parquet")
    out["cpi_full"] = {"source_note": str(cpi["source_note"].iloc[0]),
                       "food_yoy_varies_across_provinces": bool(cpi.groupby("quarter")["cpi_food_yoy_pct"].nunique().max() > 1)}
    psa = pd.read_parquet("data/processed/psa_indicators.parquet")
    out["feature_food_cpi_yoy_varies_across_provinces"] = bool(psa.groupby("quarter")["food_cpi_yoy"].nunique().max() > 1)
    out["label_food_cpi_yoy_varies_across_provinces"] = bool(lab.groupby("quarter")["food_cpi_yoy"].nunique().max() > 1)
    post = fused[fused["quarter"] >= "2022-Q1"]
    anc = fused[fused["quarter"] == "2021-Q4"].set_index("province_code")
    ratio_spread = {}
    for c in COMMODITY:
        rr = post.assign(r=post[c] / post["province_code"].map(anc[c]))
        ratio_spread[c] = round(float(rr.groupby("quarter")["r"].std().max()), 6)
    out["commodity_post2021_ratio_to_province_anchor_max_within_quarter_sd"] = ratio_spread
    rel = T.sws_release_dates()
    al = []
    for q in qs(d)[OUTER_MIN:]:
        known = [s for s in rel if rel[s] < T.qstart(q)]
        latest = max(known, key=R.qi)
        al.append({"target_quarter": q, "latest_sws_round_released_before": latest,
                   "release_date": str(rel[latest].date()),
                   "sws_feature_value": float(d[d["target_quarter"] == q]["sws_hunger"].iloc[0]),
                   "target_round_used_as_feature": latest == q})
    out["sws_alignment_outer"] = al
    prov = json.loads(Path("data/processed/feature_provenance.json").read_text()) \
        if Path("data/processed/feature_provenance.json").exists() else {}
    out["fill_provenance"] = {k: v for k, v in (prov.get("columns", prov) or {}).items()
                              if isinstance(v, dict) and (v.get("forward_filled") or v.get("zero_filled"))} if prov else None
    # Target encoded in features? correlation of each input with the label of t+1 vs with the label of t
    out["max_abs_corr_feature_vs_target"] = round(float(d[GOV].corrwith(d["y"]).abs().max()), 3)
    return out


# ------------------------------------------------------------------ main
def main():
    EXP.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(PREREG.read_bytes()).hexdigest() == PREREG_SHA, "pre-registration changed"
    f, labels, cols = A.frame_t2()
    assert cols == GOV
    d = R.pairs(f, labels, 1)
    d["time_index"] = d["t"]
    res = {"provenance": {
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="..").stdout.strip(),
        "note_git": "aipheed-backend-aligned/ is untracked; provenance rests on the hashes below",
        "preregistration_sha256": PREREG_SHA,
        "governing_config_sha256": hashlib.sha256(Path("config/governing_model.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "data_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
            "data/processed/features_fused.parquet", "data/processed/labels.parquet", "data/processed/sws_hunger.parquet",
            "data/processed/commodity_prices.parquet", "data/processed/cpi_full.parquet", "data/processed/psa_indicators.parquet")},
        "seed": SEED, "outer_min": OUTER_MIN, "inner_min": INNER_MIN, "threshold": THR,
        "outer_quarters": qs(d)[OUTER_MIN:], "pool_size": len(pool())}}

    res["data_audit"] = data_audit(f, d, labels)

    # ---- baselines on the same rows
    rows55 = pd.read_csv(ROWS55)
    pers = rows55[KEY + ["y", "persistence_timing_valid"]].rename(columns={"persistence_timing_valid": "pred"})
    pers["pred"] = pers["pred"].astype(int)
    clock = walk(d, {"id": "clock", "family": "lgbm", "w": "spw", "cols": ["time_index"]})
    refs = {"persistence_timing_valid": pers, "clock_only": clock}

    # ---- primary: nested P over the full pool
    members = pool()
    P, choices = nested(d, members)
    P.to_csv(EXP / "P_nested_predictions.csv", index=False)
    res["P_nested"] = {"metrics": metrics(P), "choices": choices,
                       "times_chosen": pd.Series([c["chosen"] for c in choices]).value_counts().to_dict(),
                       "acceptance": acceptance(P, refs)}

    # ---- secondary nested procedures (by family), descriptive
    sec = {}
    for fam in ("logistic", "tree", "lgbm"):
        r, ch = nested(d, [m for m in members if m["family"] == fam])
        sec[fam] = {"metrics": metrics(r), "times_chosen": pd.Series([c["chosen"] for c in ch]).value_counts().to_dict()}
    res["nested_by_family"] = sec

    # ---- every pool member at fixed configuration (descriptive only)
    fixed, allp = {}, []
    for cfg in members:
        r = walk(d, cfg)
        fixed[cfg["id"]] = metrics(r)
        allp.append(r.assign(config=cfg["id"]))
    res["fixed_configurations"] = fixed

    # ---- named comparisons and baselines
    named = {
        "MODEL-A config (eq5_12 LightGBM default)": {"id": "a", "family": "lgbm", "w": None, "cols": EQ5},
        "MODEL-B2 (gov47 LightGBM spw)": {"id": "b2", "family": "lgbm", "w": "spw", "cols": GOV},
    }
    comp = {k: walk(d, v) for k, v in named.items()}
    comp["clock_only"] = clock
    maj = []
    for q, tr, te in splits(d, OUTER_MIN):
        share = tr["y"].mean()
        maj.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                 "y": te["y"].values, "p": share, "pred": int(share > 0.5)}))
    comp["training_majority"] = pd.concat(maj, ignore_index=True)
    comp["persistence_timing_valid"] = pers.assign(p=np.nan)
    res["named_comparisons"] = {k: metrics(v) for k, v in comp.items()}
    res["MODEL-B2_against_acceptance_rule_(descriptive, not primary)"] = acceptance(comp["MODEL-B2 (gov47 LightGBM spw)"], refs)

    # ---- ablations (descriptive), LightGBM spw and logistic C=0.1
    common = res["data_audit"]["quarter_common_features"]
    abl_sets = {
        "gov47": GOV, "gov47_no_commodity": [c for c in GOV if c not in COMMODITY],
        "gov47_no_price_levels": [c for c in GOV if c not in FOOD_LEVELS + OTHER_LEVELS],
        "gov47_no_price_related": [c for c in GOV if c not in FOOD_LEVELS + OTHER_LEVELS + PRICE_TRANSFORMS],
        "quarter_common_only": [c for c in GOV if c in common or c == "sws_hunger"],
        "province_varying_only": [c for c in GOV if c not in common and c != "sws_hunger"],
        "eq5_12": EQ5,
    }
    abl = {}
    for name, cs in abl_sets.items():
        abl[name] = {"n": len(cs),
                     "lgbm_spw": metrics(walk(d, {"id": name, "family": "lgbm", "w": "spw", "cols": cs})),
                     "logistic_C0.1": metrics(walk(d, {"id": name, "family": "logistic", "C": 0.1, "w": None, "cols": cs}))}
    res["ablations"] = abl

    # ---- label-threshold sensitivity for P (diagnostic only; target unchanged)
    lab = labels.set_index(["province_code", "quarter"])["stress_score"]
    d_s = d.assign(stress=[lab.get((p, q)) for p, q in zip(d["province_code"], d["target_quarter"])])
    rows = []
    for q, tr, te in splits(d_s, OUTER_MIN):
        th = float(tr["stress"].median())
        tr2, te2 = tr.assign(y=(tr["stress"] > th).astype(int)), te.assign(y=(te["stress"] > th).astype(int))
        scores = {c["id"]: qacc(walk(tr2, c, start=INNER_MIN)) for c in members}
        top = max(scores.values())
        ch = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te2["province_code"].values,
                                  "y": te2["y"].values, "p": fit_predict(ch, tr2, te2)}))
    lt = pd.concat(rows, ignore_index=True)
    lt["pred"] = (lt["p"] >= THR).astype(int)
    res["P_with_training_median_labels_(diagnostic)"] = metrics(lt)

    # ---- frozen prospective configuration: what P selects using all labelled data
    scores = {c["id"]: qacc(walk(d, c, start=INNER_MIN)) for c in members}
    top = max(scores.values())
    final = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
    frozen = {"procedure": "nested P, pool and order as pre-registered", "selected_with_data_through": "2025-Q4",
              "selected_configuration": {k: v for k, v in final.items()}, "inner_score_all_data": round(top, 4),
              "tied_at_top": [k for k, v in scores.items() if abs(v - top) < 1e-12],
              "comparison_frozen": GOVCFG["frozen_from"],
              "preregistration_sha256": PREREG_SHA,
              "protocol": "Fit the selected configuration on every labelled row through 2025-Q4 with the strict-timing "
                          "frame; forecast each quarter from 2026-Q1 onward from data released before that quarter; score "
                          "against Eq. 3 labels (global threshold 14.6 unchanged) once SWS publishes the round; report "
                          "every quarter, whatever the result, alongside persistence and clock-only."}
    (EXP / "FROZEN_PROSPECTIVE_CONFIG.json").write_text(json.dumps(frozen, indent=2, default=str))
    frozen_sha = hashlib.sha256((EXP / "FROZEN_PROSPECTIVE_CONFIG.json").read_bytes()).hexdigest()
    res["frozen_prospective"] = {**frozen, "sha256": frozen_sha}

    pd.concat(allp).to_csv(EXP / "fixed_config_predictions.csv", index=False)
    (EXP / "results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({"P": r["P_nested"]["metrics"], "acceptance": r["P_nested"]["acceptance"]}, default=str)[:3000])
