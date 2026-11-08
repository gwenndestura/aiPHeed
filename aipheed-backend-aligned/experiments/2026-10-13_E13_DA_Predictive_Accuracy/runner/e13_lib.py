"""E13 library: availability-safe target and feature construction, forecasters and metrics.

No function here opens a file. Loading is done by run_e13.py through the guard.

Targets (see EXPERIMENT_PROTOCOL.md):
  A  regional hunger H[T] (SWS Balance Luzon; one value per quarter; independently measured)
  B1 provincial food inflation F[p,T] (PSA provincial food CPI YoY; food-price pressure)
  B2 relative provincial food-price pressure D[p,T] = F[p,T] - mean of the five F[.,T]
Forecast origin for target quarter T = the first day of T.
"""
from __future__ import annotations

import itertools
from datetime import date

import numpy as np
import pandas as pd

PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
             "PH040400000": "Rizal", "PH040500000": "Batangas"}
RIDGE_ALPHA = 1.0
MIN_TRAIN_QUARTERS = 6
F_EVENT_THRESHOLD = 4.0          # upper bound of the government's 2-4% inflation target band
SEED = 20261013
N_BOOT = 10_000


# ----------------------------------------------------------------- quarters
def qi(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def origin(q: str) -> pd.Timestamp:
    y, n = q.split("-Q")
    return pd.Timestamp(date(int(y), 3 * (int(n) - 1) + 1, 1))


# ----------------------------------------------------------------- target A (regional hunger)
def quarter_values(rounds: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """Quarterly H = mean of the rounds assigned to the quarter. With as_of, only rounds published
    strictly before as_of are used, and a quarter counts as complete only if ALL its rounds are."""
    r = rounds.copy()
    out = r.groupby("quarter").agg(H=("H", "mean"), n_rounds=("H", "size"),
                                   last_published=("published", "max")).reset_index()
    if as_of is not None:
        pub = r[r["published"] < as_of]
        vis = pub.groupby("quarter").agg(H_visible=("H", "mean"), n_visible=("H", "size")).reset_index()
        out = out.merge(vis, on="quarter", how="left")
        out["complete_as_of"] = out["n_visible"].fillna(0).astype(int) == out["n_rounds"]
    return out.sort_values("quarter", key=lambda s: s.map(qi)).reset_index(drop=True)


def h_last(rounds: pd.DataFrame, as_of: pd.Timestamp) -> tuple[float, str] | tuple[None, None]:
    """Latest published regional value as of `as_of`: mean of the published rounds of the most recent
    fieldwork quarter that has at least one round published before as_of."""
    pub = rounds[rounds["published"] < as_of]
    if pub.empty:
        return None, None
    lastq = max(pub["quarter"], key=qi)
    return float(pub.loc[pub["quarter"] == lastq, "H"].mean()), lastq


def a_features(rounds: pd.DataFrame, comp: pd.DataFrame, T: str) -> dict:
    """Features known at origin(T): H_last (+ its quarter and age) and the five-province mean food
    inflation of quarter T-2 (provincial CPI for T-1 cannot be published before origin(T))."""
    o = origin(T)
    hv, hq = h_last(rounds, o)
    m5 = comp.loc[comp["quarter"] == qs(qi(T) - 2), "mean5"]
    return {"H_last": hv, "H_last_quarter": hq, "H_age_quarters": None if hq is None else qi(T) - qi(hq),
            "F5_lag2": float(m5.iloc[0]) if len(m5) and pd.notna(m5.iloc[0]) else None}


def a_training(rounds: pd.DataFrame, comp: pd.DataFrame, T: str) -> pd.DataFrame:
    """Training pairs for target T: quarters q < T whose value is fully published before origin(T),
    with features computed as of origin(q) and rows lacking any feature dropped."""
    o = origin(T)
    qv = quarter_values(rounds, as_of=o)
    rows = []
    for _, r in qv.iterrows():
        q = r["quarter"]
        if qi(q) >= qi(T) or not r["complete_as_of"]:
            continue
        f = a_features(rounds, comp, q)
        if f["H_last"] is None or f["F5_lag2"] is None:
            continue
        rows.append({"quarter": q, "y": float(r["H_visible"]), **f})
    return pd.DataFrame(rows)


def a_published_mean(rounds: pd.DataFrame, T: str) -> float | None:
    qv = quarter_values(rounds, as_of=origin(T))
    v = qv.loc[(qv["complete_as_of"]) & (qv["quarter"].map(qi) < qi(T)), "H_visible"]
    return float(v.mean()) if len(v) else None


# ----------------------------------------------------------------- targets B1/B2 (provincial)
def b_features(comp: pd.DataFrame, T: str) -> pd.DataFrame:
    """Per-province features known at origin(T): F and D of quarter T-2, the five-province mean of
    T-2, and the expanding province means of F and D over quarters <= T-2 (from 2021-Q1)."""
    lag = qs(qi(T) - 2)
    hist = comp[comp["quarter"].map(qi) <= qi(lag)]
    cur = comp[comp["quarter"] == lag].set_index("province_code")
    out = []
    for pc in PROVINCES:
        h = hist[hist["province_code"] == pc]
        out.append({"province_code": pc,
                    "F_lag2": cur["F"].get(pc, np.nan), "D_lag2": cur["D"].get(pc, np.nan),
                    "F5_lag2": cur["mean5"].get(pc, np.nan),
                    "Fbar_p": h["F"].mean() if h["F"].notna().any() else np.nan,
                    "Dbar_p": h["D"].mean() if h["D"].notna().any() else np.nan,
                    "complete_five_lag2": bool(len(cur) == 5 and cur["F"].notna().all())})
    return pd.DataFrame(out)


def b_training(comp: pd.DataFrame, T: str, first_q: str = "2021-Q3") -> pd.DataFrame:
    """Training pairs for target T: quarters first_q <= q <= T-2 (published before origin(T)),
    features as of origin(q)."""
    rows = []
    for i in range(qi(first_q), qi(T) - 1):
        q = qs(i)
        f = b_features(comp, q)
        y = comp[comp["quarter"] == q].set_index("province_code")
        f["quarter"] = q
        f["F"] = f["province_code"].map(y["F"])
        f["D"] = f["province_code"].map(y["D"])
        rows.append(f)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


# ----------------------------------------------------------------- forecasters
def ridge_fit_predict(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, alpha: float = RIDGE_ALPHA):
    """Ridge on training-standardized features with an unpenalized intercept. Returns (pred, coefs)."""
    mu, sd = Xtr.mean(0), Xtr.std(0, ddof=0)
    sd = np.where(sd > 0, sd, 1.0)
    Z, Zte = (Xtr - mu) / sd, (Xte - mu) / sd
    ym = ytr.mean()
    k = Z.shape[1]
    beta = np.linalg.solve(Z.T @ Z + alpha * np.eye(k), Z.T @ (ytr - ym))
    return ym + Zte @ beta, {"intercept": float(ym), "beta_std": [float(b) for b in beta]}


def tree_fit_predict(Xtr, ytr, Xte):
    from sklearn.tree import DecisionTreeRegressor
    m = DecisionTreeRegressor(max_depth=2, min_samples_leaf=5, random_state=0).fit(Xtr, ytr)
    return m.predict(Xte), {"n_leaves": int(m.get_n_leaves())}


# ----------------------------------------------------------------- metrics
def point_metrics(y, f) -> dict:
    e = np.asarray(f, float) - np.asarray(y, float)
    return {"n": int(len(e)), "MAE": float(np.mean(np.abs(e))), "RMSE": float(np.sqrt(np.mean(e ** 2))),
            "bias": float(np.mean(e))}


def auc_scores(y_bin, score) -> dict:
    """ROC-AUC (Mann-Whitney, ties = 0.5) and PR-AUC (average precision); None if one class."""
    y = np.asarray(y_bin, bool)
    s = np.asarray(score, float)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return {"ROC_AUC": None, "PR_AUC": None}
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    roc = gt / (len(pos) * len(neg))
    order = np.argsort(-s, kind="mergesort")
    ys, ss = y[order], s[order]
    ap, tp = 0.0, 0
    # average precision with ties handled by grouping equal scores
    i, n = 0, len(ys)
    while i < n:
        j = i
        while j < n and ss[j] == ss[i]:
            j += 1
        tp_new = tp + ys[i:j].sum()
        if ys[i:j].sum() > 0:
            ap += (ys[i:j].sum() / len(pos)) * (tp_new / j)
        tp = tp_new
        i = j
    return {"ROC_AUC": float(roc), "PR_AUC": float(ap)}


def classification(y_bin, pred_bin) -> dict:
    y = np.asarray(y_bin, bool)
    p = np.asarray(pred_bin, bool)
    tp, tn = int((y & p).sum()), int((~y & ~p).sum())
    fp, fn = int((~y & p).sum()), int((y & ~p).sum())
    rec_pos = tp / (tp + fn) if tp + fn else None
    rec_neg = tn / (tn + fp) if tn + fp else None
    prec_pos = tp / (tp + fp) if tp + fp else None
    prec_neg = tn / (tn + fn) if tn + fn else None
    ba = None if rec_pos is None or rec_neg is None else (rec_pos + rec_neg) / 2
    return {"n": int(len(y)), "positives": int(y.sum()), "negatives": int((~y).sum()),
            "TP": tp, "TN": tn, "FP": fp, "FN": fn, "balanced_accuracy": ba,
            "precision_pos": prec_pos, "recall_pos": rec_pos, "precision_neg": prec_neg, "recall_neg": rec_neg,
            "accuracy": float((y == p).mean())}


def cluster_bootstrap_mae_diff(df: pd.DataFrame, a: str, b: str, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Quarter-cluster bootstrap of MAE(a) - MAE(b). df has columns quarter, y, a, b."""
    rng = np.random.default_rng(seed)
    g = df.assign(ea=(df[a] - df["y"]).abs(), eb=(df[b] - df["y"]).abs()).groupby("quarter")
    s = g[["ea", "eb"]].sum()
    c = g.size()
    qs_ = s.index.to_numpy()
    k = len(qs_)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, k, k)
        n = c.iloc[idx].sum()
        diffs[i] = (s["ea"].iloc[idx].sum() - s["eb"].iloc[idx].sum()) / n
    point = float(((df[a] - df["y"]).abs().mean()) - ((df[b] - df["y"]).abs().mean()))
    return {"diff": point, "ci_low": float(np.quantile(diffs, 0.025)), "ci_high": float(np.quantile(diffs, 0.975)),
            "quarters": int(k)}


def sign_flip_p(per_quarter_diff: np.ndarray) -> float:
    """Exact one-sided sign-flip p for mean(diff) < 0 (model better)."""
    d = np.asarray(per_quarter_diff, float)
    obs = d.mean()
    k = len(d)
    cnt = 0
    for signs in itertools.product((1, -1), repeat=k):
        if (d * np.array(signs)).mean() <= obs + 1e-12:
            cnt += 1
    return cnt / 2 ** k


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def kendall_tau(a, b) -> float | None:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = len(a)
    if n < 2:
        return None
    s, m = 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            x, y = np.sign(a[i] - a[j]), np.sign(b[i] - b[j])
            if x == 0 or y == 0:
                continue
            s += x * y
            m += 1
    return float(s / m) if m else None


def spearman(a, b) -> float | None:
    a, b = pd.Series(a, dtype=float), pd.Series(b, dtype=float)
    if len(a) < 3:
        return None
    return float(a.rank().corr(b.rank()))
