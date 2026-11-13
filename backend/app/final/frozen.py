"""
FINAL (RATE + MIND) split into FIT (once, on the survey rounds) and PREDICT (every quarterly issue).

`app.hcw.final_engine.fit_predict` fits on the training rows and predicts the live rows in one call. Everything it learns depends
on the TRAINING rows only (anchor choice, input set, hyper-parameters, the LightGBM booster, training medians, calibration and
the residual-scale regression). The training rows change only when FNRI publishes a new provincial HFIAS survey round. So a
quarterly forecast needs no refit: `fit` runs the exact code of fit_predict up to the point where test rows enter, and `predict`
runs the rest. `tests/unit/test_final_frozen.py` checks that fit + predict == fit_predict to 1e-12 on the sealed 2026-Q4 rows.

Retraining (a new FNRI round) is a separate, controlled step (app.final.cycle refuses to issue with a stale model and records
"retraining required"); a refitted model is never served before it passes the evaluation gate.
"""
from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e164 import auto as A4
from app.e165 import final as F5
from app.hcw import engine as H
from app.hcw import final_engine as FE


def training_fingerprint(tr: pd.DataFrame) -> str:
    """SHA-256 of the rows that define the fit: keys, rounds, targets and their precision. A new survey round changes it."""
    cols = [c for c in ("key", "survey", "i", "T", "lead", "y_true", "se_true", "q_true", "gap_q") if c in tr]
    b = tr[cols].sort_values(cols[:4]).to_csv(index=False, float_format="%.10g").encode()
    return hashlib.sha256(b).hexdigest()


@dataclass
class FrozenFinal:
    seed: int
    lead: int
    anchor: str
    cfg: str
    model: object                       # FE.FinalModel (booster, training medians, selected inputs, g0)
    gappy: list[str]                    # inputs that get a MIND missing flag
    chosen: str                         # calibration: raw | linear | platt
    resid: np.ndarray                   # oof residuals (covered rows) for the raw scale
    gap_cov: np.ndarray
    lin_ab: np.ndarray | None = None
    lin_resid: np.ndarray | None = None
    gap_all: np.ndarray | None = None
    platt: object | None = None
    train_fingerprint: str = ""
    n_train: int = 0
    train_rounds: list[str] = field(default_factory=list)
    version: str = FE.VERSION

    def predict(self, te: pd.DataFrame, anchor_te: np.ndarray) -> dict:
        te = te.reset_index(drop=True).copy()
        for c in self.gappy:
            te[FE.MI + c] = te[c].isna().astype(float) if c in te else 1.0
        tag = f"a_{self.anchor}"
        te[tag] = anchor_te
        mu = np.asarray(anchor_te, float) + self.model.predict(te)
        sd_te, _ = A4.scale(self.resid, self.gap_cov, te["gap_q"].values)
        if self.chosen == "raw":
            p = norm.cdf(mu / sd_te)
        elif self.chosen == "linear":
            sd_lin, _ = A4.scale(self.lin_resid, self.gap_all, te["gap_q"].values)
            p = norm.cdf((self.lin_ab[0] + self.lin_ab[1] * mu) / sd_lin)
        else:
            p = self.platt.predict_proba(mu.reshape(-1, 1))[:, 1]
        contrib, cols = self.model.contributions(te)
        return {"mu": mu, "p": p, "half": 1.645 * np.asarray(sd_te, float), "cal": self.chosen, "cfg": self.cfg, "anchor": self.anchor,
                "contrib": contrib, "cols": cols, "te": te, "version": self.version}


def fit(tr: pd.DataFrame, AN_tr: dict, seed: int, lead: int, FS: dict | None = None) -> FrozenFinal:
    """The training half of FE.fit_predict, line for line. AN_tr: {anchor: training-row anchor values}."""
    FS = {k: list(v) for k, v in (FS or H.feature_sets()).items()}
    tr = tr.reset_index(drop=True).copy()
    allc = sorted({c for v in FS.values() for c in v if c in tr.columns})
    gappy = [c for c in allc if tr[c].isna().any() and tr[c].notna().any()]
    for c in gappy:
        tr[FE.MI + c] = tr[c].isna().astype(float)
    FS = {k: list(v) + [FE.MI + c for c in gappy if c in v] for k, v in FS.items()}
    for a in H.ANC:
        tr[f"a_{a}"] = AN_tr[a]
    y, q, w0 = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cache, best = {}, None
    for a, f, pr, h in product(H.ANC, H.FS_KEYS, H.PRUNE, H.HPO):
        tag = f"a_{a}"
        oof = np.full(len(tr), np.nan)
        for j, (i_tr, i_te) in enumerate(folds):
            d = H._with_e(tr.iloc[i_tr].reset_index(drop=True), tag)
            oof[i_te] = AN_tr[a][i_te] + FE.FinalModel(FS[f], h, pr, seed, cache, (j, f, 0), tag).fit(d).predict(tr.iloc[i_te])
        cov = ~np.isnan(oof)
        sse = float(np.sum(w0[cov] * (y[cov] - oof[cov]) ** 2) / cov.sum())
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof, "cov": cov}
    a, f, pr, h = best["cfg"]
    tag = f"a_{a}"
    m = FE.FinalModel(FS[f], h, pr, seed, cache, ("final", f, 0, 0), tag).fit(H._with_e(tr, tag))
    m.cache = None                                                           # selection cache: not needed to predict
    oof, cov = best["oof"], best["cov"]
    yc, qc, gc, oc = y[cov], q[cov], gap[cov], oof[cov]
    sd_, _ = A4.scale(yc - oc, gc, gc)
    inner = {"raw": float(np.mean((norm.cdf(oc / sd_) - qc) ** 2))}
    lin_ab = lin_resid = platt = None
    if cov.all():
        lin, pl = np.zeros(len(tr)), np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w0[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w0[i_tr]), rcond=None)[0]
            lin[i_te] = ab[0] + ab[1] * oof[i_te]
            pl[i_te] = F5.soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
        sdl, _ = A4.scale(y - lin, gap, gap)
        inner["linear"], inner["platt"] = float(np.mean((norm.cdf(lin / sdl) - q) ** 2)), float(np.mean((pl - q) ** 2))
        Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w0)[:, None]
        lin_ab = np.linalg.lstsq(Z, y * np.sqrt(w0), rcond=None)[0]
        lin_resid = y - lin
        platt = F5.soft_platt(oof, q)
    chosen = min(inner, key=inner.get)
    nl, mcs, lam, ne = h[:4]
    cfg = f"{a}|{f}|prune={pr}|leaves={nl},minchild={mcs},lambda={lam},trees={ne}|cal={chosen}|cw=balanced|sel={H.SEL}|rate=lin|miss=mind"
    return FrozenFinal(seed=seed, lead=lead, anchor=a, cfg=cfg, model=m, gappy=gappy, chosen=chosen, resid=yc - oc, gap_cov=gc,
                       lin_ab=lin_ab, lin_resid=lin_resid, gap_all=gap, platt=platt, train_fingerprint=training_fingerprint(tr),
                       n_train=len(tr), train_rounds=sorted(tr["survey"].dropna().unique().tolist()) if "survey" in tr else [])


def save(models: list[FrozenFinal], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    b = pickle.dumps(models, protocol=4)
    path.write_bytes(b)
    return hashlib.sha256(b).hexdigest()


def load(path: Path) -> list[FrozenFinal]:
    return pickle.loads(path.read_bytes())
