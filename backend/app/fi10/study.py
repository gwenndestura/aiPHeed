"""FI10 locked province-level study: food-price pressure in Cavite, Laguna, Batangas, Rizal, Quezon, Leads 1-4.

    python -m app.fi10.study lock
    python -m app.fi10.study run

Walk-forward over issue quarters (FI9 timing); at each issue date train on province-rows whose target was published
by that date. Hyperparameters, decision thresholds and (for classifiers) Platt calibration are chosen on an inner
time holdout (the latest 25 % of training target quarters), never on evaluation rows. Linear/baseline models refit
every quarter; tree models are tuned and refitted at each first-quarter issue and used for that year.
Periods: DEV = targets 2005-2015 (model selection), TEST = targets 2016-2026 (reported; disclosed: 2021+ provincial CPI
was examined in earlier aiPHeed work as a predictor).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi10 import OUT, PROVINCES, VERSION
from app.fi10.data import GROUPS, PROV_FE, SEASON
from app.fi9z.classmetrics import class_metrics
from app.paths import BACKEND_DIR

ALL = sum(GROUPS.values(), [])
NO = lambda *g: [c for c in ALL if not any(c in GROUPS[x] for x in g)]
CONFIGS = {   # name -> (kind, features, leads)
    "Always LOW": ("low", [], [1, 2, 3, 4]), "Climatology (province base rate)": ("clim", [], [1, 2, 3, 4]),
    "Naive persistence": ("persist", [], [1, 2, 3, 4]), "Damped persistence": ("damped", [], [1, 2, 3, 4]),
    "Ridge market only (pooled)": ("ridge", GROUPS["market"] + SEASON, [1, 2, 3, 4]),
    "Ridge all groups (pooled)": ("ridge", ALL + SEASON, [1, 2, 3, 4]),
    "Ridge all groups + province effects (partial pooling)": ("ridge", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    "Ridge all groups, separate per province (no pooling)": ("ridge_sep", ALL + SEASON, [1, 2, 3, 4]),
    "Ridge all groups without news": ("ridge", NO("news") + SEASON + PROV_FE, [1, 2, 3, 4]),
    "Logistic L2 all groups": ("logit", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    "LightGBM regression (tuned)": ("lgb_reg", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    "LightGBM regression without news": ("lgb_reg", NO("news") + SEASON + PROV_FE, [1, 2, 3, 4]),
    "LightGBM classifier (tuned)": ("lgb_clf", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    "Random forest (tuned)": ("rf", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    "Extra trees (tuned)": ("et", ALL + SEASON + PROV_FE, [1, 2, 3, 4]),
    **{f"Ablation: ridge without {g}": ("ridge", NO(g) + SEASON + PROV_FE, [1]) for g in GROUPS if g != "news"},
    **{f"Ablation: LightGBM without {g}": ("lgb_reg", NO(g) + SEASON + PROV_FE, [1]) for g in GROUPS if g != "news"},
    "LOPO: ridge all groups (pooled)": ("lopo_ridge", ALL + SEASON, [1, 2]),
    "LOPO: LightGBM regression": ("lopo_lgb", ALL + SEASON, [1, 2]),
}
ENSEMBLE = ("Ensemble: mean of ridge (partial pooling) and LightGBM regression",
            ["Ridge all groups + province effects (partial pooling)", "LightGBM regression (tuned)"])
REQ = {"high_recall": 0.60, "high_precision": 0.50, "low_recall": 0.85, "low_precision": 0.90, "balanced_accuracy": 0.70,
       "macro_f1": 0.70, "accuracy": 0.75, "ece_5bin": 0.10}
PROTOCOL = {
    "version": VERSION,
    "target": "HIGH(p,t): provincial food CPI y/y (quarter mean) > mean + 1 SD of that province's previous 20 quarters (>= 12)",
    "construct": "provincial food-price pressure (measured by PSA); NOT food insecurity",
    "configs": {k: [v[0], len(v[1]), v[2]] for k, v in CONFIGS.items()} | {ENSEMBLE[0]: ENSEMBLE[1]},
    "tuning": "inner time holdout = latest 25 % of training target quarters; LightGBM: Optuna TPE 15 trials (seed 7); RF/ET: grid "
              "max_depth {3,5,8} x min_samples_leaf {5,15} x class_weight {None, balanced_subsample}; logistic: C {0.03,0.3,3}",
    "threshold": "balanced-accuracy-optimal on the inner holdout; naive persistence uses 0.5; classifiers Platt-calibrated on the holdout",
    "selection": "per lead, among non-baseline, non-ablation, non-LOPO models: highest DEV balanced accuracy with DEV ECE <= 0.10 "
                 "(tie: lower DEV Brier)",
    "adoption_on_TEST": {"class_requirements": REQ,
                         "skill": "beat naive persistence: Brier P(better) >= 0.90 or balanced accuracy P(better) >= 0.90 with macro-F1 not "
                                  "lower (quarter-block bootstrap, all provinces resampled together)",
                         "every_province_balanced_accuracy": 0.65, "lopo_balanced_accuracy_if_pooled": 0.65},
    "max_reliable_lead": "longest lead whose selected model meets every TEST adoption requirement",
    "periods": {"DEV": [2005, 2015], "TEST": [2016, 2026]},
}


def _digest():
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def _code():
    return hashlib.sha256(b"".join((BACKEND_DIR / "app" / "fi10" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("study.py", "data.py"))).hexdigest()


def load() -> pd.DataFrame:
    D = pd.read_csv(OUT / "dataset.csv", parse_dates=["issue_date", "target_published"])
    return D[D["y"].notna()].reset_index(drop=True)


def _prep(cols):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler())


def _usable(tr, cols):
    return [c for c in cols if tr[c].notna().sum() >= 10 and tr[c].nunique() > 1]


def _gauss(level, thr, sd):
    return 1 - norm.cdf((np.asarray(thr, float) - np.asarray(level, float)) / sd)


def _tau(p, y):
    best, tau = -1, 0.5
    if len(set(y)) == 2:
        for t in np.linspace(0.05, 0.95, 91):
            ba = (np.mean(p[y == 1] >= t) + np.mean(p[y == 0] < t)) / 2
            if ba > best + 1e-9:
                best, tau = ba, float(t)
    return tau


def _split(tr):
    qs = np.sort(tr["target_quarter"].unique())
    cut = qs[int(len(qs) * 0.75)]
    return tr[tr["target_quarter"] < cut], tr[tr["target_quarter"] >= cut]


class Fitted:
    """predict(te) -> (p, level or nan)"""


def fit(kind, feats, tr, params=None):
    """Fit one model on tr. Returns (predict_fn, info). Hyperparameters are tuned on the inner holdout when params is None."""
    y = tr["y"].to_numpy(int)
    if kind in ("low", "clim"):
        rate = tr.groupby("province")["y"].mean().to_dict() if kind == "clim" else {}
        return (lambda te: (np.array([rate.get(p, y.mean()) if kind == "clim" else y.mean() for p in te["province"]]), np.full(len(te), np.nan))), {}
    if kind == "persist":
        sd = max(float(np.std(tr["delta"], ddof=1)), 0.25)
        return (lambda te: (_gauss(te["f_m"], te["thr_known"], sd), te["f_m"].to_numpy(float))), {"sd": sd}
    if kind == "damped":
        d0, d1 = (tr["f_m"] - tr["base_mean"]).to_numpy(float), (tr["level"] - tr["base_mean"]).to_numpy(float)
        ok = ~(np.isnan(d0) | np.isnan(d1))
        grid = np.linspace(0, 1, 101)
        phi = float(grid[int(np.argmin([np.sum((d1[ok] - g * d0[ok]) ** 2) for g in grid]))])
        sd = max(float(np.std(d1[ok] - phi * d0[ok], ddof=1)), 0.25)
        lv = lambda te: (te["base_mean"] + phi * (te["f_m"] - te["base_mean"])).to_numpy(float)
        return (lambda te: (_gauss(lv(te), te["thr_known"], sd), lv(te))), {"phi": phi, "sd": sd}
    cols = _usable(tr, feats)
    if kind in ("ridge", "lopo_ridge"):
        if params is None:
            a, b = _split(tr)
            best = min([1.0, 10.0, 100.0], key=lambda al: np.mean((b["delta"] - make_pipeline(_prep(cols), Ridge(alpha=al)).fit(a[cols], a["delta"]).predict(b[cols])) ** 2))
            m0 = make_pipeline(_prep(cols), Ridge(alpha=best)).fit(a[cols], a["delta"])
            sd = max(float(np.sqrt(np.mean((b["delta"] - m0.predict(b[cols])) ** 2))), 0.25)
            params = {"alpha": best, "sd": sd}
        m = make_pipeline(_prep(cols), Ridge(alpha=params["alpha"])).fit(tr[cols], tr["delta"])
        lv = lambda te: te["f_m"].to_numpy(float) + m.predict(te[cols])
        return (lambda te: (_gauss(lv(te), te["thr_known"], params["sd"]), lv(te))), params
    if kind in ("lgb_reg", "lopo_lgb"):
        import lightgbm as lgb
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        if params is None:
            a, b = _split(tr)

            def obj(trial):
                pr = {"num_leaves": trial.suggest_int("num_leaves", 3, 15), "min_child_samples": trial.suggest_int("min_child_samples", 10, 60),
                      "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.15, log=True), "n_estimators": trial.suggest_int("n_estimators", 50, 400),
                      "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 20, log=True), "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0)}
                mm = lgb.LGBMRegressor(**pr, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(a[cols], a["delta"])
                return float(np.mean((b["delta"] - mm.predict(b[cols])) ** 2))
            st = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
            st.optimize(obj, n_trials=15)
            params = dict(st.best_params)
            params["sd"] = max(float(np.sqrt(st.best_value)), 0.25)
        hp = {k: v for k, v in params.items() if k != "sd"}
        m = lgb.LGBMRegressor(**hp, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(tr[cols], tr["delta"])
        lv = lambda te: te["f_m"].to_numpy(float) + m.predict(te[cols])
        return (lambda te: (_gauss(lv(te), te["thr_known"], params["sd"]), lv(te))), params
    if kind in ("logit", "lgb_clf", "rf", "et"):
        a, b = _split(tr)
        if params is None:
            cands = {"logit": [{"C": c} for c in (0.03, 0.3, 3.0)],
                     "rf": [{"max_depth": d, "min_samples_leaf": s, "class_weight": w} for d in (3, 5, 8) for s in (5, 15) for w in (None, "balanced_subsample")],
                     "et": [{"max_depth": d, "min_samples_leaf": s, "class_weight": w} for d in (3, 5, 8) for s in (5, 15) for w in (None, "balanced_subsample")]}.get(kind)
            if kind == "lgb_clf":
                import lightgbm as lgb
                import optuna
                optuna.logging.set_verbosity(optuna.logging.WARNING)

                def obj(trial):
                    pr = {"num_leaves": trial.suggest_int("num_leaves", 3, 15), "min_child_samples": trial.suggest_int("min_child_samples", 10, 60),
                          "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.15, log=True), "n_estimators": trial.suggest_int("n_estimators", 50, 400),
                          "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 20, log=True), "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"])}
                    mm = lgb.LGBMClassifier(**pr, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(a[cols], a["y"].astype(int))
                    pp = np.clip(mm.predict_proba(b[cols])[:, 1], 1e-6, 1 - 1e-6)
                    yb = b["y"].to_numpy(int)
                    return float(-np.mean(yb * np.log(pp) + (1 - yb) * np.log(1 - pp)))
                st = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
                st.optimize(obj, n_trials=15)
                cands = [st.best_params]
            scores = []
            for c in cands:
                mm = _clf(kind, c).fit(a[cols], a["y"].astype(int))
                pp = np.clip(mm.predict_proba(b[cols])[:, 1], 1e-6, 1 - 1e-6)
                yb = b["y"].to_numpy(int)
                scores.append(float(-np.mean(yb * np.log(pp) + (1 - yb) * np.log(1 - pp))))
            params = dict(cands[int(np.argmin(scores))])
            mm = _clf(kind, params).fit(a[cols], a["y"].astype(int))
            z = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4)))
            pb = mm.predict_proba(b[cols])[:, 1]
            if b["y"].nunique() == 2:
                pl = LogisticRegression(C=1e4, max_iter=2000).fit(z(pb).reshape(-1, 1), b["y"].astype(int))
                params["platt"] = [float(pl.coef_[0][0]), float(pl.intercept_[0])]
            else:
                params["platt"] = [1.0, 0.0]
        m = _clf(kind, {k: v for k, v in params.items() if k != "platt"}).fit(tr[cols], y)
        s, i = params["platt"]
        cal = lambda q: 1 / (1 + np.exp(-(s * np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4))) + i)))
        return (lambda te: (cal(m.predict_proba(te[cols])[:, 1]), np.full(len(te), np.nan))), params
    raise ValueError(kind)


def _clf(kind, p):
    if kind == "logit":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=p["C"], max_iter=3000))
    if kind == "lgb_clf":
        import lightgbm as lgb
        return lgb.LGBMClassifier(**p, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1)
    cls = RandomForestClassifier if kind == "rf" else ExtraTreesClassifier
    return make_pipeline(SimpleImputer(strategy="median"), cls(n_estimators=300, random_state=7, n_jobs=1, **p))


TREE = ("lgb_reg", "lgb_clf", "rf", "et", "lopo_lgb")


def _task(args):
    name, lead = args
    kind, feats, _ = CONFIGS[name]
    D = load()
    L = D[D["lead"] == lead].sort_values(["issue_date", "province"]).reset_index(drop=True)
    out = []
    issues = sorted(L.loc[L["target_quarter"] >= "2005-Q1", "issue_date"].unique())
    cache = {}
    for d in issues:
        d = pd.Timestamp(d)
        tr = L[L["target_published"] <= d]
        te = L[L["issue_date"] == d]
        if len(tr) < 100 or tr["y"].nunique() < 2:
            continue
        year = d.year
        if kind == "ridge_sep":
            parts = []
            for p in PROVINCES:
                trp, tep = tr[tr["province"] == p], te[te["province"] == p]
                if len(tep):
                    fn, prm = fit("ridge", feats, trp)
                    parts.append((tep, fn, prm, trp))
            for tep, fn, prm, trp in parts:
                p_, lv = fn(tep)
                a, b = _split(trp)
                fa, _ = fit("ridge", feats, a)
                tau = _tau(fa(b)[0], b["y"].to_numpy(int))
                out += _rows(name, lead, tep, p_, lv, tau, None)
            continue
        if kind.startswith("lopo"):
            base = "ridge" if kind == "lopo_ridge" else "lgb_reg"
            for p in PROVINCES:
                trx, tep = tr[tr["province"] != p], te[te["province"] == p]
                key = (p, year)
                if base == "lgb_reg" and key in cache:
                    fn, tau = cache[key]
                else:
                    fn, prm = fit(base, feats, trx)
                    a, b = _split(trx)
                    fa, _ = fit(base, feats, a, prm if base == "lgb_reg" else None)
                    tau = _tau(fa(b)[0], b["y"].to_numpy(int))
                    if base == "lgb_reg":
                        cache[key] = (fn, tau)
                p_, lv = fn(tep)
                out += _rows(name, lead, tep, p_, lv, tau, None)
            continue
        if kind in TREE and year in cache:
            fn, tau, prm = cache[year]
        else:
            fn, prm = fit(kind, feats, tr)
            if kind == "persist":
                tau = 0.5
            elif kind in ("low",):
                tau = 1.01
            elif kind == "clim":
                tau = 1.01
            else:
                a, b = _split(tr)
                fa, _ = fit(kind, feats, a, prm if kind in TREE else None)
                tau = _tau(fa(b)[0], b["y"].to_numpy(int))
            if kind in TREE:
                cache[year] = (fn, tau, prm)
        p_, lv = fn(te)
        out += _rows(name, lead, te, p_, lv, tau, prm)
    return out


def _rows(name, lead, te, p, lv, tau, prm):
    return [{"config": name, "lead": lead, "province": r["province"], "issue_date": str(pd.Timestamp(r["issue_date"]).date()),
             "target_quarter": r["target_quarter"], "y": int(r["y"]), "p": float(pi), "cls": int(pi >= tau), "tau": tau, "level_hat": float(li),
             "level": float(r["level"]), "train_cutoff": None} for (_, r), pi, li in zip(te.iterrows(), p, lv)]


# ------------------------------------------------------------------------------------------------ evaluation
def _boot(a_cls, b_cls, a_p, b_p, y, q, reps=3000, block=4, seed=7):
    """Quarter-block bootstrap (all provinces of a quarter resampled together)."""
    rng = np.random.default_rng(seed)
    uq = np.array(sorted(set(q)))
    idx_by_q = {k: np.where(q == k)[0] for k in uq}
    starts = np.arange(len(uq) - block + 1)
    dba, dbr = [], []
    for _ in range(reps):
        qs = np.concatenate([uq[s:s + block] for s in rng.choice(starts, int(np.ceil(len(uq) / block)))])[:len(uq)]
        idx = np.concatenate([idx_by_q[k] for k in qs])
        yy = y[idx]
        if 0 < yy.sum() < len(yy):
            ba = lambda c: (np.mean(c[idx][yy == 1] == 1) + np.mean(c[idx][yy == 0] == 0)) / 2
            dba.append(ba(a_cls) - ba(b_cls))
            dbr.append(np.mean((a_p[idx] - yy) ** 2) - np.mean((b_p[idx] - yy) ** 2))
    return {"ba_diff": float(np.mean(dba)), "ba_p_better": float(np.mean(np.array(dba) > 0)),
            "brier_diff": float(np.mean(dbr)), "brier_p_better": float(np.mean(np.array(dbr) < 0)),
            "ba_ci95": [float(np.percentile(dba, 2.5)), float(np.percentile(dba, 97.5))]}


def evaluate(W: pd.DataFrame) -> dict:
    res = {"by_lead": {}}
    W = W.copy()
    W["year"] = W["target_quarter"].str[:4].astype(int)
    for lead, G in W.groupby("lead"):
        R = {}
        for c, g in G.groupby("config"):
            dev, test = g[g["year"].between(2005, 2015)], g[g["year"] >= 2016]
            m = {"dev": class_metrics(dev["y"], dev["cls"], dev["p"]), "test": class_metrics(test["y"], test["cls"], test["p"])}
            m["test_by_province"] = {p: class_metrics(x["y"], x["cls"], x["p"]) for p, x in test.groupby("province")}
            m["train_like_dev_vs_test_ba_drop"] = (m["dev"]["balanced_accuracy"] or 0) - (m["test"]["balanced_accuracy"] or 0)
            nv = G[(G["config"] == "Naive persistence") & (G["year"] >= 2016)].set_index(["target_quarter", "province"])
            t2 = test.set_index(["target_quarter", "province"]).loc[nv.index.intersection(test.set_index(["target_quarter", "province"]).index)]
            n2 = nv.loc[t2.index]
            if c != "Naive persistence" and len(t2):
                m["test_vs_naive"] = _boot(t2["cls"].to_numpy(), n2["cls"].to_numpy(), t2["p"].to_numpy(), n2["p"].to_numpy(),
                                           t2["y"].to_numpy(int), t2.index.get_level_values(0).to_numpy())
            R[c] = m
        res["by_lead"][int(lead)] = R
    sel = {}
    for lead, R in res["by_lead"].items():
        pool = {c: v for c, v in R.items() if not c.startswith(("Ablation", "LOPO")) and c not in ("Always LOW", "Climatology (province base rate)", "Naive persistence", "Damped persistence")}
        ok = {c: v for c, v in pool.items() if (v["dev"]["ece_5bin"] or 1) <= 0.10}
        cand = ok or pool
        best = max(cand, key=lambda c: ((cand[c]["dev"]["balanced_accuracy"] or 0), -(cand[c]["dev"]["brier"] or 1)))
        v = R[best]
        t = v["test"]
        chk = {f"{k}_ok": ((t[k] or 0) >= thr if k != "ece_5bin" else (t[k] is not None and t[k] <= thr)) for k, thr in REQ.items()}
        vs = v.get("test_vs_naive", {})
        chk["skill_vs_naive"] = (vs.get("brier_diff", 1) < 0 and vs.get("brier_p_better", 0) >= 0.90) or \
                                (vs.get("ba_diff", -1) > 0 and vs.get("ba_p_better", 0) >= 0.90 and t["macro_f1"] >= R["Naive persistence"]["test"]["macro_f1"])
        chk["every_province_ba_ge_065"] = all((x["balanced_accuracy"] or 0) >= 0.65 for x in v["test_by_province"].values())
        lopo = R.get("LOPO: LightGBM regression" if "LightGBM" in best else "LOPO: ridge all groups (pooled)")
        chk["lopo_ba_ge_065"] = bool(lopo and (lopo["test"]["balanced_accuracy"] or 0) >= 0.65) if lead in (1, 2) else None
        sel[lead] = {"selected": best, "checks": chk, "adopt": all(v_ for v_ in chk.values() if v_ is not None)}
    res["selection"] = sel
    ok = [l for l, s in sel.items() if s["adopt"]]
    res["max_reliable_lead"] = max(ok) if ok else None
    res["best_lead_by_test_balanced_accuracy"] = max(sel, key=lambda l: res["by_lead"][l][sel[l]["selected"]]["test"]["balanced_accuracy"] or 0)
    return res


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code():
        raise RuntimeError("FI10 protocol or code changed after lock")
    tasks = [(c, l) for c, v in CONFIGS.items() for l in v[2]]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        W = pd.DataFrame([r for part in ex.map(_task, tasks) for r in part])
    for lead in W["lead"].unique():
        a = W[(W["config"] == ENSEMBLE[1][0]) & (W["lead"] == lead)].set_index(["target_quarter", "province"])
        b = W[(W["config"] == ENSEMBLE[1][1]) & (W["lead"] == lead)].set_index(["target_quarter", "province"])
        common = a.index.intersection(b.index)
        e = a.loc[common].copy()
        e["p"] = (a.loc[common, "p"] + b.loc[common, "p"]) / 2
        e["tau"] = (a.loc[common, "tau"] + b.loc[common, "tau"]) / 2
        e["cls"] = (e["p"] >= e["tau"]).astype(int)
        e["level_hat"] = (a.loc[common, "level_hat"] + b.loc[common, "level_hat"]) / 2
        e["config"] = ENSEMBLE[0]
        W = pd.concat([W, e.reset_index()], ignore_index=True)
    W.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n")
    res = evaluate(W)
    res["protocol_sha256"] = lock["sha256"]
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        from datetime import datetime, timezone
        p = OUT / "PROTOCOL_LOCK.json"
        if p.exists():
            sys.exit("already locked")
        p.write_text(json.dumps({"sha256": _digest(), "code_sha256": _code(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        r = run()
        print(json.dumps(r["selection"], indent=1, default=str)[:3000], "\nmax reliable lead:", r["max_reliable_lead"])
