"""FI6 walk-forward evaluation (fixed in METHOD_LOCK.json before the run).

Identical protocol to FI5 so the two can be compared: issue at quarter end, leads 1-4, refit at every origin on
rows whose target was published by the issue date, evaluated targets 2010-Q1..2026-Q3, eras 2010-15 / 2016-20 /
2021-26, the same reliability rules. Added for FI6: balanced accuracy, false-negative rate, calibration bins,
Wilson intervals for recall/precision, label-confidence-weighted accuracy, and the news / domain ablations.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from app.fi5.evaluate import block_bootstrap_diff, mcnemar_p, metrics as base_metrics
from app.fi5.target import qindex
from app.fi6 import models as M
from app.fi6.features import DOMAIN, NEWS, SETS, design
from app.fi6.paths import OUT

LEADS = [1, 2, 3, 4]
EVAL_FIRST_TARGET = "2010-Q1"
ERAS = [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]
RELIABILITY = {"accuracy": 0.75, "recall": 0.50, "precision": 0.50, "auc": 0.70, "brier_skill": 0.0, "era_accuracy": 0.60}
PROPOSED = "LightGBM (proposed)"
BASELINES = {
    "Naive persistence": ("persist", None),
    "PSA-only (government indicators)": ("clf_lgbm", "psa_only"),
    "NLP-only (news composites)": ("clf_lgbm", "nlp_only"),
    "Logistic regression": ("logit", "full"),
}
REFERENCE = {
    "Climatology (base rate)": ("clim", None),
    "LightGBM classifier, direct (reference)": ("clf_lgbm", "full"),
    "LightGBM without news (government + latest reading)": ("reg", "gov_only"),
    **{f"LightGBM without {n}": ("reg", f"minus_{n}") for n in NEWS},
    **{f"LightGBM without {d} domain": ("reg", f"minus_domain_{d}") for d in ["market", "climate", "employment", "remittance", "poverty"]},
}
SPECS = {PROPOSED: ("reg", "full"), **BASELINES, **REFERENCE}


def _wilson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(c - h), float(c + h)]


def metrics(y, p, base=None, w=None) -> dict:
    m = base_metrics(y, p, base)
    if not m.get("n"):
        return m
    tpr = m["tp"] / (m["tp"] + m["fn"]) if m["tp"] + m["fn"] else None
    tnr = m["tn"] / (m["tn"] + m["fp"]) if m["tn"] + m["fp"] else None
    m["balanced_accuracy"] = float((tpr + tnr) / 2) if tpr is not None and tnr is not None else None
    m["fnr"] = float(1 - tpr) if tpr is not None else None
    m["recall_ci95"] = _wilson(m["tp"], m["tp"] + m["fn"])
    m["precision_ci95"] = _wilson(m["tp"], m["tp"] + m["fp"])
    m["accuracy_ci95"] = _wilson(m["tp"] + m["tn"], m["n"])
    if w is not None:
        w = np.asarray(w, float)
        m["confidence_weighted_accuracy"] = float(np.sum(w * ((np.asarray(p) >= .5) == np.asarray(y))) / np.sum(w))
    pb = np.asarray(p, float)
    bins = [(0, .2), (.2, .5), (.5, .8), (.8, 1.01)]
    m["calibration"] = [{"bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(((pb >= a) & (pb < b)).sum()),
                         "mean_p": float(pb[(pb >= a) & (pb < b)].mean()) if ((pb >= a) & (pb < b)).any() else None,
                         "observed": float(np.asarray(y)[(pb >= a) & (pb < b)].mean()) if ((pb >= a) & (pb < b)).any() else None}
                        for a, b in bins]
    return m


def walk_forward(args) -> dict:
    lead, X, chunk = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST_TARGET)].iloc[chunk[0]::chunk[1]]
    rows, gaps = [], []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        te = L.loc[[i]]
        rec = {"lead": lead, "issue_quarter": r["issue_quarter"], "target_quarter": r["target_quarter"], "y": int(r["y"]),
               "p_flip": r["p_flip"], "hunger_target": r["hunger_target"], "hunger_last": r["hunger_last"],
               "threshold_known": r["threshold_known"], "threshold_actual": r["threshold_actual"], "n_train": int(len(tr))}
        for name, (kind, fs) in SPECS.items():
            m = M.fit(M.make(kind, SETS.get(fs) if fs else None), kind, tr)
            rec[name] = float(m.predict_proba(te)[0])
            if name == PROPOSED:
                rec["delta_hat"] = float(m.predict_delta(te)[0])
                rec["sigma"] = m.sigma
                rec["config"] = m.choice
                ptr = m.predict_proba(tr)
                gaps.append({"lead": lead, "target_quarter": r["target_quarter"],
                             "train_accuracy": float(((ptr >= .5) == tr["y"]).mean()),
                             "oos_correct": int((rec[name] >= .5) == r["y"])})
        rows.append(rec)
    return {"lead": lead, "oos": rows, "gaps": gaps}


def permutation(args) -> dict:
    """Shuffle the training changes at every origin (lead fixed): the model should lose any real skill."""
    lead, X, k = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST_TARGET)]
    rng = np.random.default_rng([13, lead, k])
    ps = []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]].copy()
        tr["delta_target"] = rng.permutation(tr["delta_target"].to_numpy())
        m = M.DeltaModel(SETS["full"]).fit(tr, tr["delta_target"].to_numpy())
        ps.append(float(m.predict_proba(L.loc[[i]])[0]))
    from sklearn.metrics import roc_auc_score
    y = ev["y"].astype(int).to_numpy()
    return {"lead": lead, "auc": float(roc_auc_score(y, ps)), "brier": float(np.mean((np.array(ps) - y) ** 2))}


def summarise(oos: pd.DataFrame) -> dict:
    res = {}
    for lead, g in oos.groupby("lead"):
        y = g["y"].to_numpy(int)
        clim = g["Climatology (base rate)"].to_numpy(float)
        w = 1 - g["p_flip"].to_numpy(float)
        per = {}
        for name in SPECS:
            p = g[name].to_numpy(float)
            mm = metrics(y, p, clim, w)
            mm["eras"] = {}
            for era, a, b in ERAS:
                sel = g["target_quarter"].str[:4].astype(int).between(a, b).to_numpy()
                mm["eras"][era] = metrics(y[sel], p[sel], clim[sel])
            per[name] = mm
        pp = g[PROPOSED].to_numpy(float)
        comp = {}
        for name in SPECS:
            if name == PROPOSED:
                continue
            q = g[name].to_numpy(float)
            bd = block_bootstrap_diff((pp - y) ** 2, (q - y) ** 2)
            comp[name] = {"brier_diff_proposed_minus_other": bd[0], "ci95": [bd[1], bd[2]],
                          "accuracy_diff": float(((pp >= .5) == y).mean() - ((q >= .5) == y).mean()),
                          "mcnemar_p": mcnemar_p(((pp >= .5) == y).astype(int), ((q >= .5) == y).astype(int))}
        lvl_hat = g["hunger_last"] + g["delta_hat"]
        lvl = {"n": int(len(g)), "mae_lgbm": float(np.mean(np.abs(lvl_hat - g["hunger_target"]))),
               "mae_persistence": float(np.mean(np.abs(g["hunger_last"] - g["hunger_target"])))}
        lvl["mae_skill_vs_persistence"] = float(1 - lvl["mae_lgbm"] / lvl["mae_persistence"])
        bd = block_bootstrap_diff(np.abs(lvl_hat - g["hunger_target"]), np.abs(g["hunger_last"] - g["hunger_target"]))
        lvl["mae_diff_ci95"] = [bd[1], bd[2]]
        lvl["mean_sigma"] = float(g["sigma"].mean())
        res[int(lead)] = {"models": per, "vs_proposed": comp, "level": lvl, "reliability": reliability(per[PROPOSED]),
                          "configs": g["config"].value_counts().to_dict()}
    return res


def reliability(m: dict) -> dict:
    chk = {"accuracy": m["accuracy"] >= RELIABILITY["accuracy"],
           "recall": (m["recall"] or 0) >= RELIABILITY["recall"],
           "precision": (m["precision"] or 0) >= RELIABILITY["precision"],
           "auc": (m["auc"] or 0) >= RELIABILITY["auc"],
           "brier_skill": (m.get("brier_skill") or -1) > RELIABILITY["brier_skill"],
           "era_accuracy": all(e.get("accuracy", 0) >= RELIABILITY["era_accuracy"] for e in m["eras"].values() if e.get("n"))}
    return {"checks": chk, "reliable": all(chk.values())}


def max_reliable_lead(summary: dict) -> int | None:
    best = None
    for L in sorted(summary):
        if summary[L]["reliability"]["reliable"]:
            best = L
        else:
            break
    return best


def run(n_perm: int = 20, workers: int | None = None) -> dict:
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        designs = dict(zip(LEADS, ex.map(design, LEADS)))
        n_chunks = max(1, workers // len(LEADS))
        parts = list(ex.map(walk_forward, [(L, designs[L], (k, n_chunks)) for L in LEADS for k in range(n_chunks)]))
        perms = list(ex.map(permutation, [(L, designs[L], k) for L in [1, 2] for k in range(n_perm)]))
    oos = pd.DataFrame([r for p in parts for r in p["oos"]]).sort_values(["lead", "target_quarter"]).reset_index(drop=True)
    gaps = pd.DataFrame([r for p in parts for r in p["gaps"]])
    oos.to_csv(OUT / "walkforward_predictions.csv", index=False, lineterminator="\n")
    gaps.to_csv(OUT / "overfit_train_vs_oos.csv", index=False, lineterminator="\n")
    summary = summarise(oos)
    perm = {}
    for L in [1, 2]:
        a = [p["auc"] for p in perms if p["lead"] == L]
        perm[L] = {"n_perm": len(a), "auc_mean": float(np.mean(a)), "auc_sd": float(np.std(a)),
                   "real_auc": summary[L]["models"][PROPOSED]["auc"],
                   "share_perm_auc_ge_real": float(np.mean(np.array(a) >= (summary[L]["models"][PROPOSED]["auc"] or 0)))}
    audit = {"train_vs_oos": {int(L): {"mean_train_accuracy": float(g["train_accuracy"].mean()),
                                       "oos_accuracy": float(g["oos_correct"].mean())} for L, g in gaps.groupby("lead")},
             "label_permutation": perm}
    result = {"summary": summary, "max_reliable_lead": max_reliable_lead(summary), "audit": audit,
              "protocol": {"leads": LEADS, "eval_first_target": EVAL_FIRST_TARGET, "eras": ERAS, "reliability": RELIABILITY,
                           "specs": {k: list(v) for k, v in SPECS.items()}}}
    (OUT / "evaluation.json").write_text(json.dumps(result, indent=1, default=str))
    return result
