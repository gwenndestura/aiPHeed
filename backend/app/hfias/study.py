"""
HFIAS study: fixed protocol, decided before any test score was computed (2026-11-03).

Target   y = provincial share of households food insecure by HFIAS (any level; FNRI headline indicator), %, ENNS
         round 2018 or 2019. Secondary target: moderate-or-severe (same design, reported separately).
Models   predict d = logit(y) - logit(y2015) and add it back. Candidates (fixed list):
           B0 no change (y2015), B1 mean change of the training provinces, B2 mean level of the training provinces,
           M1 ridge (alpha by inner leave-one-out), M2 random forest, M3 gradient boosting, M4 LightGBM.
Features PANEL.FAMILIES as of the issue date (`lead` quarters before Q1 of the survey year); imputation by training
         medians; no test row is used in fitting, imputation, scaling or selection.
Design   PRIMARY: train on provinces surveyed in 2018, test on provinces surveyed in 2019 (later and different
         provinces). SECONDARY: leave-one-island-group-out over all rows.
Select   the candidate with the lowest leave-one-out MAE inside the 2018 training rows at Lead 1 (test not used).
Classes  HIGH = y >= the national moderate-or-severe prevalence of the same round (FNRI's own comparison). Predicted
         HIGH = predicted y >= the national level predicted from training data only.
Accept   ACCEPT below; every check must pass on the primary test.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

from app.hfias import OUT
from app.hfias import panel as P

ACCEPT = {"mae_pp_max": 5.0, "beats_best_baseline_mae": True, "coverage90_range": [0.80, 0.97], "accuracy_min": 0.75,
          "balanced_accuracy_min": 0.70, "high_recall_min": 0.60, "ece_max": 0.10, "n_test_min": 20, "n_high_min": 10}
CANDIDATES = ["B0 no change", "B1 mean change", "B2 mean level", "M1 ridge", "M2 random forest", "M3 gradient boosting",
              "M4 LightGBM"]
FEATURES = list(P.FAMILIES)
SEED = 20261103
NATIONAL_2015 = {"insecure": 66.1, "mod_sev": 53.8}   # FNRI 2015 Philippines (Appendices 1, 3-4)


def protocol_sha() -> str:
    return hashlib.sha256(json.dumps({"accept": ACCEPT, "candidates": CANDIDATES, "features": FEATURES, "seed": SEED,
                                      "target": P.TARGET, "national_2015": NATIONAL_2015}, sort_keys=True).encode()).hexdigest()


def _learner(name: str, n_trees: int = 500):
    if name == "M1 ridge":
        from sklearn.linear_model import RidgeCV
        return RidgeCV(alphas=np.logspace(-2, 3, 30))                       # alpha by efficient leave-one-out
    if name == "M2 random forest":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=n_trees, min_samples_leaf=3, random_state=SEED)
    if name == "M3 gradient boosting":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=SEED)
    import lightgbm as lgb
    return lgb.LGBMRegressor(n_estimators=200, num_leaves=4, min_child_samples=5, learning_rate=0.05, subsample=0.8,
                             subsample_freq=1, random_state=SEED, verbose=-1)


def _point(name: str, tr: pd.DataFrame, te: pd.DataFrame, feats: list[str], n_trees: int = 500) -> np.ndarray:
    """Predicted logit change for `te` from a fit on `tr` only (imputation and scaling from `tr`)."""
    dtr = (P.logit(tr["y"]) - tr["y2015_logit"]).to_numpy()
    if name == "B0 no change":
        return np.zeros(len(te))
    if name == "B1 mean change":
        return np.full(len(te), dtr.mean())
    if name == "B2 mean level":
        return (P.logit(tr["y"]).mean() - te["y2015_logit"]).to_numpy()
    med = tr[feats].median()
    Xtr, Xte = tr[feats].fillna(med).to_numpy(float), te[feats].fillna(med).to_numpy(float)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    return _learner(name, n_trees).fit((Xtr - mu) / sd, dtr).predict((Xte - mu) / sd)


def _loo_resid(name: str, tr: pd.DataFrame, feats: list[str]) -> np.ndarray:
    """Leave-one-out residuals (logit change) inside `tr`."""
    out = []
    for i in range(len(tr)):
        a, b = tr.drop(tr.index[i]), tr.iloc[[i]]
        p = _point(name, a, b, feats, n_trees=200)
        out.append(float(P.logit(b["y"].iloc[0]) - b["y2015_logit"].iloc[0] - p[0]))
    return np.array(out)


def _fit_predict(name: str, tr: pd.DataFrame, te: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, float]:
    """Point predictions and the leave-one-out residual SD (logit) from the training rows only."""
    return _point(name, tr, te, feats), float(np.sqrt(np.mean(_loo_resid(name, tr, feats) ** 2)))


def evaluate(name: str, tr: pd.DataFrame, te: pd.DataFrame, feats: list[str] = FEATURES) -> dict:
    d, sres = _fit_predict(name, tr, te, feats)
    eta = te["y2015_logit"].to_numpy() + d
    pred = P.expit(eta)
    y = te["y"].to_numpy(float)
    # predictive SD in logit: model residual SD plus the test survey's own sampling error
    s_obs = (te["y_se"].to_numpy(float) / 100) / ((y / 100) * (1 - y / 100))
    s = np.sqrt(sres ** 2 + s_obs ** 2)
    lo, hi = P.expit(eta - 1.645 * s), P.expit(eta + 1.645 * s)
    dtr = (P.logit(tr["y"]) - tr["y2015_logit"]).mean()
    nat_hat = float(P.expit(P.logit(NATIONAL_2015[te["target"].iloc[0]]) + dtr))
    nat = te["nat"].to_numpy(float)
    true_high = y >= nat
    p_high = 1 - stats.norm.cdf((P.logit(nat_hat) - eta) / s)
    pred_high = pred >= nat_hat
    err = pred - y
    return {"model": name, "n": int(len(y)), "mae_pp": float(np.mean(np.abs(err))), "rmse_pp": float(np.sqrt(np.mean(err ** 2))),
            "bias_pp": float(err.mean()), "spearman": float(stats.spearmanr(pred, y).correlation),
            "coverage90": float(np.mean((y >= lo) & (y <= hi))), "national_hat_pct": nat_hat,
            **_cls(true_high, pred_high, p_high),
            "rows": [{"province": p, "year": int(yr), "observed_pct": float(o), "predicted_pct": float(q),
                      "interval90_pct": [float(a), float(b)], "p_high": float(ph), "observed_high": bool(t)}
                     for p, yr, o, q, a, b, ph, t in zip(te["province"], te["year"], y, pred, lo, hi, p_high, true_high)]}


def _cls(t: np.ndarray, p: np.ndarray, prob: np.ndarray) -> dict:
    tp, tn = int((t & p).sum()), int((~t & ~p).sum())
    fp, fn = int((~t & p).sum()), int((t & ~p).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    bins = np.linspace(0, 1, 6)
    idx = np.clip(np.digitize(prob, bins) - 1, 0, 4)
    ece = sum(abs(prob[idx == b].mean() - t[idx == b].mean()) * (idx == b).sum() for b in range(5) if (idx == b).any()) / len(t)
    return {"n_high": int(t.sum()), "tp": tp, "tn": tn, "fp": fp, "fn": fn, "accuracy": (tp + tn) / len(t),
            "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "high_recall": rec, "high_precision": prec, "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
            "brier": float(np.mean((prob - t) ** 2)), "ece": float(ece)}


def checks(m: dict, best_baseline_mae: float) -> dict:
    A = ACCEPT
    c = {"mae": m["mae_pp"] <= A["mae_pp_max"], "beats_baseline": m["mae_pp"] < best_baseline_mae,
         "coverage": A["coverage90_range"][0] <= m["coverage90"] <= A["coverage90_range"][1],
         "accuracy": m["accuracy"] >= A["accuracy_min"],
         "balanced_accuracy": (m["balanced_accuracy"] or 0) >= A["balanced_accuracy_min"],
         "high_recall": (m["high_recall"] or 0) >= A["high_recall_min"], "ece": m["ece"] <= A["ece_max"],
         "n_test": m["n"] >= A["n_test_min"], "n_high": m["n_high"] >= A["n_high_min"]}
    return {"checks": c, "passed": all(c.values())}


def run(target: str = P.TARGET) -> dict:
    o = P.outcomes(target)
    res = {"protocol_sha256": protocol_sha(), "target": target, "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "accept": ACCEPT, "n_rows": int(len(o)), "years": o["year"].value_counts().to_dict(),
           "unmatched_enns": o.attrs["unmatched_enns"], "leads": {}}
    for lead in (1, 2, 3, 4):
        X = P.features(o, lead)
        tr, te = X[X["year"] == 2018].reset_index(drop=True), X[X["year"] == 2019].reset_index(drop=True)
        # selection on training rows only (lead 1 decides; reused at other leads)
        if lead == 1:
            sel_scores = {n: float(np.mean(np.abs(P.expit(tr["y2015_logit"] + (P.logit(tr["y"]) - tr["y2015_logit"]) -
                                                            _loo_resid(n, tr, FEATURES)) - tr["y"]))) for n in CANDIDATES}
            selected = min(sel_scores, key=sel_scores.get)
            res["selection"] = {"rule": "lowest leave-one-out MAE on 2018 training provinces, Lead 1", "loo_mae_pp": sel_scores,
                                "selected": selected}
        primary = {n: evaluate(n, tr, te) for n in CANDIDATES}
        best_base = min(primary[n]["mae_pp"] for n in CANDIDATES if n.startswith("B"))
        sel = res["selection"]["selected"]
        res["leads"][str(lead)] = {
            "issue_rule": f"first day of the quarter {lead} quarter(s) before Q1 of the survey year",
            "n_train": int(len(tr)), "n_test": int(len(te)), "primary": primary,
            "selected_checks": checks(primary[sel], best_base),
            "secondary_island_cv": _island_cv(X, sel),
            "ablation": _ablation(tr, te, sel) if lead == 1 else None}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"study_{target}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def _island_cv(X: pd.DataFrame, name: str) -> dict:
    rows = []
    for isl in sorted(X["island"].dropna().unique()):
        tr, te = X[X["island"] != isl], X[X["island"] == isl]
        if len(te) and len(tr) >= 10:
            e = evaluate(name, tr.reset_index(drop=True), te.reset_index(drop=True))
            rows.append({"held_out": isl, "n": e["n"], "mae_pp": e["mae_pp"], "accuracy": e["accuracy"]})
    n = sum(r["n"] for r in rows)
    return {"folds": rows, "pooled_mae_pp": sum(r["mae_pp"] * r["n"] for r in rows) / n if n else None}


def _ablation(tr: pd.DataFrame, te: pd.DataFrame, name: str) -> dict:
    groups = {}
    for f, fam in P.FAMILIES.items():
        groups.setdefault(P.GROUP[fam], []).append(f)
    model = name if name.startswith("M") else "M1 ridge"
    full = evaluate(model, tr, te)["mae_pp"]
    out = {"model": model, "full_mae_pp": full, "drop": {}, "only_with_lag": {}}
    for g, fs in groups.items():
        rest = [f for f in FEATURES if f not in fs]
        out["drop"][g] = evaluate(model, tr, te, rest)["mae_pp"] - full
        if g != "lag":
            out["only_with_lag"][g] = evaluate(model, tr, te, ["y2015_logit"] + fs)["mae_pp"]
    out["note"] = ("drop[g] > 0 means removing group g made test MAE worse (the group helped). Groups not in the "
                   "panel (employment, news, climate C1-C2) are listed in the report as not testable nationally.")
    return out


if __name__ == "__main__":
    import sys
    r = run(sys.argv[1] if len(sys.argv) > 1 else P.TARGET)
    print(json.dumps(r["selection"], indent=1))
    for k, v in r["leads"].items():
        print(k, {n: round(m["mae_pp"], 2) for n, m in v["primary"].items()}, v["selected_checks"])
