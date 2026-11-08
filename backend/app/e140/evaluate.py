"""
E140 locked run: four-way comparison and decision (PROTOCOL.md).

    python -m app.e140.evaluate lock | run      -> data/e140/out/results.json, oof_<scheme>.csv

Reuses E139's metrics, bootstrap, lead checks and thresholds unchanged (imported).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.e137 import model as M137
from app.e138 import where as WH
from app.e139 import evaluate as E9
from app.e140 import model as M
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e140" / "out"
PROTOCOL = BACKEND_DIR.parent / "docs" / "e140" / "PROTOCOL.md"
CODE = ["model.py", "evaluate.py"]
SCHEMES = ("LORO", "LOPO", "ISLAND", "V2", "TFWD")
T = {**E9.THRESHOLDS, "T1_min_share_folds_with_trees": 0.75, "T2_ci_upper_vs_prior": 0.0}


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e140"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps({"protocol_version": "E140-P1", "locked_utc": datetime.now(timezone.utc).isoformat(),
                                                        "hashes": _hashes(), "thresholds": T}, indent=2))


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E140 lock mismatch: {bad}")


def oof(X, scheme, names):
    out = X[E9.KEEP].copy()
    trees, gaps = [], {n: [] for n in names}
    for tr, te in E9.folds(X, scheme):
        for n in names:
            m = M.make(n).fit(X[tr])
            rows = X.index[te] if n != "PERS" else X.index[te & X["prev_y"].notna()]
            if len(rows):
                out.loc[rows, n] = m.predict_proba(X.loc[rows])
            if n != "PERS":
                gaps[n].append((int(tr.sum()), M137.expected_brier(m.predict_proba(X[tr]), X.loc[tr, "q"])))
            if n == "LGBM-AUTO":
                trees.append({"fold": str(X.loc[te, "region" if scheme == "LORO" else "key"].iloc[0]),
                              "kind": m.kind_, "n_trees": m.n_trees_})
    tr_eb = {n: sum(k * e for k, e in v) / sum(k for k, _ in v) for n, v in gaps.items() if v}
    return out, tr_eb, trees


def dependence(o, a, b):
    """EB(a) - EB(b) when each region / island group / survey round is left out of the scoring set."""
    res = {}
    for g in ("region", "island", "survey"):
        vals = {}
        for v in o[g].unique():
            s = o[o[g] != v].dropna(subset=[a, b])
            vals[str(v)] = M137.expected_brier(s[a], s["q"]) - M137.expected_brier(s[b], s["q"])
        res[g] = {"min": min(vals.values()), "max": max(vals.values()), "all_negative": all(x < 0 for x in vals.values())}
    return res


def run():
    verify_lock()
    rng = np.random.default_rng(M.SEED)
    X = M.data()
    names = M.CANDIDATES + ["LGBM-AUTO-noQ"]
    res = {"protocol_version": "E140-P1", "run_utc": datetime.now(timezone.utc).isoformat(), "schemes": {}, "trees": {}}
    store, treb = {}, {}
    for sch in SCHEMES:
        o, tr_eb, trees = oof(X, sch, names)
        store[sch], treb[sch] = o, tr_eb
        res["schemes"][sch] = {n: E9.metrics(o, n, tr_eb) for n in names if o[n].notna().any()}
        res["trees"][sch] = trees
        print(sch, "done", flush=True)
    lo = store["LORO"]
    comp = {}
    for sch in SCHEMES:
        o = store[sch]
        comp[sch] = {b: WH.boot(o, "LGBM-AUTO", b, rng) for b in ["PRIOR", "E139", "RR-F", "PRIOR+TREES30", "LGBM-GBC", "LGBM-LT"]
                     if o[b].notna().any()}
    res["comparisons_LGBM_AUTO_minus"] = comp
    res["dependence_vs_PRIOR_LORO"] = dependence(lo, "LGBM-AUTO", "PRIOR")
    enns = lo[lo["prev_y"].notna()]
    res["quarterly_test"] = {"ENNS_rows_LORO": WH.boot(enns, "LGBM-AUTO", "LGBM-AUTO-noQ", rng),
                             "TFWD": WH.boot(store["TFWD"], "LGBM-AUTO", "LGBM-AUTO-noQ", rng)}
    # final fit
    final = M.make("LGBM-AUTO").fit(X)
    res["final_model"] = {"kind": final.kind_, "n_trees": final.n_trees_, "sigma": final.chosen_.sigma_}
    # gate: tree contribution + E139's checks at lead 0 (E139 functions, columns renamed)
    lt = res["trees"]["LORO"]
    share = float(np.mean([t["n_trees"] > 0 for t in lt]))
    t2 = comp["LORO"]["PRIOR"]
    lo9 = lo.assign(LGBM=lo["LGBM-AUTO"])
    tf9 = store["TFWD"].assign(LGBM=store["TFWD"]["LGBM-AUTO"])
    lc = E9.lead_checks(lo9, tf9, rng, {"LGBM": treb["LORO"]["LGBM-AUTO"]})
    L0 = res["schemes"]["LORO"]["LGBM-AUTO"]
    bench = min(["PRIOR", "RR-F", "E139"], key=lambda n: res["schemes"]["LORO"][n]["expected_brier"])
    bb = WH.boot(lo, "LGBM-AUTO", bench, rng)
    glob = {"G4_not_worse_than_best_benchmark": bb["diff"] <= bb["se"],
            "G7_overfitting": L0.get("overfit_gap", 1) <= T["G7_gap"],
            "G8_island_transfer": res["schemes"]["ISLAND"]["LGBM-AUTO"].get("auc", 0) >= T["G8_island_auc"]}
    checks = {"T1_trees_selected": final.n_trees_ > 0 and share >= T["T1_min_share_folds_with_trees"],
              "T2_trees_beat_linear_prior": t2["ci95"][1] < T["T2_ci_upper_vs_prior"], **lc["checks"], **glob}
    structural = ["T1_trees_selected", "T2_trees_beat_linear_prior", "G1_beats_national", "G5_discrimination_classes",
                  "G6_calibration", "G4_not_worse_than_best_benchmark", "G7_overfitting", "G8_island_transfer"]
    forecasting = ["G2_beyond_region_history", "G3_noninferior_persistence", "G9_forward_in_time"]
    if all(checks[c] for c in structural + forecasting):
        decision = "A"
    elif all(checks[c] for c in structural):
        decision = "B"
    else:
        decision = "C"
    res["gate"] = {"checks": checks, "best_benchmark": bench, "vs_best_benchmark": bb, "share_folds_with_trees": share,
                   "lead0_detail": {k: v for k, v in lc.items() if k != "checks"}, "decision": decision}
    OUT.mkdir(parents=True, exist_ok=True)
    for sch, o in store.items():
        o.to_csv(OUT / f"oof_{sch}.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print("decision", decision, checks)
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
