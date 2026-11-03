"""
E138 runner (PROTOCOL.md). Run once after the lock.

    python -m app.e138.evaluate lock     data/e138/out/PROTOCOL_LOCK.json (protocol, code and thresholds hashes)
    python -m app.e138.evaluate run      WHERE comparison + selection + gate checks + WHEN study -> results.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.e137 import evaluate as E137
from app.e137 import features as F137
from app.e138 import OUT, PROTOCOL_VERSION, VERSION
from app.e138 import models as M
from app.e138 import when as W
from app.e138 import where as WH
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e138" / "PROTOCOL.md"
CODE = ["models.py", "where.py", "when.py", "evaluate.py"]
THRESHOLDS = {
    "G1_ci_upper_vs_NAT": 0.0, "G2_ci_upper_vs_REG": 0.0,
    "G3_auc": 0.75, "G3_auc_ci_lower": 0.60,
    "G4_balanced_accuracy": 0.70, "G4_recall": 0.60, "G4_precision": 0.60,
    "G5_ece": 0.10, "G6_island_auc": 0.65, "G7_overfit_gap": 0.05,
    "G8_noninferiority_vs_PERS": 0.02, "G9_v2_auc": 0.70, "G10_sensitivity_auc": 0.70, "G11_mask_eb_change": 0.02,
}


def _sha(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes() -> dict:
    here = BACKEND_DIR / "app" / "e138"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()}


def lock() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "locked_utc": datetime.now(timezone.utc).isoformat(),
           "hashes": _hashes(), "thresholds": THRESHOLDS,
           "note": "written before any E138 candidate was fitted to real outcomes (smoke test used shuffled labels)"}
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps(rec, indent=2))
    return rec


def verify_lock() -> None:
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E138 lock mismatch: {bad}")


def anchored(sel: str) -> str:
    kind, fs = sel.split("-") if "-" in sel else (None, None)
    if kind is None:
        return "PERS"
    if "A" in fs:
        return sel
    return f"{kind}-PA" if fs in ("P1", "P", "PD") else f"{kind}-ALL"


def auc_ci(df, col, rng, n=WH.N_BOOT):
    d = df[df["status"].isin(["ELEVATED", "LOWER"])].dropna(subset=[col])
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    v = []
    for _ in range(n):
        s = pd.concat([g[r] for r in rng.choice(regs, len(regs))])
        if s["status"].nunique() == 2:
            v.append(roc_auc_score((s["status"] == "ELEVATED").astype(int), s[col]))
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def run() -> dict:
    verify_lock()
    rng = np.random.default_rng(M.SEED)
    X = WH.data()
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(),
           "n_rows": int(len(X)), "schemes": {}, "incremental": {}}
    cand = M.CANDIDATES
    store = {}
    for sch in ("LORO", "LOPO", "ISLAND", "V2"):
        o, gaps = WH.oof(X, sch, cand)
        store[sch] = o
        res["schemes"][sch] = WH.table(o, cand, gaps)
        print(sch, "done")
    lo, lp = store["LORO"], store["LOPO"]
    enns = lo[lo["prev_y"].notna()]
    res["incremental"]["LORO_vs_LR-P"] = {n: WH.boot(lo, n, "LR-P", rng) for n in cand if n not in ("PERS", "LR-P") and n in lo}
    res["incremental"]["LORO_vs_NAT"] = {n: WH.boot(lo, n, "NAT", rng) for n in cand if n not in ("PERS", "NAT") and n in lo}
    res["incremental"]["LOPO_vs_REG"] = {n: WH.boot(lp, n, "REG", rng) for n in cand if n not in ("PERS", "REG") and n in lp}
    res["incremental"]["ENNS_rows_vs_PERS"] = {n: WH.boot(enns, n, "PERS", rng) for n in cand if n != "PERS" and n in enns}
    sel = WH.select(lo, rng)
    s = sel["selected"]
    res["selection"] = sel
    a = anchored(s)
    if a not in lo:
        o_a, _ = WH.oof(X, "LORO", [a])
        lo[a] = o_a[a]
        enns = lo[lo["prev_y"].notna()]
    # selected model: structural stability across leads, sensitivity, robustness, contributions
    sm = res.setdefault("selected_model", {"name": s, "anchored_variant": a})
    sm["auc_ci95_LORO"] = auc_ci(lo, s, rng)
    sm["by_lead_LORO"] = {}
    for lead in (0, 2, 4):
        o, g = WH.oof(WH.data(lead=lead), "LORO", [s, "LR-P", "NAT"])
        sm["by_lead_LORO"][lead] = WH.table(o, [s, "LR-P", "NAT"], g)
    sm["sensitivity"] = {}
    for oc, ref in (("insecure", "pooled"), ("mod_sev", "round")):
        o, g = WH.oof(WH.data(oc, ref), "LORO", [s, "LR-P", "NAT", "PERS"])
        sm["sensitivity"][f"{oc}/{ref}"] = WH.table(o, [s, "LR-P", "NAT", "PERS"], g)
    cols = M.make(s).cols if s not in ("NAT", "REG", "PERS") else []
    sm["robustness_mask"] = {}
    base = E137.metrics(lo, s)["expected_brier"]
    for grp, fs in F137.GROUPS.items():
        m = [c for c in fs if c in cols]
        if m:
            o, _ = WH.oof(X, "LORO", [s], mask=m)
            sm["robustness_mask"][grp] = {"masked": m, "expected_brier": E137.metrics(o, s)["expected_brier"],
                                          "change": E137.metrics(o, s)["expected_brier"] - base}
    if cols:
        full = M.make(s).fit(X)
        if hasattr(full, "coefficients"):
            sm["coefficients_full_fit"] = full.coefficients()
            sh = WH.linear_group_shares(full, X)
            sm["group_share_mean"] = sh.mean().round(4).to_dict()
            sm["group_share_top"] = sh.idxmax(axis=1).value_counts().to_dict()
        elif hasattr(full, "contributions"):
            c = full.contributions(X).drop(columns=["bias"]).abs()
            g = pd.DataFrame({k: c[[f for f in v if f in c]].sum(axis=1) for k, v in F137.GROUPS.items() if any(f in c for f in v)})
            sm["group_share_mean"] = g.div(g.sum(axis=1), axis=0).mean().round(4).to_dict()
    # gate
    T = THRESHOLDS
    L = res["schemes"]["LORO"][s]
    isl = res["schemes"]["ISLAND"].get(s, {})
    v2 = res["schemes"]["V2"].get(s, {})
    pers = WH.boot(enns, a, "PERS", rng)
    gates = {
        "G1_beats_national": res["incremental"]["LORO_vs_NAT"].get(s, {"ci95": [0, 1]})["ci95"][1] < T["G1_ci_upper_vs_NAT"],
        "G2_beats_regional_LOPO": res["incremental"]["LOPO_vs_REG"].get(s, {"ci95": [0, 1]})["ci95"][1] < T["G2_ci_upper_vs_REG"],
        "G3_discrimination": L.get("auc", 0) >= T["G3_auc"] and sm["auc_ci95_LORO"][0] >= T["G3_auc_ci_lower"],
        "G4_classes": L.get("balanced_accuracy", 0) >= T["G4_balanced_accuracy"] and L.get("recall_elevated", 0) >= T["G4_recall"]
                      and (L.get("precision_elevated") or 0) >= T["G4_precision"],
        "G5_calibration": L["ece"] <= T["G5_ece"],
        "G6_island_transfer": isl.get("auc", 0) >= T["G6_island_auc"],
        "G7_overfitting": L.get("overfit_gap", 1) <= T["G7_overfit_gap"],
        "G8_noninferior_to_persistence": pers["ci95"][1] <= T["G8_noninferiority_vs_PERS"],
        "G9_across_surveys": v2.get("auc", 0) >= T["G9_v2_auc"],
        "G10_sensitivity": all(v[s].get("auc", 0) >= T["G10_sensitivity_auc"] for v in sm["sensitivity"].values()),
        "G11_robust_to_missing": all(abs(v["change"]) <= T["G11_mask_eb_change"] for k, v in sm["robustness_mask"].items()
                                     if k != "poverty"),
    }
    res["gate"] = {"checks": gates, "anchored_vs_persistence": pers, "passed_development": all(gates.values()),
                   "G12_confirmatory": "pending: sealed prediction for the next provincial survey round"}
    res["when"] = W.run()
    OUT.mkdir(parents=True, exist_ok=True)
    for sch, o in store.items():
        o.to_csv(OUT / f"oof_{sch}.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print("selected", s, "gate", gates)
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
