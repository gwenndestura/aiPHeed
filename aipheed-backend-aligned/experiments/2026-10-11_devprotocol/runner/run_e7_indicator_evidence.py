"""
E7: one-time evaluation of indicator-group evidence (protocol ../E7_INDICATOR_EVIDENCE_PROTOCOL.md).

All predictions are produced label-free and written first; labels are revealed afterwards.
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e7_indicator_evidence.py --execute --authorized-by "<name>"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_here = Path(__file__).parent
for _name, _file in (("run_exploratory", "run_exploratory.py"), ("run_e3_compact_lgbm", "run_e3_compact_lgbm.py"),
                     ("run_e6_final_evaluation", "run_e6_final_evaluation.py")):
    if _name not in sys.modules:
        _s = importlib.util.spec_from_file_location(_name, _here / _file)
        _m = importlib.util.module_from_spec(_s)
        sys.modules[_name] = _m
        _s.loader.exec_module(_m)
E1, E3, E6 = (sys.modules[n] for n in ("run_exploratory", "run_e3_compact_lgbm", "run_e6_final_evaluation"))

import scripts.supplementary.devprotocol_rule_l as D
from app.ml.features import risk_score_v2 as R
from app.ml.training import datadriven_trainer as DD
from app.ml.training import revised_trainer as RT

EXP = Path("experiments/2026-10-11_devprotocol")
PROTOCOL = EXP / "E7_INDICATOR_EVIDENCE_PROTOCOL.md"
SERVED = Path("data/revised/datadriven_forecasts_retrospective.parquet")
E6_SERVED = Path("data/revised/revised_forecasts_retrospective.parquet")
TEST = E1.TEST_PRIMARY
CONFIGS = {"M1 R (core)": ("R",), "M2 government (GP+GN)": ("GP", "GN"), "M3 news (N)": ("N",),
           "M4 government+news": ("GP", "GN", "N"), "M5 full (R+GP+GN+N)": ("R", "GP", "GN", "N")}
PERM_DRAWS = 200
# Fixed 2026-10-12 after the E7 run: "runs/20261012T*/*" also matched E7's own run folder, so the guard flagged
# E7's outputs as changes. The E6 run folder is now named explicitly. (E7 was not re-run.)
PROTECTED_GLOBS = E6.PROTECTED_GLOBS + ("experiments/2026-10-11_devprotocol/runs/20261012T083041Z_E6/*",
                                         "experiments/2026-10-11_devprotocol/E7_INDICATOR_EVIDENCE_PROTOCOL.md")
SEED = 42


# ---------------------------------------------------------------- existing configuration (M0)
def m0_forecast(frame, labels, target, tau):
    import joblib
    from lightgbm import LGBMClassifier
    from app.ml.features.feature_selector import EQUATION5_FEATURES
    params = joblib.load("models/lgbm_best.pkl")["model"].get_params()
    params.update(random_state=SEED, verbosity=-1)
    train_q = D.eligible_training_quarters(target, "development")
    lab = labels.for_target(train_q, target)
    tr = frame[frame["target_quarter"].isin(train_q)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"])
    te = frame[frame["target_quarter"] == target].sort_values("province_code")
    cols = list(EQUATION5_FEATURES)
    y = (tr["stress"] > tau).astype(int).values
    m = LGBMClassifier(**params).fit(tr[cols], y)
    return pd.DataFrame({"target_quarter": target, "province_code": te["province_code"].values,
                         "probability": m.predict_proba(te[cols])[:, 1]})


def m5_models(frame, labels, target, tau, kind):
    train_q = D.eligible_training_quarters(target, "development")
    lab = labels.for_target(train_q, target)
    tr = frame[frame["target_quarter"].isin(train_q)].merge(
        lab, left_on=["target_quarter", "province_code"], right_on=["quarter", "province_code"])
    tr = RT.with_last_published_stress(tr, labels, target)
    te = RT.with_last_published_stress(frame[frame["target_quarter"] == target].sort_values("province_code"), labels, target)
    cols = DD.usable_columns(tr, DD.columns_for(("R", "GP", "GN", "N")))
    y = (tr["stress"] > tau).astype(int).values if kind == "classifier" else tr["stress"].values
    return DD.fit(tr[cols], y, kind), te.reset_index(drop=True), cols


# ---------------------------------------------------------------- metrics helpers
def binary_rows(name, preds, base):
    """preds: target_quarter, province_code, probability (+ optional classification); base: artifact-like inputs."""
    m = preds.merge(base, on=["target_quarter", "province_code"], how="left")
    cls = m["classification"] if "classification" in m else m["probability"].map(lambda p: R.final_classification(p))
    pred = np.where(cls == R.HIGH, 1, np.where(cls == R.LOW, 0, -1))
    return pd.DataFrame({"target_quarter": m["target_quarter"], "province_code": m["province_code"], "model": name,
                         "score": m["probability"], "pred": pred, "classification": cls})


def baselines(base, tau):
    out = []
    s3 = base["sws_hunger"] + 2 * base["cpi_rel"]
    for name, sc in (("Carry-forward", base["last_published_stress"] - tau), ("Equation 3 rule", s3 - tau),
                     ("Regional-only rule", base["sws_hunger"] - tau)):
        pr = (sc > 0).astype(int)
        out.append(pd.DataFrame({"target_quarter": base["target_quarter"], "province_code": base["province_code"],
                                 "model": name, "score": sc, "pred": pr, "classification": np.where(pr == 1, "HIGH", "LOW")}))
    for name, v in (("Always-HIGH", 1), ("Always-LOW", 0)):
        out.append(pd.DataFrame({"target_quarter": base["target_quarter"], "province_code": base["province_code"],
                                 "model": name, "score": np.nan, "pred": v, "classification": "HIGH" if v else "LOW"}))
    return pd.concat(out, ignore_index=True)


def reg_metrics(r: pd.DataFrame, col: str) -> dict:
    from scipy.stats import spearmanr
    e = r[col] - r["stress"]
    wq = [spearmanr(g[col], g["stress"]).correlation for _, g in r.groupby("target_quarter")
          if g[col].nunique() > 1 and g["stress"].nunique() > 1]
    return {"rmse": round(float(np.sqrt(np.mean(e ** 2))), 3), "mae": round(float(np.mean(np.abs(e))), 3),
            "within_quarter_spearman_mean": round(float(np.nanmean(wq)), 3) if wq else None,
            "per_quarter_mae": {q: round(float(np.mean(np.abs(g[col] - g["stress"]))), 2) for q, g in r.groupby("target_quarter")}}


def rmse_boot(r: pd.DataFrame, a: str, b: str, draws=10_000) -> dict:
    qs = sorted(r["target_quarter"].unique())
    groups = {q: r[r["target_quarter"] == q] for q in qs}
    rng = np.random.default_rng(SEED)
    d = []
    for _ in range(draws):
        s = pd.concat([groups[qs[i]] for i in rng.integers(0, len(qs), len(qs))])
        d.append(np.sqrt(np.mean((s[a] - s["stress"]) ** 2)) - np.sqrt(np.mean((s[b] - s["stress"]) ** 2)))
    point = np.sqrt(np.mean((r[a] - r["stress"]) ** 2)) - np.sqrt(np.mean((r[b] - r["stress"]) ** 2))
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"rmse_diff": round(float(point), 3), "ci95": [round(float(lo), 3), round(float(hi), 3)]}


def permutation(models: dict, y_by_key: dict, kind: str) -> dict:
    """Permute one group's columns jointly across the pooled test rows; mean increase in loss."""
    rng = np.random.default_rng(SEED)
    pooled = pd.concat([te.assign(_fold=t) for t, (m, te, cols) in models.items()], ignore_index=True)
    y = np.array([y_by_key[(r.target_quarter, r.province_code)] for r in pooled.itertuples()])

    def loss(df):
        pred = np.empty(len(df))
        for t, (m, _, cols) in models.items():
            idx = (df["_fold"] == t).values
            pred[idx] = m.predict_proba(df.loc[idx, cols])[:, 1] if kind == "classifier" else m.predict(df.loc[idx, cols])
        if kind == "classifier":
            p = np.clip(pred, 1e-6, 1 - 1e-6)
            return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        return float(np.sqrt(np.mean((pred - y) ** 2)))

    base = loss(pooled)
    out = {"baseline_loss": round(base, 4)}
    for g, cols in DD.GROUPS.items():
        present = [c for c in cols if c in pooled.columns]
        inc = []
        for _ in range(PERM_DRAWS):
            perm = rng.permutation(len(pooled))
            d = pooled.copy()
            d[present] = pooled[present].values[perm]
            inc.append(loss(d) - base)
        out[g] = {"mean_increase": round(float(np.mean(inc)), 4), "p5_p95": [round(float(np.percentile(inc, 5)), 4),
                                                                            round(float(np.percentile(inc, 95)), 4)]}
    return out


# ---------------------------------------------------------------- run
def execute(authorized_by: str) -> Path:
    E6.assert_isolated()
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    meta = json.loads(SERVED.with_name(SERVED.stem + "_meta.json").read_text(encoding="utf-8"))
    if E1.sha256(SERVED) != meta["sha256"]["artifact"]:
        raise RuntimeError("served artifact hash mismatch")
    run = E1.RunDir(E1.RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E7"))
    labels = RT.TrainingLabels(RT.load_stress())
    taus = {"tau0_10.843 (primary)": labels.reference(RT.RETROSPECTIVE_AS_OF)[0],
            "approved_14.345 (leakage-affected)": labels.reference(RT.PROSPECTIVE_AS_OF)[0]}
    frame, _ = D.development_frame()
    served = pd.read_parquet(SERVED)
    selected = {t: tuple(served.loc[served["target_quarter"] == t, "selected_groups"].iloc[0].split("+")) for t in TEST}

    # ---- 1. label-free predictions
    preds, regs, perm_models, base_rows = {}, [], {}, []
    for tname, tau in taus.items():
        rows = []
        for t in TEST:
            fx = DD.forecast_quarter(frame, labels, t, tau, groups=("R",))         # inputs for baselines
            base_rows.append(fx.rows.assign(reference=tname, tau=tau)[["reference", "tau", "target_quarter", "province_code",
                             "sws_hunger", "cpi_rel", "last_published_stress"]])
            for name, g in CONFIGS.items():
                rows.append(DD.forecast_quarter(frame, labels, t, tau, groups=g).rows.assign(model=name))
            if tname.startswith("tau0"):
                rows.append(served[served["target_quarter"] == t].assign(model="M6 training-only selection (served)"))
            else:
                rows.append(DD.forecast_quarter(frame, labels, t, tau).rows.assign(model="M6 training-only selection (served)"))
            rows.append(m0_forecast(frame, labels, t, tau).assign(model="M0 existing configuration"))
            perm_models[(tname, t)] = m5_models(frame, labels, t, tau, "classifier")
        p = pd.concat(rows, ignore_index=True)
        preds[tname] = p
        run.write_csv(f"pred_{tname.split(' ')[0]}.csv", p[["model", "target_quarter", "province_code", "probability"] +
                                                            (["classification", "selected_groups"] if "classification" in p else [])])
    reg_models = {}
    for t in TEST:
        r = DD.forecast_quarter(frame, labels, t, taus["tau0_10.843 (primary)"], groups=("R",)).rows
        rr = r[["target_quarter", "province_code", "last_published_stress", "sws_hunger", "cpi_rel"]].copy()
        for name, g in list(CONFIGS.items()) + [("M6 training-only selection (served)", selected[t])]:
            rr[name] = DD.regress_quarter(frame, labels, t, g)["pred_stress"].values
        regs.append(rr)
        reg_models[t] = m5_models(frame, labels, t, 0.0, "regressor")
    reg = pd.concat(regs, ignore_index=True)
    run.write_csv("pred_regression.csv", reg)
    base_df = pd.concat(base_rows, ignore_index=True)

    # ---- 2. labels revealed only now
    vault = E1.LabelVault.from_project()
    for k in list(preds) + ["regression"]:
        vault.register_predictions(k, run.path / ("pred_regression.csv" if k == "regression" else f"pred_{k.split(' ')[0]}.csv"))
    stress = pd.concat([vault.reveal("regression", t) for t in TEST])[["quarter", "province_code", "stress_score"]]
    stress = stress.rename(columns={"quarter": "target_quarter", "stress_score": "stress"})
    for k in preds:
        for t in TEST:
            vault.reveal(k, t)

    # ---- 3. binary metrics
    results = {}
    for tname, tau in taus.items():
        p = preds[tname]
        b = base_df[base_df["reference"] == tname]
        scored = [binary_rows(m, g[["target_quarter", "province_code", "probability"]].reset_index(drop=True),
                              b.drop(columns=["reference", "tau"])) for m, g in p.groupby("model")]
        scored.append(baselines(b.reset_index(drop=True), tau))
        s = pd.concat(scored, ignore_index=True).merge(stress, on=["target_quarter", "province_code"])
        s["y"] = (s["stress"] > tau).astype(int)
        block = {m: E6.metrics(g, probabilistic=m.startswith("M")) for m, g in s.groupby("model")}
        cf = s[s["model"] == "Carry-forward"]
        block["paired_BA_vs_carry_forward"] = {m: E3.paired_ba_bootstrap(s[(s["model"] == m) & (s["pred"] >= 0)], cf)
                                               for m in s["model"].unique() if m.startswith("M")}
        yk = {(r.target_quarter, r.province_code): int(r.stress > tau) for r in stress.itertuples()}
        block["permutation_importance_M5_logloss"] = permutation({t: perm_models[(tname, t)] for t in TEST}, yk, "classifier")
        results[tname] = block
        run.write_csv(f"scored_{tname.split(' ')[0]}.csv", s)

    # ---- 4. continuous stress (tertiary)
    r = reg.merge(stress, on=["target_quarter", "province_code"])
    r["Carry-forward stress"] = r["last_published_stress"]
    r["Equation 3 origin estimate"] = r["sws_hunger"] + 2 * r["cpi_rel"]
    r["SWS input only"] = r["sws_hunger"]
    cols = list(CONFIGS) + ["M6 training-only selection (served)", "Carry-forward stress", "Equation 3 origin estimate",
                            "SWS input only"]
    regression = {c: reg_metrics(r, c) for c in cols}
    regression["rmse_diff_vs_carry_forward"] = {c: rmse_boot(r, c, "Carry-forward stress") for c in cols[:6]}
    regression["group_comparisons"] = {
        "adding government to news (M4 - M3)": rmse_boot(r, "M4 government+news", "M3 news (N)"),
        "adding news to government (M4 - M2)": rmse_boot(r, "M4 government+news", "M2 government (GP+GN)"),
        "adding all non-core groups to core (M5 - M1)": rmse_boot(r, "M5 full (R+GP+GN+N)", "M1 R (core)")}
    yk = {(x.target_quarter, x.province_code): x.stress for x in stress.itertuples()}
    regression["permutation_importance_M5_rmse"] = permutation(reg_models, yk, "regressor")
    run.write_csv("scored_regression.csv", r)

    # ---- 5. before/after: E6 served (fixed 7 inputs) vs M6 served (data-driven)
    e6 = pd.read_parquet(E6_SERVED)
    ba = {}
    for name, a in (("E6 fixed 7 inputs", e6), ("E7 M6 data-driven", served)):
        ba[name] = {"probabilities": E6.describe(a["probability"]),
                    "classifications_by_year": {y: g["classification"].value_counts().to_dict()
                                                for y, g in a.groupby(a["target_quarter"].str[:4])}}
    ba["selection_by_quarter"] = {q: v for q, v in meta["selection_by_quarter"].items() if v and v.get("selected")}

    run.write_json("metrics.json", {
        "label": "E7 EXPLORATORY (7th analysis on 7 reused quarters; n_eff ~ 7). Contributions are not causal.",
        "binary": results, "continuous_stress": regression, "before_after": ba})
    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    E6.assert_isolated()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(), "authorized_by": authorized_by,
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed,
                                     "served_artifact_sha256": E1.sha256(SERVED), "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not a.execute or not a.authorized_by.strip():
        ap.error("this one-time evaluation requires --execute --authorized-by")
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
