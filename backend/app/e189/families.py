"""
E189 step 2 (docs/e189/PROTOCOL.md): E168's Stage A with the model family added to the inner selection (LightGBM, ridge,
random forest), then E184's synthetic 50/50 training for the selected configuration. Leads 1-3. Local only.

    python -m app.e189.families run
"""
from __future__ import annotations

import sys
import time
import warnings
from itertools import product

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from app.e168 import lgbm_only as E
from app.e178 import common as K
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e184 import candidate as C184

warnings.filterwarnings("ignore")
OUT = K.D / "e189" / "out"
PROTOCOL = K.BACKEND_DIR.parent / "docs" / "e189" / "PROTOCOL.md"
RIDGE_ALPHA = (1.0, 10.0, 100.0)
RF_LEAF = (5, 20)
FAMILIES = [("lgb", h) for h in E.HPO] + [("ridge", a) for a in RIDGE_ALPHA] + [("rf", m) for m in RF_LEAF]


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


class SkRes:
    """Ridge or random forest on the change from the anchor. Column filter, pruning, medians and scaling come from the
    real rows only; synthetic rows (if any) are added to the fit set with weight syn_weight x 1/(se^2+0.05)."""

    def __init__(self, cols, kind, par, prune):
        self.cols, self.kind, self.par, self.prune = list(cols), kind, par, prune
        self.syn_weight = 1.0

    def _X(self, d):
        X = d[self.use_].astype(float).fillna(self.med_)
        return ((X - self.mu_) / self.sd_).values if self.kind == "ridge" else X.values

    def fit(self, d, syn=None):
        self.use_ = _use(self.cols, d, self.prune)
        R = d[self.use_].astype(float)
        self.med_ = R.median()
        self.mu_ = R.fillna(self.med_).mean()
        self.sd_ = R.fillna(self.med_).std().replace(0, 1.0).fillna(1.0)
        X, e = self._X(d), d["e"].values
        w = 1.0 / (d["se_true"].values ** 2 + 0.05)
        if syn is not None and len(syn):
            X = np.vstack([X, self._X(syn)])
            e = np.r_[e, syn["e"].values]
            w = np.r_[w, self.syn_weight / (syn["se_true"].values ** 2 + 0.05)]
        self.m_ = (Ridge(alpha=self.par) if self.kind == "ridge" else
                   RandomForestRegressor(n_estimators=300, min_samples_leaf=self.par, max_features=0.33, random_state=189, n_jobs=1)).fit(X, e, sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(self._X(X))


def make(f, fam, par, pr):
    if fam == "lgb":
        m = RT.LGBResAug(E.FS[f], *par, pr)
        return m
    return SkRes(E.FS[f], fam, par, pr)


def stage_a(tr, AN, folds):
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    best = {}
    for a, f, pr, (fam, par) in product(E.ANCH, E.FS, (False, True), FAMILIES):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            m = E.LGBRes(E.FS[f], *par, pr) if fam == "lgb" else make(f, fam, par, pr)
            oof[i_te] = atr[i_te] + m.fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if fam not in best or sse < best[fam]["sse"]:
            best[fam] = {"sse": sse, "cfg": (a, f, pr, fam, par)}
    return best


def seed_run(tr, te, AN, folds, cfg, seed, stream):
    a, f, pr, fam, par = cfg
    setting = C184.SETTING
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    atr, ate = AN[a]
    an_all = {x: np.asarray(AN[x][0], float) for x in E.ANCH}
    oof = np.zeros(len(tr))
    for fi, (i_tr, i_te) in enumerate(folds):
        syn, sa = T._augment(tr.iloc[i_tr].reset_index(drop=True), {x: v[i_tr] for x, v in an_all.items()}, setting, seed, stream, fi)[:2]
        m = make(f, fam, par, pr)
        m.syn_weight = setting[2]
        m.fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr]), syn.assign(e=syn["y_true"].values - sa[a]))
        oof[i_te] = atr[i_te] + m.predict(tr.iloc[i_te])
    syn, sa = T._augment(tr, an_all, setting, seed, stream, "final")[:2]
    m = make(f, fam, par, pr)
    m.syn_weight = setting[2]
    m.fit(tr.assign(e=y - atr), syn.assign(e=syn["y_true"].values - sa[a]))
    P, chosen, _ = RT._calibrate(tr, te, folds, oof, ate + m.predict(te), y, q, w, gap)
    return P[chosen]


def job(survey, lead, H, L, S_P):
    t0 = time.time()
    tr, te, AN = RT.build(survey, lead, H, L, S_P, "main")
    assert "is_synthetic" not in te.columns
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    best = stage_a(tr, AN, folds)
    overall = min(best.values(), key=lambda b: b["sse"])["cfg"]
    stream = RT.job_id(survey, lead, "main")
    cache, rows = {}, []
    for arm, cfg in (("E184", best["lgb"]["cfg"]), ("E189_ridge", best["ridge"]["cfg"]), ("E189_rf", best["rf"]["cfg"]), ("E189", overall)):
        if cfg not in cache:
            rs = [seed_run(tr, te, AN, folds, cfg, s, stream) for s in T.SEEDS]
            cache[cfg] = tuple(np.mean([np.asarray(r[k], float) for r in rs], axis=0) for k in range(3))
        o = te[RT.KEYS].copy()
        o["arm"], o["cfg"] = arm, "|".join(map(str, cfg))
        o["mu"], o["p"], o["half"] = cache[cfg]
        rows.append(o)
    return {"rows": pd.concat(rows, ignore_index=True), "job": stream, "selected": "|".join(map(str, overall)),
            "sse": {k: round(v["sse"], 3) for k, v in best.items()}, "seconds": round(time.time() - t0, 1)}


def _m(x, c):
    y, pr = x["y_high"] == 1, x[c] >= .5
    tp, fp, fn, tn = int((pr & y).sum()), int((pr & ~y).sum()), int((~pr & y).sum()), int((~pr & ~y).sum())
    return {"accuracy": round((tp + tn) / len(x), 4), "correct": tp + tn, "balanced_accuracy": round((tp / (tp + fn) + tn / (tn + fp)) / 2, 4),
            "recall": round(tp / (tp + fn), 3), "specificity": round(tn / (tn + fp), 3), "precision": round(tp / max(1, tp + fp), 3),
            "false_alarms": fp, "missed": fn, "brier": round(float(np.mean((x[c] - x["q_true"]) ** 2)), 5)}


def evaluate(R, log):
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    st = pd.concat([pd.read_csv(K.D / "e184" / "out" / n, float_precision="round_trip") for n in ("all_rows.csv", "lead3_rows.csv")])
    st = st[(st["arm"] == "E184") & (st["mode"] == "main")][RT.KEYS + ["p"]].drop_duplicates(RT.KEYS).rename(columns={"p": "E184_stored"})
    arms = ("E184", "E189", "E189_ridge", "E189_rf")
    res = {"protocol": "docs/e189/PROTOCOL.md", "leads": {}}
    pvals = {a: [] for a in arms[1:]}
    for Ld in (1, 2, 3):
        x = G[G["lead"] == Ld]
        for a in arms:
            x = x.merge(R[(R["lead"] == Ld) & (R["arm"] == a)][RT.KEYS + ["p"]].rename(columns={"p": a}), on=RT.KEYS)
        x = x.merge(st, on=RT.KEYS)
        assert len(x) == 72
        Lr = {"reproduction_max_abs_diff_p": float(np.max(np.abs(x["E184"] - x["E184_stored"]))), "metrics": {a: _m(x, a) for a in ("PERS",) + arms}}
        for a in arms[1:]:
            v = E.E7.diff_ci(x, a, "E184", "q_true", np.random.default_rng(189), n=2000)
            cA, cB = (x[a] >= .5) == (x["y_high"] == 1), (x["E184"] >= .5) == (x["y_high"] == 1)
            b, c = int((cA & ~cB).sum()), int((~cA & cB).sum())
            p = float(binomtest(b, b + c, .5).pvalue) if b + c else 1.0
            pvals[a].append(p)
            Lr[a] = {"brier_minus_E184": [round(v["diff"], 5), [round(z, 5) for z in v["ci95"]]], "mcnemar": {"only_this_right": b, "only_E184_right": c, "p": round(p, 4)}}
        res["leads"][Ld] = Lr
    for a in arms[1:]:
        order = np.argsort(pvals[a])
        adj, run = [0.0] * 3, 0.0
        for k, i in enumerate(order):
            run = max(run, min(1.0, (3 - k) * pvals[a][i]))
            adj[i] = round(run, 4)
        M = {L: res["leads"][L]["metrics"] for L in (1, 2, 3)}
        crit = {"acc80_all": all(M[L][a]["accuracy"] >= 0.8 - 1e-9 for L in M),
                "balacc_ok": all(M[L][a]["balanced_accuracy"] >= M[L]["E184"]["balanced_accuracy"] - 0.02 for L in M),
                "recall_ok": all(M[L][a]["recall"] >= M[L]["E184"]["recall"] - 0.04 - 1e-9 for L in M),
                "brier_ok": all(M[L][a]["brier"] <= M[L]["E184"]["brier"] + 0.005 for L in M)}
        res[a] = {"criteria_1_4": crit, "passes_1_4": all(crit.values()), "holm_adjusted_mcnemar_p": adj,
                  "statistically_supported": any(p < .05 for p in adj) or any(res["leads"][L][a]["brier_minus_E184"][1][1] < 0 for L in (1, 2, 3))}
    log("evaluated", **{a: res[a]["passes_1_4"] for a in arms[1:]})
    return res


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log = K.RunLog(OUT / "run_log.jsonl")
    RT._check_inputs(log)
    log("start", protocol_sha256=K.sha256(PROTOCOL), families=[f"{f}:{p}" for f, p in FAMILIES])
    H, L, S_P = K.pipeline_inputs()
    t0 = time.time()
    out = Parallel(n_jobs=RT.N_JOBS, verbose=5)(delayed(job)(s, l, H, L, S_P) for s in RT.SURVEYS for l in (1, 2, 3))
    for o in out:
        log("job", job=o["job"], selected=o["selected"], sse=o["sse"], seconds=o["seconds"])
    R = pd.concat([o["rows"] for o in out], ignore_index=True)
    R.to_csv(OUT / "rows.csv", index=False, lineterminator="\n")
    res = evaluate(R, log)
    res["selected_per_job"] = {o["job"]: o["selected"] for o in out}
    res["inner_sse_per_family"] = {o["job"]: o["sse"] for o in out}
    K.dump_json(res, OUT / "results.json")
    K.write_hashes([OUT / n for n in ("rows.csv", "results.json", "run_log.jsonl")], OUT / "hashes.json")
    print("selected:", res["selected_per_job"])
    print("inner SSE:", res["inner_sse_per_family"])
    for Ld, v in res["leads"].items():
        print(f"Lead {Ld} repro {v['reproduction_max_abs_diff_p']:.1e}")
        for a, m in v["metrics"].items():
            extra = v.get(a, {})
            print(f"   {a:11s} {m} {extra}")
    for a in ("E189", "E189_ridge", "E189_rf"):
        print(a, res[a])


if __name__ == "__main__":
    {"run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit("usage: python -m app.e189.families run"))()
