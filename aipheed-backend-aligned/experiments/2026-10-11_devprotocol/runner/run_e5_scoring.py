"""
E5: candidate risk-scoring formulas (protocol ../E5_SCORING_PROTOCOL.md). Isolated; evaluates S2 and P1 once.

  S2  z = (SWS_t - mu_R)/sigma_R + d_p,t/sigma_d ; HIGH if z > median_ref(z)      (standardized equal weights)
  P1  HIGH if food YoY(p,t) > r_ref and food YoY(p,t-1) > r_ref                (inflation RATE, not index level)
All reference parameters come from data published before 2023-10-01 and are frozen.

DRY RUN BY DEFAULT.
    PYTHONPATH=. python experiments/2026-10-11_devprotocol/runner/run_e5_scoring.py [--execute --authorized-by "<name>"]
Tests: tests/unit/test_e5_scoring.py
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

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T

_here = Path(__file__).parent
for _name, _file in (("run_exploratory", "run_exploratory.py"), ("run_e3_compact_lgbm", "run_e3_compact_lgbm.py"),
                     ("run_e2_relative_cpi", "run_e2_relative_cpi.py"), ("run_e4_risk_definitions", "run_e4_risk_definitions.py")):
    if _name not in sys.modules:
        _s = importlib.util.spec_from_file_location(_name, _here / _file)
        _m = importlib.util.module_from_spec(_s)
        sys.modules[_name] = _m
        _s.loader.exec_module(_m)
E1, E2, E3, E4 = (sys.modules[n] for n in ("run_exploratory", "run_e2_relative_cpi", "run_e3_compact_lgbm",
                                            "run_e4_risk_definitions"))

EXP = Path("experiments/2026-10-11_devprotocol")
RUNS = EXP / "runs"
PROTOCOL = EXP / "E5_SCORING_PROTOCOL.md"
RUNNER = Path(__file__)
FIRST = "2023-Q4"
TEST_QUARTERS = E1.TEST_PRIMARY
MODEL = "E3-LightGBM"
MONO = {"S2": E3.MONOTONE, "P1": [0] * len(E3.INPUTS)}
PROTECTED_GLOBS = E4.PROTECTED_GLOBS + ("experiments/2026-10-11_devprotocol/runs/20261011T120714Z_E4/*",)


def prev_q(q: str) -> str:
    return T.prev(q)


# ---------------------------------------------------------------- S2 (hunger-anchored, standardized)
def s2_reference(vault) -> dict:
    ref_q = E1.fold_plan([FIRST])[0].train_quarters
    ref = vault.training(ref_q, FIRST)
    sws = ref.groupby("quarter")["stress_score"].mean()                 # quarter mean of stress = SWS
    d = (ref["stress_score"] - ref["quarter"].map(sws)) / 2
    p = {"mu_R": float(sws.mean()), "sigma_R": float(sws.std(ddof=0)), "sigma_d": float(d.std(ddof=0)),
         "reference_quarters": ref_q}
    p["cutoff"] = float(np.median(s2_score(ref, p, "quarter")))
    return p


def s2_score(rows: pd.DataFrame, p: dict, qcol: str) -> np.ndarray:
    if not (rows.groupby(qcol).size() == 5).all():
        raise RuntimeError("S2 needs all five provinces of each quarter")
    sws = rows.groupby(qcol)["stress_score"].transform("mean")
    d = (rows["stress_score"] - sws) / 2
    return ((sws - p["mu_R"]) / p["sigma_R"] + d / p["sigma_d"]).values


# ---------------------------------------------------------------- P1 (price stress, inflation rate)
class PriceVault:
    """P1 labels with publication timing; training access only before the target; reveal after predictions."""

    def __init__(self, table: pd.DataFrame, r_ref: float):
        t = table[["quarter", "province_code", "food_cpi_yoy_target"]].rename(columns={"food_cpi_yoy_target": "yoy"})
        if (t["quarter"] > E1.LAST_LABEL).any():
            raise RuntimeError("a 2026 value is present")
        prev = t.assign(quarter=t["quarter"].map(lambda q: T.nxt(q))).rename(columns={"yoy": "yoy_prev"})
        t = t.merge(prev, on=["quarter", "province_code"], how="left")
        t = t[t["yoy_prev"].notna()].copy()                              # 2021-Q1 has no in-window predecessor
        t["y"] = ((t["yoy"] > r_ref) & (t["yoy_prev"] > r_ref)).astype(int)
        self._t, self.r_ref = t, r_ref
        self._registered, self.revealed = {}, []

    def quarters(self):
        return sorted(self._t["quarter"].unique())

    def training(self, quarters, target):
        if any(q >= target for q in quarters):
            raise PermissionError(f"training access to a quarter not before {target}")
        return self._t[self._t["quarter"].isin(quarters)].copy()

    def register_predictions(self, key, path):
        self._registered[key] = E1.sha256(path)

    def reveal(self, key, target):
        if key not in self._registered:
            raise PermissionError(f"{target} requested before predictions {key} were written")
        self.revealed.append(key)
        return self._t[self._t["quarter"] == target].copy()


def p1_reference(table: pd.DataFrame) -> dict:
    ref_q = E2.eligible_quarters(FIRST, sorted(table["quarter"].unique()))
    vals = table[table["quarter"].isin(ref_q)]["food_cpi_yoy_target"]
    return {"r_ref": float(vals.median()), "reference_quarters": ref_q}


def p1_folds(pv: PriceVault):
    out = []
    for t in TEST_QUARTERS:
        e = [q for q in pv.quarters() if q < t and E2.published(q)[0] < T.qstart(t)]
        out.append(E1.Fold(t, T.qstart(t), e) if len(e) >= E1.MIN_TRAIN_QUARTERS else None)
    return out


# ---------------------------------------------------------------- predictions (label-free)
def _add(out, fold_target, prov, model, score, pred, thr, n, share, note=""):
    out.append(pd.DataFrame({"target_quarter": fold_target, "province_code": prov, "model": model,
                             "score": score, "pred": np.asarray(pred).astype(int), "cutoff": thr,
                             "n_train_quarters": n, "train_high_share": share, "note": note}))


def _lgbm(tr_X, y, te_X, mono, fitter, check):
    m = fitter(tr_X, y, mono)
    p = m.predict_proba(te_X)[:, 1]
    if check and not np.array_equal(p, fitter(tr_X, y, mono).predict_proba(te_X)[:, 1]):
        raise RuntimeError("not reproducible")
    return p


def predict_s2(frame, vault, fold, ref, fitter=E3.fit_lgbm, check=True):
    tr = E3.add_last_published_stress(E1.training_matrix(frame, vault, fold), vault, fold.target)
    te = E3.add_last_published_stress(E1.test_matrix(frame, fold.target), vault, fold.target)
    y = (s2_score(tr, ref, "target_quarter") > ref["cutoff"]).astype(int)
    share, out, prov = float(y.mean()), [], te["province_code"].values
    p = _lgbm(tr[E3.INPUTS], y, te[E3.INPUTS], MONO["S2"], fitter, check)
    _add(out, fold.target, prov, MODEL, p, p >= E3.CUT, ref["cutoff"], len(fold.train_quarters), share)
    lps = te["last_published_stress"].values                              # anchor quarter: 5 provinces
    anchor = pd.DataFrame({"q": "a", "stress_score": lps})
    z_cf = s2_score(anchor, ref, "q")
    _add(out, fold.target, prov, "carry-forward", z_cf - ref["cutoff"], z_cf > ref["cutoff"], ref["cutoff"],
         len(fold.train_quarters), share)
    z_rule = (te["sws_hunger"].values - ref["mu_R"]) / ref["sigma_R"] + te["cpi_rel"].values / ref["sigma_d"]
    fb = int(share >= 0.5)
    _add(out, fold.target, prov, "origin-rule", z_rule - ref["cutoff"],
         np.where(np.isnan(z_rule), fb, z_rule > ref["cutoff"]), ref["cutoff"], len(fold.train_quarters), share)
    for name, v in (("always-HIGH (reference)", 1), ("always-LOW (reference)", 0)):
        _add(out, fold.target, prov, name, np.full(5, np.nan), np.full(5, v), ref["cutoff"],
             len(fold.train_quarters), share, "constant: AUC undefined")
    return pd.concat(out, ignore_index=True)


def predict_p1(frame, vault, pv, fold, fitter=E3.fit_lgbm, check=True):
    lab = pv.training(fold.train_quarters, fold.target)
    tr = frame[frame["target_quarter"].isin(fold.train_quarters)].merge(
        lab[["quarter", "province_code", "y"]], left_on=["target_quarter", "province_code"],
        right_on=["quarter", "province_code"], how="inner", suffixes=("", "_l"))
    if len(tr) != 5 * len(fold.train_quarters):
        raise RuntimeError(f"{fold.target}: P1 training rows incomplete")
    tr = E3.add_last_published_stress(tr, vault, fold.target)
    te = E3.add_last_published_stress(E1.test_matrix(frame, fold.target), vault, fold.target)
    y = tr["y"].values
    share, out, prov = float(y.mean()), [], te["province_code"].values
    p = _lgbm(tr[E3.INPUTS], y, te[E3.INPUTS], MONO["P1"], fitter, check)
    _add(out, fold.target, prov, MODEL, p, p >= E3.CUT, pv.r_ref, len(fold.train_quarters), share)
    last = lab[lab["quarter"] == max(fold.train_quarters)].set_index("province_code")["y"].reindex(prov).values
    _add(out, fold.target, prov, "carry-forward", np.full(5, np.nan), last, pv.r_ref, len(fold.train_quarters), share,
         "binary label carried forward: AUC not computed")
    r = te["food_cpi_yoy"].values
    fb = int(share >= 0.5)
    _add(out, fold.target, prov, "origin-rule", r - pv.r_ref, np.where(np.isnan(r), fb, r > pv.r_ref), pv.r_ref,
         len(fold.train_quarters), share, "latest available provincial food YoY vs r_ref")
    for name, v in (("always-HIGH (reference)", 1), ("always-LOW (reference)", 0)):
        _add(out, fold.target, prov, name, np.full(5, np.nan), np.full(5, v), pv.r_ref,
             len(fold.train_quarters), share, "constant: AUC undefined")
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- descriptive proportions (post-run)
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
         "PH040400000": "Rizal", "PH040500000": "Batangas"}


def proportions(df: pd.DataFrame, ycol: str) -> dict:
    return {"all": {"HIGH": int(df[ycol].sum()), "LOW": int(len(df) - df[ycol].sum())},
            "high_share_by_year": df.groupby(df["quarter"].str[:4])[ycol].mean().round(3).to_dict(),
            "high_count_by_quarter": df.groupby("quarter")[ycol].sum().astype(int).to_dict(),
            "high_share_by_province": {NAMES[k]: round(v, 3) for k, v in df.groupby("province_code")[ycol].mean().items()}}


# ---------------------------------------------------------------- run
def summarize(g):
    block = {}
    for m, mg in g.groupby("model"):
        block[m] = {**E3.metrics(mg, brier=(m == MODEL)), **E4.extra_metrics(mg)}
        block[m]["quarter_bootstrap_accuracy_95"] = E1.quarter_bootstrap(mg[mg["pred"] >= 0])
    lg = g[g["model"] == MODEL]
    boots = {b: E3.paired_ba_bootstrap(lg, g[g["model"] == b]) for b in ("carry-forward", "origin-rule")}
    block["paired_balanced_accuracy_bootstrap_LightGBM_minus"] = boots
    shim = {**block, "Eq3-rule": block["origin-rule"]}                  # E3.decision expects this key
    block["decision_rule"] = E3.decision(shim, {"carry-forward": boots["carry-forward"], "Eq3-rule": boots["origin-rule"]})
    return block


def execute(authorized_by: str, runs_root: Path = RUNS) -> Path:
    E1.assert_no_forbidden_modules()
    if not PROTOCOL.exists():
        raise FileNotFoundError(PROTOCOL)
    before = E1.snapshot_hashes(PROTECTED_GLOBS)
    vault = E1.LabelVault.from_project()
    table = E2.target_table()
    s2ref, p1ref = s2_reference(vault), p1_reference(table)
    pv = PriceVault(table, p1ref["r_ref"])
    frame, _ = D.development_frame()
    s2_folds, p1f = E1.fold_plan(TEST_QUARTERS), p1_folds(pv)

    run = E1.RunDir(runs_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_E5"))
    run.write_json("config.json", {
        "experiment": "E5 candidate scoring formulas S2 and P1 (isolated; exploratory; 5th analysis on reused quarters)",
        "authorized_by": authorized_by, "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": PROTOCOL.as_posix(), "sha256": E1.sha256(PROTOCOL)}, "runner_sha256": E1.sha256(RUNNER),
        "S2": {"formula": "z = (SWS_t - mu_R)/sigma_R + d/sigma_d; HIGH if z > cutoff", **s2ref},
        "P1": {"formula": "HIGH if food_yoy(p,t) > r_ref and food_yoy(p,t-1) > r_ref", **p1ref},
        "model": {"lgbm_params": E3.LGBM_PARAMS, "inputs": E3.INPUTS, "monotone": MONO},
        "test_quarters": TEST_QUARTERS,
        "folds": {"S2": {f.target: f.train_quarters for f in s2_folds},
                  "P1": {t: (f.train_quarters if f else "ineligible") for t, f in zip(TEST_QUARTERS, p1f)}},
        "input_provenance_sha256": {k: v for k, v in before.items() if k.startswith(("data/processed", "evidence/2026-10"))},
    })
    scored = []
    for f in s2_folds:
        key = f"S2__{f.target}"
        preds = predict_s2(frame, vault, f, s2ref)
        vault.register_predictions(key, run.write_csv(f"pred_{key}.csv", preds))
        lab = vault.reveal(key, f.target)
        y = (s2_score(lab, s2ref, "quarter") > s2ref["cutoff"]).astype(int)
        scored.append(preds.merge(lab[["province_code"]].assign(y=y), on="province_code").assign(candidate="S2"))
    for t, f in zip(TEST_QUARTERS, p1f):
        if f is None:
            continue
        key = f"P1__{t}"
        preds = predict_p1(frame, vault, pv, f)
        pv.register_predictions(key, run.write_csv(f"pred_{key}.csv", preds))
        lab = pv.reveal(key, t)
        scored.append(preds.merge(lab[["province_code", "y"]], on="province_code").assign(candidate="P1"))
    allr = pd.concat(scored, ignore_index=True)
    run.write_csv("scored_rows.csv", allr)

    # descriptive class proportions over authorized history (after every reveal)
    lab_all = vault._lab.copy()
    lab_all["S2"] = (s2_score(lab_all, s2ref, "quarter") > s2ref["cutoff"]).astype(int)
    p1_all = pv._t.copy()
    run.write_json("metrics.json", {
        "label": "E5 EXPLORATORY: 5th analysis on 7 reused quarters; n_eff ~ 7; thresholds are empirical, not official.",
        "results": {c: summarize(g) for c, g in allr.groupby("candidate")},
        "class_proportions_2021_2025": {"S2": proportions(lab_all, "S2"), "P1": proportions(p1_all, "y")},
        "test_class_counts": {c: {"HIGH": int(g[g["model"] == MODEL]["y"].sum()),
                                  "LOW": int((g[g["model"] == MODEL]["y"] == 0).sum())} for c, g in allr.groupby("candidate")}})
    after = E1.snapshot_hashes(PROTECTED_GLOBS)
    E1.assert_unchanged(before, after)
    E1.assert_no_forbidden_modules()
    run.write_json("manifest.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                     "protected_files_checked": len(before), "protected_files_unchanged": True,
                                     "labels_revealed_after_predictions": vault.revealed + pv.revealed,
                                     "outputs_sha256": dict(run.written)})
    return run.path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E5 candidate scoring formulas")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--authorized-by", default="")
    a = ap.parse_args(argv)
    if not Path("app/ml").is_dir():
        ap.error("run from aipheed-backend-aligned/ with PYTHONPATH=.")
    if a.execute and not a.authorized_by.strip():
        ap.error("--execute requires --authorized-by")
    E1.assert_no_forbidden_modules()
    if not a.execute:
        v, t = E1.LabelVault.from_project(), E2.target_table()
        pv = PriceVault(t, p1_reference(t)["r_ref"])
        print(json.dumps({"S2": s2_reference(v), "P1": p1_reference(t),
                          "P1_fold_sizes": {tq: (len(f.train_quarters) if f else None)
                                            for tq, f in zip(TEST_QUARTERS, p1_folds(pv))}}, indent=1, default=str))
        print("DRY RUN: nothing fitted, nothing written.")
        return 0
    print(f"run written to {execute(a.authorized_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
