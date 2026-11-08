"""
E142 locked evaluation (PROTOCOL.md). Identical rows, folds and cutoffs to E141 (E141 panel, origins O1-O3, Lead 1).

    python -m app.e142.evaluate lock | run    -> data/e142/out/results.json, oof_rolling.csv, oof_untouched_2013.csv

Candidates: STATE-LGBM (risk-state model, LightGBM structural level), STATE-RIDGE (same, ridge level), LGBM-PLATT (E141
LightGBM with a Platt calibrator fitted on inner out-of-fold predictions of the training rows only). References: the
E141 models (LGBM, linear prior, ridge, logistic, PSA-only, persistence, region's previous level, national base rate).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from app.e138 import where as WH
from app.e139 import evaluate as E9
from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e142 import OUT, PROTOCOL_VERSION, VERSION
from app.e142 import model as M
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e142" / "PROTOCOL.md"
CODE = ["model.py", "evaluate.py"]
REFS = E141.NAMES
CANDS = ["STATE-LGBM", "STATE-RIDGE", "LGBM-PLATT"]
T = {"S1_ci_upper_vs_PERS": 0.0, "S2_ci_upper_vs_REGPREV": 0.0, "S3_ece": 0.10, "S4_auc": 0.75, "S4_recall": 0.60,
     "S4_precision": 0.60, "S5_change_rho_ci_lower": 0.0}


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e142"
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
        raise RuntimeError(f"E142 lock mismatch: {bad}")


class PlattLGBM:
    """E141 LightGBM plus a Platt calibrator (logistic on logit p) fitted on inner grouped out-of-fold predictions of
    the training rows, with soft labels."""

    def fit(self, tr):
        tr = tr.reset_index(drop=True)
        g = tr["region"].values
        p = np.full(len(tr), np.nan)
        for a, b in GroupKFold(min(5, len(np.unique(g)))).split(tr, groups=g):
            p[b] = M140.LGBAuto().fit(tr.iloc[a]).predict_proba(tr.iloc[b])
        z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1)
        q = tr["q"].values
        self.cal_ = LogisticRegression(C=1.0).fit(np.vstack([z, z]), np.r_[np.ones(len(q)), np.zeros(len(q))],
                                                  sample_weight=np.r_[q, 1 - q])
        self.m_ = M140.LGBAuto().fit(tr)
        return self

    def predict_proba(self, X):
        p = np.clip(self.m_.predict_proba(X), 1e-4, 1 - 1e-4)
        return self.cal_.predict_proba(np.log(p / (1 - p)).reshape(-1, 1))[:, 1]


def _prev_rows(X_all: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    idx = X_all.set_index(["key", "survey"])
    keys = list(zip(rows["key"], rows["prev_survey"].fillna("NONE")))
    out = pd.DataFrame([idx.loc[k] if k in idx.index else idx.iloc[0] * np.nan for k in keys]).reset_index(drop=True)
    out.index = rows.index
    return out


def rolling(X, lead_label="lead1"):
    out = []
    params = []
    for oid, train_rounds, target in E141.ORIGINS:
        tr, te = X[X["survey"].isin(train_rounds)], X[X["survey"] == target]
        o = te[E141.KEEP].copy()
        o["origin"] = oid
        for n in REFS:
            m = E141.make(n).fit(tr)
            rows = te.index if n != "PERS" else te.index[te["prev_y"].notna()]
            o.loc[rows, n] = m.predict_proba(te.loc[rows])
        prev = _prev_rows(X, te)
        for n, mu in (("STATE-LGBM", "lgbm"), ("STATE-RIDGE", "ridge")):
            sm = M.StateModel(mu).fit(tr)
            o[n] = sm.predict_proba(te, prev_rows=prev)
            params.append({"origin": oid, "model": n, "phi": sm.phi_, "tau2": sm.tau2_, "n_transitions": sm.n_transitions_,
                           "weight_on_previous_round": float(sm.phi_ ** float(M.gap_quarters(te).iloc[0]))})
        o["LGBM-PLATT"] = PlattLGBM().fit(tr).predict_proba(te)
        out.append(o)
    return pd.concat(out), params


def change_rho(o, m, rng, n=1000):
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    d = o.dropna(subset=[m, "PERS", "prev_y"]).copy()
    d["pc"], d["dy"] = lg(d[m]) - lg(d["PERS"]), d["y"] - d["prev_y"]
    est = float(spearmanr(d["pc"], d["dy"]).statistic)
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    v = [spearmanr(s["pc"], s["dy"]).statistic for s in (pd.concat([g[r] for r in rng.choice(regs, len(regs))]) for _ in range(n))]
    return {"rho": est, "ci95": [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))], "n": int(len(d))}


def untouched(rng):
    tr = M140.data(lead=1).copy()
    tr["prev_survey"] = np.where(tr["prev_y"].notna(), "FNRI2015", None)
    te = P.data(1)
    te = te[te["survey"] == "NNS2013"].reset_index(drop=True)
    te[["a_prev_y", "a_region_prev"]] = np.nan
    o = te[E141.KEEP].copy()
    o["STATE-LGBM"] = M.StateModel("lgbm").fit(tr).predict_proba(te)       # no earlier round: structural level only
    o["STATE-RIDGE"] = M.StateModel("ridge").fit(tr).predict_proba(te)
    o["LGBM-PLATT"] = PlattLGBM().fit(tr).predict_proba(te)
    ref = pd.read_csv(BACKEND_DIR / "data" / "e141" / "out" / "oof_untouched_2013.csv")
    for n in ("LGBM", "PRIOR", "LR-P (PSA-only)", "NAT"):
        o[n] = ref[n].values
    o.to_csv(OUT / "oof_untouched_2013.csv", index=False)
    return {n: E9.metrics(o, n) for n in CANDS + ["LGBM", "PRIOR", "LR-P (PSA-only)", "NAT"]}


def run():
    verify_lock()
    rng = np.random.default_rng(20261105)
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat()}
    X = P.data(1)
    R, params = rolling(X)
    R.to_csv(OUT / "oof_rolling.csv", index=False)
    names = CANDS + REFS
    res["rolling"] = {"params": params, "pooled": {n: E9.metrics(R, n) for n in names},
                      "by_origin": {o: {n: E9.metrics(g, n) for n in names} for o, g in R.groupby("origin")},
                      "vs": {c: {b: WH.boot(R, c, b, rng) for b in names if b != c} for c in CANDS},
                      "change_rho": {n: change_rho(R, n, rng) for n in names if n not in ("PERS", "NAT")},
                      "calabarzon": R[R["province"].isin(E141.CAL)][["origin", "province", "survey", "status", "q"] + names].round(4).to_dict(orient="records")}
    print("rolling done", flush=True)
    res["untouched_2013"] = untouched(rng)
    print("untouched done", flush=True)
    res["timing_sensitivity"] = {}
    for lead in (0, 3):
        Rl, _ = rolling(P.data(lead))
        res["timing_sensitivity"][f"lead{lead}"] = {n: E9.metrics(Rl, n)["expected_brier"] for n in ("STATE-LGBM", "LGBM", "PERS", "REGPREV")}
    C = "STATE-LGBM"
    L, vs = res["rolling"]["pooled"][C], res["rolling"]["vs"][C]
    bo = res["rolling"]["by_origin"]
    checks = {
        "S1_beats_persistence": vs["PERS"]["ci95"][1] < T["S1_ci_upper_vs_PERS"],
        "S2_beats_region_history": vs["REGPREV"]["ci95"][1] < T["S2_ci_upper_vs_REGPREV"],
        "S3_calibration": L["ece"] <= T["S3_ece"] and res["untouched_2013"][C]["ece"] <= T["S3_ece"],
        "S4_classes": L.get("auc", 0) >= T["S4_auc"] and L.get("recall_elevated", 0) >= T["S4_recall"]
                      and (L.get("precision_elevated") or 0) >= T["S4_precision"],
        "S5_predicts_change": res["rolling"]["change_rho"][C]["ci95"][0] > T["S5_change_rho_ci_lower"],
        "S6_beats_persistence_O2_O3": all(bo[o][C]["expected_brier"] < bo[o]["PERS"]["expected_brier"] for o in ("O2", "O3")),
        "S7_lightgbm_level_not_worse_than_ridge_level": vs["STATE-RIDGE"]["diff"] <= vs["STATE-RIDGE"]["se"],
    }
    res["gate"] = {"candidate": C, "checks": checks, "passed": all(checks.values())}
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print("gate", res["gate"])
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
