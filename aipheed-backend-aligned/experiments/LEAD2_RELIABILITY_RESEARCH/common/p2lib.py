"""Phase 2 shared code (SEARCH_LOG.md, EXPERIMENT_PLAN_PHASE2.md). Read-only on every input.

Wraps the frozen scorers so any probability column can be scored with the official seven rules on the identical P0H4
evaluation rows, and adds an independent re-implementation of the rules (Y0 audit) that does not share code with them.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import importlib.util  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import confusion_matrix, roc_auc_score  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE.parent
EXP = RES.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(RES / "runner"))
sys.path.insert(0, str(EXP / "FIRI_LEAD2_FEASIBILITY" / "runner"))
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))

import rlib as R  # noqa: E402

_spec = importlib.util.spec_from_file_location("p0h4_review", EXP / "P0H4_LEAD12_REVIEW" / "runner" / "reproduce.py")
RV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RV)

SEED, B = 2036, 5000
PLAN2 = RES / "EXPERIMENT_PLAN_PHASE2.md"


def plan2_ok() -> None:
    want = (RES / "common" / "PLAN2_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256(PLAN2.read_bytes()).hexdigest() == want, "EXPERIMENT_PLAN_PHASE2.md changed after freezing"


def load_p0h4() -> pd.DataFrame:
    """The official walk-forward evaluation rows (FINAL_ARCHITECTURE/out/predictions.csv), Leads 1 and 2."""
    return RV.load()


def official_rules(g: pd.DataFrame, col: str) -> dict:
    """The frozen rule implementation (P0H4_LEAD12_REVIEW/reproduce.py, protocol section 7) applied to `col`."""
    h = g.copy()
    h[RV.P] = h[col].clip(0, 1)
    r = RV.rules(h)
    s = RV.scores(h)
    return {"scores": s, "rules": r, "passesAll": all(v["pass"] for v in r.values()),
            "failed": [k.split()[0] for k, v in r.items() if not v["pass"]]}


# ------------------------------------------------------------------------------------------------ independent rules
def _acc(y, p):
    return float(((np.asarray(p) >= 0.5).astype(int) == np.asarray(y)).mean())


def _boot_p(g, col, base):
    """One-sided quarter-cluster bootstrap p for mean Brier(col) - Brier(base) >= 0."""
    l = ((g[col] - g["y"]) ** 2 - (g[base] - g["y"]) ** 2).to_numpy()
    q = g["q"].to_numpy()
    uq = np.unique(q)
    idx = {u: np.where(q == u)[0] for u in uq}
    rng = np.random.default_rng(SEED)
    bs = np.empty(B)
    for b in range(B):
        pick = rng.choice(uq, len(uq))
        bs[b] = np.concatenate([l[idx[u]] for u in pick]).mean()
    return float(l.mean()), float(np.mean(bs >= 0))


def independent_rules(g: pd.DataFrame, col: str) -> dict:
    """Second implementation of R1-R7 (sklearn confusion matrix with explicit label order, own bootstrap loop)."""
    y, p = g["y"].to_numpy(int), g[col].to_numpy(float)
    tn, fp, fn, tp = confusion_matrix(y, (p >= 0.5).astype(int), labels=[0, 1]).ravel()
    acc = (tp + tn) / len(y)
    rec, spec = tp / (tp + fn), tn / (tn + fp)
    prec = tp / (tp + fp) if tp + fp else 0.0
    qs = sorted(g["q"].unique())
    thirds = np.array_split(np.array(qs), 3)
    d_p, p_p = _boot_p(g, col, "PERSIST-SI_p")
    d_c, p_c = _boot_p(g, col, "CLIM_p")
    r = {"R1": len(qs) >= 10 and len(y) >= 40,
         "R2": acc >= 0.75,
         "R3": (rec + spec) / 2 >= 0.70,
         "R4": acc > _acc(y, g["ALWAYS-LOW_p"]) and acc > _acc(y, g["PERSIST-SI_p"]),
         "R5": d_p < 0 and p_p < 0.10 and d_c < 0 and p_c < 0.10,
         "R6": prec >= 0.60 and rec >= 0.60,
         "R7": min(_acc(g[g.q.isin(t)]["y"], g[g.q.isin(t)][col]) for t in thirds) >= 0.60
               and min(_acc(g[g.q != q]["y"], g[g.q != q][col]) for q in qs) >= 0.70}
    return {"cm": {"TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)}, "accuracy": acc,
            "balanced": (rec + spec) / 2, "precision": prec, "recall": rec, "specificity": spec,
            "brier": float(np.mean((p - y) ** 2)), "auc": float(roc_auc_score(y, p)),
            "auc_of_1_minus_p": float(roc_auc_score(y, 1 - p)),
            "R5_detail": {"vsPERSIST": [d_p, p_p], "vsCLIM": [d_c, p_c]}, "rules": r}


def full_metrics(g: pd.DataFrame, col: str) -> dict:
    """Reporting set: counts, prevalence, all classification metrics, AUC, Brier, quarter-cluster 90% CI for accuracy
    and balanced accuracy."""
    y, p = g["y"].to_numpy(int), g[col].to_numpy(float)
    yh = (p >= .5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    q = g["q"].to_numpy()
    uq = np.unique(q)
    idx = {u: np.where(q == u)[0] for u in uq}
    rng = np.random.default_rng(SEED)
    accs, bals = [], []
    for _ in range(2000):
        ii = np.concatenate([idx[u] for u in rng.choice(uq, len(uq))])
        yy, hh = y[ii], yh[ii]
        accs.append(float((yy == hh).mean()))
        if 0 < yy.sum() < len(yy):
            bals.append(0.5 * (((hh == 1) & (yy == 1)).sum() / yy.sum() + ((hh == 0) & (yy == 0)).sum() / (len(yy) - yy.sum())))
    return {"n": int(len(y)), "quarters": int(len(uq)), "pos": int(y.sum()), "prevalence": float(y.mean()),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": r(tp + tn, len(y)),
            "balanced": None if rec is None or spec is None else (rec + spec) / 2,
            "precision": prec, "recall": rec, "specificity": spec,
            "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
            "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None,
            "brier": float(np.mean((p - y) ** 2)),
            "accuracyCI90": [float(np.quantile(accs, .05)), float(np.quantile(accs, .95))],
            "balancedCI90": [float(np.quantile(bals, .05)), float(np.quantile(bals, .95))] if bals else None}


def design_effect(g: pd.DataFrame, col: str) -> dict:
    """Effective number of independent rows: intra-quarter correlation of the 0/1 error indicator (ANOVA estimator),
    Kish design effect 1 + (m - 1) * rho."""
    e = ((g[col] >= .5).astype(int) != g["y"]).astype(float)
    gr = pd.DataFrame({"q": g["q"].to_numpy(), "e": e.to_numpy()})
    k = gr["q"].nunique()
    m = len(gr) / k
    msb = m * ((gr.groupby("q")["e"].mean() - gr["e"].mean()) ** 2).sum() / (k - 1)
    msw = ((gr["e"] - gr.groupby("q")["e"].transform("mean")) ** 2).sum() / (len(gr) - k)
    rho = float((msb - msw) / (msb + (m - 1) * msw)) if msb + (m - 1) * msw > 0 else 0.0
    rho = max(rho, 0.0)
    deff = 1 + (m - 1) * rho
    return {"rows": int(len(gr)), "quarters": int(k), "rowsPerQuarter": m, "iccError": rho, "designEffect": deff,
            "effectiveN": float(len(gr) / deff)}
