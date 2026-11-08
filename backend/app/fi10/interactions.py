"""FI10-A: do poverty x food-price interactions improve the hunger forecast (the only food-insecurity outcome)?

Hypothesis (owner, 2026-11-03; literature: Semeniano et al. 2025 PJD 10.62986/pjd2025.49.2b; Javier et al. 2024 PJS
10.56899/153.04.20; Bogmans et al. 2024 IMF WP 10.5089/9798400287336.001; Headey & Martin 2016 ARRE
10.1146/annurev-resource-100815-095303): poverty is the underlying vulnerability and food-price increases are a shock
whose effect is larger where poverty is higher.

Target: SWS Balance Luzon HIGH, FI9 issue timing, Lead 1 (FI9-X design rows; 62 targets 2010-2026).
Interactions are products of variables standardised with TRAINING means and SDs at each origin:
    poverty x food inflation, poverty x rice inflation, unemployment x food inflation
Poverty enters as the latest RELEASED estimate (triennial), never as a new quarterly observation.

    python -m app.fi10.interactions lock | run
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi7 import models as M7
from app.fi10 import OUT, VERSION
from app.fi9z.classmetrics import class_metrics
from app.paths import BACKEND_DIR

X9 = BACKEND_DIR / "data" / "fi9x" / "out"
STATE = ["gap", "hunger_last_anom", "hunger_age_q", "moe_last"]
MAIN = ["cpi_food_yoy", "cpi_rice_yoy", "poverty_inc", "unemp_rate"]
PAIRS = [("poverty_inc", "cpi_food_yoy"), ("poverty_inc", "cpi_rice_yoy"), ("unemp_rate", "cpi_food_yoy")]
INTER = [f"{a}__x__{b}" for a, b in PAIRS]
CANDIDATES = {"I1 residual correction, main effects": ("resid", MAIN), "I2 residual correction, main effects + interactions": ("resid", MAIN + INTER),
              "I3 logistic, SWS state + main effects": ("logit", STATE + MAIN), "I4 logistic, SWS state + main effects + interactions": ("logit", STATE + MAIN + INTER)}
COUNTERPART = {"I2 residual correction, main effects + interactions": "I1 residual correction, main effects",
               "I4 logistic, SWS state + main effects + interactions": "I3 logistic, SWS state + main effects"}
PROTOCOL = {"version": VERSION, "candidates": {k: v[1] for k, v in CANDIDATES.items()}, "interactions": PAIRS,
            "threshold": "balanced-accuracy-optimal on the inner time holdout (latest 25 % of training targets)",
            "interaction_adds_value": "Brier better than the no-interaction counterpart with quarter-block bootstrap P >= 0.90, or "
                                      "balanced accuracy better with P >= 0.90",
            "production_adoption": "only if a candidate also meets every FI9-Z class, skill and robustness requirement"}


def _digest():
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def _code():
    return hashlib.sha256((BACKEND_DIR / "app" / "fi10" / "interactions.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _with_inter(tr, te):
    tr, te = tr.copy(), te.copy()
    for a, b in PAIRS:
        za = lambda d: (d[a] - tr[a].mean()) / (tr[a].std(ddof=1) or 1)
        zb = lambda d: (d[b] - tr[b].mean()) / (tr[b].std(ddof=1) or 1)
        tr[f"{a}__x__{b}"], te[f"{a}__x__{b}"] = za(tr) * zb(tr), za(te) * zb(te)
    return tr, te


def _tau(p, y):
    best, tau = -1, 0.5
    if len(set(y)) == 2:
        for t in np.linspace(0.05, 0.95, 91):
            ba = (np.mean(p[y == 1] >= t) + np.mean(p[y == 0] < t)) / 2
            if ba > best + 1e-9:
                best, tau = ba, float(t)
    return tau


def run() -> dict:
    lock = json.loads((OUT / "INTERACTIONS_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code():
        raise RuntimeError("FI10-A protocol or code changed after lock")
    X = pd.read_csv(X9 / "design_OP1.csv", parse_dates=["issue_ts", "target_published"])
    X = X[X["y"].notna()].sort_values("issue_ts").reset_index(drop=True)
    X["gap"] = X["hunger_last"] - X["threshold_known"]
    dl = {}                                                 # damped persistence walk-forward level for every row
    for i in range(len(X)):
        tr = X[X["target_published"] <= X.loc[i, "issue_ts"]]
        if len(tr) >= 25:
            dl[i] = float(M7.make("damped", []).fit(tr, tr["delta_target"].to_numpy(float)).predict_level(X.loc[[i]])[0])
    X["d_level"] = pd.Series(dl)

    def predict(kind, feats, tr, te):
        tr, te = _with_inter(tr, te)
        if kind == "logit":
            cols = [c for c in feats if tr[c].notna().sum() >= 10]
            m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=5000)).fit(tr[cols], tr["y"].astype(int))
            return m.predict_proba(te[cols])[:, 1]
        trr = tr[tr["d_level"].notna()]
        cols = [c for c in feats if trr[c].notna().sum() >= 10]
        if len(trr) < 15 or not cols:                    # nothing to learn a correction from: damped persistence as is
            sd = max(float(np.std(trr["hunger_target"] - trr["d_level"], ddof=1)), 1.0) if len(trr) > 2 else 4.5
            return 1 - norm.cdf((te["threshold_known"].to_numpy(float) - te["d_level"].to_numpy(float)) / sd)
        rg = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), RidgeCV(alphas=[1.0, 10.0, 100.0, 1000.0], store_cv_results=True))
        rg.fit(trr[cols], trr["hunger_target"] - trr["d_level"])
        cv = rg[-1].cv_results_[:, list(rg[-1].alphas).index(rg[-1].alpha_)]
        sd = max(float(np.sqrt(np.mean(cv))), 1.0)
        lv = te["d_level"].to_numpy(float) + rg.predict(te[cols])
        return 1 - norm.cdf((te["threshold_known"].to_numpy(float) - lv) / sd)

    rows = []
    for name, (kind, feats) in CANDIDATES.items():
        for i in range(len(X)):
            r = X.loc[i]
            if r["target_quarter"] < "2010-Q1" or pd.isna(r["d_level"]):
                continue
            tr = X[(X["target_published"] <= r["issue_ts"])]
            qs = np.sort(tr["target_quarter"].unique())
            a, b = tr[tr["target_quarter"] < qs[int(len(qs) * 0.75)]], tr[tr["target_quarter"] >= qs[int(len(qs) * 0.75)]]
            tau = _tau(predict(kind, feats, a, b), b["y"].to_numpy(int)) if b["y"].nunique() == 2 else 0.5
            p = float(predict(kind, feats, tr, X.loc[[i]])[0])
            rows.append({"config": name, "target_quarter": r["target_quarter"], "y": int(r["y"]), "p": p, "cls": int(p >= tau), "tau": tau})
    W = pd.DataFrame(rows)
    Z = pd.read_csv(BACKEND_DIR / "data" / "fi9z" / "out" / "predictions.csv")
    Z = Z[(Z["origin"] == "OP1") & Z["config"].isin(["Naive persistence", "C0 damped persistence (production)"])][["config", "target_quarter", "y", "p", "cls"]]
    W = pd.concat([W, Z], ignore_index=True)
    W.to_csv(OUT / "interactions_predictions.csv", index=False, lineterminator="\n")
    from app.fi9z.study import _boot_ba, _boot_brier
    piv = {c: g.set_index("target_quarter").sort_index() for c, g in W.groupby("config")}
    res = {"protocol_sha256": lock["sha256"], "models": {}}
    nv = piv["Naive persistence"]
    for c, g in piv.items():
        common = g.index.intersection(nv.index)
        y = g.loc[common, "y"].to_numpy(int)
        m = {"n": len(common), "metrics": class_metrics(y, g.loc[common, "cls"], g.loc[common, "p"]),
             "vs_naive_brier": _boot_brier(g.loc[common, "p"].to_numpy(), nv.loc[common, "p"].to_numpy(), y),
             "vs_naive_ba": _boot_ba(g.loc[common, "cls"].to_numpy(), nv.loc[common, "cls"].to_numpy(), y)}
        if c in COUNTERPART:
            cp = piv[COUNTERPART[c]].loc[common]
            m["vs_counterpart_brier"] = _boot_brier(g.loc[common, "p"].to_numpy(), cp["p"].to_numpy(), y)
            m["vs_counterpart_ba"] = _boot_ba(g.loc[common, "cls"].to_numpy(), cp["cls"].to_numpy(), y)
            m["interaction_adds_value"] = bool((m["vs_counterpart_brier"]["mean"] < 0 and m["vs_counterpart_brier"]["p_better"] >= 0.90)
                                               or (m["vs_counterpart_ba"]["mean"] > 0 and m["vs_counterpart_ba"]["p_better"] >= 0.90))
        res["models"][c] = m
    (OUT / "interactions_evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        from datetime import datetime, timezone
        p = OUT / "INTERACTIONS_LOCK.json"
        if p.exists():
            sys.exit("already locked")
        p.write_text(json.dumps({"sha256": _digest(), "code_sha256": _code(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        r = run()
        for c, m in r["models"].items():
            k = m["metrics"]
            print(f"{c[:55]:55s} n={m['n']} HR={k['high_recall']} HP={k['high_precision']} LR={k['low_recall']:.2f} BA={k['balanced_accuracy']:.3f} mF1={k['macro_f1']:.3f} br={k['brier']:.3f} "
                  f"vsN br {m['vs_naive_brier']['mean']:+.4f}/{m['vs_naive_brier']['p_better']:.2f}"
                  + (f" | vs no-interaction: br {m['vs_counterpart_brier']['mean']:+.4f}/{m['vs_counterpart_brier']['p_better']:.2f} BA {m['vs_counterpart_ba']['mean']:+.3f}/{m['vs_counterpart_ba']['p_better']:.2f} adds={m['interaction_adds_value']}" if "vs_counterpart_brier" in m else ""))
