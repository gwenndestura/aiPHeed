"""
E191 (docs/e191/PROTOCOL.md): exhaustive synthetic-data search with fully nested (per-job, training-only) selection.
Local only.

    python -m app.e191.run all        frames -> nested jobs -> shuffle control -> evaluation
"""
from __future__ import annotations

import json
import math
import pickle
import sys
import time
import warnings
from itertools import combinations

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest, norm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import augment as A
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e182 import candidate as C182
from app.e184 import candidate as C184
from app.e191 import gens as GN

warnings.filterwarnings("ignore")
OUT = K.D / "e191" / "out"
FR = OUT / "frames"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e191" / "PROTOCOL.md"
SEEDS = T.SEEDS
RATIOS = (0.111, 0.25, 0.429, 0.667, 1.5, 2.333, 4.0)
LEADS = (1, 2, 3, 4, 5, 6)
N_JOBS = RT.N_JOBS


# ------------------------------------------------------------------------------------------------ models
def _use(cols, d, prune):
    use = [c for c in cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
    if prune and len(use) > 1:
        R = d[use].rank().corr().abs()
        keep = []
        for c in use:
            if all(not (R.at[c, k] > 0.95) for k in keep):
                keep.append(c)
        use = keep
    return use


class LGBW(RT.LGBResAug):
    """E184's model; with weight multipliers (class weights) when given. Without them it is LGBResAug exactly."""

    def fit(self, d, syn=None, md=None, ms=None):
        if md is None and ms is None:
            return super().fit(d, syn)
        use = _use(self.cols, d, self.prune)
        self.use_ = use
        X, e = d[use], d["e"].values
        w = (1.0 if md is None else md) / (d["se_true"].values ** 2 + 0.05)
        if syn is not None and len(syn):
            X = pd.concat([X, syn[use]], ignore_index=True)
            e = np.r_[e, syn["e"].values]
            w = np.r_[w, self.syn_weight * (1.0 if ms is None else ms) / (syn["se_true"].values ** 2 + 0.05)]
        self.m_ = lgb.LGBMRegressor(**RT._params(self, use)).fit(X, e, sample_weight=w)
        return self


class SkW:
    """Ridge / random forest / CatBoost on the change from the anchor (E189's SkRes, with CatBoost and weights)."""

    def __init__(self, cols, kind, par, prune):
        self.cols, self.kind, self.par, self.prune, self.syn_weight = list(cols), kind, par, prune, 1.0

    def _X(self, d):
        X = d[self.use_].astype(float)
        if self.kind == "cat":
            return X.values
        X = X.fillna(self.med_)
        return ((X - self.mu_) / self.sd_).values if self.kind == "ridge" else X.values

    def fit(self, d, syn=None, md=None, ms=None):
        self.use_ = _use(self.cols, d, self.prune)
        R = d[self.use_].astype(float)
        self.med_ = R.median()
        self.mu_, self.sd_ = R.fillna(self.med_).mean(), R.fillna(self.med_).std().replace(0, 1.0).fillna(1.0)
        X, e = self._X(d), d["e"].values
        w = (1.0 if md is None else md) / (d["se_true"].values ** 2 + 0.05)
        if syn is not None and len(syn):
            X = np.vstack([X, self._X(syn)])
            e = np.r_[e, syn["e"].values]
            w = np.r_[w, self.syn_weight * (1.0 if ms is None else ms) / (syn["se_true"].values ** 2 + 0.05)]
        if self.kind == "ridge":
            self.m_ = Ridge(alpha=self.par).fit(X, e, sample_weight=w)
        elif self.kind == "rf":
            self.m_ = RandomForestRegressor(n_estimators=300, min_samples_leaf=self.par, max_features=0.33, random_state=191, n_jobs=1).fit(X, e, sample_weight=w)
        else:
            from catboost import CatBoostRegressor
            self.m_ = CatBoostRegressor(depth=self.par, iterations=400, learning_rate=0.03, l2_leaf_reg=3.0, random_seed=191,
                                        verbose=0, thread_count=1, allow_writing_files=False).fit(X, e, sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(self._X(X))


def make_model(cfg, model):
    a, f, pr, h = cfg
    if model[0] == "lgb":
        m = LGBW(E.FS[f], *h, pr)
    else:
        m = SkW(E.FS[f], model[0], model[1], pr)
    m.syn_weight = 1.0
    return m


# ------------------------------------------------------------------------------------------------ one configuration
def fit_set(real, an, spec, seed, stream, fold, cfg, cols):
    """(real fit rows, synthetic rows, synthetic anchors, real multipliers, synthetic multipliers, info)."""
    info = {}
    rf = real
    if spec.get("under"):
        hi = real["y_true"].values >= 0
        n1, n0 = int(hi.sum()), int((~hi).sum())
        maj = 1 if n1 > n0 else 0
        rng = GN.rng_for(seed, stream, fold, "under", 0)
        idx_maj = np.flatnonzero(hi == bool(maj))
        drop = rng.choice(idx_maj, size=abs(n1 - n0), replace=False) if n1 != n0 else np.empty(0, int)
        keep = np.setdiff1d(np.arange(len(real)), drop)
        rf = real.iloc[keep].reset_index(drop=True)
        an = {a: np.asarray(v)[keep] for a, v in an.items()}
    syns, sas = [], []
    for g, r in spec.get("gens", []):
        if g == "e184":
            s = ("jitter", r, 1.0, 0.5, "boundary")
            syn, sa = T._augment(rf, an, s, seed, stream, fold)[:2]
        else:
            syn, sa, inf = GN.generate(g, rf, an, int(round(r * len(rf))), GN.rng_for(seed, stream, fold, g, r), cols, {"cfg": cfg})
            info[g] = inf
        if syn is not None and len(syn):
            syns.append(syn.reset_index(drop=True))
            sas.append(sa)
    syn = pd.concat(syns, ignore_index=True) if syns else None
    sa = {a: np.concatenate([s[a] for s in sas]) for a in E.ANCH} if sas else None
    md = ms = None
    if spec.get("cw"):
        hi = rf["y_true"].values >= 0
        n, n1 = len(hi), int(hi.sum())
        f1, f0 = n / (2 * max(1, n1)), n / (2 * max(1, n - n1))
        md = np.where(hi, f1, f0)
        ms = None if syn is None else np.where(syn["y_true"].values >= 0, f1, f0)
    return rf, an, syn, sa, md, ms, info


def run_cfg(tr, te, AN, folds, cfg, spec, seed, stream, model=("lgb", None), want_quality=False):
    a, f, pr, h = cfg
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    atr, ate = AN[a]
    an_all = {x: np.asarray(AN[x][0], float) for x in E.ANCH}
    cols = A.feature_columns(tr)
    oof = np.zeros(len(tr))
    for fi, (i_tr, i_te) in enumerate(folds):
        real = tr.iloc[i_tr].reset_index(drop=True)
        rf, an, syn, sa, md, ms, _ = fit_set(real, {x: v[i_tr] for x, v in an_all.items()}, spec, seed, stream, fi, cfg, cols)
        m = make_model(cfg, model)
        m.fit(rf.assign(e=rf["y_true"].values - an[a]), None if syn is None else syn.assign(e=syn["y_true"].values - sa[a]), md, ms)
        oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])
    rf, an, syn, sa, md, ms, info = fit_set(tr, an_all, spec, seed, stream, "final", cfg, cols)
    m = make_model(cfg, model)
    m.fit(rf.assign(e=rf["y_true"].values - an[a]), None if syn is None else syn.assign(e=syn["y_true"].values - sa[a]), md, ms)
    P, chosen, _ = RT._calibrate(tr, te, folds, oof, ate + m.predict(te), y, q, w, gap)
    qual = GN.quality(tr, syn, cols) if want_quality else None
    if want_quality and qual is not None:
        qual["fallback"] = int(sum(v.get("fallback", 0) for v in info.values()))
    return P[chosen], oof, chosen, qual


# ------------------------------------------------------------------------------------------------ frames
def _frame(survey, lead, mode):
    p = FR / f"{survey}_L{lead}_{mode}.pkl"
    if not p.exists():
        H, L, S_P = K.pipeline_inputs()
        tr, te, AN = RT.build(survey, lead, H, L, S_P, mode)
        with open(p, "wb") as fh:
            pickle.dump((tr.reset_index(drop=True), te.reset_index(drop=True), AN), fh)
    return str(p)


def load(p):
    with open(p, "rb") as fh:
        return pickle.load(fh)


def same_train(a, b):
    (t1, _, A1), (t2, _, A2) = a, b
    if t1.shape != t2.shape or not t1.equals(t2):
        return False
    return all(np.array_equal(np.asarray(A1[k][0], float), np.asarray(A2[k][0], float), equal_nan=True) for k in A1)


def groups():
    G = []
    for s in RT.SURVEYS:
        fr = {l: load(FR / f"{s}_L{l}_main.pkl") for l in LEADS}
        gs = []
        for l in LEADS:
            for g in gs:
                if same_train(fr[g[0]], fr[l]):
                    g.append(l)
                    break
            else:
                gs.append([l])
        G += [(s, g) for g in gs]
    return G


def stacked(survey, leads, mode="main"):
    fr = [load(FR / f"{survey}_L{l}_{mode}.pkl") for l in leads]
    tr = fr[0][0]
    te = pd.concat([f[1] for f in fr], ignore_index=True)
    AN = {k: (fr[0][2][k][0], np.concatenate([np.asarray(f[2][k][1], float) for f in fr])) for k in fr[0][2]}
    return tr, te, AN


# ------------------------------------------------------------------------------------------------ nested job
def spec_of(name, r=1.0):
    if name == "none":
        return {"gens": []}
    if name == "undersample":
        return {"gens": [], "under": True}
    if name == "classw":
        return {"gens": [], "cw": True}
    if name == "hybrid":
        return {"gens": [("e184", r)], "cw": True}
    return {"gens": [(name, r)]}


def job(survey, leads):
    t0 = time.time()
    tr, te, AN = stacked(survey, leads)
    assert "is_synthetic" not in te.columns
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, leads[0], "main")
    reg = tr["region"].values
    R, Q = {}, []

    def ev(cid, spec, stage, family, model=("lgb", None)):
        det = (not spec.get("gens")) and not spec.get("under")
        seeds = SEEDS[:1] if det else SEEDS
        runs, oofs = [], []
        for k, s in enumerate(seeds):
            P, oof, ch, qual = run_cfg(tr, te, AN, folds, cfg, spec, s, stream, model, want_quality=(k == 0 and stage == 2))
            runs.append(P)
            oofs.append(oof)
            if qual:
                Q.append({"job": stream, "cid": cid, **qual})
        oofm = np.mean(oofs, axis=0)
        loss = w * (y - oofm) ** 2
        R[cid] = {"spec": spec, "stage": stage, "family": family, "model": model, "sse": float(loss.sum()), "loss": loss,
                  "te": tuple(np.mean([np.asarray(r[k], float) for r in runs], axis=0) for k in range(3)),
                  "seeds_p": [np.asarray(r[1], float) for r in runs]}
        return R[cid]["sse"]

    # Stage 2
    for g in GN.STAGE2:
        ev(g, spec_of(g), 2, GN.FAMILY[g])
    ratio_ok = [g for g in GN.STAGE2 if R[g]["spec"].get("gens")]
    top3 = sorted(ratio_ok, key=lambda g: R[g]["sse"])[:3]
    # Stage 3
    best_r = {}
    for g in top3:
        for r in RATIOS:
            ev(f"{g}@{r:g}", spec_of(g, r), 3, GN.FAMILY[g])
        cand = {1.0: R[g]["sse"], **{r: R[f"{g}@{r:g}"]["sse"] for r in RATIOS}}
        best_r[g] = min(cand, key=cand.get)
    # Stage 4
    for g1, g2 in combinations(top3, 2):
        if g1 == "hybrid" and g2 == "e184" or g2 == "hybrid" and g1 == "e184":
            continue
        r = best_r[g1] if min(R[g1]["sse"], R.get(f"{g1}@{best_r[g1]:g}", R[g1])["sse"]) <= min(R[g2]["sse"], R.get(f"{g2}@{best_r[g2]:g}", R[g2])["sse"]) else best_r[g2]
        s1, s2 = spec_of(g1), spec_of(g2)
        spec = {"gens": [(s1["gens"][0][0], r / 2), (s2["gens"][0][0], r / 2)], "cw": bool(s1.get("cw") or s2.get("cw"))}
        ev(f"{g1}+{g2}@{r:g}", spec, 4, "combination")
    # Stage 5: model interaction for the best configuration so far
    best = min((c for c in R if c != "none"), key=lambda c: R[c]["sse"])
    a, f, pr, h = cfg
    atr = AN[a][0]
    for kind, grid in (("ridge", (1.0, 10.0, 100.0)), ("rf", (5, 20)), ("cat", (4, 6))):
        scores = {}
        for par in grid:
            oof = np.zeros(len(tr))
            for i_tr, i_te in folds:
                m = SkW(E.FS[f], kind, par, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr]))
                oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])
            scores[par] = float(np.sum(w * (y - oof) ** 2))
        par = min(scores, key=scores.get)
        ev(f"{best}|{kind}{par:g}", R[best]["spec"], 5, R[best]["family"], (kind, par))
    # Stage 6: selection
    def d_se(c):
        d = pd.Series(R[c]["loss"] - R["e184"]["loss"]).groupby(reg).sum()
        return float(d.sum()), float(math.sqrt(len(d)) * d.std(ddof=1))
    allc = [c for c in R if c != "none"]
    cmin = min(allc, key=lambda c: R[c]["sse"])
    D, SE = d_se(cmin)
    final = cmin if (cmin != "e184" and D < -SE) else "e184"
    fam_best = {}
    for fam in ("bootstrap", "minority", "multivariate", "temporal", "feature", "boundary", "weighting"):
        cs = [c for c in R if R[c]["family"] == fam and R[c]["stage"] in (2, 3)]
        if cs:
            fam_best[fam] = min(cs, key=lambda c: R[c]["sse"])
    s3 = [c for c in R if R[c]["stage"] == 3] + top3
    s4 = [c for c in R if R[c]["stage"] == 4]
    s5 = [c for c in R if R[c]["stage"] == 5]
    arms = {"E168": "none", "E184": "e184", "E191": final, "E191_min": cmin,
            "best_ratio": min(s3, key=lambda c: R[c]["sse"]),
            "best_combination": min(s4, key=lambda c: R[c]["sse"]) if s4 else None,
            "best_model": min(s5, key=lambda c: R[c]["sse"]), **{f"best_{k}": v for k, v in fam_best.items()}}
    rows, conf = [], []
    for cid, r in R.items():
        o = te[RT.KEYS].copy()
        o["cid"] = cid
        o["mu"], o["p"], o["half"] = r["te"]
        for k, sp in enumerate(r["seeds_p"]):
            o[f"p_s{k}"] = sp
        rows.append(o)
        dd, se = d_se(cid)
        conf.append({"job": stream, "survey": survey, "leads": "-".join(map(str, leads)), "cid": cid, "stage": r["stage"], "family": r["family"],
                     "model": f"{r['model'][0]}{'' if r['model'][1] is None else r['model'][1]}", "spec": json.dumps(r["spec"]),
                     "inner_sse": round(r["sse"], 4), "minus_e184": round(dd, 4), "se": round(se, 4)})
    return {"survey": survey, "leads": leads, "job": stream, "cfg": "|".join(map(str, cfg)), "rows": pd.concat(rows, ignore_index=True),
            "configs": pd.DataFrame(conf), "quality": pd.DataFrame(Q), "arms": arms, "top3": top3, "best_ratio": best_r,
            "selected": final, "min": cmin, "one_se": {"D": D, "SE": SE}, "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------ controls
def shuffle_job(survey, mode, spec, model):
    tr, te, AN = stacked(survey, [1], mode)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cfg, _ = C182.stage_a(tr, AN, folds)
    stream = RT.job_id(survey, 1, mode)
    runs = [run_cfg(tr, te, AN, folds, cfg, spec, s, stream, model)[0] for s in (SEEDS[:1] if not spec.get("gens") and not spec.get("under") else SEEDS)]
    o = te[RT.KEYS].copy()
    o["mode"] = mode
    o["mu"], o["p"], o["half"] = (np.mean([np.asarray(r[k], float) for r in runs], axis=0) for k in range(3))
    return o


# ------------------------------------------------------------------------------------------------ evaluation
def metrics(y, p, q):
    y, p = np.asarray(y).astype(bool), np.asarray(p, float)
    pr = p >= .5
    tp, fp, fn, tn = int((pr & y).sum()), int((pr & ~y).sum()), int((~pr & y).sum()), int((~pr & ~y).sum())
    n = len(y)
    acc = (tp + tn) / n
    z = 1.959964
    c, r_ = acc + z * z / (2 * n), z * math.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n))
    rec, spec = tp / max(1, tp + fn), tn / max(1, tn + fp)
    prec = tp / max(1, tp + fp)
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    cal = LogisticRegression(C=1e6).fit(lp[:, None], y)
    return {"accuracy": round(acc, 4), "correct": tp + tn, "accuracy_ci95": [round((c - r_) / (1 + z * z / n), 3), round((c + r_) / (1 + z * z / n), 3)],
            "balanced_accuracy": round((rec + spec) / 2, 4), "precision": round(prec, 3), "recall": round(rec, 3), "specificity": round(spec, 3),
            "f1": round(2 * prec * rec / max(1e-9, prec + rec), 3), "false_positives": fp, "false_negatives": fn,
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "brier": round(float(np.mean((p - np.asarray(q)) ** 2)), 5),
            "roc_auc": round(float(roc_auc_score(y, p)), 3), "pr_auc": round(float(average_precision_score(y, p)), 3),
            "cal_intercept": round(float(cal.intercept_[0]), 3), "cal_slope": round(float(cal.coef_[0, 0]), 3)}


def _stored():
    a = pd.read_csv(K.D / "e184" / "out" / "all_rows.csv", float_precision="round_trip")
    b = pd.read_csv(K.D / "e184" / "out" / "lead3_rows.csv", float_precision="round_trip")
    c = pd.read_csv(K.D / "e187" / "out" / "lead4_6_rows.csv", float_precision="round_trip")
    d = pd.concat([a, b, c], ignore_index=True)
    d = d[d["mode"] == "main"]
    e84 = d[d["arm"] == "E184"][RT.KEYS + ["p"]].drop_duplicates(RT.KEYS)
    e68 = d[d["arm"] == "E168_rerun"][RT.KEYS + ["p"]].drop_duplicates(RT.KEYS)
    return e84, e68


def evaluate(J, sh, log):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    rows = []
    for j in J:
        r = j["rows"]
        for arm, cid in j["arms"].items():
            if cid is None:
                continue
            x = r[r["cid"] == cid].copy()
            x["arm"] = arm
            rows.append(x)
        x = r.copy()
        x["arm"] = "gen:" + x["cid"]
        rows.append(x[x["cid"].isin(GN.STAGE2)])
    Rr = pd.concat(rows, ignore_index=True)
    e84, e68 = _stored()
    res = {"protocol": "docs/e191/PROTOCOL.md", "reproduction": {}, "leads": {}, "descriptive_generators": {}}
    for nm, st, arm in (("E184", e84, "E184"), ("E168", e68, "E168")):
        m = Rr[Rr["arm"] == arm].merge(st.rename(columns={"p": "ps"}), on=RT.KEYS)
        res["reproduction"][nm] = {"rows": int(len(m)), "max_abs_diff_p": float(np.max(np.abs(m["p"] - m["ps"])))}
    arms = sorted(set(Rr["arm"]) - {a for a in Rr["arm"] if a.startswith("gen:")})
    holm = {}
    for Ld in LEADS:
        x = G[G["lead"] == Ld]
        P = Rr[Rr["lead"] == Ld].pivot_table(index=RT.KEYS, columns="arm", values="p").reset_index()
        x = x.merge(P, on=RT.KEYS)
        if len(x) != 72:
            continue
        y = x["y_high"].astype(bool)
        L_ = {"metrics": {}, "vs_E184": {}, "by_round": {}}
        for a in ["PERS"] + arms:
            if a in x and x[a].notna().all():
                L_["metrics"][a] = metrics(y, x[a], x["q_true"])
                L_["by_round"][a] = {s: round(float(((g[a] >= .5) == g["y_high"].astype(bool)).mean()), 3) for s, g in x.groupby("survey")}
        for a in arms + [c for c in x.columns if str(c).startswith("gen:")]:
            if a == "E184" or a not in x or x[a].isna().any():
                continue
            cA, cB = (x[a] >= .5) == y, (x["E184"] >= .5) == y
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            p = float(binomtest(b, b + c, .5).pvalue) if b + c else 1.0
            v = E.E7.diff_ci(x, a, "E184", "q_true", np.random.default_rng(191), n=2000) if not str(a).startswith("gen:") else None
            ent = {"only_this_right": b, "only_E184_right": c, "mcnemar_p": round(p, 4),
                   "brier_minus_E184": None if v is None else [round(v["diff"], 5), [round(z, 5) for z in v["ci95"]]]}
            if str(a).startswith("gen:"):
                res["descriptive_generators"].setdefault(a[4:], {})[Ld] = {"accuracy": round(float(cA.mean()), 4), "false_positives": int(((x[a] >= .5) & ~y).sum()),
                                                                          "brier": round(float(np.mean((x[a] - x["q_true"]) ** 2)), 5), **ent}
            else:
                L_["vs_E184"][a] = ent
                if Ld <= 3:
                    holm.setdefault(a, []).append(p)
        res["leads"][Ld] = L_
    for a, ps in holm.items():
        order = np.argsort(ps)
        adj, run = [0.0] * len(ps), 0.0
        for k, i in enumerate(order):
            run = max(run, min(1.0, (len(ps) - k) * ps[i]))
            adj[i] = round(run, 4)
        for Ld, pa in zip((1, 2, 3), adj):
            res["leads"][Ld]["vs_E184"][a]["holm_p"] = pa
    # BH over descriptive generators x leads 1-3
    flat = [(g, L, v["mcnemar_p"]) for g, d in res["descriptive_generators"].items() for L, v in d.items() if L <= 3]
    if flat:
        ps = np.array([f[2] for f in flat])
        o = np.argsort(ps)
        bh = np.empty(len(ps))
        prev = 1.0
        for rank in range(len(ps) - 1, -1, -1):
            i = o[rank]
            prev = min(prev, ps[i] * len(ps) / (rank + 1))
            bh[i] = prev
        for (g, L, _), q_ in zip(flat, bh):
            res["descriptive_generators"][g][L]["bh_q"] = round(float(q_), 4)
    # seed sensitivity for E191 / E184
    res["seed_accuracy"] = {}
    for arm in ("E184", "E191"):
        out = {}
        for Ld in (1, 2, 3):
            x = G[G["lead"] == Ld][RT.KEYS + ["y_high"]].merge(Rr[(Rr["arm"] == arm) & (Rr["lead"] == Ld)], on=RT.KEYS)
            out[Ld] = [round(float(((x[f"p_s{k}"] >= .5) == x["y_high"].astype(bool)).mean()), 4) for k in range(5) if f"p_s{k}" in x and x[f"p_s{k}"].notna().all()]
        res["seed_accuracy"][arm] = out
    # shuffle control (Lead 1)
    if sh is not None and len(sh):
        x = G[G["lead"] == 1].merge(Rr[(Rr["arm"] == "E191") & (Rr["lead"] == 1)][RT.KEYS + ["p"]].rename(columns={"p": "E191"}), on=RT.KEYS)
        S_ = sh.groupby(RT.KEYS)["p"].mean().reset_index().rename(columns={"p": "SHUF"})
        x = x.merge(S_, on=RT.KEYS)
        v = E.E7.diff_ci(x, "E191", "SHUF", "q_true", np.random.default_rng(191), n=2000)
        res["shuffle_control_L1"] = {"E191_minus_shuffled_brier": [round(v["diff"], 5), [round(z, 5) for z in v["ci95"]]],
                                     "shuffled_accuracy": round(float(((x["SHUF"] >= .5) == x["y_high"].astype(bool)).mean()), 4)}
    # decision
    M = {L: res["leads"][L]["metrics"] for L in (1, 2, 3)}
    if "E191" in M[1]:
        crit = {"acc_ge": all(M[L]["E191"]["accuracy"] >= M[L]["E184"]["accuracy"] for L in M),
                "brier_ok": all(M[L]["E191"]["brier"] <= M[L]["E184"]["brier"] + 0.002 for L in M),
                "balacc_ok": all(M[L]["E191"]["balanced_accuracy"] >= M[L]["E184"]["balanced_accuracy"] - 0.02 for L in M),
                "fa_ok": all(M[L]["E191"]["false_positives"] <= M[L]["E184"]["false_positives"] for L in M)}
        sig = any(res["leads"][L]["vs_E184"].get("E191", {}).get("holm_p", 1) < .05 or
                  (res["leads"][L]["vs_E184"].get("E191", {}).get("brier_minus_E184") or [0, [0, 0]])[1][1] < 0 for L in M)
        res["decision"] = {"criteria": crit, "significant": bool(sig),
                           "verdict": "E191 replaces E184 (candidate only; not staged)" if all(crit.values()) and sig else "E184 stays",
                           "reaches_80_all_leads_1_3": all(M[L]["E191"]["accuracy"] >= .8 - 1e-9 for L in M)}
    log("evaluated", verdict=res.get("decision", {}).get("verdict"))
    return res, Rr


def run_all() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FR.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl", fresh=False)
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL))
    t0 = time.time()
    todo = [(s, l, "main") for s in RT.SURVEYS for l in LEADS] + [(s, 1, m) for s in RT.SURVEYS for m in ("corrupt", "shuf1", "shuf2", "shuf3")]
    Parallel(n_jobs=N_JOBS, verbose=2)(delayed(_frame)(*t) for t in todo)
    log("frames", seconds=round(time.time() - t0, 1))
    leak = {}
    for s in RT.SURVEYS:
        a, b = load(FR / f"{s}_L1_main.pkl"), load(FR / f"{s}_L1_corrupt.pkl")
        leak[s] = bool(same_train(a, b) and a[1].equals(b[1]) and all(np.array_equal(np.asarray(a[2][k][1], float), np.asarray(b[2][k][1], float), equal_nan=True) for k in a[2]))
    log("leakage_frames_identical", **leak)
    G = groups()
    log("groups", groups=[f"{s}:{'-'.join(map(str, g))}" for s, g in G])
    print("groups:", G, "leak-identical:", leak, flush=True)
    order = sorted(G, key=lambda t: -len(load(FR / f"{t[0]}_L{t[1][0]}_main.pkl")[0]))
    J = Parallel(n_jobs=N_JOBS, verbose=5)(delayed(job)(s, g) for s, g in order)
    for j in J:
        log("job", job=j["job"], leads=j["leads"], seconds=j["seconds"], top3=j["top3"], best_ratio={k: v for k, v in j["best_ratio"].items()},
            selected=j["selected"], min=j["min"], one_se=j["one_se"], arms=j["arms"])
    with open(OUT / "jobs.pkl", "wb") as fh:
        pickle.dump(J, fh)
    pd.concat([j["configs"] for j in J], ignore_index=True).to_csv(OUT / "configs.csv", index=False, lineterminator="\n")
    pd.concat([j["quality"] for j in J], ignore_index=True).to_csv(OUT / "quality.csv", index=False, lineterminator="\n")
    # shuffle control: each survey's Lead-1 job's selected configuration
    sel = {j["survey"]: j for j in J if 1 in j["leads"]}
    tasks = []
    for s, j in sel.items():
        cid = j["selected"]
        spec = json.loads(j["configs"].set_index("cid").at[cid, "spec"])
        spec["gens"] = [tuple(g) for g in spec.get("gens", [])]
        mstr = j["configs"].set_index("cid").at[cid, "model"]
        model = ("lgb", None) if mstr.startswith("lgb") else (mstr[:-1] if mstr[-1].isdigit() and not mstr.startswith("ridge") else mstr, None)
        if not mstr.startswith("lgb"):
            kind = "ridge" if mstr.startswith("ridge") else ("rf" if mstr.startswith("rf") else "cat")
            par = float(mstr[len(kind):])
            model = (kind, par if kind == "ridge" else int(par))
        for m in ("shuf1", "shuf2", "shuf3"):
            tasks.append(delayed(shuffle_job)(s, m, spec, model))
    sh = pd.concat(Parallel(n_jobs=N_JOBS, verbose=2)(tasks), ignore_index=True) if tasks else None
    if sh is not None:
        sh.to_csv(OUT / "shuffle_rows.csv", index=False, lineterminator="\n")
    res, Rr = evaluate(J, sh, log)
    res["leakage_frames_identical"] = leak
    res["jobs"] = [{k: j[k] for k in ("job", "survey", "leads", "cfg", "top3", "best_ratio", "selected", "min", "one_se", "arms", "seconds")} for j in J]
    Rr.to_csv(OUT / "arm_rows.csv", index=False, lineterminator="\n")
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("arm_rows.csv", "configs.csv", "quality.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    log("done", seconds=round(time.time() - t0, 1))
    print(json.dumps({"reproduction": res["reproduction"], "decision": res.get("decision"), "jobs": res["jobs"]}, default=str, indent=1))


if __name__ == "__main__":
    {"all": run_all}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: python -m app.e191.run all"))()
