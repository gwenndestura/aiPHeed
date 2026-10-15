"""E38: nested tuning of the next-quarter (lead 2) LightGBM (PROTOCOL.md sections 3-4). Inputs, labels, origins and
the six baselines are E37's; only the proposed model's pool, the prior-shift adjustment and the inner threshold
rule are new."""
from __future__ import annotations

import json
import math
import sys
import warnings
from pathlib import Path

E38 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E38.parent / "E37_Next_Quarter_Forecast" / "runner"))
import e37_lib as L7  # noqa: E402

L7.L6.guard32.EXP = E38
L6, C, np, pd = L7.L6, L7.C, L7.np, L7.pd
qk, qs, PROVS = C.qk, C.qs, C.PROVS
K = 2
ROOT = E38.parents[2]
TRIG = ["market", "climate", "employment", "ofw_remittance", "fish_kill"]
TRIG_COLS = [f"trig_{x}" for x in TRIG]
FEATURE_SETS = {"COMPACT": L6.COMPACT, "COMB": L6.COMB, "COMB_T5": L6.COMB + TRIG_COLS}
GRID = {"G1": L6.GRID["G1"], "G3": L6.GRID["G3"],
        "G5": dict(num_leaves=2, max_depth=1, min_child_samples=10, n_estimators=60, learning_rate=0.05,
                   reg_lambda=5.0, reg_alpha=1.0, colsample_bytree=1.0),
        "G6": dict(num_leaves=2, max_depth=1, min_child_samples=5, n_estimators=100, learning_rate=0.05,
                   reg_lambda=1.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8)}
BASE = {k: v for k, v in L6._BASE.items() if k not in ("bagging_fraction", "bagging_freq")}
ADJ = ["none", "prior_shift"]
FS_ORDER, G_ORDER = ["COMPACT", "COMB", "COMB_T5"], ["G1", "G5", "G6", "G3"]
POOL = [(a, fs, g) for a in ADJ for fs in FS_ORDER for g in G_ORDER]          # simplicity order (PROTOCOL 3)
DEFAULT = ("none", "COMB", "G1")
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]
TIE = 0.002
MIN_PRIOR = 3


def name(c) -> str:
    return f"{c[1]}x{c[2]}" + ("+PS" if c[0] == "prior_shift" else "")


class Data(L7.Data):
    """E37 data plus the five trigger proportions per province and publication quarter (existing classifier)."""

    def __init__(self):
        super().__init__()
        sys.path.insert(0, str(ROOT / "backend"))
        from app.ml.nlp.trigger_classifier import classify_triggers

        rows = [json.loads(x) for x in open(C.STORE / "articles.jsonl", encoding="utf-8")]
        a = pd.DataFrame(rows)
        a = a[a["geo_province_code"].notna() & (a["quarter"].map(qk) <= qk(C.LAST))].copy()
        tr = a["title"].fillna("").map(classify_triggers)
        for x in TRIG:
            a[f"trig_{x}"] = tr.map(lambda t, x=x: int(x in t))
        g = a.groupby(["geo_province_code", "quarter"])[TRIG_COLS].mean()
        self.trig = {(p, qk(q)): r.to_dict() for (p, q), r in g.iterrows()}

    def _add(self, X: pd.DataFrame, tcol: str) -> pd.DataFrame:
        X = X.copy()
        for c in TRIG_COLS:
            X[c] = [self.trig.get((p, int(t)), {}).get(c, 0.0) for p, t in zip(X["province_code"], X[tcol])]
        return X

    def train(self, t, k=K):
        tr = super().train(t, k)
        return tr if tr.empty else self._add(tr, "t")

    def test(self, t, k=K):
        return self._add(super().test(t, k), "t")


def _logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def recent_rate(d: Data, t: int) -> float:
    posted = [q for q in d.posted_quarters(L7.origin(t)) if q <= t - 1][-4:]
    ys = [d.label(p, q, t) for q in posted for p in PROVS]
    ys = [y for y in ys if y is not None]
    return (sum(ys) + 1) / (len(ys) + 2)


def fit_predict(tr, te, feats, g):
    import lightgbm as lgb

    y = tr["y"].to_numpy(int)
    if len(set(y)) < 2:
        r = (y.sum() + 1) / (len(y) + 2)
        return {p: float(r) for p in te["province_code"]}, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = lgb.LGBMClassifier(**BASE, **GRID[g]).fit(tr[feats].astype(float), y)
        pr = m.predict_proba(te[feats].astype(float))[:, 1]
    return dict(zip(te["province_code"], pr.astype(float))), m


def pool_predictions(d: Data, t: int) -> dict:
    tr, te = d.train(t), d.test(t)
    shift = _logit(recent_rate(d, t)) - _logit((tr["y"].sum() + 1) / (len(tr) + 2))
    out = {}
    for fs in FS_ORDER:
        for g in G_ORDER:
            base, _ = fit_predict(tr, te, FEATURE_SETS[fs], g)
            out[name(("none", fs, g))] = base
            out[name(("prior_shift", fs, g))] = {p: 1 / (1 + math.exp(-(_logit(v) + shift))) for p, v in base.items()}
    out["_shift"] = shift
    return out


def per_date_brier(pr: dict, lab: dict) -> float:
    return float(np.mean([(pr[p] - lab[p]) ** 2 for p in PROVS]))


def choose(prior, preds, labels):
    if len(prior) < MIN_PRIOR:
        return DEFAULT, {"rule": "default (fewer than 3 eligible prior dates)"}
    sc = {name(c): float(np.mean([per_date_brier(preds[tj][name(c)], labels[tj]) for tj in prior])) for c in POOL}
    best = min(sc.values())
    return next(c for c in POOL if sc[name(c)] <= best + TIE), {"rule": "lowest mean per-date Brier (tie 0.002)",
                                                               "scores": sc}


def threshold(prior, preds, labels, cfg) -> tuple[float, dict]:
    ys = [labels[tj][p] for tj in prior for p in PROVS]
    if sum(1 for y in ys if y == 0) < 3:
        return 0.5, {"rule": "0.5 (fewer than 3 LOW rows on prior dates)"}
    ps = [preds[tj][name(cfg)][p] for tj in prior for p in PROVS]
    res = {}
    for th in THRESHOLDS:
        yh = [int(p >= th) for p in ps]
        hi = [a == b for a, b in zip(yh, ys) if b == 1]
        lo = [a == b for a, b in zip(yh, ys) if b == 0]
        res[th] = (np.mean(hi) + np.mean(lo)) / 2
    best = max(res.values())
    th = min((x for x in THRESHOLDS if res[x] >= best - 1e-12), key=lambda x: (abs(x - 0.5), x))
    return th, {"rule": "max balanced accuracy on prior dates (>= 3 LOW rows)", "balanced_accuracy": res}


def walk_forward(d: Data):
    dates = L7.eval_dates(d, K)
    preds, labels = {}, {}
    for t in dates:
        preds[t] = pool_predictions(d, t)
        labels[t] = {p: d.label(p, t + K, t) for p in PROVS}
    rows, path = [], {}
    for t in dates:
        prior = L7.eligible_prior(d, t, K, dates)
        cfg, info = choose(prior, preds, labels)
        th, tinfo = threshold(prior, preds, labels, cfg)
        path[qs(t + K)] = {"chosen": name(cfg), "threshold": th, "prior_dates": [qs(x + K) for x in prior],
                           "selection": info, "threshold_rule": tinfo, "prior_shift_logodds": preds[t]["_shift"]}
        for p in PROVS:
            rows.append({"lead": K, "t": qs(t), "origin": str(L7.origin(t).date()), "target_quarter": qs(t + K),
                         "province_code": p, "arm": "E38-LGBM", "p": float(preds[t][name(cfg)][p]), "threshold": th,
                         "y": int(labels[t][p])})
            for c in POOL:                      # every configuration, for the record (fixed, without selection)
                rows.append({"lead": K, "t": qs(t), "origin": str(L7.origin(t).date()), "target_quarter": qs(t + K),
                             "province_code": p, "arm": "FIXED:" + name(c), "p": float(preds[t][name(c)][p]),
                             "threshold": 0.5, "y": int(labels[t][p])})
    return pd.DataFrame(rows), {"dates": [qs(t + K) for t in dates], "path": path}


def operational(d: Data, Pr: pd.DataFrame):
    """Configuration and threshold the rule picks at O(2026-Q3) = 2026-10-01 for 2027-Q1."""
    t = L7.OPERATIONAL_T
    dates = sorted({qk(x) for x in Pr["t"].unique()})
    prior = L7.eligible_prior(d, t, K, dates)
    preds, labels = {}, {}
    for tj in prior:
        s = Pr[(Pr["t"] == qs(tj)) & Pr["arm"].str.startswith("FIXED:")]
        preds[tj] = {a[6:]: dict(zip(g["province_code"], g["p"])) for a, g in s.groupby("arm")}
        e = s[s["arm"] == "FIXED:" + name(DEFAULT)]
        labels[tj] = dict(zip(e["province_code"], e["y"]))
    cfg, info = choose(prior, preds, labels)
    th, tinfo = threshold(prior, preds, labels, cfg)
    return cfg, th, {"prior_dates": [qs(x + K) for x in prior], "selection": info, "threshold_rule": tinfo}
