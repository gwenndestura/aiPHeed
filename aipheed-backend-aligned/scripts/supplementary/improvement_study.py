"""
scripts/supplementary/improvement_study.py

Improvement study v2 under experiments/2026-10-09_improvement/PREREGISTRATION_v2.json
(hash checked at start). It builds a CORRECTED strict-timing frame in memory
(data corrections K1-K4), adds the Eq. 3-structured predictors, runs the
pre-registered nested procedure P3, and records descriptive comparisons and
diagnostics. It never writes to data/processed, models/, config/ or earlier
evidence, and serves nothing.

    python -m scripts.supplementary.improvement_study
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
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.generalization_study as G
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
EXP = Path("experiments/2026-10-09_improvement")
PREREG = EXP / "PREREGISTRATION_v2.json"
PREREG_SHA = "380c005041806c492e94a9e628717b9a1f97f1715883800dac063604423bf8ca"
P = Path("data/processed")
SEED, OUTER_MIN, INNER_MIN, THR = 42, 8, 5, 0.5
KEY = ["target_quarter", "province_code"]
THRESHOLD_EQ3 = 14.6

COMMODITY = ["commodity_fruit_veg", "commodity_leafy_veg", "commodity_livestock", "commodity_poultry", "commodity_rootcrops"]
LAG_SERIES = ["food_cpi_yoy", "food_minus_headline_yoy", "unemployment_rate", "ofw_remit_yoy_pct",
              "rainfall_anomaly_pct", "rice_price_regular", "diesel_php_per_l"]
SOURCE_GAPS = {  # column -> (source table, source column)
    "diesel_php_per_l": ("oil_prices", "diesel_php_per_l"), "gasoline_php_per_l": ("oil_prices", "gasoline_php_per_l"),
    "brent_usd_per_bbl": ("oil_prices", "brent_usd_per_bbl"), "fx_usd_php_avg": ("bsp_macro", "fx_usd_php_avg"),
    "ofw_remit_yoy_pct": ("bsp_macro", "ofw_remit_yoy_pct"), "tc_count": ("pagasa_climate", "tc_count"),
    "tc_severe_flag": ("pagasa_climate", "tc_severe_flag"), "drought_alert": ("pagasa_climate", "drought_alert"),
    "enso_numeric": ("pagasa_climate", "enso_phase"),
}
TRIGGERS = ["trigger_market", "trigger_climate", "trigger_employment", "trigger_ofw_remittance", "trigger_fish_kill"]


# ======================================================= corrected frame
def corrected_features() -> tuple[pd.DataFrame, dict]:
    """K1-K4 applied to the fused matrix, before strict-timing alignment."""
    f, labels, _ = R.load()           # fused matrix + poverty vintage (Rule 3)
    f = f.drop(columns=["sws_hunger"])
    log = {}
    key = ["province_code", "quarter"]

    # K1: missing where the source has no observation (was zero-filled)
    for col, (tab, scol) in SOURCE_GAPS.items():
        src = pd.read_parquet(P / f"{tab}.parquet")[key + [scol]]
        m = f[key].merge(src, on=key, how="left")
        missing = m[scol].isna().values
        log[col] = {"cells_set_missing": int(missing.sum()),
                    "were_zero": int((f.loc[missing, col] == 0).sum())}
        f.loc[missing, col] = np.nan

    # K2: province-measured rainfall for every covered quarter
    rain = pd.read_parquet(P / "province_rainfall.parquet")[key + ["rainfall_anomaly_pct"]].rename(
        columns={"rainfall_anomaly_pct": "rain_measured"})
    m = f[key].merge(rain, on=key, how="left")
    changed = (m["rain_measured"].notna() & (m["rain_measured"].values != f["rainfall_anomaly_pct"].values))
    log["rainfall_anomaly_pct"] = {"cells_replaced": int(changed.sum()),
                                   "cells_replaced_2020": int((changed & f["quarter"].str.startswith("2020").values).sum()),
                                   "still_missing": int(m["rain_measured"].isna().sum())}
    f["rainfall_anomaly_pct"] = m["rain_measured"].values

    # K3: news features only where retained articles exist
    fq = pd.read_parquet(P / "fssi_quarterly.parquet")
    fq = fq[fq["quarter"].astype(str).str.match(r"^\d{4}-Q\d$")][key + ["FSSI", "article_count"]]
    m = f[key].merge(fq, on=key, how="left")
    log["FSSI"] = {"observed_cells": int(m["FSSI"].notna().sum()),
                   "previously_filled_cells_now_missing": int(m["FSSI"].isna().sum())}
    f["FSSI"] = m["FSSI"].values
    f["fssi_article_count"] = m["article_count"].fillna(0).values
    tp = pd.read_parquet(P / "trigger_proportions.parquet")
    tp = tp[tp["quarter"].astype(str).str.match(r"^\d{4}-Q\d$")][key + TRIGGERS]
    m = f[key].merge(tp, on=key, how="left")
    log["triggers"] = {"observed_cells": int(m["trigger_market"].notna().sum())}
    for c in TRIGGERS:
        f[c] = m[c].values

    # recompute lags / accel / cpi_dev on the calendar grid, NaN-aware
    f = f.sort_values(["province_code", "t"]).reset_index(drop=True)
    g = f.groupby("province_code")
    for c in LAG_SERIES:
        f[f"{c}_lag1"] = g[c].shift(1)
        f[f"{c}_accel"] = f[c] - f[f"{c}_lag1"]
    f["FSSI_lag1"] = g["FSSI"].shift(1)
    f["FSSI_lag2"] = g["FSSI"].shift(2)
    f["FSSI_accel"] = f["FSSI"] - f["FSSI_lag1"]
    f["cpi_dev"] = f["food_cpi_yoy"] - g["food_cpi_yoy"].transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())

    # K4: drop CPI-derived commodity series
    f = f.drop(columns=COMMODITY)

    # M: Eq. 3's province term (same-quarter cross-section; shifted to t-1 below)
    f["cpi_rel"] = f["food_cpi_yoy"] - f.groupby("quarter")["food_cpi_yoy"].transform("mean")
    return f, log


def corrected_frame():
    f, log = corrected_features()
    labels = pd.read_parquet(P / "labels.parquet")
    rel = T.sws_release_dates()
    sws = pd.read_parquet(P / "sws_hunger.parquet").groupby("quarter")["pct_total_hunger"].first()

    def val(q):
        known = [(rel[s], s) for s in sws.index if s in rel and rel[s] < T.qstart(T.nxt(q))]
        return sws[max(known)[1]] if known else np.nan
    f["sws_hunger"] = f["quarter"].map(val)
    nlp = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "fssi_article_count"] + TRIGGERS
    skip = set(nlp) | {"province_code", "quarter", "t", "poverty_incidence", "sws_hunger"}
    gov = [c for c in f.columns if c not in skip and pd.api.types.is_numeric_dtype(f[c])]
    f = f.sort_values(["province_code", "t"])
    f[gov] = f.groupby("province_code")[gov].shift(1)        # strict timing: t-1, no zero fill
    inputs = [c for c in f.columns if c not in ("province_code", "quarter", "t")]
    return f, labels, inputs, log, gov


# ============================================================ models
class StructRule:
    """HIGH if sws_hunger + 2 * cpi_rel > 14.6 (Eq. 3 applied to origin-known values)."""
    def fit(self, X, y):
        self.base = float(np.mean(y))
        return self

    def predict_proba(self, X):
        s = X["sws_hunger"].values + 2 * X["cpi_rel"].values
        p = 1 / (1 + np.exp(-(s - THRESHOLD_EQ3) / 2.0))
        p = np.where(np.isnan(p), self.base, p)
        return np.c_[1 - p, p]


def make(cfg, ytr):
    if cfg["family"] == "rule":
        return StructRule()
    if cfg["family"] == "logistic":
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                             LogisticRegression(C=cfg["C"], class_weight=cfg["w"], max_iter=5000, random_state=SEED))
    if cfg["family"] == "tree":
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                             DecisionTreeClassifier(max_depth=cfg["depth"], min_samples_leaf=5,
                                                    class_weight=cfg["w"], random_state=SEED))
    p = {"objective": "binary", "verbosity": -1, "random_state": SEED}
    if cfg.get("small"):
        p.update(num_leaves=4, min_child_samples=10, n_estimators=100, learning_rate=0.05)
    if cfg["w"] == "spw":
        pos = float(np.mean(ytr))
        p["scale_pos_weight"] = (1 - pos) / pos
    return LGBMClassifier(**p)


def feature_sets(inputs):
    eq5 = list(EQUATION5_FEATURES)
    struct2 = ["sws_hunger", "cpi_rel"]
    gov_c = [c for c in inputs if c not in ("sws_hunger",)] + ["sws_hunger"]
    return {"struct2": struct2, "eq5_12c": eq5, "eq5_struct": eq5 + struct2 + ["fssi_article_count"], "gov_c": gov_c}


def pool(fsets):
    out = [{"id": "struct_rule", "family": "rule", "cols": ["sws_hunger", "cpi_rel"]}]
    for fs, cols in fsets.items():
        for C in (0.01, 0.1, 1.0, 10.0):
            for w in (None, "balanced"):
                out.append({"id": f"{fs}|logistic|C={C}|w={w}", "family": "logistic", "C": C, "w": w, "cols": cols})
        for depth in (1, 2, 3):
            for w in (None, "balanced"):
                out.append({"id": f"{fs}|tree|depth={depth}|w={w}", "family": "tree", "depth": depth, "w": w, "cols": cols})
        for small in (True, False):
            for w in (None, "spw"):
                out.append({"id": f"{fs}|lgbm|{'small' if small else 'default'}|w={w}", "family": "lgbm",
                            "small": small, "w": w, "cols": cols})
    return out


def fit_predict(cfg, tr, te):
    c = cfg["cols"]
    m = make(cfg, tr["y"].values).fit(tr[c], tr["y"])
    return m.predict_proba(te[c])[:, 1]


def walk(d, cfg, start=OUTER_MIN):
    rows = []
    for q, tr, te in G.splits(d, start):
        if tr["y"].nunique() < 2:
            continue
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(cfg, tr, te)}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= THR).astype(int)
    return r


def nested(d, members):
    rows, choices = [], []
    for q, tr, te in G.splits(d, OUTER_MIN):
        scores = {c["id"]: G.qacc(walk(tr, c, start=INNER_MIN)) for c in members}
        top = max(scores.values())
        ch = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(ch, tr, te)}))
        choices.append({"outer_quarter": q, "chosen": ch["id"], "inner_score": round(top, 4),
                        "n_tied": sum(abs(v - top) < 1e-12 for v in scores.values())})
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= THR).astype(int)
    return r, choices


# ======================================================= diagnostics
def diagnostics(d, labels):
    out = {}
    rel = T.sws_release_dates()
    gaps = []
    for q in sorted(d["target_quarter"].unique(), key=R.qi):
        known = [s for s in rel if rel[s] < T.qstart(q)]
        if known:
            gaps.append({"target_quarter": q, "latest_sws_round": max(known, key=R.qi),
                         "quarters_between": R.qi(q) - R.qi(max(known, key=R.qi))})
    gq = pd.DataFrame(gaps)
    out["effective_sws_horizon"] = {"by_target_quarter": gaps,
                                    "mean_quarters_between_latest_known_sws_and_label": round(float(gq["quarters_between"].mean()), 2),
                                    "outer_mean": round(float(gq[gq["target_quarter"].map(R.qi) >= R.qi("2022-Q4")]["quarters_between"].mean()), 2)}

    lab = labels.copy()
    lab["cpi_rel_target"] = lab["food_cpi_yoy"] - lab["regional_food_cpi_yoy"]
    x = d.merge(lab[["province_code", "quarter", "sws_hunger_pct", "cpi_rel_target", "stress_score"]]
                .rename(columns={"quarter": "target_quarter"}), on=KEY)
    ok = x.dropna(subset=["sws_hunger", "cpi_rel"])
    outer = ok[ok["target_quarter"].map(R.qi) >= R.qi("2022-Q4")]
    qlev = ok.groupby("target_quarter").agg(sws_known=("sws_hunger", "first"), sws_target=("sws_hunger_pct", "first"))
    wq = [spearmanr(g["cpi_rel"], g["cpi_rel_target"]).correlation for _, g in ok.groupby("target_quarter")
          if g["cpi_rel"].nunique() > 1 and g["cpi_rel_target"].nunique() > 1]
    out["component_predictability"] = {
        "sws_known_vs_sws_target_corr_quarters": round(float(qlev["sws_known"].corr(qlev["sws_target"])), 3),
        "sws_target_minus_known_mean_abs": round(float((qlev["sws_target"] - qlev["sws_known"]).abs().mean()), 2),
        "cpi_rel_origin_vs_target_corr": round(float(ok["cpi_rel"].corr(ok["cpi_rel_target"])), 3),
        "cpi_rel_within_quarter_spearman_mean": round(float(np.nanmean(wq)), 3),
        "cpi_rel_sign_agreement": round(float((np.sign(ok["cpi_rel"]) == np.sign(ok["cpi_rel_target"])).mean()), 3),
        "share_of_stress_variance_from_sws_term": round(float(ok.groupby("target_quarter")["stress_score"].transform("mean").var()
                                                              / ok["stress_score"].var()), 3),
    }
    # Oracles (diagnostic only; use target-quarter values, never a model input)
    y = outer["y"].values
    out["oracles_outer_55"] = {
        "true_sws_target_plus_known_cpi_rel": round(float(accuracy_score(y, (outer["sws_hunger_pct"] + 2 * outer["cpi_rel"] > THRESHOLD_EQ3).astype(int))), 4),
        "known_sws_plus_true_cpi_rel_target": round(float(accuracy_score(y, (outer["sws_hunger"] + 2 * outer["cpi_rel_target"] > THRESHOLD_EQ3).astype(int))), 4),
        "true_sws_target_only (quarter regime)": round(float(accuracy_score(y, (outer["sws_hunger_pct"] > THRESHOLD_EQ3).astype(int))), 4),
        "origin_known_both (struct_rule)": round(float(accuracy_score(y, (outer["sws_hunger"] + 2 * outer["cpi_rel"] > THRESHOLD_EQ3).astype(int))), 4),
    }
    # Alternative targets (diagnostic; NOT adopted)
    alt = {}
    qo = qlev[qlev.index.map(R.qi) >= R.qi("2022-Q4")]
    rows = []
    for q in qo.index:
        prior = qlev[qlev.index.map(R.qi) < R.qi(q)]
        med = float(prior["sws_target"].median())
        rows.append({"q": q, "y": int(qo.loc[q, "sws_target"] > med), "pred": int(qo.loc[q, "sws_known"] > med)})
    rr = pd.DataFrame(rows)
    alt["regional_regime: SWS(t+1) above training-period median, predicted by latest released SWS"] = {
        "quarters": int(len(rr)), "accuracy": round(float((rr["y"] == rr["pred"]).mean()), 4)}
    alt["province_relative: cpi_rel(t+1) > 0, predicted by cpi_rel known at origin"] = {
        "rows": int(len(outer)),
        "accuracy": round(float(((outer["cpi_rel_target"] > 0) == (outer["cpi_rel"] > 0)).mean()), 4),
        "within_quarter_spearman_mean_outer": round(float(np.nanmean([spearmanr(g["cpi_rel"], g["cpi_rel_target"]).correlation
                                                                      for _, g in outer.groupby("target_quarter")])), 3)}
    out["alternative_targets"] = alt
    return out


def error_analysis(r, d):
    x = r.merge(d[KEY], on=KEY)
    x["province"] = x["province_code"].map({"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
                                            "PH040400000": "Rizal", "PH040500000": "Batangas"})
    x["err"] = (x["y"] != x["pred"]).astype(int)
    byq = x.groupby("target_quarter").agg(pred_high=("pred", "sum"), high=("y", "sum"))
    return {"errors_by_province": x.groupby("province")["err"].sum().to_dict(),
            "missed_high": int(((x["y"] == 1) & (x["pred"] == 0)).sum()),
            "false_high": int(((x["y"] == 0) & (x["pred"] == 1)).sum()),
            "recall_high": round(float(x[x["y"] == 1]["pred"].mean()), 4),
            "quarters_uniform_prediction": int(byq["pred_high"].isin([0, 5]).sum())}


# ============================================================== main
def main():
    EXP.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(PREREG.read_bytes()).hexdigest() == PREREG_SHA, "pre-registration changed"
    f, labels, inputs, corr_log, gov_cols = corrected_frame()
    d = R.pairs(f, labels, 1)
    d["time_index"] = d["t"]
    fsets = feature_sets(inputs)
    members = pool(fsets)

    f0, lab0, cols0 = A.frame_t2()
    d0 = R.pairs(f0, lab0, 1)
    d0["time_index"] = d0["t"]
    res = {"provenance": {
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="..").stdout.strip(),
        "preregistration_sha256": PREREG_SHA,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "data_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.glob("*.parquet"))
                        if p.stem in ("features_fused", "labels", "sws_hunger", "oil_prices", "bsp_macro", "pagasa_climate",
                                      "province_rainfall", "fssi_quarterly", "trigger_proportions", "psa_indicators")},
        "corrected_inputs": inputs, "n_inputs": len(inputs), "pool_size": len(members),
        "feature_sets": fsets, "seed": SEED, "outer_quarters": G.qs(d)[OUTER_MIN:]},
        "corrections_log": corr_log}

    # same rows as before?
    res["same_outer_rows_as_original"] = bool(d[d["target_quarter"].map(R.qi) >= R.qi("2022-Q4")][KEY].sort_values(KEY).values.tolist()
                                              == d0[d0["target_quarter"].map(R.qi) >= R.qi("2022-Q4")][KEY].sort_values(KEY).values.tolist())

    rows55 = pd.read_csv(G.ROWS55)
    pers = rows55[KEY + ["y", "persistence_timing_valid"]].rename(columns={"persistence_timing_valid": "pred"})
    pers["pred"] = pers["pred"].astype(int)
    clock = walk(d, {"id": "clock", "family": "lgbm", "w": "spw", "cols": ["time_index"]})
    refs = {"persistence_timing_valid": pers, "clock_only": clock}

    # ---------------- primary
    P3, choices = nested(d, members)
    P3.to_csv(EXP / "P3_nested_predictions.csv", index=False)
    res["P3_primary"] = {"metrics": G.metrics(P3), "acceptance": G.acceptance(P3, refs), "choices": choices,
                         "times_chosen": pd.Series([c["chosen"] for c in choices]).value_counts().to_dict(),
                         "errors": error_analysis(P3, d)}

    # ---------------- descriptive
    named = {
        "struct_rule (no fitting)": {"id": "sr", "family": "rule", "cols": ["sws_hunger", "cpi_rel"]},
        "struct2 logistic C=1": {"id": "s2", "family": "logistic", "C": 1.0, "w": None, "cols": fsets["struct2"]},
        "MODEL-A config on corrected frame": {"id": "a", "family": "lgbm", "w": None, "cols": fsets["eq5_12c"]},
        "MODEL-B2 config on corrected frame (gov_c, spw)": {"id": "b2c", "family": "lgbm", "w": "spw", "cols": fsets["gov_c"]},
    }
    desc = {k: walk(d, v) for k, v in named.items()}
    desc["MODEL-B2 original frame"] = G.walk(d0, {"id": "b2", "family": "lgbm", "w": "spw", "cols": cols0})
    desc["MODEL-A config original frame"] = G.walk(d0, {"id": "a0", "family": "lgbm", "w": None, "cols": list(EQUATION5_FEATURES)})
    desc["clock_only"] = clock
    desc["persistence_timing_valid"] = pers.assign(p=np.nan)
    res["descriptive"] = {k: G.metrics(v) for k, v in desc.items()}
    res["descriptive_acceptance"] = {k: G.acceptance(desc[k], refs)["verdict"] for k in named}
    res["descriptive_errors"] = {k: error_analysis(desc[k], d) for k in named}

    fixed = {}
    allp = []
    for cfg in members:
        r = walk(d, cfg)
        fixed[cfg["id"]] = G.metrics(r)
        allp.append(r.assign(config=cfg["id"]))
    res["fixed_configurations"] = fixed
    pd.concat(allp).to_csv(EXP / "fixed_config_predictions.csv", index=False)

    res["diagnostics"] = diagnostics(d, labels)

    # frozen choice of the procedure using all data through 2025-Q4
    scores = {c["id"]: G.qacc(walk(d, c, start=INNER_MIN)) for c in members}
    top = max(scores.values())
    final = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
    frozen = {"procedure": "P3 as pre-registered", "selected": final, "inner_score_all_data": round(top, 4),
              "tied": [k for k, v in scores.items() if abs(v - top) < 1e-12], "preregistration_sha256": PREREG_SHA}
    (EXP / "FROZEN_P3_CHOICE.json").write_text(json.dumps(frozen, indent=2, default=str))
    res["frozen_P3_choice"] = frozen
    (EXP / "results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({"P3": r["P3_primary"]["metrics"], "verdict": r["P3_primary"]["acceptance"]["verdict"]}, default=str)[:2500])
