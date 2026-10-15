"""E39 prediction procedures A-G and scoring-v2 (scoring_v2_spec.json), for Label A (Food Price Pressure HIGH),
Target B (provincial food CPI YoY) and Target C (regional SWS hunger), leads 1 and 2. The as-of features are E36's
(E32 construction, reused unchanged); only y_last is redefined as each target's own latest published value."""
from __future__ import annotations

import json
import math
import sys
import warnings
from functools import lru_cache
from pathlib import Path

E39 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E39.parent / "E37_Next_Quarter_Forecast" / "runner"))
sys.path.insert(0, str(E39.parent / "E31_Chapter1_Completion" / "runner"))
import e37_lib as L7  # noqa: E402

L7.L6.guard32.EXP = E39                      # writes confined to E39 (and the OS temp directory)
import e28_metrics as M  # noqa: E402

L6, C, np, pd = L7.L6, L7.C, L7.np, L7.pd
qk, qs, PROVS, NAMES = C.qk, C.qs, C.PROVS, C.NAMES
THRESHOLD = 4.0
GOV, NLP, COMB, COMPACT = L6.GOV, L6.NLP, L6.COMB, L6.COMPACT
BASE = dict(n_jobs=1, random_state=36, deterministic=True, force_col_wise=True, verbose=-1)
HP = {1: dict(num_leaves=4, max_depth=-1, min_child_samples=5, n_estimators=150, learning_rate=0.05, reg_lambda=0.0,
              colsample_bytree=0.8),
      2: dict(num_leaves=2, max_depth=1, min_child_samples=10, n_estimators=60, learning_rate=0.05, reg_lambda=5.0,
              reg_alpha=1.0, colsample_bytree=1.0)}
FEATS = {1: COMB, 2: COMPACT}                # E36 operational (lead 1) / E38 operational (lead 2)
MIN_PRIOR = 8
SHRINK = 0.5
TARGETS = ("A", "B", "C")
FIRST_TARGET = qk("2021-Q3")
LAST_OBS = qk("2026-Q3")


class Data(L7.Data):
    def __init__(self, label_csv: Path | None = None):
        super().__init__()
        lab = pd.read_csv(label_csv or (E39 / "label_v2.csv"), dtype={"province_code": str})
        self.F = {(r.province_code, qk(r.quarter)): float(r.F) for r in lab.itertuples()}
        self.Hq = {qk(q): float(h) for q, h in lab.dropna(subset=["H"]).groupby("quarter")["H"].first().items()}

    # ---------------------------------------------------------------- targets and their availability
    def target(self, kind: str, p: str, q: int):
        if kind == "A":
            f = self.F.get((p, q))
            return None if f is None else int(f > THRESHOLD)
        if kind == "B":
            return self.F.get((p, q))
        return self.Hq.get(q)

    def available(self, kind: str, q: int, t: int) -> bool:
        """Is the target value of quarter q published before O(t)?"""
        if q > t - 1:
            return False
        if kind in ("A", "B"):
            return (PROVS[0], q) in self.F
        return q in set(self.posted_quarters(L7.origin(t)))

    def latest(self, kind: str, p: str, t: int):
        """The target's own latest published value at O(t) (the redefined y_last)."""
        if kind in ("A", "B"):
            return self.target(kind, p, t - 1)
        posted = [q for q in self.posted_quarters(L7.origin(t)) if q <= t - 1 and q in self.Hq]
        return self.Hq[posted[-1]] if posted else None

    # ---------------------------------------------------------------- features and training rows
    @lru_cache(maxsize=4096)
    def X(self, kind: str, t: int, k: int) -> pd.DataFrame:
        X = self.features(t, k).copy()
        X["y_last"] = [self.latest(kind, p, t) for p in X["province_code"]]
        X["y_last"] = X["y_last"].astype(float)
        return X

    def train(self, kind: str, t: int, k: int, feats: list[str]) -> pd.DataFrame:
        rows = []
        for tp in range(qk("2021-Q2"), t - k + 1):
            q = tp + k
            if not self.available(kind, q, t):
                continue
            try:
                X = self.X(kind, tp, k)
            except (IndexError, KeyError, ValueError):
                continue
            ys = [self.target(kind, p, q) for p in X["province_code"]]
            X = X.assign(y=ys, target_q=q)
            rows.append(X[X["y"].notna()])
        if not rows:
            return pd.DataFrame()
        tr = pd.concat(rows, ignore_index=True)
        return tr.dropna(subset=feats).reset_index(drop=True)


# ==================================================================== models
def _lgbm(kind, tr, te, feats, k):
    import lightgbm as lgb

    y = tr["y"].to_numpy(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if kind == "A":
            if len(set(y.astype(int))) < 2:
                r = (y.sum() + 1) / (len(y) + 2)
                return {p: float(r) for p in te["province_code"]}
            m = lgb.LGBMClassifier(objective="binary", **BASE, **HP[k]).fit(tr[feats].astype(float), y.astype(int))
            pr = m.predict_proba(te[feats].astype(float))[:, 1]
        else:
            m = lgb.LGBMRegressor(objective="regression", **BASE, **HP[k]).fit(tr[feats].astype(float), y)
            pr = m.predict(te[feats].astype(float))
    return dict(zip(te["province_code"], pr.astype(float)))


def _linear(kind, tr, te, feats):
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.preprocessing import StandardScaler

    y = tr["y"].to_numpy(float)
    X = tr[feats].to_numpy(float)
    sc = StandardScaler().fit(X)
    Zt = np.nan_to_num(sc.transform(te[feats].to_numpy(float)), nan=0.0)
    if kind == "A":
        if len(set(y.astype(int))) < 2:
            r = (y.sum() + 1) / (len(y) + 2)
            return {p: float(r) for p in te["province_code"]}
        m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(X), y.astype(int))
        return dict(zip(te["province_code"], m.predict_proba(Zt)[:, 1].astype(float)))
    m = Ridge(alpha=1.0).fit(sc.transform(X), y)
    return dict(zip(te["province_code"], m.predict(Zt).astype(float)))


def _ar1(kind, tr, te):
    from sklearn.linear_model import LinearRegression, LogisticRegression

    ok = tr["y_last"].notna()
    x, y = tr.loc[ok, ["y_last"]].to_numpy(float), tr.loc[ok, "y"].to_numpy(float)
    xt = te[["y_last"]].to_numpy(float)
    xt = np.where(np.isnan(xt), np.nanmean(x), xt)
    if kind == "A":
        if len(set(y.astype(int))) < 2:
            r = (y.sum() + 1) / (len(y) + 2)
            return {p: float(r) for p in te["province_code"]}
        m = LogisticRegression(C=1.0, max_iter=5000).fit(x, y.astype(int))
        return dict(zip(te["province_code"], m.predict_proba(xt)[:, 1].astype(float)))
    m = LinearRegression().fit(x, y)
    return dict(zip(te["province_code"], m.predict(xt).astype(float)))


def baselines(d: Data, kind: str, t: int, k: int, tr: pd.DataFrame, te: pd.DataFrame) -> dict:
    out = {}
    q = t + k
    clim = (tr["y"].sum() + 1) / (len(tr) + 2) if kind == "A" else float(tr["y"].mean())
    out["climatology"] = {p: float(clim) for p in te["province_code"]}
    out["persistence"] = {p: (float(v) if v == v and v is not None else float(clim))
                          for p, v in zip(te["province_code"], te["y_last"])}
    sn = {}
    for p in te["province_code"]:
        v = d.target(kind, p, q - 4) if d.available(kind, q - 4, t) else None
        sn[p] = float(v) if v is not None else out["persistence"][p]
    out["seasonal_naive"] = sn
    out["AR1"] = _ar1(kind, tr, te)
    if kind == "A":
        out["always_LOW"] = {p: 0.0 for p in te["province_code"]}
        out["always_HIGH"] = {p: 1.0 for p in te["province_code"]}
    for name, feats in (("B2_LR_COMB", COMB), ("B3_LR_GOV", GOV), ("B4_LR_NLP", NLP)):
        tr2 = tr.dropna(subset=feats)
        out[name] = _linear(kind, tr2, te, feats)
    for name, feats in (("B5_LGBM_GOV", GOV), ("B6_LGBM_NLP", NLP)):
        out[name] = _lgbm(kind, tr.dropna(subset=feats), te, feats, k)
    return out


# ==================================================================== calibration and intervals (procedures C, E)
def calibrate(raw: dict, prior: list[tuple[float, int]], prior_dates: int, clim: float) -> tuple[dict, str]:
    """E: Platt (L2, C=1) on earlier walk-forward (raw P, outcome) pairs; else shrinkage to climatology."""
    ys = {y for _, y in prior}
    if prior_dates >= MIN_PRIOR and ys == {0, 1}:
        from sklearn.linear_model import LogisticRegression

        x = np.array([[math.log(max(min(p, 1 - 1e-6), 1e-6) / (1 - max(min(p, 1 - 1e-6), 1e-6)))] for p, _ in prior])
        m = LogisticRegression(C=1.0, max_iter=5000).fit(x, np.array([y for _, y in prior]))
        z = lambda v: [[math.log(max(min(v, 1 - 1e-6), 1e-6) / (1 - max(min(v, 1 - 1e-6), 1e-6)))]]  # noqa: E731
        return {p: float(m.predict_proba(z(v))[0, 1]) for p, v in raw.items()}, "platt"
    return {p: SHRINK * v + (1 - SHRINK) * clim for p, v in raw.items()}, "shrinkage_to_climatology"


def conformal(res: list[float], dates: int) -> float | None:
    if dates < MIN_PRIOR or not res:
        return None
    a = sorted(abs(r) for r in res)
    i = min(len(a), math.ceil(0.8 * (len(a) + 1))) - 1
    return float(a[i])


def avg_rank(values: dict) -> tuple[dict, dict]:
    """Descending rank (1 = highest); ties share the average rank and are flagged."""
    s = pd.Series(values)
    r = s.rank(ascending=False, method="average")
    tied = s.duplicated(keep=False)
    return r.to_dict(), tied.to_dict()


# ==================================================================== walk-forward (procedures A-G)
def walk_forward(d: Data, kind: str, k: int) -> tuple[pd.DataFrame, dict]:
    feats = FEATS[k]
    last_t = (LAST_OBS + 1) - k                       # origin that targets the first forecast-only quarter
    rows, meta, history = [], {}, []                 # history: (origin t, target q, province, raw/pred, outcome)
    for t in range(FIRST_TARGET - k, last_t + 1):
        q = t + k
        try:
            te = d.X(kind, t, k)
        except (IndexError, KeyError, ValueError):
            continue
        tr = d.train(kind, t, k, feats)
        n_q = int(tr["target_q"].nunique()) if len(tr) else 0
        observed = {p: d.target(kind, p, q) for p in PROVS}
        has_outcome = q <= LAST_OBS and all(v is not None for v in observed.values())
        if kind == "C" and q <= LAST_OBS and not has_outcome:
            status = "Missing round"
        elif n_q < MIN_PRIOR:
            status = "Withheld"
        else:
            status = "Scored" if has_outcome else "No outcome yet"
        naive = (tr["y"] - tr["y_last"]).abs().mean() if len(tr) else None   # MASE scale: training rows only
        meta[qs(q)] = {"origin": str(L7.origin(t).date()), "training_rows": int(len(tr)), "training_quarters": n_q,
                       "status": status, "naive_scale": None if naive is None or naive != naive else float(naive)}
        if status in ("Withheld",) or (status == "Missing round" and n_q < MIN_PRIOR):
            for p in PROVS:
                rows.append({"target": kind, "lead": k, "t": qs(t), "target_quarter": qs(q), "province_code": p,
                             "arm": "model", "pred": None, "y": observed[p], "status": status})
            continue
        te2 = te.copy()
        for f in feats:                               # LightGBM handles NaN; nothing imputed for the model
            te2[f] = te2[f].astype(float)
        pred = _lgbm(kind, tr, te2, feats, k)
        base = baselines(d, kind, t, k, tr, te)
        # outcomes known before O(t): earlier forecasts whose target <= t-1 and available at O(t)
        prior = [h for h in history if d.available(kind, h["q"], t)]
        prior_dates = len({h["q"] for h in prior})
        extra = {}
        if kind == "A":
            clim = base["climatology"][PROVS[0]]
            cal, how = calibrate(pred, [(h["raw"], h["y"]) for h in prior], prior_dates, clim)
            extra = {"raw": pred, "calibration": how}
            pred_out = cal
        else:
            qhat = conformal([h["raw"] - h["y"] for h in prior], prior_dates)
            extra = {"interval_halfwidth": qhat}
            pred_out = pred
        meta[qs(q)].update({"prior_forecast_dates": prior_dates, **{k2: v for k2, v in extra.items() if k2 != "raw"}})
        ranks, tied = avg_rank(pred) if kind == "B" else ({}, {})
        for p in PROVS:
            row = {"target": kind, "lead": k, "t": qs(t), "target_quarter": qs(q), "province_code": p, "arm": "model",
                   "pred": float(pred_out[p]), "y": observed[p], "status": status}
            if kind == "A":
                row.update(raw=float(pred[p]), calibration=extra["calibration"])
            else:
                hw = extra["interval_halfwidth"]
                row.update(lo=None if hw is None else pred[p] - hw, hi=None if hw is None else pred[p] + hw)
            if kind == "B":
                row.update(rank=ranks[p], tied=bool(tied[p]))
            rows.append(row)
            for name, bp in base.items():
                rows.append({"target": kind, "lead": k, "t": qs(t), "target_quarter": qs(q), "province_code": p,
                             "arm": name, "pred": float(bp[p]), "y": observed[p], "status": status})
            if has_outcome:
                history.append({"q": q, "p": p, "raw": float(pred[p]), "y": observed[p]})
    return pd.DataFrame(rows), meta


# ==================================================================== scoring-v2
def per_date_loss(g: pd.DataFrame, kind: str) -> pd.Series:
    e = (g["pred"] - g["y"]) ** 2 if kind == "A" else (g["pred"] - g["y"]).abs()
    return e.groupby(g["target_quarter"]).mean()


def boot_dates(g: pd.DataFrame, stat, b=2000, seed=20261015):
    rng = np.random.default_rng(seed)
    ds = sorted(g["target_quarter"].unique())
    parts = {x: g[g["target_quarter"] == x] for x in ds}
    vals = []
    for _ in range(b):
        s = pd.concat([parts[ds[i]] for i in rng.choice(len(ds), len(ds))])
        v = stat(s)
        if v is not None and v == v:
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else None


def pooled_binary(g: pd.DataFrame) -> dict:
    y, p = g["y"].astype(int).to_numpy(), g["pred"].to_numpy(float)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    return {"n": int(len(y)), "HIGH": int(y.sum()), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
            "accuracy_DIAGNOSTIC": (tp + tn) / len(y), "HIGH_recall": rec,
            "HIGH_precision": tp / (tp + fp) if tp + fp else None,
            "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "auc": M._auc(y, p)}
