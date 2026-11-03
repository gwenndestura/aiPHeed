"""
E141 evaluation (PROTOCOL.md), run once after the lock.

    python -m app.e141.evaluate lock | run     -> data/e141/out/results.json, oof_*.csv

U  UNTOUCHED round: the E140 candidate and its references, trained exactly as served (E140 rows, Lead 1), predict the
   2013 provinces (features as of 2013, Lead 1; no earlier survey, so measured history is missing, as for 2015 rows in
   training). No model in this project has used 2013.
R  Rolling-origin survey-round forecasting at Lead 1 (issue one quarter before the target round's reference quarter):
       O1 train NNS2013                     -> predict FNRI2015 (78 provinces)
       O2 train NNS2013 + FNRI2015          -> predict ENNS2018 (22)
       O3 train NNS2013 + FNRI2015 + 2018   -> predict ENNS2019 (25)
   Every predicted row has its previous measured round as history. Architectures are E140/E139's, unchanged; the
   nested inner selection runs inside each training set only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e137 import model as M137
from app.e138 import where as WH
from app.e139 import evaluate as E9
from app.e139 import model as M9
from app.e140 import model as M140
from app.e141 import OUT, PROTOCOL_VERSION, VERSION
from app.e141 import panel as P
from app.paths import BACKEND_DIR

PROTOCOL = BACKEND_DIR.parent / "docs" / "e141" / "PROTOCOL.md"
CODE = ["panel.py", "evaluate.py", "nns2013.py"]
KEEP = ["key", "province", "region", "island", "survey", "y", "se_y", "q", "status", "prev_y", "prev_se_y", "a_region_prev"]
ORIGINS = [("O1", ["NNS2013"], "FNRI2015"), ("O2", ["NNS2013", "FNRI2015"], "ENNS2018"),
           ("O3", ["NNS2013", "FNRI2015", "ENNS2018"], "ENNS2019")]
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
T = {"U_auc": 0.75, "U_auc_ci_lower": 0.60, "U_ece": 0.10,
     "R_ci_upper_vs_PERS": 0.0, "R_ci_upper_vs_REGPREV": 0.0, "R_auc": 0.75, "R_recall": 0.60, "R_precision": 0.60,
     "R_ece": 0.10, "R3_ci_upper_vs_PRIOR": 0.0}


class RegPrev(M9.RegPrev):
    """E139 REGPREV, but with the training between-province spread when no training row has a previous round (O1)."""

    def fit(self, tr):
        super().fit(tr)
        if self.s_ is None:
            self.s_ = float(np.sqrt(M137.tau2(tr)))
        return self


def make(name: str, drop=None):
    return {"LGBM": lambda: M140.LGBAuto(drop), "PRIOR": lambda: M9.Ridge_(M9.BASE), "RR-F": lambda: M9.Ridge_(M9.ALL),
            "LR-F": lambda: M9.Logit_(M9.ALL), "LR-P (PSA-only)": lambda: M9.Logit_(M9.POV), "PERS": M137.Persistence,
            "REGPREV": RegPrev, "NAT": M137.BaseRate}[name]()


NAMES = ["LGBM", "PRIOR", "RR-F", "LR-F", "LR-P (PSA-only)", "PERS", "REGPREV", "NAT"]
DROPS = {"market": M9.MKT, "climate": M9.CLI, "poverty": M9.POV + M9.DENS, "history": M9.HIST,
         "geography": ["island_code"], "quarterly": M140.QUARTERLY}


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _hashes():
    here = BACKEND_DIR / "app" / "e141"
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
        raise RuntimeError(f"E141 lock mismatch: {bad}")


def untouched(rng) -> dict:
    tr = M140.data(lead=1)                                  # exactly the served candidate's training rows
    te = P.data(1)
    te = te[te["survey"] == "NNS2013"].reset_index(drop=True)
    te[["a_prev_y", "a_region_prev"]] = np.nan              # no earlier survey: as for the 2015 rows in training
    out = te[KEEP].copy()
    trees = None
    for n in NAMES:
        if n in ("PERS", "REGPREV"):
            continue                                        # need an earlier round, which 2013 does not have
        m = make(n).fit(tr)
        out[n] = m.predict_proba(te)
        if n == "LGBM":
            trees = {"kind": m.kind_, "n_trees": int(m.n_trees_)}
    res = {"n": int(len(out)), "lgbm": trees, "metrics": {n: E9.metrics(out, n) for n in NAMES if n in out},
           "auc_ci95": E9.auc_ci(out, "LGBM", rng),
           "vs": {n: WH.boot(out, "LGBM", n, rng) for n in NAMES if n in out and n != "LGBM"},
           "calabarzon": out[out["province"].isin(CAL)][["province", "status", "q", "LGBM", "PRIOR", "LR-P (PSA-only)"]].round(4).to_dict(orient="records")}
    out.to_csv(OUT / "oof_untouched_2013.csv", index=False)
    return res


def rolling(X: pd.DataFrame, names=NAMES, drop=None) -> tuple[pd.DataFrame, list]:
    out, trees = [], []
    for oid, train_rounds, target in ORIGINS:
        tr, te = X[X["survey"].isin(train_rounds)], X[X["survey"] == target]
        o = te[KEEP].copy()
        o["origin"] = oid
        for n in names:
            m = make(n, drop).fit(tr)
            rows = te.index if n != "PERS" else te.index[te["prev_y"].notna()]
            o.loc[rows, n] = m.predict_proba(te.loc[rows])
            if n == "LGBM":
                trees.append({"origin": oid, "kind": m.kind_, "n_trees": int(m.n_trees_), "n_train": int(len(tr))})
        out.append(o)
    return pd.concat(out), trees


def run() -> dict:
    verify_lock()
    rng = np.random.default_rng(20261104)
    res = {"version": VERSION, "protocol_version": PROTOCOL_VERSION, "run_utc": datetime.now(timezone.utc).isoformat()}
    res["untouched_2013"] = untouched(rng)
    print("untouched done", flush=True)
    X = P.data(1)
    R, trees = rolling(X)
    R.to_csv(OUT / "oof_rolling.csv", index=False)
    res["rolling"] = {"trees": trees, "pooled": {n: E9.metrics(R, n) for n in NAMES},
                      "auc_ci95": E9.auc_ci(R, "LGBM", rng),
                      "vs": {n: WH.boot(R, "LGBM", n, rng) for n in NAMES if n != "LGBM"},
                      "by_origin": {o: {n: E9.metrics(g, n) for n in NAMES} for o, g in R.groupby("origin")},
                      "calabarzon": R[R["province"].isin(CAL)][["origin", "province", "survey", "status", "q"] + NAMES].round(4).to_dict(orient="records")}
    print("rolling done", flush=True)
    res["ablation"] = {}
    for g, cols in DROPS.items():
        Ra, _ = rolling(X, ["LGBM"], drop=cols)
        res["ablation"][g] = WH.boot(Ra.assign(FULL=R["LGBM"].values), "LGBM", "FULL", rng)
    # gate
    U, Rr = res["untouched_2013"], res["rolling"]
    Lu, Lr = U["metrics"]["LGBM"], Rr["pooled"]["LGBM"]
    best_simple = min(["PRIOR", "RR-F", "LR-F", "LR-P (PSA-only)"], key=lambda n: Rr["pooled"][n]["expected_brier"])
    checks = {
        "U1_untouched_beats_NAT_and_PSA_only": Lu["expected_brier"] < U["metrics"]["NAT"]["expected_brier"]
                                                and Lu["expected_brier"] < U["metrics"]["LR-P (PSA-only)"]["expected_brier"],
        "U2_untouched_discrimination": Lu.get("auc", 0) >= T["U_auc"] and U["auc_ci95"][0] >= T["U_auc_ci_lower"],
        "U3_untouched_calibration": Lu["ece"] <= T["U_ece"],
        "R1_beats_persistence": Rr["vs"]["PERS"]["ci95"][1] < T["R_ci_upper_vs_PERS"],
        "R1_beats_region_history": Rr["vs"]["REGPREV"]["ci95"][1] < T["R_ci_upper_vs_REGPREV"],
        "R1_not_worse_than_best_simple": Rr["vs"][best_simple]["diff"] <= Rr["vs"][best_simple]["se"],
        "R1_classes": Lr.get("auc", 0) >= T["R_auc"] and Lr.get("recall_elevated", 0) >= T["R_recall"]
                      and (Lr.get("precision_elevated") or 0) >= T["R_precision"],
        "R1_calibration": Lr["ece"] <= T["R_ece"],
        "R2_beats_persistence_every_origin": all(Rr["by_origin"][o]["LGBM"]["expected_brier"] < Rr["by_origin"][o]["PERS"]["expected_brier"]
                                                 for o in Rr["by_origin"]),
        "R3_trees_beat_linear_prior": Rr["vs"]["PRIOR"]["ci95"][1] < T["R3_ci_upper_vs_PRIOR"],
    }
    forecast_checks = [k for k in checks if k != "R3_trees_beat_linear_prior"]
    res["gate"] = {"checks": checks, "best_simple": best_simple,
                   "survey_to_survey_forecast_validated": all(checks[k] for k in forecast_checks),
                   "lightgbm_trees_justified": checks["R3_trees_beat_linear_prior"]}
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=lambda o: None if isinstance(o, float) and np.isnan(o) else str(o)))
    print("gate", res["gate"])
    return res


if __name__ == "__main__":
    {"lock": lock, "run": run}[sys.argv[1]]()
