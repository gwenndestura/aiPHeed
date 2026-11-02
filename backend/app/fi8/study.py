"""FI8 persistence-correction study.

    python -m app.fi8.study run

Diagnostic that motivated it (docs/fi8): on walk-forward damped-persistence errors, news-reported displacement in
CALABARZON (FI6-N `na_displaced`) has Spearman rho 0.48 (p = 0.001, n = 44) at the next quarter; world/domestic rice
prices rho ~0.2 (p ~0.08-0.10); 23 indicators tested.

Candidates (registered before running; judged against the STRONGEST baselines, damped and naive persistence):
  C1  damped + lasso correction, inputs selected inside each training window from all 23 government/news indicators
  C2  as C1 with ridge (no selection, strong shrinkage)
  U1  UPPER BOUND ONLY: damped + correction on the 3 indicators picked by the full-sample diagnostic (selection used
      the test quarters, so it is optimistic and can never be adopted)
Adoption: next-quarter mean Brier change < 0 against BOTH damped and naive persistence with block-bootstrap
P(change < 0) >= 0.90, and no worse than +0.005 at the current quarter or two quarters ahead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Lasso, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi5.target import qindex
from app.fi6.features import GOV
from app.fi6.news_model import NEWSA
from app.fi7 import models as M7
from app.fi7.design import Designer
from app.fi7.experiments import EVAL_FIRST, FINAL_SPECS, compare, reliability, scores
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "fi8"
OUT.mkdir(parents=True, exist_ok=True)
CANDIDATES = GOV + NEWSA + ["world_rice_yoy", "world_rice_3m", "world_urea_yoy", "tc_max_wind_q", "underemp_yoy", "fish_yoy"]
DIAG_PICKED = ["na_displaced", "world_rice_yoy", "cpi_rice_yoy"]


class DampedCorrection:
    """level = damped anchor + linear correction of the anchor's error; sigma from expanding inner folds."""

    def __init__(self, features, kind: str = "lasso"):
        self.features, self.kind = features, kind

    def _make(self, a):
        reg = Lasso(alpha=a, max_iter=20000) if self.kind == "lasso" else Ridge(alpha=a)
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), reg)

    def fit(self, X, delta):
        self.anchor = M7.Damped().fit(X, delta)
        resid = X["hunger_target"].to_numpy(float) - self.anchor.predict_level(X)
        self.cols = [c for c in self.features if X[c].notna().sum() >= 10 and X[c].nunique() > 1]
        grid = [0.05, 0.1, 0.2, 0.4, 0.8] if self.kind == "lasso" else [10.0, 30.0, 100.0, 300.0]
        best = None
        if not M7._folds(len(resid)):          # too few rows for inner folds: middle penalty, in-sample spread
            best = (grid[len(grid) // 2], float(np.var(resid, ddof=1)))
            grid = []
        for a in grid:
            errs = []
            for lo, hi in M7._folds(len(resid)):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = self._make(a).fit(X.iloc[:lo][self.cols], resid[:lo])
                errs.append(resid[lo:hi] - m.predict(X.iloc[lo:hi][self.cols]))
            e = np.concatenate(errs)
            if best is None or np.mean(e ** 2) < best[1]:
                best = (a, float(np.mean(e ** 2)))
        self.alpha = best[0]
        self.sigma = max(np.sqrt(best[1]), M7.M6.SIGMA_FLOOR)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.est = self._make(self.alpha).fit(X[self.cols], resid)
        coef = self.est[-1].coef_
        self.selected = [c for c, w in zip(self.cols, coef) if abs(w) > 1e-9]
        self.choice = f"alpha={self.alpha}; selected={len(self.selected)}"
        return self

    def predict_level(self, X):
        return self.anchor.predict_level(X) + self.est.predict(X[self.cols])

    def predict_delta(self, X):
        return self.predict_level(X) - X["hunger_last"].to_numpy(float)

    def predict_proba(self, X):
        return M7._prob(self.predict_level(X), X["threshold_known"], self.sigma)


SPECS = {
    "C1 damped + lasso correction (in-window selection)": ("lasso", CANDIDATES),
    "C2 damped + ridge correction": ("ridge", CANDIDATES),
    "U1 UPPER BOUND: damped + diagnostic-picked inputs": ("ridge", DIAG_PICKED),
}


def _task(args):
    tag, kind, feats, lead, X, chunk = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST)].iloc[chunk[0]::chunk[1]]
    rows = []
    for i, r in ev.iterrows():
        tr = L[(L["target_published"] <= r["issue_ts"]) & L["baseline_known"].notna()]
        m = M7.Thresholded(lambda: DampedCorrection(feats, kind)).fit(tr, tr["delta_target"].to_numpy(float))
        te = L.loc[[i]]
        p = float(m.predict_proba(te)[0])
        rows.append({"tag": tag, "lead": lead, "issue_date": r["issue_date"], "target_quarter": r["target_quarter"],
                     "y": int(r["y"]), "p": p, "cls": int(m.predict_class(te)[0]), "p_flip": r["p_flip"], "n_train": int(len(tr)),
                     "train_acc": float(((m.predict_proba(tr) >= m.tau) == tr["y"]).mean()),
                     "config": f"{m.inner.choice}; tau={m.tau:.2f}", "selected": "|".join(m.inner.selected)})
    return rows


def run() -> dict:
    lock = {"specs": {k: [v[0], v[1]] for k, v in SPECS.items()},
            "code_sha256": hashlib.sha256(open(__file__, "rb").read().replace(b"\r\n", b"\n")).hexdigest()}
    (OUT / "STUDY_LOCK.json").write_text(json.dumps(lock, indent=1))
    D = Designer("operational")
    designs = {h: D.frame(h) for h in [0, 1, 2, 3]}
    tasks = [(tag, kind, feats, h, designs[h], (c, 3)) for tag, (kind, feats) in SPECS.items() for h in designs for c in range(3)]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        new = pd.DataFrame([r for part in ex.map(_task, tasks) for r in part])
    base = pd.read_csv(BACKEND_DIR / "data" / "fi7" / "out" / "final_predictions.csv")
    pr = pd.concat([base, new], ignore_index=True)
    pr.to_csv(OUT / "study_predictions.csv", index=False, lineterminator="\n")
    res = {"by_lead": {}, "adoption": {}}
    for h in [0, 1, 2, 3]:
        g = pr[pr["lead"] == h]
        clim = g[g["tag"] == "Always LOW (reference)"]
        cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
        res["by_lead"][h] = {}
        for tag in list(FINAL_SPECS) + list(SPECS):
            s = scores(g[g["tag"] == tag])
            s["reliability"] = reliability(s, cb)
            res["by_lead"][h][tag] = s
    for tag in SPECS:
        c_d = compare(pr, tag, "Damped persistence (statistical)")
        c_n = compare(pr, tag, "Naive persistence (latest reading)")
        ok = all(c[1]["mean"] < 0 and c[1]["p_negative"] >= 0.90 for c in (c_d, c_n)) and \
            all(c_d.get(h, {"mean": 0})["mean"] <= 0.005 for h in (0, 2))
        sel = new[(new["tag"] == tag) & (new["lead"] == 1)]["selected"].str.split("|").explode()
        res["adoption"][tag] = {"vs_damped": c_d, "vs_naive": c_n, "adopt": bool(ok) and not tag.startswith("U1"),
                                "selection_frequency_h1": sel[sel != ""].value_counts().to_dict()}
    (OUT / "study_results.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    a = ap.parse_args()
    r = run()
    for tag, v in r["adoption"].items():
        print(tag, "adopt" if v["adopt"] else "reject", {h: round(x["mean"], 4) for h, x in v["vs_damped"].items()},
              {h: round(x["p_negative"], 2) for h, x in v["vs_damped"].items()}, list(v["selection_frequency_h1"].items())[:5])
