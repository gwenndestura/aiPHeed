"""
scripts/supplementary/window2021_study.py

Window study v3 under experiments/2026-10-09_window2021/PREREGISTRATION_v3.json
(hash checked at start): approved period 2021-2026 only, data corrections
K1-K4 kept, strict Rule 3 timing, pre-registered nested procedure P4, frozen
label-blind 2026 forecasts. In-memory only: nothing in data/processed,
models/, config/ or earlier evidence is written; nothing is served.

    python -m scripts.supplementary.window2021_study
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import scripts.supplementary.generalization_study as G
import scripts.supplementary.improvement_study as I
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
from app.ml.features.feature_selector import EQUATION5_FEATURES

warnings.filterwarnings("ignore")
EXP = Path("experiments/2026-10-09_window2021")
PREREG = EXP / "PREREGISTRATION_v3.json"
PREREG_SHA = "34ea59d455b85e9b9e59aec1416eb03b743c01c4abbf94db0b1ac570172fa606"
P = Path("data/processed")
START = "2021-Q1"
THR_PRIMARY, THR_SENS = 14.345, 14.6
SEED, OUTER_MIN, INNER_MIN, CUT = 42, 8, 5, 0.5
KEY = ["target_quarter", "province_code"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
         "PH040400000": "Rizal", "PH040500000": "Batangas"}
NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "fssi_article_count", "news_ph_fssi", "news_ph_count"] + I.TRIGGERS
DERIVED_PREFIX = ("_lag1", "_accel")
EXTRA_PROSPECTIVE = ["2026-Q1"]          # feature quarters appended for label-blind forecasts


def qi(q):
    return R.qi(q)


# ============================================================ frame
def window_features(extend=True):
    f, log = I.corrected_features()              # K1-K4 on the 2020-2025 grid
    key = ["province_code", "quarter"]
    if extend:
        add = pd.DataFrame([{"province_code": p, "quarter": q, "t": qi(q)}
                            for q in EXTRA_PROSPECTIVE for p in NAMES])
        f = pd.concat([f, add], ignore_index=True)
        # sources that genuinely cover 2026 (no fill)
        fq = pd.read_parquet(P / "fssi_quarterly.parquet")[key + ["FSSI", "article_count"]]
        tp = pd.read_parquet(P / "trigger_proportions.parquet")[key + I.TRIGGERS]
        m = f[key].merge(fq, on=key, how="left").merge(tp, on=key, how="left", suffixes=("", "_tp"))
        new = f["quarter"].isin(EXTRA_PROSPECTIVE).values
        f.loc[new, "FSSI"] = m.loc[new, "FSSI"].values
        f.loc[new, "fssi_article_count"] = m.loc[new, "article_count"].fillna(0).values
        for c in I.TRIGGERS:
            f.loc[new, c] = m.loc[new, c].values
        pov = f[f["quarter"] == "2025-Q4"].set_index("province_code")["poverty_incidence"]
        f.loc[new, "poverty_incidence"] = f.loc[new, "province_code"].map(pov).values   # 2023 survey, released 2024-08

    # previously unused provincial retail rice (PSA OpenStat), t-1 after the shift below
    psa = pd.read_parquet(P / "psa_indicators.parquet")[key + ["rice_price_regular", "rice_price_well"]].rename(
        columns={"rice_price_regular": "rice_retail_regular", "rice_price_well": "rice_retail_well"})
    f = f.drop(columns=[c for c in ("rice_retail_regular", "rice_retail_well") if c in f]).merge(psa, on=key, how="left")

    # national/regional news pool: every retained article in quarter t, any province
    g = pd.read_parquet(P / "corpus_geocoded.parquet")[["quarter", "food_insecurity_score"]]
    g = g[pd.to_numeric(g["food_insecurity_score"], errors="coerce") >= 0.30]
    ph = g.groupby(g["quarter"].astype(str))["food_insecurity_score"].agg(["mean", "size"])
    f["news_ph_fssi"] = f["quarter"].map(ph["mean"])
    f["news_ph_count"] = f["quarter"].map(ph["size"]).fillna(0)

    # Window rule W: nothing with a reference period before 2021-Q1
    pre = f["quarter"].map(qi) < qi(START)
    base = [c for c in f.columns if c not in ("province_code", "quarter", "t", "cpi_dev", "cpi_rel")
            and not c.endswith(DERIVED_PREFIX) and c not in ("FSSI_lag2",)]
    f.loc[pre, base] = np.nan
    f.loc[f["quarter"] <= "2022-Q3", "poverty_incidence"] = np.nan      # 2018 survey vintage
    log["window"] = {"pre2021_rows_blanked": int(pre.sum()),
                     "poverty_2018_vintage_blanked": int(((f["quarter"] <= "2022-Q3") & ~pre).sum())}

    # recompute every derived column from the windowed bases
    f = f.sort_values(["province_code", "t"]).reset_index(drop=True)
    gp = f.groupby("province_code")
    for c in I.LAG_SERIES:
        f[f"{c}_lag1"] = gp[c].shift(1)
        f[f"{c}_accel"] = f[c] - f[f"{c}_lag1"]
    f["FSSI_lag1"] = gp["FSSI"].shift(1)
    f["FSSI_lag2"] = gp["FSSI"].shift(2)
    f["FSSI_accel"] = f["FSSI"] - f["FSSI_lag1"]
    f["cpi_dev"] = f["food_cpi_yoy"] - gp["food_cpi_yoy"].transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean())
    f["cpi_rel"] = f["food_cpi_yoy"] - f.groupby("quarter")["food_cpi_yoy"].transform("mean")
    f["cpi_rel_lag1"] = f.groupby("province_code")["cpi_rel"].shift(1)
    return f, log


def sws_known(q_feature):
    """Latest and previous SWS rounds (reference >= 2021-Q1) released before the forecast quarter starts."""
    rel = T.sws_release_dates()
    sws = pd.read_parquet(P / "sws_hunger.parquet").groupby("quarter")["pct_total_hunger"].first()
    target = T.nxt(q_feature)
    known = sorted([s for s in sws.index if s in rel and qi(s) >= qi(START) and rel[s] < T.qstart(target)], key=qi)
    if not known:
        return np.nan, np.nan, np.nan, None
    last = known[-1]
    change = sws[last] - sws[known[-2]] if len(known) > 1 else np.nan
    return float(sws[last]), float(change) if change == change else np.nan, qi(target) - qi(last), last


def window_frame(extend=True):
    f, log = window_features(extend)
    k = f["quarter"].map(lambda q: sws_known(q)[:3])
    f["sws_hunger"] = [v[0] for v in k]
    f["sws_change"] = [v[1] for v in k]
    f["sws_age"] = [v[2] for v in k]
    skip = set(NLP) | {"province_code", "quarter", "t", "poverty_incidence", "sws_hunger", "sws_change", "sws_age"}
    gov = [c for c in f.columns if c not in skip and pd.api.types.is_numeric_dtype(f[c])]
    f = f.sort_values(["province_code", "t"])
    f[gov] = f.groupby("province_code")[gov].shift(1)          # strict timing, no fill
    inputs = [c for c in f.columns if c not in ("province_code", "quarter", "t")]
    return f, inputs, gov, log


def window_labels(threshold):
    lab = pd.read_parquet(P / "labels.parquet")
    lab = lab[lab["quarter"].map(qi) >= qi(START)].copy()
    lab["label_stress"] = (lab["stress_score"] > threshold).astype(int)
    return lab


def feature_sets(inputs):
    eq5 = list(EQUATION5_FEATURES)
    struct2 = ["sws_hunger", "cpi_rel"]
    struct5 = ["sws_hunger", "sws_change", "sws_age", "cpi_rel", "cpi_rel_lag1"]
    plus = ["rice_retail_regular", "rice_retail_well", "news_ph_fssi", "news_ph_count"]
    extra = set(plus) | {"sws_change", "sws_age", "cpi_rel_lag1"}
    gov_c = [c for c in inputs if c not in extra]
    return {"struct2": struct2, "struct5": struct5, "eq5_struct": eq5 + struct2 + ["fssi_article_count"],
            "gov_c": gov_c, "gov_c_plus": gov_c + plus}


# ============================================================ models
class RuleT:
    """Eq. 3 applied to origin-known values with the label threshold."""
    def __init__(self, thr):
        self.thr = thr

    def fit(self, X, y):
        self.base = float(np.mean(y))
        return self

    def predict_proba(self, X):
        s = X["sws_hunger"].values + 2 * X["cpi_rel"].values
        p = 1 / (1 + np.exp(-(s - self.thr) / 2.0))
        p = np.where(np.isnan(p), self.base, p)
        return np.c_[1 - p, p]


def pool(fsets, thr):
    out = [{"id": "struct_rule", "family": "rule", "thr": thr, "cols": ["sws_hunger", "cpi_rel"]}]
    for m in I.pool(fsets)[1:]:
        out.append(m)
    return out


def make(cfg, y):
    return RuleT(cfg["thr"]) if cfg["family"] == "rule" else I.make(cfg, y)


def fit_predict(cfg, tr, te):
    m = make(cfg, tr["y"].values).fit(tr[cfg["cols"]], tr["y"])
    return m.predict_proba(te[cfg["cols"]])[:, 1]


def walk(d, cfg, start=OUTER_MIN):
    rows = []
    for q, tr, te in G.splits(d, start):
        if tr["y"].nunique() < 2:
            continue
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(cfg, tr, te)}))
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= CUT).astype(int)
    return r


def choose(tr, members):
    scores = {c["id"]: G.qacc(walk(tr, c, start=INNER_MIN)) for c in members}
    top = max(scores.values())
    ch = next(c for c in members if abs(scores[c["id"]] - top) < 1e-12)
    return ch, top, sum(abs(v - top) < 1e-12 for v in scores.values()), scores


def nested(d, members):
    rows, choices = [], []
    for q, tr, te in G.splits(d, OUTER_MIN):
        ch, top, nt, _ = choose(tr, members)
        rows.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                  "y": te["y"].values, "p": fit_predict(ch, tr, te)}))
        choices.append({"outer_quarter": q, "chosen": ch["id"], "inner_score": round(top, 4), "n_tied": nt})
    r = pd.concat(rows, ignore_index=True)
    r["pred"] = (r["p"] >= CUT).astype(int)
    return r, choices


# ============================================================ references
def persistence(d, labels):
    rel = T.sws_release_dates()
    lab = labels.set_index(["province_code", "quarter"])["label_stress"]
    out = []
    for _, r in d.iterrows():
        cand = [s for (p, s) in lab.index if p == r["province_code"] and qi(s) < qi(r["target_quarter"])
                and s in rel and rel[s] < T.qstart(r["target_quarter"])]
        out.append(int(lab[(r["province_code"], max(cand, key=qi))]) if cand else np.nan)
    return np.array(out, dtype=float)


def detail(r):
    x = r.copy()
    x["province"] = x["province_code"].map(NAMES)
    x["correct"] = (x["y"] == x["pred"]).astype(int)
    byq = x.groupby("target_quarter").agg(high=("y", "sum"), pred_high=("pred", "sum"))
    out = {"accuracy_by_province": x.groupby("province")["correct"].mean().round(3).to_dict(),
           "missed_high_rows": int(((x["y"] == 1) & (x["pred"] == 0)).sum()),
           "false_high_rows": int(((x["y"] == 0) & (x["pred"] == 1)).sum()),
           "recall_high": round(float(x[x["y"] == 1]["pred"].mean()), 4) if (x["y"] == 1).any() else None,
           "missed_high_risk_quarters (majority HIGH, predicted majority LOW)": int(((byq["high"] >= 3) & (byq["pred_high"] < 3)).sum()),
           "quarters_uniform_prediction": int(byq["pred_high"].isin([0, 5]).sum())}
    if "p" in x and x["p"].notna().all():
        out["share_of_probability_variance_between_quarters"] = round(
            float(x.groupby("target_quarter")["p"].transform("mean").var() / x["p"].var()), 3) if x["p"].var() > 0 else None
    return out


def evaluate(d, labels, thr, members, inputs, tag):
    pers = d[KEY + ["y"]].copy()
    pers["pred"] = persistence(d, labels)
    pers = pers[pers["target_quarter"].map(qi) >= qi(G.qs(d)[OUTER_MIN])].copy()
    pers["pred"] = pers["pred"].fillna(0).astype(int)
    clock = walk(d.assign(time_index=d["t"]), {"id": "clock", "family": "lgbm", "w": "spw", "cols": ["time_index"]})
    refs = {"persistence_timing_valid": pers, "clock_only": clock}
    P4, choices = nested(d, members)
    fs = feature_sets(inputs)
    named = {"struct_rule": members[0],
             "MODEL-B2 config (gov_c, spw)": {"id": "b2", "family": "lgbm", "w": "spw", "cols": fs["gov_c"]},
             "MODEL-A config (eq5, default)": {"id": "a", "family": "lgbm", "w": None, "cols": list(EQUATION5_FEATURES)}}
    desc = {k: walk(d, v) for k, v in named.items()}
    maj = []
    for q, tr, te in G.splits(d, OUTER_MIN):
        s = tr["y"].mean()
        maj.append(pd.DataFrame({"target_quarter": q, "province_code": te["province_code"].values,
                                 "y": te["y"].values, "p": s, "pred": int(s > 0.5)}))
    desc["clock_only"] = clock
    desc["training_majority"] = pd.concat(maj, ignore_index=True)
    desc["persistence_timing_valid"] = pers.assign(p=np.nan)
    out = {"threshold": thr, "P4": {"metrics": G.metrics(P4), "acceptance": G.acceptance(P4, refs),
                                    "choices": choices, "detail": detail(P4)},
           "descriptive": {k: {"metrics": G.metrics(v), "detail": detail(v)} for k, v in desc.items()},
           "descriptive_acceptance": {k: G.acceptance(desc[k], refs)["verdict"] for k in named}}
    return out, P4, desc


# ============================================================ main
def main():
    EXP.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(PREREG.read_bytes()).hexdigest() == PREREG_SHA, "pre-registration changed"
    f, inputs, gov, log = window_frame(extend=True)
    fs = feature_sets(inputs)
    res = {"provenance": {
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="..").stdout.strip(),
        "preregistration_sha256": PREREG_SHA, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "improvement_script_sha256": hashlib.sha256(Path(I.__file__).read_bytes()).hexdigest(),
        "data_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.glob("*.parquet"))
                        if p.stem in ("features_fused", "labels", "sws_hunger", "oil_prices", "bsp_macro", "pagasa_climate",
                                      "province_rainfall", "fssi_quarterly", "trigger_proportions", "psa_indicators",
                                      "corpus_geocoded", "commodity_prices")},
        "inputs": inputs, "n_inputs": len(inputs), "feature_sets": fs, "seed": SEED}, "frame_log": log}

    # data audit within the window
    lab_all = window_labels(THR_PRIMARY)
    inwin = f[(f["quarter"].map(qi) >= qi(START)) & (f["quarter"] <= "2025-Q4")]
    res["data_audit"] = {
        "missing_share_by_input_2021_2025": inwin[inputs].isna().mean().round(3).to_dict(),
        "fssi_observed_cells_2021_2025": int(inwin["FSSI"].notna().sum()), "cells_2021_2025": int(len(inwin)),
        "news_ph_count_by_quarter": inwin.groupby("quarter")["news_ph_count"].first().astype(int).to_dict(),
        "quarter_common_inputs": [c for c in inputs if inwin.groupby("quarter")[c].nunique().max() <= 1],
        "label_rows": int(len(lab_all)), "label_quarters": int(lab_all["quarter"].nunique()),
        "high_share_primary": round(float(lab_all["label_stress"].mean()), 3),
        "between_quarter_share_of_stress_variance": round(float(
            lab_all.groupby("quarter")["stress_score"].transform("mean").var() / lab_all["stress_score"].var()), 3),
        "label_equals_sws_above_threshold": round(float(((lab_all["sws_hunger_pct"] > THR_PRIMARY).astype(int)
                                                         == lab_all["label_stress"]).mean()), 3),
        "rows_differ_14345_vs_146": int(((lab_all["stress_score"] > THR_PRIMARY) != (lab_all["stress_score"] > THR_SENS)).sum()),
    }

    # ---- primary threshold
    d = R.pairs(f[f["quarter"] <= "2025-Q4"], lab_all, 1)
    res["outer_test_quarters"] = G.qs(d)[OUTER_MIN:]
    members = pool(fs, THR_PRIMARY)
    res["pool_size"] = len(members)
    primary, P4, desc = evaluate(d, lab_all, THR_PRIMARY, members, inputs, "primary")
    res["primary"] = primary
    P4.to_csv(EXP / "P4_nested_predictions.csv", index=False)
    pd.concat([v.assign(model=k) for k, v in desc.items()]).to_csv(EXP / "descriptive_predictions.csv", index=False)

    # every pool member at fixed settings (descriptive)
    fixed, allp = {}, []
    for cfg in members:
        r = walk(d, cfg)
        fixed[cfg["id"]] = {**G.metrics(r), "detail": detail(r)}
        allp.append(r.assign(config=cfg["id"]))
    res["fixed_configurations"] = fixed
    pd.concat(allp).to_csv(EXP / "fixed_config_predictions.csv", index=False)

    # ---- diagnostics: components and alternative targets (not adopted)
    lab = lab_all.assign(cpi_rel_target=lab_all["food_cpi_yoy"] - lab_all["regional_food_cpi_yoy"])
    x = d.merge(lab[["province_code", "quarter", "sws_hunger_pct", "cpi_rel_target"]].rename(columns={"quarter": "target_quarter"}), on=KEY)
    outer = x[x["target_quarter"].map(qi) >= qi(G.qs(d)[OUTER_MIN])].dropna(subset=["sws_hunger", "cpi_rel"])
    ql = x.dropna(subset=["sws_hunger"]).groupby("target_quarter").agg(known=("sws_hunger", "first"), target=("sws_hunger_pct", "first"),
                                                                       age=("sws_age", "first"))
    regime = []
    for q in res["outer_test_quarters"]:
        prior = ql[ql.index.map(qi) < qi(q)]
        med = float(prior["target"].median())
        regime.append(int((ql.loc[q, "target"] > med) == (ql.loc[q, "known"] > med)))
    y = outer["y"].values
    res["diagnostics"] = {
        "sws_age_quarters_mean_all": round(float(ql["age"].mean()), 2),
        "sws_age_quarters_mean_outer": round(float(ql.loc[res["outer_test_quarters"], "age"].mean()), 2),
        "sws_known_vs_target_corr": round(float(ql["known"].corr(ql["target"])), 3),
        "oracle_true_sws_plus_known_cpi_rel": round(float(((outer["sws_hunger_pct"] + 2 * outer["cpi_rel"] > THR_PRIMARY).astype(int) == y).mean()), 4),
        "oracle_known_sws_plus_true_cpi_rel": round(float(((outer["sws_hunger"] + 2 * outer["cpi_rel_target"] > THR_PRIMARY).astype(int) == y).mean()), 4),
        "alt_target_regional_regime_rule_accuracy": round(float(np.mean(regime)), 4), "alt_regime_quarters": len(regime),
        "alt_target_province_relative_rule_accuracy": round(float(((outer["cpi_rel_target"] > 0) == (outer["cpi_rel"] > 0)).mean()), 4),
        "alt_province_relative_within_quarter_spearman": round(float(np.nanmean(
            [spearmanr(g["cpi_rel"], g["cpi_rel_target"]).correlation for _, g in outer.groupby("target_quarter")])), 3),
    }

    # ---- sensitivity: threshold 14.6
    lab_s = window_labels(THR_SENS)
    d_s = R.pairs(f[f["quarter"] <= "2025-Q4"], lab_s, 1)
    sens, _, _ = evaluate(d_s, lab_s, THR_SENS, pool(fs, THR_SENS), inputs, "sens")
    res["sensitivity_threshold_14.6"] = {"P4": sens["P4"]["metrics"], "P4_verdict": sens["P4"]["acceptance"]["verdict"],
                                         "descriptive": {k: v["metrics"] for k, v in sens["descriptive"].items()}}

    # ---- frozen, label-blind 2026 forecasts
    ch, top, nt, scores = choose(d, members)
    feats = f[f["quarter"].isin(["2025-Q4"] + EXTRA_PROSPECTIVE)].copy()
    feats["target_quarter"] = feats["quarter"].map(T.nxt)
    cands = {"P4_choice": ch, "struct_rule": members[0],
             "MODEL-B2 config (gov_c, spw)": {"id": "b2", "family": "lgbm", "w": "spw", "cols": fs["gov_c"]}}
    rows = []
    for name, cfg in cands.items():
        m = make(cfg, d["y"].values).fit(d[cfg["cols"]], d["y"])
        p = m.predict_proba(feats[cfg["cols"]])[:, 1]
        rows.append(pd.DataFrame({"candidate": name, "config": cfg["id"], "target_quarter": feats["target_quarter"].values,
                                  "province": feats["province_code"].map(NAMES).values, "p_high": np.round(p, 4),
                                  "pred_high": (p >= CUT).astype(int), "sws_known": feats["sws_hunger"].values,
                                  "cpi_rel_known": np.round(feats["cpi_rel"].values, 3)}))
    fc = pd.concat(rows, ignore_index=True)
    fc.to_csv(EXP / "FROZEN_2026_FORECASTS.csv", index=False)
    frozen = {"issued": pd.Timestamp.now().isoformat(timespec="seconds"),
              "labels_seen": "none: no 2026 SWS round is in the project data",
              "targets": sorted(fc["target_quarter"].unique()), "P4_choice": ch, "P4_inner_score": round(top, 4),
              "P4_tied_at_top": nt, "threshold": THR_PRIMARY, "preregistration_sha256": PREREG_SHA,
              "forecasts_sha256": hashlib.sha256((EXP / "FROZEN_2026_FORECASTS.csv").read_bytes()).hexdigest(),
              "not_issued": {"2026-Q3": "needs provincial food CPI for 2026-Q1 (psa_indicators ends 2025-Q4)",
                             "2026-Q4": "needs provincial food CPI for 2026-Q2"},
              "caveat": "issued after the forecast origin from current data vintages; label-blind, not as-released"}
    (EXP / "FROZEN_2026_FORECASTS.json").write_text(json.dumps(frozen, indent=2, default=str))
    res["frozen_2026"] = frozen
    (EXP / "results.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({"P4": r["primary"]["P4"]["metrics"], "verdict": r["primary"]["P4"]["acceptance"]["verdict"]}, default=str)[:2000])
