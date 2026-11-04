"""
E143 locked evaluation (docs/e143/PROTOCOL.md). Identical rows, folds and cutoffs to E141/E142.

    python -m app.e143.evaluate lock | run   -> data/e143/out/{results.json, oof_rolling.csv, oof_untouched_2013.csv}
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e137 import model as M137
from app.e139 import evaluate as E9
from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e142 import OUT as O142
from app.e142 import evaluate as E142
from app.e143 import OUT, PROTOCOL_VERSION, VERSION
from app.e143 import model as M
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e143" / "PROTOCOL.md"
CODE = ["model.py", "evaluate.py"]
CANDS = list(M.CANDIDATES)
REFS = ["STATE-LGBM", "LGBM", "PRIOR", "RR-F", "LR-F", "LR-P (PSA-only)", "PERS", "REGPREV", "NAT"]
T = {"S1_ci_upper_vs_PERS": 0.0, "S2_ci_upper_vs_REGPREV": 0.0, "S3_ece": 0.10, "S4_auc": 0.75, "S4_recall": 0.60,
     "S4_precision": 0.60, "S5_change_rho_ci_lower": 0.0, "S8_coverage90": [0.80, 0.98], "alpha": 0.05, "n_boot": 2000}
SEED = 20261107


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e143"
    return {"protocol": _sha(PROTOCOL), **{c: _sha(here / c) for c in CODE},
            "thresholds": hashlib.sha256(json.dumps(T, sort_keys=True).encode()).hexdigest()}


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps({"version": VERSION, "protocol_version": PROTOCOL_VERSION,
                                                        "locked_utc": datetime.now(timezone.utc).isoformat(),
                                                        "hashes": _hashes(), "thresholds": T}, indent=2))


def verify_lock():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if _hashes().get(k) != v]
    if bad:
        raise RuntimeError(f"E143 lock mismatch: {bad}")


def _fit_all(tr):
    lv = {"lgbm": M.Level("lgbm").fit(tr), "ridge": M.Level("ridge").fit(tr)}
    return {c: M.Anchored(f, l).fit(tr, lv[l]) for c, (f, l) in M.CANDIDATES.items()}


def rolling(X):
    ref = pd.read_csv(O142 / "oof_rolling.csv")
    out, params = [], []
    for oid, train_rounds, target in E141.ORIGINS:
        tr, te = X[X["survey"].isin(train_rounds)], X[X["survey"] == target]
        o = te[E141.KEEP].copy()
        o["origin"] = oid
        for c, m in _fit_all(tr).items():
            yhat, V = m.predict(te)
            o[c] = M.norm.cdf(yhat / np.sqrt(V))
            o[c + "::yhat"], o[c + "::V"] = yhat, V
            o[c + "::own_weight"] = m.last_detail_["weight_on_own_surveys"].values
            params.append({"origin": oid, "candidate": c, "tau2": m.tau2_, "c": m.c_, "sigma2_A": m.sA_, "sigma2_G": m.sG_,
                           "phi": m.phi_, "n_own_pairs": m.n_own_pairs_, "n_region_pairs": m.n_reg_pairs_,
                           "n_transitions": m.n_transitions_,
                           "mean_weight_on_own_surveys": float(m.last_detail_["weight_on_own_surveys"].mean())})
        r = ref[ref["origin"] == oid].set_index("key")
        for n in REFS:
            o[n] = r.loc[o["key"], n].values
        out.append(o)
        print(oid, flush=True)
    return pd.concat(out).reset_index(drop=True), params


def untouched():
    tr = M140.data(lead=1).copy()
    tr["prev_survey"] = np.where(tr["prev_y"].notna(), "FNRI2015", None)
    te = P.data(1)
    te = te[te["survey"] == "NNS2013"].reset_index(drop=True)
    o = te[E141.KEEP].copy()
    for c, m in _fit_all(tr).items():
        o[c] = m.predict_proba(te)                      # no earlier round exists: level only
    ref = pd.read_csv(O142 / "oof_untouched_2013.csv")
    for n in ("STATE-LGBM", "LGBM", "PRIOR", "LR-P (PSA-only)", "NAT"):
        o[n] = ref[n].values
    return o


def _boot(R, names, base, rng, n):
    regs = R["region"].unique()
    idx = {r: np.flatnonzero(R["region"].values == r) for r in regs}
    q = R["q"].values
    eb = lambda p, ii: np.mean((p[ii] - q[ii]) ** 2 + q[ii] * (1 - q[ii]))
    P_ = {m: R[m].values for m in names + [base]}
    draws = {m: [] for m in names}
    for _ in range(n):
        ii = np.concatenate([idx[r] for r in rng.choice(regs, len(regs))])
        for m in names:
            draws[m].append(eb(P_[m], ii) - eb(P_[base], ii))
    return {m: np.asarray(v) for m, v in draws.items()}


def holm(draws: dict, alpha: float) -> dict:
    """Holm step-down on bootstrap draws of the EB difference (candidate - baseline); two-sided levels."""
    p = {m: float(np.mean(v >= 0)) for m, v in draws.items()}
    order = sorted(draws, key=lambda m: p[m])
    out, stop = {}, False
    for i, m in enumerate(order):
        a = alpha / (len(order) - i)
        up = float(np.percentile(draws[m], 100 * (1 - a / 2)))
        ok = (not stop) and up < 0
        stop = stop or not ok
        out[m] = {"rank": i + 1, "level": 1 - a, "upper": up, "lower": float(np.percentile(draws[m], 100 * a / 2)),
                  "boot_p_one_sided": p[m], "passes": ok}
    return out


def coverage(R, c):
    y, yh, V, se = R["y"].values, R[c + "::yhat"].values, R[c + "::V"].values, R["se_y"].values
    return float(np.mean(np.abs(y - yh) <= 1.645 * np.sqrt(V + se ** 2)))


def run():
    verify_lock()
    rng = np.random.default_rng(SEED)
    X = P.data(1)
    R, params = rolling(X)
    R.to_csv(OUT / "oof_rolling.csv", index=False)
    U = untouched()
    U.to_csv(OUT / "oof_untouched_2013.csv", index=False)
    names = CANDS + REFS
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(),
           "params": params}
    res["pooled"] = {n: E9.metrics(R, n) for n in names}
    for n in names:
        res["pooled"][n]["auc_ci95"] = E9.auc_ci(R, n, rng)
    res["by_origin"] = {o: {n: E9.metrics(g, n) for n in names} for o, g in R.groupby("origin")}
    res["untouched_2013"] = {n: E9.metrics(U, n) for n in CANDS + ["STATE-LGBM", "LGBM", "PRIOR", "LR-P (PSA-only)", "NAT"]}
    res["coverage90"] = {c: coverage(R, c) for c in CANDS}
    res["coverage90_by_origin"] = {o: {c: coverage(g, c) for c in CANDS} for o, g in R.groupby("origin")}
    res["change_rho"] = {n: E142.change_rho(R, n, rng) for n in names if n not in ("PERS", "NAT")}
    D = {b: _boot(R, CANDS + ["STATE-LGBM"], b, rng, T["n_boot"]) for b in ("PERS", "REGPREV")}
    res["vs"] = {b: {c: {"diff": float(M137.expected_brier(R[c], R["q"]) - M137.expected_brier(R[b], R["q"])),
                         "se": float(D[b][c].std(ddof=1)), "ci95": [float(np.percentile(D[b][c], 2.5)), float(np.percentile(D[b][c], 97.5))]}
                     for c in CANDS + ["STATE-LGBM"]} for b in ("PERS", "REGPREV")}
    res["holm"] = {b: holm({c: D[b][c] for c in CANDS}, T["alpha"]) for b in ("PERS", "REGPREV")}
    Dr = _boot(R, CANDS + ["STATE-LGBM"], "C3 RE-RIDGE-X", rng, T["n_boot"])
    res["vs_ridge_level"] = {c: {"diff": float(M137.expected_brier(R[c], R["q"]) - M137.expected_brier(R["C3 RE-RIDGE-X"], R["q"])),
                                 "se": float(Dr[c].std(ddof=1))} for c in CANDS + ["STATE-LGBM"] if c != "C3 RE-RIDGE-X"}
    De = _boot(R, CANDS, "STATE-LGBM", rng, T["n_boot"])
    res["vs_E142"] = {c: {"diff": float(M137.expected_brier(R[c], R["q"]) - M137.expected_brier(R["STATE-LGBM"], R["q"])),
                          "ci95": [float(np.percentile(De[c], 2.5)), float(np.percentile(De[c], 97.5))]} for c in CANDS}
    res["calabarzon"] = R[R["province"].isin(E141.CAL)][["origin", "province", "survey", "y", "se_y", "status", "q"] + names].round(4).to_dict(orient="records")
    gate = {}
    for c in CANDS:
        L, bo = res["pooled"][c], res["by_origin"]
        ck = {"S1_beats_persistence_holm": res["holm"]["PERS"][c]["passes"],
              "S2_beats_region_previous_holm": res["holm"]["REGPREV"][c]["passes"],
              "S3_calibration": L["ece"] <= T["S3_ece"] and res["untouched_2013"][c]["ece"] <= T["S3_ece"],
              "S4_classes": L.get("auc", 0) >= T["S4_auc"] and L.get("recall_elevated", 0) >= T["S4_recall"]
                            and (L.get("precision_elevated") or 0) >= T["S4_precision"],
              "S5_predicts_change": res["change_rho"][c]["ci95"][0] > T["S5_change_rho_ci_lower"],
              "S6_beats_persistence_O2_O3": all(bo[o][c]["expected_brier"] < bo[o]["PERS"]["expected_brier"] for o in ("O2", "O3")),
              "S7_lightgbm_level_not_worse_than_ridge": (res["vs_ridge_level"][c]["diff"] <= res["vs_ridge_level"][c]["se"])
              if c != "C3 RE-RIDGE-X" else None,
              "S8_interval_coverage": T["S8_coverage90"][0] <= res["coverage90"][c] <= T["S8_coverage90"][1]}
        gate[c] = {"checks": ck, "passed": all(v for v in ck.values() if v is not None)}
    passing = [c for c in CANDS if gate[c]["passed"]]
    pref = sorted(passing, key=lambda c: (M.N_VAR_PARAMS[c], "RIDGE" in c, res["pooled"][c]["expected_brier"]))
    res["gate"] = {"per_candidate": gate, "adopted": pref[0] if pref else None,
                   "adoption_meaning": "development-supported candidate on re-used folds (not a validated forecast)" if pref
                   else "no candidate adopted; C2 issued as the E143 candidate"}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print(json.dumps(res["gate"], indent=1))
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
