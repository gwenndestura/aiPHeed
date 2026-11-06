"""
E169: E168 with seed-bagged LightGBM (mean of 5 fixed seeds, 151-155), per docs/e169/PROTOCOL.md. Nothing else changes.

E168 (unchanged otherwise): E166 (AUTO + temperature shrink) with the learner fixed to LightGBM, per docs/e168/PROTOCOL.md.

Menu: 4 survey anchors x LightGBM (app.e151.prov.Res2, the E151/E158 settings) x 2 input sets = 8 configurations, chosen
by AUTO's training-only inner score; AUTO's identity-or-linear calibration; E166's temperature shrink with the SWS
out-of-time forecasts made by LightGBM (app.e151.sws.PAR) instead of ElasticNet. Everything else is E166's code.

    python -m app.e169.bag lock    hash code, protocol and inputs
    python -m app.e169.bag eval    once; refuses if not locked, if anything changed, or if it already ran
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
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e144 import data as SWSD
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e151 import sws as SWS151
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e164 import auto as U
from app.e166 import temperature as T
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e169" / "out"
SEEDS = (151, 152, 153, 154, 155)
LEADS = range(1, 9)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
MENU = [(a, "LGBM", f) for a in U.ANCH for f in ("GOV", "FULL")]
BASELINES = ("E168", "E166", "AUTO", "E158", "GNT", "GOV", "NEWS", "LR", "LR_GOV", "LR_NEWS", "PSA", "PERS", "ANCHOR")
CODE = [BACKEND_DIR / "app" / "e169" / "bag.py", BACKEND_DIR / "app" / "e151" / "prov.py", BACKEND_DIR / "app" / "e166" / "temperature.py", BACKEND_DIR.parent / "docs" / "e169" / "PROTOCOL.md"]
INPUTS = [D / "e168" / "out" / "oof.csv", D / "e166" / "out" / "oof.csv", D / "e166" / "out" / "objectives" / "baseline_lr_gov.csv", D / "e164" / "out" / "oof.csv",
          D / "e158" / "out" / "oof.csv", D / "e151" / "out" / "prov_oof.csv", E154.RAW / "regional_income_long.csv",
          D / "e147" / "raw" / "sealed_2021_labels.csv", D / "e147" / "raw" / "heatmap_provincial.jsonl", D / "fi5" / "raw" / "sws" / "sws_area_rounds_full.csv"]
FILES = CODE + INPUTS


class Bag(Pv.Res2):
    """app.e151.prov.Res2 with every LightGBM fit replaced by the mean of the same fit over SEEDS (seed bagging)."""

    def _fit(self, n, par, X, y, w):
        return [lgb.LGBMRegressor(n_estimators=n, **par, random_state=s).fit(X, y, sample_weight=w) for s in SEEDS]

    def fit(self, d):
        d = d.reset_index(drop=True)
        self.use_ = [c for c in self.cols if d[c].notna().any() and d[c].nunique() > 1]
        par = dict(M.PARAMS, monotone_constraints=[Pv.SIGN.get(c, 0) for c in self.use_], monotone_constraints_method="basic")
        par.pop("random_state", None)
        w = 1.0 / (d["se_true"] ** 2 + 0.05)
        best = (np.inf, 100, None)
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        for n in self.GRID:
            pred = np.zeros(len(d))
            for a, b in folds:
                ms = self._fit(n, par, d.iloc[a][self.use_], d.iloc[a]["e"], w.iloc[a])
                pred[b] = np.mean([m.predict(d.iloc[b][self.use_]) for m in ms], axis=0)
            sse = float(np.sum(w * (d["e"] - pred) ** 2))
            if sse < best[0]:
                best = (sse, n, (d["e"] - pred).values)
        self.n_, self.oof_ = best[1], best[2]
        self.gap_ = d["gap_q"].values.astype(float)
        self.ms_ = self._fit(self.n_, par, d[self.use_], d["e"], w)
        self.m_ = self.ms_[0]
        return self

    def predict(self, X):
        return np.mean([m.predict(X[self.use_]) for m in self.ms_], axis=0)

    def contrib(self, X):
        """Exact additive contributions of the bagged model: the mean of each seed's pred_contrib."""
        return np.mean([m.booster_.predict(X[self.use_], pred_contrib=True) for m in self.ms_], axis=0)


U.LEARNERS["LGBM"] = Bag          # every LightGBM fit in this process (selection, lambda rounds) is the bagged one


def procedure(tr, te, AN):
    """app.e164.auto.run_procedure restricted to MENU (LightGBM only); returns mu, tag, the chosen configuration's OOF, y, w."""
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    res = []
    for a, l, f in MENU:
        atr, ate = AN[a]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            d = tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])
            oof[i_te] = atr[i_te] + U.LEARNERS[l](U.FS[f]).fit(d).predict(tr.iloc[i_te])
        sse_id = float(np.sum(w * (y - oof) ** 2))
        cal = np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
            cal[i_te] = ab[0] + ab[1] * oof[i_te]
        sse_cal = float(np.sum(w * (y - cal) ** 2))
        res.append({"cfg": (a, l, f), "sse": min(sse_id, sse_cal), "calib": sse_cal < sse_id, "oof": cal if sse_cal < sse_id else oof, "oof_id": oof})
    best = min(res, key=lambda r: r["sse"])
    a, l, f = best["cfg"]
    atr, ate = AN[a]
    mu = ate + U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - atr)).predict(te)
    if best["calib"]:
        Z = np.column_stack([np.ones(len(tr)), best["oof_id"]]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
        mu = ab[0] + ab[1] * mu
    return np.asarray(mu, float), f"{a}|{l}|{f}|{'cal' if best['calib'] else 'id'}", best["oof"], y, w


def sws_forecasts(s: pd.DataFrame, last_issue: int) -> pd.DataFrame:
    """E168's SWS out-of-time LightGBM forecasts, each the mean of 5 seeds."""
    A = T.sws_area_table(s)
    out = []
    for qs in range(T.SWS_FIRST_ISSUE, last_issue + 1):
        cut = Pn.q_start(qs)
        tr = A[A["dy"].notna() & (A["published"] < cut)]
        te = A[(A["qi"] == qs) & A["dy"].notna()]
        if len(tr) < T.SWS_MIN_TRAIN or te.empty:
            continue
        p = np.mean([lgb.LGBMRegressor(**SWS151.PAR, random_state=s).fit(tr[T.SWS_COLS], tr["dy"]).predict(te[T.SWS_COLS]) for s in SEEDS], axis=0)
        out.append(pd.DataFrame({"area": te["area"].values, "issue": qs, "issue_start": cut, "lead": te["lead"].values, "published": te["published"].values,
                                 "f": te["sws_last"].values + p, "y": te["sws_last"].values + te["dy"].values}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["area", "issue", "issue_start", "lead", "published", "f", "y"])


def forecast(tr, te, AN, SW, cut, lead):
    """app.e166.temperature.forecast with the LightGBM-only procedure."""
    mu, tag, oof, y, _w = procedure(tr, te, AN)
    gtr, gte = tr["gap_q"].values, te["gap_q"].values
    sd, half = U.scale(y - oof, gtr, gte)
    la, va, n_rounds = T.lam_round_heldout(tr, AN, tag)
    lb, vb, nb, kb = T.lam_sws(SW, cut, lead)
    lam, src = T.combine(la, va, lb, vb)
    sd_l, half_l = U.scale(y - lam * oof, gtr, gte)
    s, ps, cls = T.apply_lambda(mu, sd_l, lam)
    return {"mu": mu, "p": norm.cdf(mu / sd), "s": s, "ps": ps, "half": half_l, "cls": cls, "tag": tag, "lam": lam, "src": src,
            "la": la, "lb": lb, "nb": nb, "rounds": n_rounds}


def task(survey, lead, H, SW, mode="main"):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    cut = Pn.q_start(i)
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
        SW = sws_forecasts(T.corrupt_sws(SWSD.sws_quarterly(), cut), i)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    r = forecast(tr, te, AN, SW, cut, lead)
    o = te[KEY].copy()
    o["mode"] = mode
    o["mu_L"], o["L"], o["half_L"] = r["s"], r["ps"], r["half"]
    for k in ("tag", "lam", "src", "la", "lb", "nb", "rounds"):
        o[k] = r[k]
    return o


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p):
    return str(p.relative_to(BACKEND_DIR.parent)).replace("\\", "/")


def _preflight():
    miss = [str(p) for p in FILES if not p.exists()]
    if miss:
        sys.exit("missing files, nothing locked:\n  " + "\n  ".join(miss))


def lock():
    _preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "lock.json").exists():
        sys.exit("already locked: one locked run only (docs/e169/PROTOCOL.md)")
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {_rel(p): _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _check_lock():
    lk = OUT / "lock.json"
    if not lk.exists():
        sys.exit("not locked")
    h = json.loads(lk.read_text())["hashes"]
    bad = [p.name for p in FILES if h.get(_rel(p)) != _sha(p)]
    if bad:
        sys.exit(f"changed since lock: {bad}. The locked run is void.")
    if (OUT / "results.json").exists():
        sys.exit("E169 has already run once. Re-running is not allowed by the protocol.")


def cls(g, a):
    from sklearn.metrics import roc_auc_score
    y, p = g["y_high"].values == 1, g[a].values >= .5
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    prec, hr, lr = tp / max(1, tp + fp), tp / max(1, tp + fn), tn / max(1, tn + fp)
    return {"correct": tp + tn, "accuracy": round((tp + tn) / len(g), 3), "precision": round(prec, 3), "high_recall": round(hr, 3), "low_recall": round(lr, 3),
            "f1": round(2 * prec * hr / max(1e-9, prec + hr), 3), "auc": round(float(roc_auc_score(y, g[a])), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4)}


def evaluate():
    _preflight()
    _check_lock()
    H = E154.income()
    SW = sws_forecasts(SWSD.sws_quarterly(), max(M8.RQ[s] - 1 for s in SURVEYS))
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, 1, "corrupt") for s in SURVEYS]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, SW, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    main, cor = Al[Al["mode"] == "main"].drop(columns="mode"), Al[Al["mode"] == "corrupt"]
    F = pd.read_csv(D / "e168" / "out" / "oof.csv").rename(columns={"L": "E168", "mu_L": "mu_E168", "half_L": "half_E168"})
    F = F.drop(columns=[c for c in ("tag", "lam", "src", "la", "lb", "nb", "rounds") if c in F]).merge(main, on=KEY, how="inner")
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    x1 = F[F["lead"] == 1].reset_index(drop=True)
    lk = x1[KEY + ["mu_L", "L"]].merge(cor[KEY + ["mu_L", "L"]], on=KEY, suffixes=("", "_c"))
    leak = float(max(np.max(np.abs(lk["mu_L"] - lk["mu_L_c"])), np.max(np.abs(lk["L"] - lk["L_c"]))))
    void = bool(leak >= 1e-9 or len(lk) != len(x1))
    rel = LD.evaluate(F, "L", "L")
    l1 = next(r for r in rel["leads"] if r["lead"] == 1)
    l2 = next(r for r in rel["leads"] if r["lead"] == 2)
    rng = np.random.default_rng(169)
    comp = {}
    for b in BASELINES:
        if b in x1 and x1[b].notna().all():
            d = E7.diff_ci(x1, "L", b, "q_true", rng, n=2000)
            comp[b] = {"metrics": cls(x1, b), "E169_minus_brier": {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}}
    calib = {int(L): T.cal_ci(g.reset_index(drop=True).rename(columns={"mu_L": "mu_L"}), "L") for L, g in F.groupby("lead")}
    cfg = main.groupby(["survey", "lead"])[["tag", "lam", "src", "la", "lb", "nb", "rounds"]].first().reset_index().to_dict("records")
    decision = {"leakage_max_abs_change": leak, "void": void, "lead1_correct": int(l1["confusion"]["tp"] + l1["confusion"]["tn"]),
                "lead1_criteria": {k: bool(v) for k, v in l1["criteria"].items()}, "max_reliable_lead": rel["maximum_reliable_lead"],
                "lead2_criteria": {k: bool(v) for k, v in l2["criteria"].items()},
                "becomes_thesis_model": bool(all(l1["criteria"].values()) and all(l2["criteria"].values()) and not void)}
    out = {"model": "E169: E168 with seed-bagged LightGBM (5 seeds)", "decision": decision, "config_by_issue": cfg, "reliability": rel,
           "calibration": calib, "lead1_vs": comp, "lead1_bands": T.bands(x1, "L")}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(pd.DataFrame(cfg).to_string(index=False))
    for r in rel["leads"]:
        print("lead", r["lead"], r["rows"], r["accuracy"], r["precision"], r["high_recall"], r["f1"], r["auc"], r["brier_soft"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()})
    print("lead1 vs:", json.dumps({b: [v["metrics"]["accuracy"], v["metrics"]["f1"], v["metrics"]["auc"], v["E169_minus_brier"]] for b, v in comp.items()}))


if __name__ == "__main__":
    {"lock": lock, "eval": evaluate}[sys.argv[1]]()
