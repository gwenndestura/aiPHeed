"""
E137 Layer S evaluation (development evidence; PROTOCOL.md). Run once after the lock:

    python -m app.e137.evaluate lock        write data/e137/out/PROTOCOL_LOCK.json (hashes of protocol + code)
    python -m app.e137.evaluate run         verify the lock, then evaluate and write data/e137/out/results.json

Schemes
    V1  pooled HFIAS rows (2015 + ENNS), leave-one-region-out (17 FNRI 2015 regions; a province's rows share a fold)
    V2  train on FNRI 2015 only, predict ENNS 2018/2019 (out-of-round transfer; ENNS was examined in hfias-1.0)
Leads 0-4 (features frozen k quarters before the survey's reference quarter).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from sklearn.metrics import roc_auc_score

from app.e137 import OUT, PROTOCOL_VERSION, VERSION
from app.e137 import features as F
from app.e137 import model as M
from app.e137 import outcomes as O
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e137" / "PROTOCOL.md"
CODE = ["outcomes.py", "features.py", "model.py", "evaluate.py"]
PRIMARY = ("mod_sev", "pooled")
SENSITIVITY = [("insecure", "pooled"), ("mod_sev", "round")]
N_BOOT = 2000
THRESHOLDS = {
    "S1_eb_ci_upper_vs_B0_B2": 0.0,   # cluster-bootstrap 95 % upper bound of EB(LGBM) - EB(baseline) must be < 0
    "S2_auc": 0.70, "S2_auc_ci_lower": 0.60,
    "S3_balanced_accuracy": 0.70, "S3_recall_elevated": 0.60, "S3_precision_elevated": 0.50,
    "S4_ece": 0.10,
    "S5_island_auc": 0.60,
    "S6_overfit_gap": 0.05,
    "S8_v2_auc": 0.65,
    "S9_sensitivity_auc": 0.65,
    "S10_dominance_median": 0.80,
    "S11_external_spearman": 0.40, "S11_external_p": 0.05,
    "formulation_tie": 0.005,
}


def _sha(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes() -> dict:
    here = BACKEND_DIR / "app" / "e137"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()}


def lock() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(),
           "hashes": _hashes(), "thresholds": THRESHOLDS, "note": "written before any E137 model was fitted"}
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps(rec, indent=2))
    return rec


def verify_lock() -> None:
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    now = _hashes()
    bad = [k for k, v in rec["hashes"].items() if now.get(k) != v]
    if bad:
        raise RuntimeError(f"E137 lock mismatch: {bad}")


# ---------------------------------------------------------------- metrics
def metrics(df: pd.DataFrame, p_col: str = "p") -> dict:
    d = df.dropna(subset=[p_col])
    p, q = d[p_col].values, d["q"].values
    out = {"n": int(len(d)), "expected_brier": M.expected_brier(p, q)}
    dec = d[d["status"].isin(["ELEVATED", "LOWER"])]
    out["n_decisive"], out["n_elevated"] = int(len(dec)), int((dec["status"] == "ELEVATED").sum())
    if len(dec) and dec["status"].nunique() == 2:
        yt = (dec["status"] == "ELEVATED").astype(int).values
        pr = dec[p_col].values
        yh = (pr >= 0.5).astype(int)
        tp, fp = int(((yh == 1) & (yt == 1)).sum()), int(((yh == 1) & (yt == 0)).sum())
        tn, fn = int(((yh == 0) & (yt == 0)).sum()), int(((yh == 0) & (yt == 1)).sum())
        rec = tp / (tp + fn) if tp + fn else np.nan
        spec = tn / (tn + fp) if tn + fp else np.nan
        prec = tp / (tp + fp) if tp + fp else np.nan
        out.update({"auc": float(roc_auc_score(yt, pr)), "accuracy": (tp + tn) / len(yt), "recall_elevated": rec,
                    "specificity": spec, "precision_elevated": prec, "balanced_accuracy": (rec + spec) / 2,
                    "f1_elevated": 2 * prec * rec / (prec + rec) if prec and rec and (prec + rec) else 0.0,
                    "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}})
    bins = np.clip((p * 5).astype(int), 0, 4)
    out["ece"] = float(sum(abs(p[bins == b].mean() - q[bins == b].mean()) * (bins == b).mean() for b in range(5) if (bins == b).any()))
    nd = d[d["status"] == "NOT_DISTINGUISHABLE"]
    out["mean_p_not_distinguishable"] = float(nd[p_col].mean()) if len(nd) else None
    if "yhat" in d and d["yhat"].notna().sum() > 3:
        out["spearman_y"] = float(spearmanr(d["yhat"], d["y"]).statistic)
    return out


def boot_diff(df: pd.DataFrame, a: str, b: str, rng) -> list[float]:
    """Cluster (region) bootstrap 95 % interval of EB(a) - EB(b) on rows where both exist."""
    d = df.dropna(subset=[a, b])
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    vals = []
    for _ in range(N_BOOT):
        s = pd.concat([g[r] for r in rng.choice(regs, len(regs))])
        vals.append(M.expected_brier(s[a], s["q"]) - M.expected_brier(s[b], s["q"]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def boot_auc(df: pd.DataFrame, col: str, rng) -> list[float] | None:
    d = df[df["status"].isin(["ELEVATED", "LOWER"])].dropna(subset=[col])
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    vals = []
    for _ in range(N_BOOT):
        s = pd.concat([g[r] for r in rng.choice(regs, len(regs))])
        if s["status"].nunique() == 2:
            vals.append(roc_auc_score((s["status"] == "ELEVATED").astype(int), s[col]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else None


# ---------------------------------------------------------------- schemes
def _data(outcome, reference, lead) -> pd.DataFrame:
    d = O.load(outcome, reference)
    d = d[d["has_value"]].reset_index(drop=True)
    return F.build(d, lead)


def _group_shares(c: pd.DataFrame) -> pd.DataFrame:
    a = c.drop(columns=["bias"]).abs()
    g = pd.DataFrame({grp: a[[f for f in fs if f in a]].sum(axis=1) for grp, fs in F.GROUPS.items() if grp != "anchor"})
    return g.div(g.sum(axis=1).replace(0, np.nan), axis=0)


def run_v1(X: pd.DataFrame, kind: str) -> tuple[pd.DataFrame, dict]:
    oof = X[["key", "province", "region", "island", "survey", "y", "se_y", "q", "status", "prev_y"]].copy()
    for c in ["LGBM", "B0_base_rate", "B1_persistence", "B2_psa_only", "B3_logistic", "yhat"]:
        oof[c] = np.nan
    shares, train_eb, cfgs = [], [], []
    for reg in X["region"].unique():
        te, tr = X["region"] == reg, X["region"] != reg
        for name, mdl in M.candidates(kind).items():
            mdl.fit(X[tr])
            if name == "B1_persistence":
                rows = te & X["prev_y"].notna()
                if rows.any():
                    oof.loc[rows, name] = mdl.predict_proba(X[rows])
                continue
            oof.loc[te, name] = mdl.predict_proba(X[te])
            if name == "LGBM":
                oof.loc[te, "yhat"] = mdl.predict_y(X[te])
                train_eb.append((tr.sum(), M.expected_brier(mdl.predict_proba(X[tr]), X.loc[tr, "q"])))
                shares.append(_group_shares(mdl.contributions(X[te])))
                cfgs.append(mdl.cfg_)
    tw = sum(n for n, _ in train_eb)
    extra = {"train_expected_brier": float(sum(n * e for n, e in train_eb) / tw),
             "configs": pd.Series(cfgs).value_counts().to_dict(), "group_shares": pd.concat(shares)}
    return oof, extra


def run_v2(X: pd.DataFrame, kind: str) -> pd.DataFrame:
    tr, te = X[X["survey"] == "FNRI2015"], X[X["survey"] != "FNRI2015"]
    cols = [f for f in F.FEATURES if f != "a_prev_y"]
    oof = te[["key", "province", "region", "island", "survey", "y", "se_y", "q", "status", "prev_y"]].copy()
    mods = {"LGBM": M.LGBRisk(kind, cols), "B0_base_rate": M.BaseRate(), "B2_psa_only": M.SoftLogit(M.PSA_ONLY),
            "B3_logistic": M.SoftLogit(cols)}
    for name, mdl in mods.items():
        mdl.fit(tr)
        oof[name] = mdl.predict_proba(te)
        if name == "LGBM":
            oof["yhat"] = mdl.predict_y(te)
    oof["B1_persistence"] = M.Persistence().fit(tr).predict_proba(te)       # change variance = 2015 between-province
    return oof


def summarise(oof: pd.DataFrame, rng, with_ci: bool = True) -> dict:
    out = {}
    for c in ["LGBM", "B0_base_rate", "B1_persistence", "B2_psa_only", "B3_logistic"]:
        sub = oof.copy()
        if c != "LGBM":
            sub = sub.drop(columns=["yhat"])
        out[c] = metrics(sub, c)
    if with_ci:
        out["LGBM"]["auc_ci95"] = boot_auc(oof, "LGBM", rng)
        out["diff_ci95"] = {b: boot_diff(oof, "LGBM", b, rng) for b in ["B0_base_rate", "B2_psa_only", "B3_logistic", "B1_persistence"]}
        isl = {}
        for i, g in oof.groupby("island"):
            dec = g[g["status"].isin(["ELEVATED", "LOWER"])]
            cnt = dec["status"].value_counts()
            if cnt.get("ELEVATED", 0) >= 3 and cnt.get("LOWER", 0) >= 3:
                isl[i] = float(roc_auc_score((dec["status"] == "ELEVATED").astype(int), dec["LGBM"]))
            else:
                isl[i] = None
        out["island_auc"] = isl
        enns = oof[oof["prev_y"].notna()]
        out["enns_rows"] = {c: metrics(enns.drop(columns=["yhat"]) if c != "LGBM" else enns, c) for c in ["LGBM", "B1_persistence"]}
    return out


def gate_checks(v1: dict, v2: dict, extra: dict, sens: dict, external: dict | None) -> dict:
    T, L = THRESHOLDS, v1["LGBM"]
    pts_better = all(L["expected_brier"] < v1[b]["expected_brier"] for b in ["B0_base_rate", "B2_psa_only", "B3_logistic"])
    ci_ok = all(v1["diff_ci95"][b][1] < T["S1_eb_ci_upper_vs_B0_B2"] for b in ["B0_base_rate", "B2_psa_only"])
    isl = [a for a in v1["island_auc"].values() if a is not None]
    dom = float(extra["group_shares"].max(axis=1).median())
    c = {
        "S1_beats_baselines": pts_better and ci_ok,
        "S2_discrimination": L.get("auc", 0) >= T["S2_auc"] and (L.get("auc_ci95") or [0])[0] >= T["S2_auc_ci_lower"],
        "S3_classes": L.get("balanced_accuracy", 0) >= T["S3_balanced_accuracy"] and L.get("recall_elevated", 0) >= T["S3_recall_elevated"]
                      and (L.get("precision_elevated") or 0) >= T["S3_precision_elevated"],
        "S4_calibration": L["ece"] <= T["S4_ece"],
        "S5_island_stability": len(isl) >= 2 and min(isl) >= T["S5_island_auc"],
        "S6_overfitting": L["expected_brier"] - extra["train_expected_brier"] <= T["S6_overfit_gap"],
        "S7_beats_persistence_enns": v1["enns_rows"]["LGBM"]["expected_brier"] < v1["enns_rows"]["B1_persistence"]["expected_brier"],
        "S8_out_of_round": v2["LGBM"].get("auc", 0) >= T["S8_v2_auc"],
        "S9_sensitivity": all(s["LGBM"].get("auc", 0) >= T["S9_sensitivity_auc"] for s in sens.values()) if sens else None,
        "S10_no_dominance": dom <= T["S10_dominance_median"],
        "S11_external": None if external is None else (external["spearman"] >= T["S11_external_spearman"] and external["p"] < T["S11_external_p"]),
    }
    return {"checks": c, "dominance_median": dom, "passed_development": all(v is True for k, v in c.items() if k != "S11_external")}


def run() -> dict:
    verify_lock()
    rng = np.random.default_rng(M.SEED)
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(),
           "leads": {}, "formulation_choice": {}}
    # formulation choice at Lead 0 (frozen rule)
    X0 = _data(*PRIMARY, 0)
    eb = {}
    for kind in ("REL", "SOFT"):
        oof, _ = run_v1(X0, kind)
        eb[kind] = metrics(oof, "LGBM")["expected_brier"]
    kind = "SOFT" if eb["SOFT"] < eb["REL"] - THRESHOLDS["formulation_tie"] else "REL"
    res["formulation_choice"] = {"lead0_v1_expected_brier": eb, "chosen": kind}
    preds = []
    for lead in F.LEADS:
        X = _data(*PRIMARY, lead)
        oof1, extra = run_v1(X, kind)
        v1 = summarise(oof1, rng)
        oof2 = run_v2(X, kind)
        v2 = summarise(oof2, rng, with_ci=False)
        sens = {}
        for oc, ref in SENSITIVITY:
            o_s, _ = run_v1(_data(oc, ref, lead), kind)
            sens[f"{oc}/{ref}"] = summarise(o_s, rng, with_ci=False)
        other = "REL" if kind == "SOFT" else "SOFT"
        o_other, _ = run_v1(X, other)
        g = gate_checks(v1, v2, extra, sens, None)
        res["leads"][str(lead)] = {"V1": v1, "V2": v2, "sensitivity": sens, "other_formulation_V1": summarise(o_other, rng, with_ci=False)["LGBM"],
                                   "train_expected_brier": extra["train_expected_brier"], "configs": extra["configs"],
                                   "group_share_mean": extra["group_shares"].mean().round(4).to_dict(),
                                   "group_share_top": extra["group_shares"].idxmax(axis=1).value_counts().to_dict(),
                                   "gate": g}
        preds.append(oof1.assign(lead=lead, scheme="V1"))
        preds.append(oof2.assign(lead=lead, scheme="V2"))
        print("lead", lead, "AUC", round(v1["LGBM"].get("auc", np.nan), 3), "EB", round(v1["LGBM"]["expected_brier"], 4),
              {k: v for k, v in g["checks"].items()})
    passed = [int(L) for L, r in res["leads"].items() if r["gate"]["passed_development"]]
    mx = None
    for L in F.LEADS:
        if L in passed:
            mx = L
        else:
            break
    res["max_reliable_lead_development"] = mx
    OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(preds).to_csv(OUT / "oof_predictions.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
