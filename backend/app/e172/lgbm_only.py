"""
E172 (EXPLORATORY): LightGBM-only Lead-2 candidates, per docs/e172/PROTOCOL.md. Reads E168/E171 outputs; writes data/e172/out only.

Stage 1 keeps the anchor of E168's best configuration (training score); stage 2 chooses among 32 LightGBM variants (inputs GOV/FULL/
GOV_S x complexity R0-R4 x pooled/lead-exact, plus 5-seed bagging of R0) by the survey-round-aware training-only score of app.e171.
E168's temperature shrink, sd and HIGH line are applied unchanged. E168 itself is re-run inside every job as a reproduction check.

    python -m app.e172.lgbm_only lock
    python -m app.e172.lgbm_only eval     (once)
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GroupKFold

from app.e144 import data as SWSD
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e164 import auto as U
from app.e166 import temperature as T
from app.e168 import lgbm as L
from app.e171 import candidates as C171
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e172" / "out"
LEADS = (1, 2, 3)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
SEEDS1, SEEDS5 = (151,), (151, 152, 153, 154, 155)
R = {"R0": dict(M.PARAMS),
     "R1": dict(M.PARAMS, num_leaves=2, max_depth=1, min_child_samples=20, reg_lambda=10.0),
     "R2": dict(M.PARAMS, num_leaves=3, max_depth=2, min_child_samples=20, reg_lambda=10.0),
     "R3": dict(M.PARAMS, min_child_samples=30, reg_lambda=20.0),
     "R4": dict(M.PARAMS, num_leaves=2, max_depth=1, min_child_samples=40, reg_lambda=20.0, colsample_bytree=0.5)}


class LGB:
    """E168's survey-error LightGBM (app.e151.prov.Res2) with settings P, seeds SEEDS and optional lead-exact training rows."""

    P, SEEDS, EXACT, GRID = R["R0"], SEEDS1, False, [100, 300, 600]

    def __init__(self, cols):
        self.cols = list(cols)

    def _fits(self, n, par, X, y, w):
        return [lgb.LGBMRegressor(n_estimators=n, **par, random_state=s).fit(X, y, sample_weight=w) for s in self.SEEDS]

    def fit(self, d):
        d = d.reset_index(drop=True)
        if self.EXACT:
            b = d[d["lead"] == C171.LEAD_NOW["v"]].reset_index(drop=True)
            if len(b) >= 30 and b["region"].nunique() >= 2:
                d = b
        self.use_ = [c for c in self.cols if d[c].notna().any() and d[c].nunique() > 1]
        par = dict(self.P, monotone_constraints=[Pv.SIGN.get(c, 0) for c in self.use_], monotone_constraints_method="basic")
        par.pop("random_state", None)
        w = 1.0 / (d["se_true"] ** 2 + 0.05)
        best = (np.inf, 100)
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        for n in self.GRID:
            pred = np.zeros(len(d))
            for a, b in folds:
                pred[b] = np.mean([m.predict(d.iloc[b][self.use_]) for m in self._fits(n, par, d.iloc[a][self.use_], d.iloc[a]["e"], w.iloc[a])], axis=0)
            sse = float(np.sum(w * (d["e"] - pred) ** 2))
            if sse < best[0]:
                best = (sse, n)
        self.n_ = best[1]
        self.ms_ = self._fits(self.n_, par, d[self.use_], d["e"], w)
        return self

    def predict(self, X):
        return np.mean([m.predict(X[self.use_]) for m in self.ms_], axis=0)


VARIANTS = {f"G{r}{'X' if ex else 'P'}": type(f"G{r}{'X' if ex else 'P'}", (LGB,), {"P": p, "EXACT": ex}) for r, p in R.items() for ex in (False, True)}
VARIANTS["GR0PB"] = type("GR0PB", (LGB,), {"P": R["R0"], "SEEDS": SEEDS5})
STAGE1 = C171.FAMILIES["E168TA"]


def stage2(anchor):
    m = [(anchor, v, f) for f in ("GOV", "FULL", "GOV_S") for r in R for v in (f"G{r}P", f"G{r}X")]
    return m + [(anchor, "GR0PB", f) for f in ("GOV", "FULL")]


SUBSETS = {"E172": lambda c: True, "POOLED": lambda c: c[1].endswith("P"), "EXACT": lambda c: c[1].endswith("X"),
           "SIMPLE": lambda c: c[1][:3] in ("GR1", "GR2", "GR3", "GR4"), "BAG": lambda c: c[1] == "GR0PB"}


def _install():
    """Register inputs and learners in THIS process (every worker job calls it; see the E169 defect in docs/e171)."""
    C171._install()
    U.LEARNERS.update(VARIANTS)
    assert U.LEARNERS["LGBM"] is Pv.Res2 and U.LEARNERS["GR0PB"].SEEDS == SEEDS5 and "GOV_S" in U.FS


_install()


def score(tr, AN, menu):
    """app.e171.candidates.score_all over `menu` (survey-round-aware, training rows only)."""
    keep = C171.MENU
    C171.MENU = menu
    try:
        return C171.score_all(tr, AN)
    finally:
        C171.MENU = keep


def task(survey, lead, H, SW, mode="main"):
    _install()
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    C171.LEAD_NOW["v"] = lead
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    cut = Pn.q_start(i)
    sw = SWSD.sws_quarterly()
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
        sw = T.corrupt_sws(sw, cut)
        SW = L.sws_forecasts(sw, i)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = C171.add_sws(E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H), sw).reset_index(drop=True)
    if te.empty:
        return None
    tr = C171.add_sws(E154.add_income(Pv.add_inputs(S, P.tr), H), sw).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    o = te[KEY].copy()
    o["mode"] = mode
    e168_tag = None
    if mode == "main":
        r8 = L.forecast(tr, te, AN, SW, cut, lead)
        o["mu_R168"], o["R168"] = r8["s"], r8["ps"]
        e168_tag = r8["tag"]
    scheme, msk, res1 = score(tr, AN, STAGE1)
    anchor = min(STAGE1, key=lambda c: res1[c]["sse"])[0]
    menu2 = stage2(anchor)
    _, _, res2 = score(tr, AN, menu2)
    res = {**res1, **res2}
    subsets = SUBSETS if mode == "main" else {"E172": SUBSETS["E172"]}
    for name, keep in subsets.items():
        r = C171.finalize(tr, te, AN, SW, cut, lead, scheme, msk, res, [c for c in menu2 if keep(c)])
        o[f"mu_{name}"], o[name], o[f"half_{name}"], o[f"tag_{name}"], o[f"lam_{name}"] = r["mu"], r["p"], r["half"], r["tag"], r["lam"]
    o["scheme"], o["anchor"], o["train_rounds"] = scheme, anchor, int(tr["survey"].nunique())
    scores = {"|".join(c): round(v["sse"], 4) for c, v in res.items()}
    if e168_tag:
        a, l_, f, _cal = e168_tag.split("|")
        scores["E168_chosen"] = round(res1[(a, l_, f)]["sse"], 4)
    o["train_scores"] = json.dumps(scores)
    return o


# ------------------------------------------------------------------ lock / eval
CODE = [BACKEND_DIR / "app" / "e172" / "lgbm_only.py", BACKEND_DIR / "app" / "e172" / "score.py", BACKEND_DIR / "app" / "e171" / "candidates.py", BACKEND_DIR / "app" / "e168" / "lgbm.py",
        BACKEND_DIR / "app" / "e166" / "temperature.py", BACKEND_DIR / "app" / "e151" / "prov.py", BACKEND_DIR.parent / "docs" / "e172" / "PROTOCOL.md"]
INPUTS = [D / "e168" / "out" / "oof.csv", D / "e171" / "out" / "oof.csv", D / "fi5" / "raw" / "sws" / "sws_area_rounds_full.csv"]
FILES = CODE + INPUTS


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p):
    return str(p.relative_to(BACKEND_DIR.parent)).replace("\\", "/")


def lock():
    miss = [str(p) for p in FILES if not p.exists()]
    if miss:
        sys.exit("missing files, nothing locked:\n  " + "\n  ".join(miss))
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "lock.json").exists():
        sys.exit("already locked")
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {_rel(p): _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _check():
    lk = OUT / "lock.json"
    if not lk.exists():
        sys.exit("not locked")
    h = json.loads(lk.read_text())["hashes"]
    bad = [p.name for p in FILES if h.get(_rel(p)) != _sha(p)]
    if bad:
        sys.exit(f"changed since lock: {bad}")
    if (OUT / "oof.csv").exists():
        sys.exit("E172 has already run once.")


def evaluate():
    _check()
    H = E154.income()
    SW = L.sws_forecasts(SWSD.sws_quarterly(), max(M8.RQ[s] - 1 for s in SURVEYS))
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, h, "corrupt") for s in SURVEYS for h in (1, 2)]
    Rr = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, SW, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(Rr, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    main = Al[Al["mode"] == "main"].drop(columns=["mode"])
    F = pd.read_csv(D / "e168" / "out" / "oof.csv").rename(columns={"L": "E168", "mu_L": "mu_E168", "half_L": "half_E168"})
    F = F[F["lead"].isin(LEADS)].drop(columns=[c for c in ("tag", "lam_y", "src", "la", "lb", "nb", "rounds") if c in F])
    e1 = pd.read_csv(D / "e171" / "out" / "oof.csv")[KEY + ["E171", "mu_E171", "half_E171"]]
    F = F.merge(e1, on=KEY, how="left").merge(main.drop(columns=["train_scores"]), on=KEY, how="inner")
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    print("forecasts written; scoring with app.e172.score")


if __name__ == "__main__":
    {"lock": lock, "eval": evaluate}[sys.argv[1]]()
