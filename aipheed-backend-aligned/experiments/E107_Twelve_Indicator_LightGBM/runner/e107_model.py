"""E107 model, arms and metrics (PROTOCOL.md sections 5-8)."""
from __future__ import annotations

import csv
import itertools
import math
import warnings

import e107_lib as E

np, pd = E.np, E.pd
warnings.filterwarnings("ignore", message="X does not have valid feature names")

GRID = [dict(id=i, depth=d, leaves=2 ** d, trees=n, cw=w)
        for i, (d, n, w) in enumerate(itertools.product((1, 2), (50, 150), (None, "balanced")))]
LGB_FIXED = dict(objective="binary", learning_rate=0.05, reg_lambda=5.0, colsample_bytree=1.0, subsample=1.0,
                 deterministic=True, force_row_wise=True, feature_pre_filter=False, random_state=E.SEED, n_jobs=1,
                 verbose=-1)
MIN_CHILD = {"T43": 5, "R": 3}
INNER_FOLDS, INNER_MIN_Q = 4, 3
EPS = 1e-6
PSA_COLS = ["A1_food", "A1_gap", "A2", "A3", "V1", "C3", "C4", "E1"]
NLP_COLS = ["N1"]
E63_FILE = E.EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv"
E63_SHA = "7acae3a1c89f72fc17fe740cf345d0c7f612e7b01ecea52730caaac4f17c16d3"
FIRI_FILE = E.BACKEND / "data" / "thesis" / "firi2_history.csv"


# ================================================================================================ rows
def regional(X: pd.DataFrame) -> pd.DataFrame:
    """R rows: one per origin, the five-province mean of each column (NaN when all five are missing)."""
    g = X.groupby(["t", "lead", "issue_date", "target_q"], as_index=False)[E.COLUMNS].mean()
    return g.assign(province_code="REGION")


def train_rows(X: pd.DataFrame, t: int, k: int, target: str, labels=None) -> pd.DataFrame:
    lab = E.known_labels(t, target) if labels is None else labels(t)
    if target == "R":
        lab = lab.drop_duplicates("q").assign(province_code="REGION")
    tr = X[(X["t"] < t) & (X["target_q"] <= t - 1)].rename(columns={"target_q": "q"})
    keep = ["province_code", "q", "y"] + [c for c in ("F", "HL") if c in lab]      # F, HL: SP's sigma (ADDENDUM_2)
    return tr.merge(lab[keep], on=["province_code", "q"], how="inner")


# ================================================================================================ LightGBM
def _lgbm(cfg: dict, target: str):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**LGB_FIXED, max_depth=cfg["depth"], num_leaves=cfg["leaves"],
                              n_estimators=cfg["trees"], class_weight=cfg["cw"], min_child_samples=MIN_CHILD[target])


class Model:
    """A fitted LightGBM, or the training HIGH share when the fit set has one class. With `init` (log-odds per row) the
    booster starts from that structural prior in fit and prediction (ADDENDUM_2 arm SP)."""

    def __init__(self, cfg, target, cols):
        self.cfg, self.target, self.cols, self.m, self.const = cfg, target, list(cols), None, None

    def fit(self, tr: pd.DataFrame, init=None):
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        kw = {} if init is None else {"init_score": np.asarray(init, float)}
        self.m = _lgbm(self.cfg, self.target).fit(tr[self.cols].astype(float), y, **kw)
        return self

    def predict(self, te: pd.DataFrame, init=None) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        if init is None:
            return self.m.predict_proba(te[self.cols].astype(float))[:, 1]
        raw = self.m.predict(te[self.cols].astype(float), raw_score=True) + np.asarray(init, float)
        return 1.0 / (1.0 + np.exp(-raw))

    def shap(self, te: pd.DataFrame) -> np.ndarray | None:
        if self.m is None:
            return None
        return self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)

    def gain(self) -> dict | None:
        if self.m is None:
            return None
        return dict(zip(self.cols, self.m.booster_.feature_importance("gain").astype(float)))


def logloss(y, p) -> float:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ================================================================================================ SP prior (ADDENDUM_2)
SIGMA_FALLBACK, SIGMA_MIN_Q, PRIOR_CLIP = 2.0, 4, 0.01


def sigmas(fit: pd.DataFrame) -> tuple[float, float]:
    """RMSE of the projection's own errors (realised minus projected distance to the threshold) on the fit rows."""
    if fit["q"].nunique() < SIGMA_MIN_Q or "F" not in fit:
        return SIGMA_FALLBACK, SIGMA_FALLBACK
    th = E.L.e40_spec()
    ef = (fit["F"] - fit["province_code"].map(th["food"])) - fit["A1_food"]
    eg = (fit["F"] - fit["HL"] - fit["province_code"].map(th["gap"])) - fit["A1_gap"]

    def rm(e):
        e = e.dropna()
        return float(np.sqrt(np.mean(e ** 2))) if len(e) else SIGMA_FALLBACK
    return rm(ef), rm(eg)


def prior(rows: pd.DataFrame, target: str, sig: tuple[float, float], fill: float) -> np.ndarray:
    """p0: T43 = H1 x P(food or gap above threshold) with normal projection errors; R = H1. Missing -> `fill`."""
    from scipy.stats import norm
    if target == "R":
        p0 = rows["H1"].to_numpy(float)
    else:
        pf = norm.cdf(rows["A1_food"].to_numpy(float) / sig[0])
        pg = norm.cdf(rows["A1_gap"].to_numpy(float) / sig[1])
        p0 = rows["H1"].to_numpy(float) * (1 - (1 - pf) * (1 - pg))
    return np.where(np.isfinite(p0), p0, fill)


def init_of(p0) -> np.ndarray:
    p = np.clip(np.asarray(p0, float), PRIOR_CLIP, 1 - PRIOR_CLIP)
    return np.log(p / (1 - p))


def select(tr: pd.DataFrame, k: int, target: str, cols, sp: bool = False) -> tuple[dict, dict, pd.DataFrame]:
    """Nested selection on training rows only (PROTOCOL 5). Returns (config, inner scores, inner OOF of the winner).
    With sp=True every inner fit uses the SP prior with sigma from that inner fit set (ADDENDUM_2)."""
    qv = sorted(tr["q"].unique())[-INNER_FOLDS:]
    folds = []
    for q in qv:
        fit, hold = tr[tr["q"] <= q - k - 1], tr[tr["q"] == q]
        if fit["q"].nunique() >= INNER_MIN_Q and fit["y"].nunique() == 2 and len(hold):
            folds.append((fit, hold))
    if not folds:
        return GRID[0], {}, pd.DataFrame()
    scores, oof = {}, {}
    for c in GRID:
        ys, ps = [], []
        for fit, hold in folds:
            if sp:
                s, fl = sigmas(fit), float(fit["y"].mean())
                ps.append(Model(c, target, cols).fit(fit, init_of(prior(fit, target, s, fl)))
                          .predict(hold, init_of(prior(hold, target, s, fl))))
            else:
                ps.append(Model(c, target, cols).fit(fit).predict(hold))
            ys.append(hold["y"].to_numpy(int))
        scores[c["id"]] = logloss(np.concatenate(ys), np.concatenate(ps))
        oof[c["id"]] = pd.DataFrame({"y": np.concatenate(ys), "p": np.concatenate(ps)})
    best = min(GRID, key=lambda c: (round(scores[c["id"]], 9), c["id"]))
    return best, scores, oof[best["id"]]


def inner_threshold(oof: pd.DataFrame) -> float:
    """THR-INNER (diagnostic): threshold maximising balanced accuracy on the inner predictions; ties -> nearest 0.5."""
    if not len(oof) or oof["y"].nunique() < 2:
        return 0.5
    best = (-1.0, 1.0, 0.5)
    for th in sorted(set(np.round(oof["p"], 9)) | {0.5}):
        c = oof["p"] >= th
        rh = float((c & (oof["y"] == 1)).sum() / (oof["y"] == 1).sum())
        rl = float((~c & (oof["y"] == 0)).sum() / (oof["y"] == 0).sum())
        key = ((rh + rl) / 2, -abs(th - 0.5))
        if key > best[:2]:
            best = (key[0], key[1], th)
    return float(best[2])


# ================================================================================================ logistic arms
def logistic(tr: pd.DataFrame, te: pd.DataFrame, cols, flags: bool) -> np.ndarray | None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    def mat(d, med):
        Z = d[cols].astype(float)
        out = [Z.fillna(med)]
        if flags:
            out.append(Z.isna().astype(float).add_suffix("_missing"))
        return pd.concat(out, axis=1)
    med = tr[cols].astype(float).median()
    med = med.fillna(0.0)                                        # an all-missing training column carries no signal
    A, B = mat(tr, med), mat(te, med)
    keep = [c for c in A.columns if A[c].nunique() > 1]
    if not keep or tr["y"].nunique() < 2:
        return None
    s = StandardScaler().fit(A[keep])
    m = LogisticRegression(C=1.0, max_iter=5000).fit(s.transform(A[keep]), tr["y"].to_numpy(int))
    return m.predict_proba(s.transform(B[keep]))[:, 1]


# ================================================================================================ sealed comparators
def e63() -> pd.DataFrame:
    assert E.sha256(E63_FILE) == E63_SHA, "E63 sealed predictions changed"
    d = pd.read_csv(E63_FILE, dtype={"province_code": str})
    d["q"] = d["target"].map(E.qi)
    return d


def firi() -> pd.DataFrame:
    h = pd.read_csv(FIRI_FILE, dtype={"province_code": str})
    h["q"] = h["target"].map(E.qi)
    h["t"] = h["origin_quarter"].map(E.qi)
    return h[["t", "q", "province_code", "FIRI", "class", "kind"]]


# ================================================================================================ one lead
def run(k: int, target: str, cols=None, quarters=None, X=None, labels=None, outcome=None, arms=True,
        explain=False, rule: str = "primary", sp: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    """Rolling-origin predictions of lead k for the labelled target quarters in `quarters` (default: all eligible).

    Returns (one row per evaluated (target quarter, province or REGION) with every arm, per-origin model records).
    """
    cols = list(E.COLUMNS if cols is None else cols)
    X = E.feature_table(k) if X is None else X
    if target == "R":
        X = regional(X)
    obs = E.outcomes(target) if outcome is None else outcome
    if target == "R":
        obs = obs.drop_duplicates("q").assign(province_code="REGION")
    obs = obs[obs["q"] <= E.LAST_OUTCOME]
    qset = sorted(obs["q"].unique()) if quarters is None else sorted(quarters)
    rows, recs = [], []
    for q in qset:
        t = q - k
        if t < E.FIRST_ORIGIN or t > E.LAST_ORIGIN:
            continue
        tr = train_rows(X, t, k, target, labels)
        if not E.eligible(tr, target, rule):
            continue
        te = X[X["t"] == t].merge(obs[obs["q"] == q][["province_code", "y"]], on="province_code", how="inner")
        if not len(te):
            continue
        cfg, scores, oof = select(tr, k, target, cols)
        mdl = Model(cfg, target, cols).fit(tr)
        p = mdl.predict(te)
        out = te[["t", "province_code", "y"]].copy()
        out = out.assign(lead=k, q=q, issue_date=E.issue(t), block="final" if q in E.FINAL_BLOCK else "dev",
                         p=p, cfg=cfg["id"], thr_inner=inner_threshold(oof), n_train=len(tr),
                         n_train_q=tr["q"].nunique(), n_train_high=int(tr["y"].sum()))
        if arms:
            clim = float(tr["y"].mean())
            out["CLIM_p"] = clim
            per = E.persistence(t, target)
            if target == "R":
                v = next(iter(per.values())) if per else (np.nan, np.nan)
                out["PERSIST_p"], out["PERSIST_from"] = float(v[0]), E.qs(int(v[1]))
            else:
                out["PERSIST_p"] = [float(per[pp][0]) if pp in per else np.nan for pp in out["province_code"]]
                out["PERSIST_from"] = [E.qs(per[pp][1]) if pp in per else "" for pp in out["province_code"]]
            out["PERSIST_p"] = out["PERSIST_p"].fillna(clim)
            if target == "T43":
                for name, cc, fl in (("PSA_LR", PSA_COLS, False), ("NLP_LR", NLP_COLS, True), ("LR12", cols, True)):
                    v = logistic(tr, te, cc, fl)
                    out[f"{name}_p"] = clim if v is None else v
                price = ((te["A1_food"] > 0) | (te["A1_gap"] > 0)).astype(float)
                out["RULE_p"] = (te["H1"] * price).fillna(clim).to_numpy()
            else:
                out["H1_p"] = te["H1"].fillna(clim).to_numpy()
        out["eligible_original_rule"] = E.eligible_original(tr)
        if sp:                                                    # ADDENDUM_2 arm SP and the STRUCT baseline
            s, fl = sigmas(tr), float(tr["y"].mean())
            p0_tr, p0_te = prior(tr, target, s, fl), prior(te, target, s, fl)
            cfg_sp, _, _ = select(tr, k, target, cols, sp=True)
            msp = Model(cfg_sp, target, cols).fit(tr, init_of(p0_tr))
            out["SP_p"], out["STRUCT_p"], out["SP_cfg"] = msp.predict(te, init_of(p0_te)), p0_te, cfg_sp["id"]
            out["SP_sigma_food"], out["SP_sigma_gap"] = s
        rec = {"lead": k, "target": target, "t": t, "q": q, "cfg": cfg["id"], "inner_logloss": scores,
               "n_train": len(tr), "n_train_q": int(tr["q"].nunique()), "n_train_high": int(tr["y"].sum()),
               "train_quarters": [E.qs(int(x)) for x in sorted(tr["q"].unique())]}
        if explain:
            sv = mdl.shap(te)
            rec["shap"] = None if sv is None else {pp: dict(zip(cols + ["_base"], map(float, row)))
                                                   for pp, row in zip(te["province_code"], sv)}
            rec["gain"] = mdl.gain()
            if sp:
                sv = msp.shap(te)
                rec["sp_cfg"] = cfg_sp["id"]
                rec["sp_prior_logodds"] = dict(zip(te["province_code"], map(float, init_of(p0_te))))
                rec["sp_shap"] = None if sv is None else {pp: dict(zip(cols + ["_base"], map(float, row)))
                                                          for pp, row in zip(te["province_code"], sv)}
                rec["sp_gain"] = msp.gain()
        rows.append(out)
        recs.append(rec)
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if arms and len(df):
        df = attach_sealed(df, k, target)
    return df, recs


def attach_sealed(df: pd.DataFrame, k: int, target: str) -> pd.DataFrame:
    s = e63()
    s = s[s["lead"] == k]
    if target == "T43":
        m = s.set_index(["q", "province_code"])["E56_p"]
        df["E56_p"] = [m.get((q, p), np.nan) for q, p in zip(df["q"], df["province_code"])]
    else:
        m = s.groupby("q")["E56_p_hunger"].mean()
        df["E56_p"] = df["q"].map(m)
    f = firi()
    f = f[f["q"] - f["t"] == k] if k == 2 else f.iloc[0:0]
    if target == "T43":
        fs = f.set_index(["q", "province_code"])
        df["FIRI_score"] = [fs["FIRI"].get((q, p), np.nan) for q, p in zip(df["q"], df["province_code"])]
    else:
        df["FIRI_score"] = df["q"].map(f.groupby("q")["FIRI"].mean())
    return df


# ================================================================================================ metrics
def wilson(x: int, n: int, z: float = 1.959964) -> list[float]:
    if not n:
        return [float("nan")] * 2
    ph = x / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


def auc(y, p) -> float | None:
    y, p = np.asarray(y, int), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return None
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def metrics(y, p, thr: float = 0.5, quarters=None) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    c = (p >= thr).astype(int)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    n = len(y)

    def div(a, b):
        return a / b if b else None
    ph, rh = div(tp, tp + fp), div(tp, tp + fn)
    pl, rl = div(tn, tn + fn), div(tn, tn + fp)
    f1 = lambda a, b: (2 * a * b / (a + b)) if a is not None and b is not None and a + b > 0 else None  # noqa: E731
    out = {"n": n, "n_high": int(y.sum()), "accuracy": (tp + tn) / n if n else None, "accuracy_wilson95": wilson(tp + tn, n),
           "balanced_accuracy": (rh + rl) / 2 if rh is not None and rl is not None else None,
           "precision_high": ph, "recall_high": rh, "f1_high": f1(ph, rh),
           "precision_low": pl, "recall_low": rl, "f1_low": f1(pl, rl),
           "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "auc": auc(y, p),
           "brier": float(np.mean((p - y) ** 2)) if n else None, "logloss": logloss(y, p) if n else None,
           "share_pred_high": float(c.mean()) if n else None,
           "calibration_in_the_large": float(p.mean() - y.mean()) if n else None}
    if quarters is not None:
        out["n_quarters"] = int(len(set(quarters)))
    return out


def reliability_table(y, p, bins: int = 5) -> list[dict]:
    y, p = np.asarray(y, int), np.asarray(p, float)
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        m = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= 1))
        out.append({"bin": [float(edges[i]), float(edges[i + 1])], "n": int(m.sum()),
                    "mean_p": float(p[m].mean()) if m.any() else None, "observed": float(y[m].mean()) if m.any() else None})
    return out


def per_quarter(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.assign(c=(df[col] >= 0.5).astype(int), b=(df[col] - df["y"]) ** 2)
    return g.groupby("q").apply(lambda x: pd.Series({"n": len(x), "n_high": int(x["y"].sum()),
                                                     "accuracy": float((x["c"] == x["y"]).mean()),
                                                     "brier_sum": float(x["b"].sum()),
                                                     "brier_mean": float(x["b"].mean())}), include_groups=False)


def paired(df: pd.DataFrame, a: str, b: str, draws: int = 2000, seed: int = 2026) -> dict:
    """Quarter-level Brier difference a - b (sum over the quarter's rows): mean, bootstrap CI, exact one-sided sign-flip p
    for 'a better than b' (mean difference <= observed)."""
    d = df.dropna(subset=[a, b])
    if not len(d):
        return {"n_quarters": 0}
    diff = d.assign(v=(d[a] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2).groupby("q")["v"].sum().to_numpy()
    n = len(diff)
    obs = float(diff.mean())
    rng = np.random.default_rng(seed)
    boots = [float(rng.choice(diff, n, replace=True).mean()) for _ in range(draws)]
    if n <= 20:
        signs = np.array(list(itertools.product((1, -1), repeat=n)))
        stats = (signs * diff).mean(axis=1)
    else:
        signs = rng.choice((1, -1), size=(200000, n))
        stats = (signs * diff).mean(axis=1)
    p = float(np.mean(stats <= obs + 1e-12))
    return {"n_quarters": n, "mean_quarter_brier_diff": obs, "boot95": [float(np.percentile(boots, 2.5)),
            float(np.percentile(boots, 97.5))], "signflip_p_one_sided": p,
            "quarters_a_better": int((diff < 0).sum()), "quarters_tied": int((diff == 0).sum())}


def cluster_ci(df: pd.DataFrame, col: str, draws: int = 2000, seed: int = 2026) -> list[float]:
    """Quarter-cluster bootstrap 95% CI of accuracy."""
    g = df.assign(ok=((df[col] >= 0.5).astype(int) == df["y"]).astype(int)).groupby("q")["ok"].agg(["sum", "size"])
    rng = np.random.default_rng(seed)
    idx = np.arange(len(g))
    vals = []
    for _ in range(draws):
        s = g.iloc[rng.choice(idx, len(idx), replace=True)]
        vals.append(s["sum"].sum() / s["size"].sum())
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def write_csv(path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL, float_format="%.10g")
