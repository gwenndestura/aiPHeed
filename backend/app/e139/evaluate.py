"""
E139 evaluation: one locked tuning-and-validation cycle (PROTOCOL.md).

    python -m app.e139.evaluate lock    data/e139/out/PROTOCOL_LOCK.json
    python -m app.e139.evaluate run     -> data/e139/out/results.json, oof_<scheme>.csv

Schemes: LORO (unseen region), LOPO (unseen province), ISLAND (unseen island group), V2 (2015 -> ENNS),
TFWD (2015 + ENNS 2018 -> ENNS 2019, strictly forward in time). Leads 0-4 for the lead-dependent checks.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import average_precision_score, roc_auc_score

from app.e137 import evaluate as E137
from app.e137 import model as M137
from app.e138 import where as WH
from app.e139 import OUT, PROTOCOL_VERSION, VERSION
from app.e139 import model as M
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e139" / "PROTOCOL.md"
CODE = ["model.py", "evaluate.py"]
N_BOOT = 1000
LEADS = [0, 1, 2, 3, 4]
THRESHOLDS = {"G1_ci_upper_vs_NAT": 0.0, "G2_ci_upper_vs_REGPREV": 0.0, "G3_noninferiority_vs_PERS": 0.02,
              "G5_auc": 0.75, "G5_auc_ci_lower": 0.60, "G5_ba": 0.70, "G5_recall": 0.60, "G5_precision": 0.60,
              "G6_ece": 0.10, "G7_gap": 0.05, "G8_island_auc": 0.65, "G9_tfwd_auc": 0.70, "G10_sens_auc": 0.70,
              "G11_mask_change": 0.02, "accuracy_objective": 0.75}
KEEP = WH.KEEP + ["a_region_prev"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e139"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()}


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps(
        {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(),
         "hashes": _hashes(), "thresholds": THRESHOLDS,
         "note": "written before any E139 model was fitted to real outcomes (smoke test used shuffled labels)"}, indent=2))


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E139 lock mismatch: {bad}")


def folds(X, scheme):
    if scheme == "TFWD":
        yield X["survey"] != "ENNS2019", X["survey"] == "ENNS2019"
        return
    yield from WH.folds(X, scheme)


def oof(X, scheme, names, cols=None, mask=None):
    out = X[KEEP].copy()
    gaps, cfg = {n: [] for n in names}, []
    for tr, te in folds(X, scheme):
        Xte = X[te].copy()
        if mask:
            Xte[mask] = np.nan
        for n in names:
            m = M.make(n, cols).fit(X[tr])
            rows = Xte.index if n != "PERS" else Xte.index[Xte["prev_y"].notna()]
            if len(rows):
                out.loc[rows, n] = m.predict_proba(Xte.loc[rows])
            if n != "PERS":
                gaps[n].append((int(tr.sum()), M137.expected_brier(m.predict_proba(X[tr]), X.loc[tr, "q"])))
            if n == "LGBM":
                cfg.append({"n_trees": m.n_trees_, "alpha": m.base_.alpha_ if m.base_ else None})
    tr_eb = {n: sum(k * e for k, e in v) / sum(k for k, _ in v) for n, v in gaps.items() if v}
    return out, tr_eb, cfg


def metrics(df, n, tr_eb=None):
    m = E137.metrics(df.drop(columns=[c for c in ["yhat"] if c in df]), n)
    d = df[df["status"].isin(["ELEVATED", "LOWER"])].dropna(subset=[n])
    if len(d) and d["status"].nunique() == 2:
        yt = (d["status"] == "ELEVATED").astype(int)
        m["pr_auc"] = float(average_precision_score(yt, d[n]))
        k = int(((d[n] >= 0.5).astype(int) == yt).sum())
        ci = binomtest(k, len(d)).proportion_ci(method="wilson")
        m["accuracy_ci95"] = [float(ci.low), float(ci.high)]
    base = M137.expected_brier(np.full(len(df.dropna(subset=[n])), df.dropna(subset=[n])["q"].mean()), df.dropna(subset=[n])["q"])
    m["brier_skill_vs_climatology"] = 1 - m["expected_brier"] / base if base else None
    if tr_eb and n in tr_eb:
        m["train_expected_brier"], m["overfit_gap"] = tr_eb[n], m["expected_brier"] - tr_eb[n]
    return m


def auc_ci(df, col, rng):
    d = df[df["status"].isin(["ELEVATED", "LOWER"])].dropna(subset=[col])
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    v = []
    for _ in range(N_BOOT):
        s = pd.concat([g[r] for r in rng.choice(regs, len(regs))])
        if s["status"].nunique() == 2:
            v.append(roc_auc_score((s["status"] == "ELEVATED").astype(int), s[col]))
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def lead_checks(lo, tf, rng, tr_eb):
    T = THRESHOLDS
    L = metrics(lo, "LGBM", tr_eb)
    enns = lo[lo["prev_y"].notna()]
    ci = auc_ci(lo, "LGBM", rng)
    r = {"metrics_LORO": L, "auc_ci95": ci, "vs_NAT": WH.boot(lo, "LGBM", "NAT", rng),
         "enns_vs_REGPREV": WH.boot(enns, "LGBM", "REGPREV", rng), "enns_vs_PERS": WH.boot(enns, "LGBM", "PERS", rng),
         "tfwd": {n: metrics(tf, n) for n in ["LGBM", "REGPREV", "PERS", "NAT"] if tf[n].notna().any()}}
    r["checks"] = {
        "G1_beats_national": r["vs_NAT"]["ci95"][1] < T["G1_ci_upper_vs_NAT"],
        "G2_beyond_region_history": r["enns_vs_REGPREV"]["ci95"][1] < T["G2_ci_upper_vs_REGPREV"],
        "G3_noninferior_persistence": r["enns_vs_PERS"]["ci95"][1] <= T["G3_noninferiority_vs_PERS"],
        "G5_discrimination_classes": L.get("auc", 0) >= T["G5_auc"] and ci[0] >= T["G5_auc_ci_lower"]
                                     and L.get("balanced_accuracy", 0) >= T["G5_ba"] and L.get("recall_elevated", 0) >= T["G5_recall"]
                                     and (L.get("precision_elevated") or 0) >= T["G5_precision"],
        "G6_calibration": L["ece"] <= T["G6_ece"],
        "G9_forward_in_time": r["tfwd"]["LGBM"].get("auc", 0) >= T["G9_tfwd_auc"],
    }
    return r


def run():
    verify_lock()
    rng = np.random.default_rng(M.SEED)
    X = M.data()
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(),
           "n_rows": int(len(X)), "n_decisive": int(X["status"].isin(["ELEVATED", "LOWER"]).sum()),
           "features": M.ALL, "schemes": {}, "lgbm_configs": {}}
    store, treb = {}, {}
    for sch in ("LORO", "LOPO", "ISLAND", "V2", "TFWD"):
        o, tr_eb, cfg = oof(X, sch, M.CANDIDATES)
        store[sch], treb[sch] = o, tr_eb
        res["schemes"][sch] = {n: metrics(o, n, tr_eb) for n in M.CANDIDATES if o[n].notna().any()}
        res["lgbm_configs"][sch] = pd.DataFrame(cfg).value_counts().reset_index().to_dict(orient="records")
        print(sch, "done", flush=True)
    lo, lp = store["LORO"], store["LOPO"]
    bench = ["RR-F", "LR-F", "RR-P", "LR-P"]
    res["comparisons"] = {"LORO_vs": {n: WH.boot(lo, "LGBM", n, rng) for n in M.CANDIDATES if n not in ("LGBM", "PERS")},
                          "LOPO_vs": {n: WH.boot(lp, "LGBM", n, rng) for n in M.CANDIDATES if n not in ("LGBM", "PERS")},
                          "ISLAND_vs": {n: WH.boot(store["ISLAND"], "LGBM", n, rng) for n in bench + ["NAT"]}}
    best_bench = min(bench, key=lambda n: res["schemes"]["LORO"][n]["expected_brier"])
    # ablations (each group removed from trees and base)
    res["ablation"] = {}
    for g, fs in M.GROUPS.items():
        cols = [c for c in M.ALL if c not in fs]
        o, _, _ = oof(X, "LORO", ["LGBM"], cols=cols)
        t, _, _ = oof(X, "TFWD", ["LGBM"], cols=cols)
        res["ablation"][g] = {"LORO": {"expected_brier": metrics(o, "LGBM")["expected_brier"],
                                       "diff_vs_full": WH.boot(o.assign(FULL=lo["LGBM"]), "LGBM", "FULL", rng)},
                              "TFWD": {"expected_brier": metrics(t, "LGBM")["expected_brier"],
                                       "full": res["schemes"]["TFWD"]["LGBM"]["expected_brier"]}}
    res["robustness_mask"] = {}
    for g in ("market", "climate", "history"):
        o, _, _ = oof(X, "LORO", ["LGBM"], mask=M.GROUPS[g])
        res["robustness_mask"][g] = metrics(o, "LGBM")["expected_brier"] - res["schemes"]["LORO"]["LGBM"]["expected_brier"]
    res["sensitivity"] = {}
    for oc, ref in (("insecure", "pooled"), ("mod_sev", "round")):
        o, _, _ = oof(M.data(oc, ref), "LORO", ["LGBM", "LR-P", "NAT"])
        res["sensitivity"][f"{oc}/{ref}"] = {n: metrics(o, n) for n in ["LGBM", "LR-P", "NAT"]}
    # leads
    res["leads"] = {}
    for lead in LEADS:
        XL = M.data(lead=lead)
        if lead == 0:
            lo_l, tf_l, tr_l = lo, store["TFWD"], treb["LORO"]
        else:
            lo_l, tr_l, _ = oof(XL, "LORO", ["LGBM", "NAT", "REGPREV", "PERS"])
            tf_l, _, _ = oof(XL, "TFWD", ["LGBM", "NAT", "REGPREV", "PERS"])
        res["leads"][str(lead)] = lead_checks(lo_l, tf_l, rng, tr_l)
        print("lead", lead, res["leads"][str(lead)]["checks"], flush=True)
    # lead-independent checks
    T = THRESHOLDS
    L0 = res["schemes"]["LORO"]["LGBM"]
    bb = WH.boot(lo, "LGBM", best_bench, rng)
    res["global_checks"] = {
        "G4_not_worse_than_best_benchmark": bb["diff"] <= bb["se"], "best_benchmark": best_bench, "vs_best_benchmark": bb,
        "G7_overfitting": L0.get("overfit_gap", 1) <= T["G7_gap"],
        "G8_island_transfer": res["schemes"]["ISLAND"]["LGBM"].get("auc", 0) >= T["G8_island_auc"],
        "G10_sensitivity": all(v["LGBM"].get("auc", 0) >= T["G10_sens_auc"] for v in res["sensitivity"].values()),
        "G11_robust_missing": all(abs(v) <= T["G11_mask_change"] for v in res["robustness_mask"].values()),
    }
    gl = {k: v for k, v in res["global_checks"].items() if k.startswith("G")}
    passed = [int(L) for L, r in res["leads"].items() if all(r["checks"].values()) and all(gl.values())]
    mx = None
    for L in LEADS:
        if L in passed:
            mx = L
        else:
            break
    res["max_reliable_lead"] = mx
    res["passed"] = mx is not None
    res["accuracy_objective_75"] = {"accuracy_decisive_LORO": L0.get("accuracy"), "ci95": L0.get("accuracy_ci95"),
                                    "n_decisive": L0.get("n_decisive"), "met": (L0.get("accuracy") or 0) >= T["accuracy_objective"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for sch, o in store.items():
        o.to_csv(OUT / f"oof_{sch}.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print("max lead", mx, "global", gl)
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
