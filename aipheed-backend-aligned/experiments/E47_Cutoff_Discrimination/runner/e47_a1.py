"""E47 addendum A1: price-signal logistic (PS-P, PS-5T) inside the product structure p = P(hunger) x P(price signal).
The price-signal model is fitted on its own outcome (observed whenever CPI is complete), not on T43."""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e47_lib as E  # noqa: E402

M, C, K, L, P2, I7, np, pd = E.M, E.C, E.K, E.L, E.P2, E.I7, E.np, E.pd
PRICE_MARGINS = ["mF1", "mF0", "mG1", "mG0"]
COLS = {"PS-P": PRICE_MARGINS, "PS-5T": PRICE_MARGINS + [c for g in E.TRIGGERS_SL.values() for c in g]}
CREG = {"PS-P": 1.0, "PS-5T": 0.1}


def ps_labels(d, t: int) -> pd.DataFrame:
    """Price signal of every quarter <= t-1 whose three CPI months were published before O(t)."""
    th = L.e40_spec()
    c = d.cut(t)
    F = L.quarter_F(c)
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL"})
    Y = F.merge(HL, on=["province_code", "q"])
    Y["ps"] = ((Y["F"] > Y["province_code"].map(th["food"])) |
               ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"]))).astype(int)
    return Y[Y["q"] <= t - 1][["province_code", "q", "ps"]]


def _fit_predict(kind, tr, te):
    from sklearn.linear_model import LogisticRegression
    s = E.Std(COLS[kind]).fit(tr)
    m = LogisticRegression(C=CREG[kind], max_iter=5000).fit(s.transform(tr), tr["ps"].astype(int))
    return m.predict_proba(s.transform(te))[:, 1], m, s


def _eligible(tr) -> bool:
    return tr["ps"].nunique() == 2 and min(tr["ps"].sum(), (1 - tr["ps"]).sum()) >= 3 and tr["q"].nunique() >= 6


def inner_threshold(kind, tr) -> float:
    oof = []
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
        if not _eligible(fit):
            continue
        p, _, _ = _fit_predict(kind, fit, hold)
        oof.append(hold[["ps"]].assign(p=p))
    if not oof:
        return 0.5
    o = pd.concat(oof)
    if o["ps"].sum() < 3 or (o["ps"] == 0).sum() < 3:
        return 0.5
    return float(max(E.THRESHOLDS, key=lambda th: (round(C.balanced(o["ps"], o["p"] >= th), 10), -abs(th - 0.5))))


def forecast_ps(kind, D, d, t):
    lab = ps_labels(d, t)
    tr = D[D["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(lab, on=["province_code", "q"])
    te = D[D["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    if not _eligible(tr):
        return None
    p, m, s = _fit_predict(kind, tr, te)
    return {"p_ps": p, "tau": inner_threshold(kind, tr), "n_train": int(len(tr)), "n_train_signal": int(tr["ps"].sum()),
            "model": m, "std": s, "te": te}
