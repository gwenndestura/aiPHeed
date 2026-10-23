"""E102 library (PROTOCOL.md): as-of market/price and economic-access indicators, walk-forward training pairs, the
trained forecast models and the extended metrics. Every indicator at origin t reads CPI quarters <= t-1 only."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E100_Market_Trigger_Investigation" / "runner"))
sys.path.insert(0, str(EXP / "E101_Access_Informed_Weighting" / "runner"))
import e100_run as R  # noqa: E402
import e101_run as E101  # noqa: E402

np, pd, TS, qi, qs = R.np, R.pd, R.TS, R.qi, R.qs
PROVS = R.PROVS
BASE_Q = "2021-Q1"
HIGH_FOOD_YOY = 4.0                       # BSP inflation-target ceiling, fixed
NEW = ("LVL", "REL", "PERS", "ACC", "VOL", "LAG")


# ------------------------------------------------------------------------------------------------ CPI
def load_cpi() -> dict:
    c = pd.read_parquet(R.BACKEND / "data/processed/cpi_full.parquet", filters=[("year", ">=", 2021)])
    assert c["year"].min() >= 2021
    c = c[c["province_code"].isin(PROVS)]
    out = {"food": {}, "all": {}, "yoy": {}}
    for r in c.itertuples():
        q = qi(r.quarter)
        if pd.notna(r.cpi_food_nab):
            out["food"][(r.province_code, q)] = float(r.cpi_food_nab)
        if pd.notna(r.cpi_all_items):
            out["all"][(r.province_code, q)] = float(r.cpi_all_items)
        if pd.notna(r.cpi_food_yoy_pct):
            out["yoy"][(r.province_code, q)] = float(r.cpi_food_yoy_pct)
    return out


def indicators_at(cpi: dict, p: str, t: int) -> dict:
    """The six new indicators for province p at origin t from CPI quarters <= t-1 only."""
    f, a, y = cpi["food"], cpi["all"], cpi["yoy"]
    last, q0 = t - 1, qi(BASE_Q)

    def get(d, q):
        return d.get((p, q)) if q <= last else None          # never read a quarter >= t
    out = {k: None for k in NEW}
    f1, f0 = get(f, last), get(f, q0)
    if f1 and f0:
        out["LVL"] = 100 * (f1 / f0 - 1)
        a1, a0 = get(a, last), get(a, q0)
        if a1 and a0:
            out["REL"] = 100 * ((f1 / a1) / (f0 / a0) - 1)
    win = [get(y, q) for q in range(t - 4, t) if q >= q0]
    win = [v for v in win if v is not None]
    if len(win) >= 2:
        out["PERS"] = sum(v > HIGH_FOOD_YOY for v in win) / len(win)
    y1, y3 = get(y, last), get(y, t - 3)
    if y1 is not None and y3 is not None:
        out["ACC"] = y1 - y3
    out["LAG"] = y3
    qoq = []
    for q in range(t - 4, t):
        b, c_ = get(f, q - 1), get(f, q)
        if b and c_ and q - 1 >= q0:
            qoq.append(100 * (c_ / b - 1))
    if len(qoq) >= 3:
        out["VOL"] = float(np.std(qoq))
    return out


def panel(cpi: dict, origins) -> dict:
    return {(t, p): indicators_at(cpi, p, t) for t in origins for p in PROVS}


def percentiles(values: dict) -> dict:
    """values {(t, p): x} -> mid-rank percentile among all provinces' values at strictly earlier origins (>= 8)."""
    out = {}
    for (t, p), x in values.items():
        if x is None:
            continue
        prior = [v for (tt, _), v in values.items() if tt < t and v is not None]
        if len(prior) >= 8:
            out[(t, p)] = (sum(v < x for v in prior) + 0.5 * sum(v == x for v in prior)) / len(prior)
    return out


# ------------------------------------------------------------------------------------------------ outcomes
def full_quarters_posted(issue: str) -> dict[str, float]:
    """Quarters whose every definition_A round was posted before the issue date -> mean H (as thesis_system._posted)."""
    s = pd.read_csv(R.BACKEND / "data/inputs/sws_rounds.csv")
    s = s[s["definition_A"].astype(str) == "True"]
    out = {}
    for q, g in s.groupby("quarter"):
        if (g["published"].astype(str).str[:10] < issue).all():
            out[q] = float(g["H"].mean())
    return out


def training_pairs(feats: dict, lead: int, t: int, cols) -> pd.DataFrame:
    """Rows (t', features at t', y at t'+lead) with t' < t and quarter t'+lead fully posted before issue(t)."""
    known = full_quarters_posted(TS.issue_of(t))
    rows = []
    for tp, fr in feats.items():
        tq = qs(tp + lead)
        if tp < t and tq in known and all(fr.get(c) is not None and not pd.isna(fr.get(c)) for c in cols):
            rows.append({**{c: fr[c] for c in cols}, "y": int(known[tq] > R.HUNGER_LINE), "t": tp})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ models
MIN_TRAIN = 8


def fit_predict(kind: str, train: pd.DataFrame, x: dict, cols) -> float | None:
    if len(train) < MIN_TRAIN or any(x.get(c) is None or pd.isna(x.get(c)) for c in cols):
        return None
    y = train["y"].to_numpy(int)
    if len(set(y)) < 2:
        return float(y.mean())
    X = train[list(cols)].to_numpy(float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    z = (np.array([float(x[c]) for c in cols]) - mu) / sd
    if kind == "logit":
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000).fit(Z, y)
        return float(m.predict_proba(z.reshape(1, -1))[0, 1])
    import lightgbm as lgb
    m = lgb.LGBMClassifier(n_estimators=25, num_leaves=2, max_depth=1, learning_rate=0.1, min_child_samples=3,
                           reg_lambda=5.0, deterministic=True, random_state=102, n_jobs=1, verbose=-1,
                           force_row_wise=True).fit(Z, y)
    return float(m.predict_proba(z.reshape(1, -1))[0, 1])


# ------------------------------------------------------------------------------------------------ metrics
def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    m = R.metrics(y, p)
    yh = (p >= 0.5).astype(int)
    tn, fn = m["confusion"]["TN"], m["confusion"]["FN"]
    prec_low = tn / (tn + fn) if tn + fn else None
    rec_low = m["recall_LOW"]
    m["precision_LOW"] = prec_low
    m["f1_LOW"] = (2 * prec_low * rec_low / (prec_low + rec_low)) if prec_low and rec_low else (
        0.0 if prec_low is not None and rec_low is not None else None)
    m["calibration_in_the_large"] = float(p.mean() - y.mean())
    m["share_predicted_HIGH"] = float(yh.mean())
    return m
