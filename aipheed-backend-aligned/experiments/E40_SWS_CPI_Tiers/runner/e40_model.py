"""E40 model library: publication-aware as-of features, the walk-forward with the >= 2-HIGH training-fold gate, the
regularized LightGBM + logistic-regression blend, walk-forward Platt calibration, baselines and metrics.

Timing (E32 convention). Origin O(t) = 00:00 PHT on the first day of quarter t+1; the target is the label of quarter
t+1 (lead 1, the quarter that starts at the origin). At O(t):
  * SWS: rounds whose verified posting date (else documented upper bound) is strictly before O(t);
  * CPI: full quarters <= t-1 and months 1-2 of quarter t (month 3 is released inside quarter t+1);
  * news: articles dated in quarters <= t;
  * labels: quarter s is known when s <= t-1 and every approved round of s and s-1 was posted before O(t).
Training row for a known label s = features at O(s-1). Nothing before 2021-01 is read (asserted in e40_label).
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e40_label as L  # noqa: E402

E40 = L.E40
qi, qn, PROVS = L.qi, L.qn, L.PROVS
NEWS = E40.parent / "E31_Chapter1_Completion" / "backend_dev" / "data" / "news_e31" / "fssi_v2_panel.csv"
COMP = E40 / "runs" / "triggers" / "composition.csv"
MIN_TRAIN_QUARTERS = 8
MIN_TRAIN_HIGH = 2
CLIP = (0.02, 0.98)
DEFAULT_CUTOFF = 0.50

SWS_F = ["H_last", "H_age", "H_trend", "H_margin", "sws_last_hi"]
CPI_F = ["food_now", "headline_now", "gap_now", "rel_now", "food_margin", "gap_margin", "cpi_sig_now", "food_chg",
         "both_proxy"]
LAB_F = ["y_last"]                                    # label-derived (the label contains CPI), so CPI-derived too
NLP_F = ["news_n", "news_adm", "news_direct_share", "fssi_v2", "fssi_missing", "news_reg", "comp_market",
         "comp_climate", "comp_fish_kill", "comp_reliable"]
FEATURE_SETS = {"BLEND": SWS_F + CPI_F + LAB_F + NLP_F, "NO_CPI": SWS_F + NLP_F, "GOV": SWS_F + CPI_F + LAB_F,
                "NLP": NLP_F}
CPI_DERIVED = set(CPI_F + LAB_F)
assert not CPI_DERIVED & set(FEATURE_SETS["NO_CPI"])
LGBM = dict(objective="binary", num_leaves=4, max_depth=3, min_child_samples=10, reg_alpha=1.0, reg_lambda=5.0,
            n_estimators=100, learning_rate=0.05, colsample_bytree=0.8, subsample=1.0, n_jobs=1, random_state=40,
            deterministic=True, force_col_wise=True, verbose=-1)
assert LGBM["min_child_samples"] >= 10 and LGBM["num_leaves"] <= 7 and LGBM["max_depth"] <= 3


def origin(t: int) -> pd.Timestamp:
    return pd.Timestamp(qn(t + 1)[:4] + "-" + f"{3 * (int(qn(t + 1)[-1]) - 1) + 1:02d}-01")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Data:
    def __init__(self, label_file: str = "label_primary.csv"):
        fr = json.loads((E40 / "frozen" / "E40_LABEL_FREEZE.json").read_text())
        assert sha(E40 / label_file) == fr["sha256"][label_file], "frozen label changed"
        self.spec = json.loads((E40 / "label_spec.json").read_text())
        self.thr = self.spec["thresholds"]
        self.lab = pd.read_csv(E40 / label_file, dtype={"province_code": str})
        self.lab["t"] = self.lab["quarter"].map(qi)
        assert self.lab["t"].min() >= qi("2021-Q1")
        self.y = {(r.province_code, r.t): r.y_high for r in self.lab.itertuples() if r.y_high == r.y_high}
        self.stress = {(r.province_code, r.t): max(r.food - self.thr["food"][r.province_code],
                                                   r.cpi_gap - self.thr["gap"][r.province_code])
                       for r in self.lab.itertuples()}
        m = L.monthly_cpi()
        self.m = m
        r = pd.read_csv(L.INP / "sws_rounds.csv")
        r = r[r["definition_A"].astype(str) == "True"].copy()
        pub = pd.to_datetime(r["published"], errors="coerce", format="ISO8601")
        eff = pd.to_datetime(r["published_eff"], errors="coerce", format="ISO8601")
        r["usable"] = pub.where(r["date_type"].astype(str).str.startswith("verified") & pub.notna(), eff)
        r["t"] = r["quarter"].map(qi)
        assert r["t"].min() >= qi("2021-Q1")
        self.rounds = r
        n = pd.read_csv(NEWS, dtype={"province_code": str})
        assert n["quarter"].map(qi).min() >= qi("2021-Q1")
        self.news = {(x.province_code, qi(x.quarter)): x for x in n.itertuples()}
        self.news_reg = n.groupby("quarter")["n_province_attributed"].sum().rename(index=qi).to_dict()
        c = pd.read_csv(COMP, dtype={"province_code": str})
        self.comp = {(x.province_code, qi(x.quarter)): x for x in c.itertuples()}

    # ------------------------------------------------------------------ publication
    def H_posted(self, o: pd.Timestamp) -> dict[int, float]:
        r = self.rounds[self.rounds["usable"].notna() & (self.rounds["usable"] < o)]
        return r.groupby("t")["H"].mean().to_dict()

    def posted(self, o: pd.Timestamp) -> set[int]:
        out = set()
        for t, g in self.rounds.groupby("t"):
            if g["usable"].notna().all() and (g["usable"] < o).all():
                out.add(int(t))
        return out

    def known_labels(self, t: int) -> list[int]:
        """Label quarters known at O(t): s <= t-1, s labelled, rounds of s (and of s-1 if it has any) posted."""
        o, post = origin(t), self.posted(origin(t))
        has_round = set(self.rounds["t"])
        labelled = sorted({s for (_, s) in self.y})
        return [s for s in labelled if s <= t - 1 and s in post and ((s - 1) not in has_round or (s - 1) in post)]

    def cpi_asof(self, t: int) -> pd.DataFrame:
        """Months 1-2 of quarter t, plus full quarter t-1 (food), as available at O(t)."""
        m = self.m
        now = m[(m["quarter"] == qn(t)) & (m["month_in_q"] <= 2)]
        prev = m[(m["quarter"] == qn(t - 1)) & (m["commodity"] == "food")]
        a = now.pivot_table(index="province_code", columns="commodity", values="yoy_pct", aggfunc="mean")
        a = a.reindex(PROVS)
        a["food_prev"] = prev.groupby("province_code")["yoy_pct"].mean().reindex(PROVS)
        return a

    # ------------------------------------------------------------------ features
    def features(self, t: int) -> pd.DataFrame:
        o = origin(t)
        Hp = self.H_posted(o)
        ks = sorted(Hp)
        Hl = Hp[ks[-1]] if ks else np.nan
        Ht = Hp[ks[-1]] - Hp[ks[-2]] if len(ks) > 1 else np.nan
        a = self.cpi_asof(t)
        known = self.known_labels(t)
        rows = []
        for p in PROVS:
            food, head = a.loc[p].get("food", np.nan), a.loc[p].get("all_items", np.nan)
            gap = food - head
            fm, gm = food - self.thr["food"][p], gap - self.thr["gap"][p]
            sig = float((fm > 0) or (gm > 0)) if fm == fm else np.nan
            shi = float(Hl > self.thr["H"]) if Hl == Hl else np.nan
            yl = [self.y[(p, s)] for s in known if (p, s) in self.y]
            n, c = self.news.get((p, t)), self.comp.get((p, t))
            f = np.nan if n is None or n.FSSI_v2 != n.FSSI_v2 else float(n.FSSI_v2)
            rows.append({
                "province_code": p, "t": t, "target_t": t + 1,
                "H_last": Hl, "H_age": float(t + 1 - ks[-1]) if ks else np.nan, "H_trend": Ht,
                "H_margin": Hl - self.thr["H"], "sws_last_hi": shi,
                "food_now": food, "headline_now": head, "gap_now": gap,
                "rel_now": food - a["food"].mean(), "food_margin": fm, "gap_margin": gm, "cpi_sig_now": sig,
                "food_chg": food - a.loc[p, "food_prev"], "both_proxy": sig * shi if sig == sig and shi == shi else np.nan,
                "y_last": float(yl[-1]) if yl else np.nan,
                "news_n": np.log1p(n.n_province_attributed) if n is not None else 0.0,
                "news_adm": np.log1p(n.n_admitted) if n is not None else 0.0,
                "news_direct_share": (n.n_direct / n.n_admitted) if (n is not None and n.n_admitted) else 0.0,
                "fssi_v2": 0.0 if f != f else f, "fssi_missing": float(f != f),
                "news_reg": np.log1p(self.news_reg.get(t, 0)),
                "comp_market": c.comp_market if c is not None else np.nan,
                "comp_climate": c.comp_climate if c is not None else np.nan,
                "comp_fish_kill": c.comp_fish_kill if c is not None else np.nan,
                "comp_reliable": float(c.reliable) if c is not None else 0.0})
        return pd.DataFrame(rows)

    def training(self, t: int, max_label_t: int | None = None) -> pd.DataFrame:
        out = []
        for s in self.known_labels(t):
            if max_label_t is not None and s > max_label_t:
                continue
            X = self.features(s - 1)
            X["y"] = [self.y.get((p, s)) for p in X["province_code"]]
            out.append(X[X["y"].notna()])
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


# ====================================================================== models
def _prep(tr: pd.DataFrame, te: pd.DataFrame, feats: list[str]):
    med = tr[feats].median().fillna(0.0)
    return tr[feats].fillna(med).to_numpy(float), te[feats].fillna(med).to_numpy(float)


def fit_predict(kind: str, tr: pd.DataFrame, te: pd.DataFrame, feats: list[str]) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    y = tr["y"].to_numpy(int)
    Xtr, Xte = _prep(tr, te, feats)
    sc = StandardScaler().fit(Xtr)
    lr = LogisticRegression(C=0.3, max_iter=2000).fit(sc.transform(Xtr), y)
    p_lr = lr.predict_proba(sc.transform(Xte))[:, 1]
    if kind == "LR":
        return p_lr
    import lightgbm as lgb
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gb = lgb.LGBMClassifier(**LGBM).fit(tr[feats].to_numpy(float), y)
        p_gb = gb.predict_proba(te[feats].to_numpy(float))[:, 1]
    return 0.5 * p_gb + 0.5 * p_lr                    # fixed equal blend; weights are not tuned


def platt(prior: list[tuple[float, int]]):
    """Walk-forward Platt scaling on earlier folds' out-of-fold raw scores; identity unless >= 2 of each class."""
    ys = [y for _, y in prior]
    if sum(ys) < 2 or len(ys) - sum(ys) < 2:
        return (lambda p: np.clip(p, *CLIP)), "uncalibrated (fewer than 2 HIGH or 2 LOW earlier out-of-fold rows)"
    from sklearn.linear_model import LogisticRegression
    s = np.array([x for x, _ in prior]).clip(1e-4, 1 - 1e-4)
    z = np.log(s / (1 - s)).reshape(-1, 1)
    m = LogisticRegression(C=1.0).fit(z, ys)

    def f(p):
        p = np.clip(p, 1e-4, 1 - 1e-4)
        return np.clip(m.predict_proba(np.log(p / (1 - p)).reshape(-1, 1))[:, 1], *CLIP)
    return f, f"platt on {len(ys)} earlier out-of-fold rows"


def choose_cutoff(oof: pd.DataFrame) -> tuple[float, str]:
    if oof.empty or oof["y"].sum() < MIN_TRAIN_HIGH or (oof["y"] == 0).sum() < MIN_TRAIN_HIGH:
        return DEFAULT_CUTOFF, "default 0.50 (fewer than 2 HIGH out-of-fold rows)"
    best = max(np.round(np.arange(0.05, 0.96, 0.05), 2),
               key=lambda c: (balanced_acc(oof["y"], (oof["p"] >= c).astype(int)), -abs(c - 0.5)))
    return float(best), "maximizes out-of-fold balanced accuracy"


def rank_with_ties(df: pd.DataFrame, score: str = "p", tie: str = "gap_now") -> pd.Series:
    """Rank by calibrated score, ties broken by the CPI gap (higher = more pressure), remaining ties shared."""
    key = list(zip(-df[score].round(6), -df[tie].fillna(-1e9).round(6)))
    return pd.Series([1 + sum(1 for k2 in key if k2 < k) for k in key], index=df.index)


# ====================================================================== metrics
def balanced_acc(y, yhat) -> float:
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    parts = [np.mean(yhat[y == c] == c) for c in (0, 1) if (y == c).any()]
    return float(np.mean(parts)) if parts else float("nan")


def metrics(g: pd.DataFrame, cutoff: float = DEFAULT_CUTOFF) -> dict:
    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score
    y, p = g["y"].to_numpy(int), g["p"].to_numpy(float)
    yh = (p >= cutoff).astype(int)
    tp, fp, fn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec == prec and rec == rec and prec + rec) else float("nan")
    auc = float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) and np.ptp(p) > 0 else float("nan")
    sp = []
    for _, q in g.groupby("target_t"):
        if q["p"].nunique() > 1 and q["stress"].nunique() > 1:
            sp.append(spearmanr(q["p"], q["stress"]).correlation)
    bins = pd.cut(p, [0, 0.2, 0.4, 0.6, 0.8, 1.0], include_lowest=True)
    rel = g.assign(bin=bins.astype(str)).groupby("bin", observed=True).agg(n=("y", "size"), mean_p=("p", "mean"),
                                                                           obs_rate=("y", "mean"))
    return {"n": int(len(y)), "HIGH": int(y.sum()), "accuracy": float((yh == y).mean()),
            "balanced_accuracy": balanced_acc(y, yh), "precision_HIGH": prec, "recall_HIGH": rec, "F1_HIGH": f1,
            "AUC": auc, "Brier": float(np.mean((p - y) ** 2)),
            "spearman_per_quarter_mean": float(np.mean(sp)) if sp else float("nan"),
            "spearman_quarters": len(sp), "reliability_5bin": rel.reset_index().to_dict("records")}


def bootstrap(g: pd.DataFrame, fn, b: int = 2000, seed: int = 20261015) -> tuple[float, float]:
    """Quarter-cluster bootstrap (the five provinces of a quarter move together)."""
    qs = g["target_t"].unique()
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(b):
        pick = rng.choice(qs, len(qs), replace=True)
        s = pd.concat([g[g["target_t"] == q] for q in pick])
        v = fn(s)
        if v == v:
            vals.append(v)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (float("nan"), float("nan"))
