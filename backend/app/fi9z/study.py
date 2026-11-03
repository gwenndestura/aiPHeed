"""FI9-Z locked class-sensitive study: can HIGH be identified better without losing LOW, at the real issue timing?

    python -m app.fi9z.study lock
    python -m app.fi9z.study run

Rows: the FI9-X design frames (OP1 = FI9 issue timing, lead 1; OP2 = lead 2), identical issue dates, cutoffs and
targets (2010-Q1 ..). Baselines are the FI9-X walk-forward predictions for the same rows.
New candidates (all fitted at every origin on rows whose targets were published by the issue date):
    Z1  class-weighted logistic (L2), SWS state only: gap = latest - significance line, anomaly, age, round MOE
    Z2  class-weighted elastic-net logistic: SWS state + government + world prices
    Z3  Z2 + news at issue timing (quarter-to-date stress index and event types)
    Z4  damped persistence, cost-sensitive threshold (missed HIGH costs 3 false alarms), chosen on earlier rows
    Z5  naive persistence, same cost-sensitive threshold rule
    Z6  class-weighted constrained LightGBM classifier: SWS state + government + world prices
    Z7  Z6 + news
Class-weighted models classify at p >= 0.5 (the weighting already balances the classes; no second adjustment).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi6 import models as M6
from app.fi6.features import GOV
from app.fi7 import models as M7
from app.fi7.experiments import WORLD, alternating_quarters
from app.fi9z import OUT, VERSION
from app.fi9z.classmetrics import class_metrics
from app.paths import BACKEND_DIR

X9 = BACKEND_DIR / "data" / "fi9x" / "out"
STATE = ["gap", "hunger_last_anom", "hunger_age_q", "moe_last"]
NEWS = ["nidx_QTD", "z_hard_QTD", "z_warn_QTD", "z_resp_QTD", "z_disr_QTD", "z_netdir_QTD"]
GOVW = GOV + WORLD
CANDIDATES = {"Z1 class-weighted logistic (SWS state)": ("logit_w", STATE),
              "Z2 class-weighted elastic net (SWS state + government)": ("enet_w", STATE + GOVW),
              "Z3 class-weighted elastic net (SWS state + government + news)": ("enet_w", STATE + GOVW + NEWS),
              "Z4 damped persistence, cost-sensitive threshold": ("cost", "damped"),
              "Z5 naive persistence, cost-sensitive threshold": ("cost", "persist"),
              "Z6 class-weighted LightGBM (SWS state + government)": ("lgbm_w", STATE + GOVW),
              "Z7 class-weighted LightGBM (SWS state + government + news)": ("lgbm_w", STATE + GOVW + NEWS)}
BASELINES = ["Always LOW", "Always HIGH", "Naive persistence", "C0 damped persistence (production)", "Damped persistence",
             "Seasonal damped persistence", "LightGBM (government)", "LightGBM (government + news R1)"]
COUNTERPART = {"Z3 class-weighted elastic net (SWS state + government + news)": "Z2 class-weighted elastic net (SWS state + government)",
               "Z7 class-weighted LightGBM (SWS state + government + news)": "Z6 class-weighted LightGBM (SWS state + government)"}
COST_FN = 3.0
PROTOCOL = {
    "version": VERSION,
    "origins": {"OP1": "FI9 issue timing (end of the quarter's 2nd month), lead 1", "OP2": "same issue timing, lead 2"},
    "candidates": {k: str(v) for k, v in CANDIDATES.items()},
    "class_requirements": {
        "high_recall": 0.60, "high_precision": 0.50, "low_recall": 0.85, "low_precision": 0.90,
        "balanced_accuracy": 0.70, "macro_f1": 0.70, "accuracy": 0.75, "ece_5bin": 0.10,
        "rationale": "HIGH recall >= 0.60: an early warning must catch most HIGH quarters (>= 7 of 11). HIGH precision >= 0.50: at most "
                     "one false alarm per true alarm. LOW recall >= 0.85: false HIGH rate <= 15 %. LOW precision >= 0.90: a LOW call is "
                     "trustworthy. Balanced accuracy and macro-F1 >= 0.70 so neither class carries the score. 75 % accuracy is the "
                     "thesis target, necessary but not sufficient. Fixed before any FI9-Z candidate was scored; all FI9-X and earlier "
                     "historical results were already known (disclosed)."},
    "skill_requirement": "beat naive persistence: Brier difference P(better) >= 0.90, OR balanced accuracy higher with block-bootstrap "
                         "P >= 0.90 and macro-F1 not lower; AND not worse than production C0 on balanced accuracy",
    "robustness": ["2018+ subset: balanced accuracy >= 0.70 and HIGH recall >= 0.50",
                   "without the FI7 sawtooth quarters: balanced accuracy >= 0.65",
                   "dropping any single quarter keeps the balanced-accuracy advantage over naive persistence >= 0"],
    "news_requirement": "a news candidate must beat its no-news counterpart on Brier (P >= 0.90) or on balanced accuracy (P >= 0.90)",
    "lead_rule": "the maximum reliable lead is the longest lead with a configuration meeting every class, skill and robustness requirement",
    "historical_status": "all historical quarters were seen in earlier studies; an adopted model is still provisional until "
                         "prospective forecasts meet the same requirements",
}


def _digest():
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def _code():
    return hashlib.sha256((BACKEND_DIR / "app" / "fi9z" / "study.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def frame(origin: str) -> pd.DataFrame:
    X = pd.read_csv(X9 / f"design_{origin}.csv", parse_dates=["issue_ts", "target_published"])
    X = X[X["y"].notna()].sort_values("issue_ts").reset_index(drop=True)
    X["gap"] = X["hunger_last"] - X["threshold_known"]
    return X


def _usable(tr, cols):
    return [c for c in cols if tr[c].notna().sum() >= 5 and tr[c].nunique() > 1]


def _fit(kind, feats, tr, te):
    y = tr["y"].to_numpy(int)
    if kind in ("logit_w", "enet_w"):
        cols = _usable(tr, feats)
        lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=5000) if kind == "logit_w" else \
            LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=0.5, C=0.5, class_weight="balanced", max_iter=10000)
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), lr).fit(tr[cols], y)
        ptr = m.predict_proba(tr[cols])[:, 1]
        p = float(m.predict_proba(te[cols])[0, 1])
        return {"p": p, "cls": int(p >= 0.5), "tr_acc": float(((ptr >= 0.5) == y).mean())}
    if kind == "lgbm_w":
        import lightgbm as lgb
        cols = _usable(tr, feats)
        m = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.05, num_leaves=4, max_depth=2, min_child_samples=5,
                               subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, class_weight="balanced",
                               random_state=7, verbose=-1).fit(tr[cols], y)
        ptr = m.predict_proba(tr[cols])[:, 1]
        p = float(m.predict_proba(te[cols])[0, 1])
        return {"p": p, "cls": int(p >= 0.5), "tr_acc": float(((ptr >= 0.5) == y).mean())}
    raise ValueError(kind)


def _base_p(kind, tr, te):
    m = (M7.make("damped", []) if kind == "damped" else M6.make("persist", None)).fit(tr, tr["delta_target"].to_numpy(float))
    return float(m.predict_proba(te)[0])


def _cost_tau(p, y):
    best, tau = None, 0.5
    for t in np.linspace(0.05, 0.95, 91):
        c = COST_FN * np.sum((p < t) & (y == 1)) + np.sum((p >= t) & (y == 0))
        if best is None or c < best - 1e-9:
            best, tau = c, float(t)
    return tau


def _task(args):
    origin, name = args
    X = frame(origin)
    kind, feats = CANDIDATES[name]
    out = []
    if kind == "cost":
        wf = {}
        for i in range(len(X)):
            tr = X[X["target_published"] <= X.loc[i, "issue_ts"]]
            if len(tr) >= 25:
                wf[i] = _base_p(feats, tr, X.loc[[i]])
        for i, p in wf.items():
            if X.loc[i, "target_quarter"] < "2010-Q1":
                continue
            tr_idx = [j for j in wf if X.loc[j, "target_published"] <= X.loc[i, "issue_ts"]]
            inn = tr_idx[max(25, int(len(tr_idx) * 0.6)):] if len(tr_idx) > 30 else tr_idx
            tau = _cost_tau(np.array([wf[j] for j in inn]), X.loc[inn, "y"].to_numpy(int)) if len(inn) >= 10 else 0.5
            out.append({"origin": origin, "config": name, "target_quarter": X.loc[i, "target_quarter"], "y": int(X.loc[i, "y"]),
                        "p": p, "cls": int(p >= tau), "tau": tau})
        return out
    for i in range(len(X)):
        if X.loc[i, "target_quarter"] < "2010-Q1":
            continue
        tr = X[X["target_published"] <= X.loc[i, "issue_ts"]]
        if len(tr) < 25 or tr["y"].nunique() < 2:
            continue
        r = _fit(kind, feats, tr, X.loc[[i]])
        out.append({"origin": origin, "config": name, "target_quarter": X.loc[i, "target_quarter"], "y": int(X.loc[i, "y"]), **r})
    return out


def _boot_ba(a, b, y, reps=5000, block=4, seed=7):
    rng = np.random.default_rng(seed)
    n = len(y)
    starts = np.arange(n - block + 1)
    d = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, int(np.ceil(n / block)))])[:n]
        yy = y[idx]
        if 0 < yy.sum() < n:
            ba = lambda c: (np.mean(c[idx][yy == 1] == 1) + np.mean(c[idx][yy == 0] == 0)) / 2
            d.append(ba(a) - ba(b))
    d = np.array(d)
    return {"mean": float(np.mean(d)), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "p_better": float(np.mean(d > 0))}


def _boot_brier(a, b, y, reps=5000, block=4, seed=7):
    from app.fi7.experiments import boot_delta
    r = boot_delta((a - y) ** 2, (b - y) ** 2, reps, block, seed)
    return {"mean": r["mean"], "ci95": r["ci95"], "p_better": r["p_negative"]}


def evaluate(W: pd.DataFrame) -> dict:
    saw = set(alternating_quarters())
    R = PROTOCOL["class_requirements"]
    res = {}
    for origin, G in W.groupby("origin"):
        piv = {c: g.set_index("target_quarter").sort_index() for c, g in G.groupby("config")}
        nv, c0 = piv["Naive persistence"], piv["C0 damped persistence (production)"]
        res[origin] = {}
        for c, g in piv.items():
            common = g.index.intersection(nv.index)
            y = g.loc[common, "y"].to_numpy(int)
            full = class_metrics(y, g.loc[common, "cls"], g.loc[common, "p"])
            yr = pd.Series(common.str[:4].astype(int), index=common)
            sub = lambda m: class_metrics(g.loc[common[m], "y"], g.loc[common[m], "cls"], g.loc[common[m], "p"])
            b = sub((yr >= 2018).to_numpy())
            ns = sub(~common.isin(saw))
            vs_nv_brier = _boot_brier(g.loc[common, "p"].to_numpy(), nv.loc[common, "p"].to_numpy(), y)
            vs_nv_ba = _boot_ba(g.loc[common, "cls"].to_numpy(), nv.loc[common, "cls"].to_numpy(), y)
            nvm = class_metrics(y, nv.loc[common, "cls"], nv.loc[common, "p"])
            c0m = class_metrics(y, c0.loc[common, "cls"], c0.loc[common, "p"])
            drop = []
            for k in range(len(common)):
                m = np.ones(len(common), bool)
                m[k] = False
                a = class_metrics(y[m], g.loc[common, "cls"].to_numpy()[m])["balanced_accuracy"]
                bb = class_metrics(y[m], nv.loc[common, "cls"].to_numpy()[m])["balanced_accuracy"]
                drop.append((a or 0) - (bb or 0))
            chk = {
                **{f"{k}_ok": (full[k] or 0) >= v if k != "ece_5bin" else (full[k] is not None and full[k] <= v) for k, v in R.items() if k != "rationale"},
                "skill_vs_naive": (vs_nv_brier["mean"] < 0 and vs_nv_brier["p_better"] >= 0.90)
                                  or (vs_nv_ba["mean"] > 0 and vs_nv_ba["p_better"] >= 0.90 and full["macro_f1"] >= nvm["macro_f1"]),
                "not_worse_than_C0_balanced_accuracy": (full["balanced_accuracy"] or 0) >= (c0m["balanced_accuracy"] or 0),
                "robust_2018plus": (b["balanced_accuracy"] or 0) >= 0.70 and (b["high_recall"] or 0) >= 0.50,
                "robust_without_sawtooth": (ns["balanced_accuracy"] or 0) >= 0.65,
                "robust_drop_one_quarter": min(drop) >= 0}
            if c in COUNTERPART and COUNTERPART[c] in piv:
                cp = piv[COUNTERPART[c]].loc[common]
                nb = _boot_brier(g.loc[common, "p"].to_numpy(), cp["p"].to_numpy(), y)
                na = _boot_ba(g.loc[common, "cls"].to_numpy(), cp["cls"].to_numpy(), y)
                chk["news_beats_counterpart"] = (nb["mean"] < 0 and nb["p_better"] >= 0.90) or (na["mean"] > 0 and na["p_better"] >= 0.90)
                news = {"brier": nb, "balanced_accuracy": na}
            else:
                news = None
            res[origin][c] = {"n": len(common), "full": full, "b_2018plus": b, "without_sawtooth": ns, "vs_naive_brier": vs_nv_brier,
                              "vs_naive_balanced_accuracy": vs_nv_ba, "vs_counterpart_news": news, "drop_one_min_ba_diff": float(min(drop)),
                              "train_acc_mean": float(g["tr_acc"].mean()) if "tr_acc" in g and g["tr_acc"].notna().any() else None,
                              "checks": {k: bool(v) for k, v in chk.items()}, "passes_all": bool(all(chk.values())),
                              "n_failed": int(sum(not v for v in chk.values()))}
    return res


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code():
        raise RuntimeError("FI9-Z protocol or code changed after the lock")
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        rows = [r for part in ex.map(_task, [(o, c) for o in ("OP1", "OP2") for c in CANDIDATES]) for r in part]
    Z = pd.DataFrame(rows)
    B = pd.read_csv(X9 / "predictions.csv")
    B = B[B["origin"].isin(["OP1", "OP2"]) & B["config"].isin(BASELINES)][["origin", "config", "target_quarter", "y", "p", "cls", "tr_acc"]]
    W = pd.concat([B, Z], ignore_index=True)
    W.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n")
    E = evaluate(W)
    passing = {o: [c for c, v in E[o].items() if v["passes_all"]] for o in E}
    lead = max([int(o[-1]) for o in ("OP1", "OP2") if passing.get(o)], default=None)
    res = {"protocol_sha256": lock["sha256"], "evaluation": E, "passing": passing, "max_reliable_lead": lead,
           "decision": (f"adopt candidate(s) {passing['OP1']}" if passing.get("OP1") else "no configuration meets the class-specific, skill and robustness requirements; production C0 retained")}
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
        print(r["decision"], "| max reliable lead:", r["max_reliable_lead"])
