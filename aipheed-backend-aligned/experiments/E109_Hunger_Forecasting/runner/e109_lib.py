"""E109 library (PROTOCOL.md): forecasting SWS Balance Luzon experienced hunger (continuous), its binary readings,
baselines, the local-level filter, ridge and the constrained LightGBM, with issue-date rules and the evaluation code.
Features are E107's issue-date-cut 13 columns (12 families), averaged over the five provinces per origin."""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E109 = HERE.parent
E107R = E109.parent / "E107_Twelve_Indicator_LightGBM" / "runner"
sys.path.insert(0, str(E107R))
import e107_lib as E  # noqa: E402

L, np, pd = E.L, E.np, E.pd
OUT = E109 / "out"
ROUNDS = E109 / "data" / "outcome_rounds.csv"
LEADS = (1, 2, 3, 4)
MIN_PAIRS = 8
MOE_BL = 4.0                                   # SWS Balance Luzon sampling margin (S1, S3)
R_OBS = (MOE_BL / 1.959964) ** 2               # observation variance of one Balance Luzon reading
THRESHOLDS = {"B1": 11.3, "B2": 15.0, "B3": 20.0}
RISE = 4.0                                     # B4: rise beyond the SWS margin
SEED = 109
BASELINES = ["RW", "MEAN", "MA2", "SEAS"]
CANDIDATES = ["LL", "RIDGE", "LGBM"]
METHODS = BASELINES + CANDIDATES
PRIMARY = "LGBM"
RULES = ("primary", "ALL", "PROD", "HH")


# ================================================================================================ outcome series
@functools.lru_cache(maxsize=1)
def rounds() -> pd.DataFrame:
    r = pd.read_csv(ROUNDS)
    r["q"] = r["quarter"].map(E.qi)
    return r


def rule_rounds(rule: str) -> pd.DataFrame:
    r = rounds()
    if rule == "primary":
        return r[r["in_primary_series"]]
    if rule == "ALL":
        return r
    if rule == "PROD":
        return r[r["in_E107_E108_production_series"]]
    if rule == "HH":
        return r[r["in_primary_series"] & (r["respondent_base"] == "household heads")]
    raise ValueError(rule)


@functools.lru_cache(maxsize=4096)
def known(issue: str, rule: str = "primary") -> tuple[tuple[int, float], ...]:
    """(quarter, mean H of its rule-rounds published before the issue date): the real-time vintage (ADDENDUM_1)."""
    r = rule_rounds(rule)
    r = r[r["published"].str[:10] < issue]
    return tuple(sorted((int(q), float(g["H"].mean())) for q, g in r.groupby("q")))


def outcome(q: int, rule: str = "primary") -> float | None:
    g = rule_rounds(rule)
    g = g[g["q"] == q]
    return float(g["H"].mean()) if len(g) else None


def outcome_quarters(rule: str = "primary") -> list[int]:
    return sorted(int(q) for q in rule_rounds(rule)["q"].unique())


def h_last(t: int, rule: str = "primary") -> tuple[int, float] | None:
    k = known(E.issue(t), rule)
    return k[-1] if k else None


# ================================================================================================ features
@functools.lru_cache(maxsize=8)
def regional_features(k: int) -> pd.DataFrame:
    X = E.feature_table(k)
    return X.groupby("t")[E.COLUMNS].mean()


# ================================================================================================ training pairs
def pairs(t: int, k: int, rule: str = "primary") -> pd.DataFrame:
    """(origin t' < t, target t'+k) with H_{t'+k} known at O(t) and H_last(t') known at O(t')."""
    kn = dict(known(E.issue(t), rule))
    X = regional_features(k)
    rows = []
    for tp in range(E.FIRST_ORIGIN, t):
        q = tp + k
        if q not in kn:
            continue
        hl = h_last(tp, rule)
        if hl is None:
            continue
        rows.append({"t": tp, "q": q, "h_last": hl[1], "y": kn[q], "dy": kn[q] - hl[1],
                     **{c: X.loc[tp, c] if tp in X.index else np.nan for c in E.COLUMNS}})
    return pd.DataFrame(rows)


# ================================================================================================ methods
def local_level(series: tuple[tuple[int, float], ...]) -> tuple[float, float, float]:
    """Kalman local-level filter with known observation variance R_OBS and Q by moments from consecutive known
    quarters ((dH^2 - 2R)/gap, floor 0.25). Returns (filtered level at the last known quarter, its variance P, Q)."""
    qs_, hs = [s[0] for s in series], [s[1] for s in series]
    d = [((hs[i] - hs[i - 1]) ** 2 - 2 * R_OBS) / (qs_[i] - qs_[i - 1]) for i in range(1, len(hs))]
    Q = max(float(np.mean(d)) if d else 0.25, 0.25)
    a, P = hs[0], R_OBS
    for i in range(1, len(hs)):
        P = P + Q * (qs_[i] - qs_[i - 1])
        K = P / (P + R_OBS)
        a, P = a + K * (hs[i] - a), (1 - K) * P
    return a, P, Q


def _ridge(tr: pd.DataFrame, x: pd.Series) -> float:
    from sklearn.linear_model import Ridge
    A = tr[E.COLUMNS].astype(float)
    med = A.median().fillna(0.0)
    A = A.fillna(med)
    keep = [c for c in E.COLUMNS if A[c].nunique() > 1]
    if not keep:
        return float(tr["dy"].mean())
    mu, sd = A[keep].mean(), A[keep].std().replace(0, 1.0)
    m = Ridge(alpha=10.0).fit(((A[keep] - mu) / sd).to_numpy(), tr["dy"].to_numpy())
    z = ((x[keep].astype(float).fillna(med[keep]) - mu) / sd).to_numpy().reshape(1, -1)
    return float(m.predict(z)[0])


def _lgbm(trees: int):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="regression", n_estimators=trees, learning_rate=0.05, max_depth=1,
                             num_leaves=2, min_child_samples=3, reg_lambda=5.0, deterministic=True,
                             force_row_wise=True, feature_pre_filter=False, random_state=SEED, n_jobs=1, verbose=-1,
                             boost_from_average=False)


def _lgbm_fit(tr: pd.DataFrame, trees: int):
    return _lgbm(trees).fit(tr[E.COLUMNS].astype(float), tr["dy"].to_numpy())


def lgbm_select(tr: pd.DataFrame, k: int) -> int:
    """Trees in {25, 75} by MAE on the last 4 training targets, each fitted on pairs with target <= q_v - k - 1."""
    qv = sorted(tr["q"].unique())[-4:]
    sc = {}
    for n in (25, 75):
        errs = []
        for q in qv:
            fit, hold = tr[tr["q"] <= q - k - 1], tr[tr["q"] == q]
            if len(fit) < 4 or not len(hold):
                continue
            errs += list(np.abs(_lgbm_fit(fit, n).predict(hold[E.COLUMNS].astype(float)) - hold["dy"].to_numpy()))
        sc[n] = float(np.mean(errs)) if errs else float("inf")
    return min((25, 75), key=lambda n: (round(sc[n], 9), n))


@functools.lru_cache(maxsize=20000)
def forecast(method: str, t: int, k: int, rule: str = "primary") -> dict | None:
    """Point forecast of H_{t+k} issued at O(t), or None when the origin has fewer than MIN_PAIRS training pairs."""
    kn = known(E.issue(t), rule)
    if not kn:
        return None
    tr = pairs(t, k, rule)
    if len(tr) < MIN_PAIRS:
        return None
    hl = kn[-1][1]
    out = {"h_last": hl, "h_last_quarter": E.qs(kn[-1][0]), "n_pairs": len(tr)}
    if method == "RW":
        f = hl
    elif method == "MEAN":
        f = float(np.mean([v for _, v in kn]))
    elif method == "MA2":
        f = float(np.mean([v for _, v in kn[-2:]]))
    elif method == "SEAS":
        f = dict(kn).get(t + k - 4, hl)
    elif method == "LL":
        f, P, Q = local_level(kn)
        out.update(ll_P=P, ll_Q=Q)
    elif method in ("RIDGE", "LGBM"):
        X = regional_features(k)
        x = X.loc[t]
        if method == "RIDGE":
            f = hl + _ridge(tr, x)
        else:
            n = lgbm_select(tr, k)
            m = _lgbm_fit(tr, n)
            d = float(m.predict(pd.DataFrame([x[E.COLUMNS].astype(float)]))[0])
            f = hl + d
            out.update(trees=n, delta=d, gain=dict(zip(E.COLUMNS, m.booster_.feature_importance("gain").astype(float))),
                       shap=dict(zip(E.COLUMNS + ["_base"], map(float, m.booster_.predict(
                           pd.DataFrame([x[E.COLUMNS].astype(float)]), pred_contrib=True)[0]))))
    else:
        raise ValueError(method)
    out["forecast"] = float(f)
    return out


def sigma(method: str, t: int, k: int, rule: str = "primary") -> float:
    """RMSE of the method's own earlier lead-k errors whose target was known at O(t) (>= 4), else the training SD of
    the change."""
    kn = dict(known(E.issue(t), rule))
    errs = []
    for tp in range(E.FIRST_ORIGIN, t - k + 1):
        q = tp + k
        if q in kn:
            f = forecast(method, tp, k, rule)
            if f is not None:
                errs.append(kn[q] - f["forecast"])
    if len(errs) >= 4:
        return float(math.sqrt(np.mean(np.square(errs))))
    tr = pairs(t, k, rule)
    return float(tr["dy"].std()) if len(tr) > 1 else 4.0


def p_above(f: float, c: float, s: float) -> float:
    return float(1 - 0.5 * (1 + math.erf((c - f) / (max(s, 1e-6) * math.sqrt(2)))))


# ================================================================================================ evaluation
def evaluate(k: int, rule: str = "primary", methods=METHODS) -> pd.DataFrame:
    """One row per evaluated target quarter: the outcome, every method's forecast, sigma and binary probabilities."""
    rows = []
    for q in outcome_quarters(rule):
        t = q - k
        if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
            continue
        base = forecast("RW", t, k, rule)
        if base is None:
            continue
        y = outcome(q, rule)
        r = {"q": q, "quarter": E.qs(q), "t": t, "origin": E.qs(t), "issue_date": E.issue(t), "lead": k, "y": y,
             "h_last": base["h_last"], "h_last_quarter": base["h_last_quarter"], "n_pairs": base["n_pairs"]}
        for m in methods:
            f = forecast(m, t, k, rule)
            s = sigma(m, t, k, rule)
            r[f"{m}"] = f["forecast"]
            r[f"{m}_sigma"] = s
            for b, c in THRESHOLDS.items():
                r[f"{m}_p{b}"] = p_above(f["forecast"], c, s)
            r[f"{m}_pB4"] = p_above(f["forecast"], base["h_last"] + RISE, s)
            if m == "LGBM":
                r["LGBM_trees"] = f["trees"]
        kn = known(E.issue(t), rule)
        for b, c in THRESHOLDS.items():
            r[f"PERSIST_p{b}"] = float(base["h_last"] > c)
            r[f"CLIM_p{b}"] = float(np.mean([v > c for _, v in kn]))
        tr = pairs(t, k, rule)
        r["PERSIST_pB4"] = 0.0
        r["CLIM_pB4"] = float((tr["dy"] > RISE).mean())
        for b, c in THRESHOLDS.items():
            r[f"y{b}"] = int(y > c)
        r["yB4"] = int(y - base["h_last"] > RISE)
        rows.append(r)
    return pd.DataFrame(rows)


def dm_test(e_model, e_base, h: int) -> dict:
    """One-sided Diebold-Mariano (HLN small-sample correction) on absolute-error differentials; H1: model better."""
    from scipy.stats import t as tdist
    d = np.abs(np.asarray(e_model)) - np.abs(np.asarray(e_base))
    n = len(d)
    if n < 3:
        return {"n": n, "p": None}
    dbar = float(d.mean())
    dc = d - dbar
    lag = max(h - 1, 0)
    v = float(np.dot(dc, dc) / n) + 2 * sum(float(np.dot(dc[j:], dc[:-j]) / n) for j in range(1, lag + 1))
    if v <= 0:
        return {"n": n, "mean_diff": dbar, "p": 0.0 if dbar < 0 else 1.0}
    dm = dbar / math.sqrt(v / n)
    adj = math.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 1e-9))
    stat = dm * adj
    return {"n": n, "mean_diff": dbar, "stat": stat, "p": float(tdist.cdf(stat, df=n - 1))}


def block_ci(err, k: int, draws: int = 2000, seed: int = 2026) -> list[float]:
    e = np.abs(np.asarray(err))
    n = len(e)
    if n < 2:
        return [float("nan")] * 2
    rng = np.random.default_rng(seed)
    b = max(k, 1)
    starts = np.arange(n - b + 1)
    vals = []
    for _ in range(draws):
        idx = np.concatenate([np.arange(s, s + b) for s in rng.choice(starts, int(math.ceil(n / b)))])[:n]
        vals.append(float(e[idx].mean()))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def cont_metrics(df: pd.DataFrame, m: str, k: int) -> dict:
    e = df[m] - df["y"]
    mae_rw = float(np.abs(df["RW"] - df["y"]).mean())
    mae = float(np.abs(e).mean())
    return {"n_quarters": len(df), "mae": mae, "rmse": float(np.sqrt(np.mean(e ** 2))), "bias": float(e.mean()),
            "mae_block95": block_ci(e.to_numpy(), k), "skill_vs_rw": 1 - mae / mae_rw if mae_rw else None,
            "within_moe_share": float((np.abs(e) <= MOE_BL).mean())}


def decide_cont(df: pd.DataFrame, m: str, k: int) -> dict:
    n = len(df)
    base = {b: float(np.abs(df[b] - df["y"]).mean()) for b in BASELINES}
    best = min(base, key=base.get)
    mae = float(np.abs(df[m] - df["y"]).mean())
    dm = dm_test((df[m] - df["y"]).to_numpy(), (df[best] - df["y"]).to_numpy(), k)
    h = (n + 1) // 2

    def mae_on(d, c):
        return float(np.abs(d[c] - d["y"]).mean())
    halves = [mae_on(p, m) < min(mae_on(p, b) for b in BASELINES) for p in (df.iloc[:h], df.iloc[h:]) if len(p)]
    last = df.iloc[-4:]
    c = {"C1": n >= 8, "C2": mae < base[best] and dm.get("p") is not None and dm["p"] < 0.10, "C3": mae <= MOE_BL,
         "C4": len(halves) == 2 and all(halves), "C5": mae_on(last, m) <= min(mae_on(last, b) for b in BASELINES),
         "C6": False}
    if not c["C1"]:
        st = "insufficient evidence"
    elif all(c[x] for x in ("C2", "C3", "C4", "C5")):
        st = "provisional"
    else:
        st = "not reliable"
    return {"status": st, "criteria": c, "failed": [x for x, v in c.items() if not v], "mae": mae,
            "best_baseline": best, "best_baseline_mae": base[best], "baseline_mae": base, "dm_vs_best": dm}


def bin_metrics(df: pd.DataFrame, pcol: str, ycol: str) -> dict:
    y, p = df[ycol].to_numpy(int), df[pcol].to_numpy(float)
    c = (p >= 0.5).astype(int)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    rh = tp / (tp + fn) if tp + fn else None
    rl = tn / (tn + fp) if tn + fp else None
    ph = tp / (tp + fp) if tp + fp else None
    auc = None
    if y.sum() >= 2 and (1 - y).sum() >= 2:
        pos, neg = p[y == 1], p[y == 0]
        auc = float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))
    return {"n": len(y), "n_high": int(y.sum()), "accuracy": (tp + tn) / len(y) if len(y) else None,
            "balanced_accuracy": (rh + rl) / 2 if rh is not None and rl is not None else None,
            "precision_high": ph, "recall_high": rh, "recall_low": rl,
            "f1_high": 2 * ph * rh / (ph + rh) if ph and rh else None, "auc": auc,
            "brier": float(np.mean((p - y) ** 2)) if len(y) else None,
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def decide_bin(df: pd.DataFrame, m: str, b: str) -> dict:
    mm = bin_metrics(df, f"{m}_p{b}", f"y{b}")
    pe, cl = bin_metrics(df, f"PERSIST_p{b}", f"y{b}"), bin_metrics(df, f"CLIM_p{b}", f"y{b}")
    both = mm["n_high"] >= 2 and mm["n"] - mm["n_high"] >= 2
    c = {"n>=8": mm["n"] >= 8, "both_classes>=2": both, "acc>=0.75": (mm["accuracy"] or 0) >= 0.75,
         "bal>=0.65": (mm["balanced_accuracy"] or 0) >= 0.65,
         "recalls>=0.5": bool(both and mm["recall_high"] is not None and mm["recall_low"] is not None
                              and mm["recall_high"] >= 0.5 and mm["recall_low"] >= 0.5),
         "brier<persist&clim": mm["brier"] < pe["brier"] and mm["brier"] < cl["brier"], "confirmed_unseen": False}
    if not c["n>=8"] or not both:
        st = "insufficient evidence"
    elif all(v for x, v in c.items() if x != "confirmed_unseen"):
        st = "provisional"
    else:
        st = "not reliable"
    return {"status": st, "criteria": c, "failed": [x for x, v in c.items() if not v], "metrics": mm,
            "persistence": pe, "climatology": cl}


def write_json(p, o):
    E.write_json(p, o)


def sha256(p):
    return E.sha256(p)
