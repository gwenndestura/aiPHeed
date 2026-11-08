"""FI11 locked study: which trigger combinations help ONE unified food-insecurity model, at Leads 1-4?

    python -m app.fi11.study lock | run

Target: SWS Balance Luzon HIGH (FI6 label). Issue: FI9 operational timing. Leads 1-4 (target = issue quarter + h).
Every feature set contains the SWS state block (latest reading, its anomaly and age, the significance line),
because models without it fail (FI7-FI9). Sets:
    S0 state only | A + market | B + poverty | C + market + poverty | D = C + affordability interactions
    E + all five triggers | F = E without market | G = E without poverty | H = E without market and poverty
New market representation (rationale: the poverty line is fixed at its survey year, so what erodes poor households'
purchasing power is the food-price rise SINCE that year): food_since_threshold = latest regional food CPI / mean food
CPI of the reference year of the latest RELEASED poverty estimate - 1. Also 8-quarter cumulative food inflation and
12-month volatility of food inflation. Interactions (D): poverty x food_since_threshold, poverty x food inflation,
products of training-standardised values.
Families: ridge change model (Gaussian probability), LightGBM change model (Optuna, 15 trials, tuned yearly),
logistic L2 (C on holdout), random forest (small grid, Platt-calibrated). Threshold: balanced-accuracy-optimal on the
inner time holdout (latest 25 % of training targets). XGBoost/CatBoost are not installed and were not added.
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi5 import sources as S5
from app.fi6.features import GOV
from app.fi6.news_model import NEWSA
from app.fi7 import models as M7
from app.fi7.experiments import WORLD, alternating_quarters
from app.fi9 import quarters as Q
from app.fi9z.classmetrics import class_metrics
from app.fi11 import OUT, VERSION
from app.paths import BACKEND_DIR

STATE = ["hunger_last", "hunger_last_anom", "hunger_age_q", "gap"]
MARKET = ["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_rel", "cpi_food_accel", *WORLD, "food_since_threshold", "food_cum8", "food_vol12"]
POVERTY = ["poverty_inc"]
EMPLOY = ["unemp_rate", "unemp_yoy", "underemp_rate", "underemp_yoy", "remit_yoy"]
CLIMATE = ["rain_anom_3m", "tc_exposure_q", "typhoon_passages_4q", "oni", "palay_yoy", "fish_yoy"]
NEWS = list(NEWSA) + ["nidx_QTD"]
INTER = ["poverty_x_food_since_threshold", "poverty_x_food_yoy"]
SETS = {"S0 state only": STATE, "A + market": STATE + MARKET, "B + poverty": STATE + POVERTY, "C + market + poverty": STATE + MARKET + POVERTY,
        "D + market + poverty + interactions": STATE + MARKET + POVERTY + INTER,
        "E all five triggers": STATE + MARKET + POVERTY + EMPLOY + CLIMATE + NEWS,
        "F all without market": STATE + POVERTY + EMPLOY + CLIMATE + NEWS, "G all without poverty": STATE + MARKET + EMPLOY + CLIMATE + NEWS,
        "H all without market and poverty": STATE + EMPLOY + CLIMATE + NEWS}
FAMILIES = ["ridge", "lgbm", "logit", "rf"]
LEADS = [1, 2, 3, 4]
REQ = {"high_recall": 0.60, "high_precision": 0.50, "low_recall": 0.85, "low_precision": 0.90, "balanced_accuracy": 0.70, "macro_f1": 0.70,
       "accuracy": 0.75, "ece_5bin": 0.10}
PROTOCOL = {"version": VERSION, "sets": SETS, "families": FAMILIES, "leads": LEADS, "class_requirements": REQ,
            "skill": "beat naive persistence on Brier (P >= 0.90) or balanced accuracy (P >= 0.90, macro-F1 not lower); quarter-block bootstrap",
            "robustness": ["2018+ balanced accuracy >= 0.70 and HIGH recall >= 0.50", "without sawtooth quarters balanced accuracy >= 0.65"],
            "complementarity": "C vs A and C vs B (paired); D vs C; E vs F, G, H; reported per family and lead",
            "selection": "per lead, highest balanced accuracy on targets <= 2017 among (set, family) with ECE <= 0.10; adoption judged on all targets",
            "periods": "targets 2010-Q1 .. 2026-Q3 (all historical quarters already examined in FI7-FI9; disclosed)"}


def _digest():
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def _code():
    return hashlib.sha256((BACKEND_DIR / "app" / "fi11" / "study.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _market_extra(dates) -> pd.DataFrame:
    c = pd.read_csv(BACKEND_DIR / "data" / "fi10" / "raw" / "cpi_monthly_long.csv")
    c = c[(c["geolocation"] == "Region IV-A (CALABARZON)") & (c["commodity_description"] == "01.1 - FOOD")].copy()
    c["ym"] = c["year"] * 12 + c["month"] - 1
    c["avail"] = [pd.Timestamp(year=(m + 1) // 12, month=(m + 1) % 12 + 1, day=10) for m in c["ym"]]
    c = c.sort_values("ym")
    c["yoy"] = (c["value"] / c["value"].shift(12) - 1) * 100
    rel = {y: pd.Timestamp(S5.POVERTY_RELEASE.get(y, f"{y + 2}-01-02")) for y in [2006, 2009, 2012, 2015, 2018, 2021, 2023, 2025]}
    rows = []
    for d in dates:
        k = c[c["avail"] <= d]
        if len(k) < 30:
            rows.append({"issue_ts": d})
            continue
        ry = max([y for y, r in rel.items() if r <= d], default=None)
        base = c[c["year"] == ry]["value"].mean() if ry else np.nan
        rows.append({"issue_ts": d, "food_since_threshold": float(k["value"].iloc[-1] / base - 1) * 100 if ry else np.nan,
                     "food_cum8": float(k["value"].iloc[-1] / k["value"].iloc[-25] - 1) * 100 if len(k) > 25 else np.nan,
                     "food_vol12": float(k["yoy"].tail(12).std(ddof=1))})
    return pd.DataFrame(rows)


def frame(h: int) -> pd.DataFrame:
    from app.fi7.design import Designer
    X = Designer("operational").frame(h).sort_values("issue_ts").reset_index(drop=True)
    nf = pd.read_csv(BACKEND_DIR / "data" / "fi9x" / "out" / "design_OP1.csv", parse_dates=["issue_ts"])[["issue_ts", "nidx_QTD"]].drop_duplicates("issue_ts")
    X = X.merge(nf, on="issue_ts", how="left").merge(_market_extra(X["issue_ts"]), on="issue_ts", how="left")
    X["gap"] = X["hunger_last"] - X["threshold_known"]
    return X[X["y"].notna()].reset_index(drop=True)


def _inter(tr, te):
    tr, te = tr.copy(), te.copy()
    z = lambda d, c: (d[c] - tr[c].mean()) / (tr[c].std(ddof=1) or 1)
    for name, (a, b) in {"poverty_x_food_since_threshold": ("poverty_inc", "food_since_threshold"), "poverty_x_food_yoy": ("poverty_inc", "cpi_food_yoy")}.items():
        tr[name], te[name] = z(tr, a) * z(tr, b), z(te, a) * z(te, b)
    return tr, te


def _cols(tr, feats):
    return [c for c in feats if tr[c].notna().sum() >= 10 and tr[c].nunique() > 1]


def _fit_predict(fam, feats, tr, te, prm=None):
    tr, te = _inter(tr, te)
    cols = _cols(tr, feats)
    y = tr["y"].to_numpy(int)
    if fam == "ridge":
        a = (prm or {}).get("alpha", 10.0)
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=a)).fit(tr[cols], tr["delta_target"])
        lv = te["hunger_last"].to_numpy(float) + m.predict(te[cols])
        return 1 - norm.cdf((te["threshold_known"].to_numpy(float) - lv) / (prm or {}).get("sd", 4.0))
    if fam == "lgbm":
        import lightgbm as lgb
        hp = {k: v for k, v in (prm or {}).items() if k != "sd"}
        m = lgb.LGBMRegressor(**hp, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(tr[cols], tr["delta_target"])
        lv = te["hunger_last"].to_numpy(float) + m.predict(te[cols])
        return 1 - norm.cdf((te["threshold_known"].to_numpy(float) - lv) / (prm or {}).get("sd", 4.0))
    if fam == "logit":
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=(prm or {}).get("C", 0.3), max_iter=5000)).fit(tr[cols], y)
        p = m.predict_proba(te[cols])[:, 1]
    else:
        m = make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(n_estimators=300, random_state=7, n_jobs=1,
                          **{k: v for k, v in (prm or {}).items() if k != "platt"})).fit(tr[cols], y)
        p = m.predict_proba(te[cols])[:, 1]
    s, i = (prm or {}).get("platt", [1.0, 0.0])
    q = np.clip(p, 1e-4, 1 - 1e-4)
    return 1 / (1 + np.exp(-(s * np.log(q / (1 - q)) + i)))


def _split(tr):
    qs = np.sort(tr["target_quarter"].unique())
    cut = qs[int(len(qs) * 0.75)]
    return tr[tr["target_quarter"] < cut], tr[tr["target_quarter"] >= cut]


def _tune(fam, feats, tr):
    a, b = _split(tr)
    yb = b["y"].to_numpy(int)
    ll = lambda p: float(-np.mean(yb * np.log(np.clip(p, 1e-6, 1)) + (1 - yb) * np.log(np.clip(1 - p, 1e-6, 1))))
    if fam in ("ridge", "lgbm"):
        aa, bb = _inter(a, b)
        cols = _cols(aa, feats)
        if fam == "ridge":
            best = min([1.0, 10.0, 100.0], key=lambda al: np.mean((bb["delta_target"] - make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=al)).fit(aa[cols], aa["delta_target"]).predict(bb[cols])) ** 2))
            m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=best)).fit(aa[cols], aa["delta_target"])
            prm = {"alpha": best}
        else:
            import lightgbm as lgb
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)

            def obj(t):
                pr = {"num_leaves": t.suggest_int("num_leaves", 3, 8), "min_child_samples": t.suggest_int("min_child_samples", 5, 20),
                      "learning_rate": t.suggest_float("learning_rate", 0.02, 0.15, log=True), "n_estimators": t.suggest_int("n_estimators", 30, 300),
                      "reg_lambda": t.suggest_float("reg_lambda", 0.1, 30, log=True)}
                mm = lgb.LGBMRegressor(**pr, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(aa[cols], aa["delta_target"])
                return float(np.mean((bb["delta_target"] - mm.predict(bb[cols])) ** 2))
            st = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
            st.optimize(obj, n_trials=15)
            prm = dict(st.best_params)
            m = lgb.LGBMRegressor(**prm, subsample=0.8, subsample_freq=1, random_state=7, verbose=-1).fit(aa[cols], aa["delta_target"])
        prm["sd"] = max(float(np.sqrt(np.mean((bb["delta_target"] - m.predict(bb[cols])) ** 2))), 1.0)
    elif fam == "logit":
        prm = min([{"C": c} for c in (0.03, 0.3, 3.0)], key=lambda pr: ll(_fit_predict("logit", feats, a, b, {**pr, "platt": [1.0, 0.0]})))
    else:
        grid = [{"max_depth": d, "min_samples_leaf": s} for d in (2, 3, 5) for s in (3, 8)]
        prm = min(grid, key=lambda pr: ll(_fit_predict("rf", feats, a, b, {**pr, "platt": [1.0, 0.0]})))
    if fam in ("logit", "rf"):
        p = _fit_predict(fam, feats, a, b, {**prm, "platt": [1.0, 0.0]})
        q = np.clip(p, 1e-4, 1 - 1e-4)
        if len(set(yb)) == 2:
            pl = LogisticRegression(C=1e4, max_iter=2000).fit(np.log(q / (1 - q)).reshape(-1, 1), yb)
            prm["platt"] = [float(pl.coef_[0][0]), float(pl.intercept_[0])]
    pb = _fit_predict(fam, feats, a, b, prm)
    best, tau = -1, 0.5
    if len(set(yb)) == 2:
        for t in np.linspace(0.05, 0.95, 91):
            ba = (np.mean(pb[yb == 1] >= t) + np.mean(pb[yb == 0] < t)) / 2
            if ba > best + 1e-9:
                best, tau = ba, float(t)
    return prm, tau


def _task(args):
    sname, fam, h = args
    X = frame(h)
    feats = SETS[sname]
    out, cache = [], {}
    for i in range(len(X)):
        r = X.loc[i]
        if r["target_quarter"] < "2010-Q1":
            continue
        tr = X[X["target_published"] <= r["issue_ts"]]
        if len(tr) < 30 or tr["y"].nunique() < 2:
            continue
        yr = r["issue_ts"].year
        if fam in ("ridge", "logit") or yr not in cache:
            cache[yr] = _tune(fam, feats, tr)
        prm, tau = cache[yr]
        p = float(_fit_predict(fam, feats, tr, X.loc[[i]], prm)[0])
        out.append({"set": sname, "family": fam, "lead": h, "target_quarter": r["target_quarter"], "y": int(r["y"]), "p": p, "cls": int(p >= tau), "tau": tau})
    return out


def _baselines(h):
    X = frame(h)
    rows = []
    for i in range(len(X)):
        r = X.loc[i]
        if r["target_quarter"] < "2010-Q1":
            continue
        tr = X[X["target_published"] <= r["issue_ts"]]
        if len(tr) < 30:
            continue
        te = X.loc[[i]]
        nv = M7.make("persist", []).fit(tr, tr["delta_target"].to_numpy(float))
        pn = float(nv.predict_proba(te)[0])
        c0 = M7.make("damped_tau", []).fit(tr, tr["delta_target"].to_numpy(float))
        for name, p, c in [("Naive persistence", pn, int(pn >= 0.5)), ("C0 damped persistence (production)", float(c0.predict_proba(te)[0]), int(c0.predict_class(te)[0])),
                           ("Always LOW", float(tr["y"].mean()), 0)]:
            rows.append({"set": name, "family": "baseline", "lead": h, "target_quarter": r["target_quarter"], "y": int(r["y"]), "p": p, "cls": c, "tau": None})
    return rows


def _boot(a, b, y, reps=5000, block=4, seed=7):
    from app.fi9z.study import _boot_ba, _boot_brier
    return {"brier": _boot_brier(a["p"].to_numpy(), b["p"].to_numpy(), y), "ba": _boot_ba(a["cls"].to_numpy(), b["cls"].to_numpy(), y)}


def evaluate(W) -> dict:
    saw = set(alternating_quarters())
    res = {"by_lead": {}, "complementarity": {}, "selection": {}}
    for h, G in W.groupby("lead"):
        piv = {(s, f): g.set_index("target_quarter").sort_index() for (s, f), g in G.groupby(["set", "family"])}
        nv = piv[("Naive persistence", "baseline")]
        R = {}
        for key, g in piv.items():
            common = g.index.intersection(nv.index)
            y = g.loc[common, "y"].to_numpy(int)
            yr = common.str[:4].astype(int)
            full = class_metrics(y, g.loc[common, "cls"], g.loc[common, "p"])
            dev = class_metrics(y[yr <= 2017], g.loc[common[yr <= 2017], "cls"], g.loc[common[yr <= 2017], "p"])
            b = class_metrics(y[yr >= 2018], g.loc[common[yr >= 2018], "cls"], g.loc[common[yr >= 2018], "p"])
            m = ~common.isin(saw)
            ns = class_metrics(y[m], g.loc[common[m], "cls"], g.loc[common[m], "p"])
            vs = _boot(g.loc[common], nv.loc[common], y) if key != ("Naive persistence", "baseline") else None
            chk = {**{f"{k}_ok": (full[k] or 0) >= v if k != "ece_5bin" else (full[k] is not None and full[k] <= v) for k, v in REQ.items()},
                   "skill_vs_naive": bool(vs and ((vs["brier"]["mean"] < 0 and vs["brier"]["p_better"] >= 0.90) or
                                                  (vs["ba"]["mean"] > 0 and vs["ba"]["p_better"] >= 0.90 and full["macro_f1"] >= class_metrics(y, nv.loc[common, "cls"])["macro_f1"]))),
                   "robust_2018plus": (b["balanced_accuracy"] or 0) >= 0.70 and (b["high_recall"] or 0) >= 0.50,
                   "robust_without_sawtooth": (ns["balanced_accuracy"] or 0) >= 0.65}
            R[f"{key[0]} | {key[1]}"] = {"n": len(common), "full": full, "dev_le_2017": dev, "b_2018plus": b, "without_sawtooth": ns, "vs_naive": vs,
                                          "checks": chk, "passes": all(chk.values()), "n_failed": sum(not v for v in chk.values())}
        res["by_lead"][int(h)] = R
        comp = {}
        for fam in FAMILIES:
            for a, b in [("C + market + poverty", "A + market"), ("C + market + poverty", "B + poverty"), ("D + market + poverty + interactions", "C + market + poverty"),
                         ("E all five triggers", "F all without market"), ("E all five triggers", "G all without poverty"),
                         ("E all five triggers", "H all without market and poverty"), ("A + market", "S0 state only"), ("B + poverty", "S0 state only"),
                         ("E all five triggers", "C + market + poverty")]:
                if (a, fam) in piv and (b, fam) in piv:
                    ga, gb = piv[(a, fam)], piv[(b, fam)]
                    common = ga.index.intersection(gb.index)
                    comp[f"{fam}: {a} vs {b}"] = _boot(ga.loc[common], gb.loc[common], ga.loc[common, "y"].to_numpy(int))
        res["complementarity"][int(h)] = comp
        cand = {k: v for k, v in R.items() if not k.endswith("baseline") and (v["dev_le_2017"]["ece_5bin"] or 1) <= 0.10}
        best = max(cand, key=lambda k: (cand[k]["dev_le_2017"]["balanced_accuracy"] or 0)) if cand else None
        res["selection"][int(h)] = {"selected": best, "adopt": bool(best and R[best]["passes"]),
                                    "failed": [k for k, v in R[best]["checks"].items() if not v] if best else None,
                                    "any_configuration_passing": [k for k, v in R.items() if v["passes"]]}
    ok = [h for h, s in res["selection"].items() if s["adopt"]]
    res["max_reliable_lead"] = max(ok) if ok else None
    return res


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code():
        raise RuntimeError("FI11 protocol or code changed after lock")
    tasks = [(s, f, h) for h in LEADS for s in SETS for f in FAMILIES]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        rows = [r for part in ex.map(_task, tasks) for r in part]
        rows += [r for part in ex.map(_baselines, LEADS) for r in part]
    W = pd.DataFrame(rows)
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
        p.write_text(json.dumps({"sha256": _digest(), "code_sha256": _code(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        r = run()
        print({h: s for h, s in r["selection"].items()}, "max reliable lead:", r["max_reliable_lead"])
