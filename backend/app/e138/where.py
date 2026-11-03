"""
E138 WHERE: controlled comparison for structural relative risk (PROTOCOL.md sections 3-6).

Identical rows (E137's 125 HFIAS rows with a value, primary outcome, pooled reference), identical folds and metrics for
every candidate. Schemes:
    LORO    leave-one-region-out (16 regions)            geographic transfer to an unseen region
    LOPO    leave-one-province-out (both rounds together) within-region information (REG, HIER become meaningful)
    ISLAND  leave-one-island-group-out (Luzon/Visayas/Mindanao)
    V2      train FNRI 2015 -> predict ENNS 2018/2019     stability across surveys (anchor models excluded)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.e137 import evaluate as E137
from app.e137 import features as F137
from app.e137 import model as M137
from app.e138 import models as M

KEEP = ["key", "province", "region", "island", "survey", "y", "se_y", "q", "status", "prev_y", "prev_se_y"]
N_BOOT = 1000


def data(outcome="mod_sev", reference="pooled", lead=0) -> pd.DataFrame:
    return E137._data(outcome, reference, lead)


def folds(X: pd.DataFrame, scheme: str):
    if scheme == "LORO":
        g = X["region"]
    elif scheme == "LOPO":
        g = X["key"]
    elif scheme == "ISLAND":
        g = X["island"]
    elif scheme == "V2":
        yield X["survey"] == "FNRI2015", X["survey"] != "FNRI2015"
        return
    for v in g.unique():
        yield g != v, g == v


def oof(X: pd.DataFrame, scheme: str, names: list[str], mask: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Out-of-fold P for each candidate. `mask`: feature columns set to missing at prediction time (robustness)."""
    out = X[KEEP].copy()
    train_eb = {n: [] for n in names}
    for tr, te in folds(X, scheme):
        Xte = X[te].copy()
        if mask:
            Xte[mask] = np.nan
        for n in names:
            if scheme == "V2" and ("A" in n.split("-")[-1] and n not in ("NAT", "REG")):
                continue
            m = M.make(n).fit(X[tr])
            rows = Xte.index if n != "PERS" else Xte.index[Xte["prev_y"].notna()]
            if len(rows):
                out.loc[rows, n] = m.predict_proba(Xte.loc[rows])
            if n not in ("PERS",):
                train_eb[n].append((int(tr.sum()), M137.expected_brier(m.predict_proba(X[tr]), X.loc[tr, "q"])))
    gaps = {n: sum(k * e for k, e in v) / sum(k for k, _ in v) for n, v in train_eb.items() if v}
    return out, gaps


def boot(df: pd.DataFrame, a: str, b: str, rng, n=N_BOOT) -> dict:
    d = df.dropna(subset=[a, b])
    regs = d["region"].unique()
    grp = {r: d[d["region"] == r] for r in regs}
    v = []
    for _ in range(n):
        s = pd.concat([grp[r] for r in rng.choice(regs, len(regs))])
        v.append(M137.expected_brier(s[a], s["q"]) - M137.expected_brier(s[b], s["q"]))
    v = np.asarray(v)
    return {"diff": M137.expected_brier(d[a], d["q"]) - M137.expected_brier(d[b], d["q"]), "se": float(v.std(ddof=1)),
            "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], "n": int(len(d))}


def table(df: pd.DataFrame, names: list[str], gaps: dict | None = None) -> dict:
    out = {}
    for n in names:
        if n in df and df[n].notna().any():
            m = E137.metrics(df.drop(columns=[c for c in ["yhat"] if c in df]), n)
            if gaps and n in gaps:
                m["train_expected_brier"] = gaps[n]
                m["overfit_gap"] = m["expected_brier"] - gaps[n]
            out[n] = m
    return out


def select(df: pd.DataFrame, rng) -> dict:
    """One-SE rule (frozen): best = lowest LORO expected Brier among COMPLEXITY; choose the first (simplest) candidate
    whose EB - EB(best) <= bootstrap SE of that difference."""
    eb = {n: M137.expected_brier(df[n], df["q"]) for n in M.COMPLEXITY if n in df}
    best = min(eb, key=eb.get)
    trail = []
    for n in M.COMPLEXITY:
        if n not in eb:
            continue
        b = boot(df, n, best, rng) if n != best else {"diff": 0.0, "se": 0.0}
        trail.append({"model": n, "eb": eb[n], "diff_vs_best": b["diff"], "se": b["se"]})
        if b["diff"] <= b["se"]:
            return {"best": best, "selected": n, "trail": trail}
    return {"best": best, "selected": best, "trail": trail}


def linear_group_shares(model, X: pd.DataFrame) -> pd.DataFrame:
    """Exact additive logit contributions coef x standardised value, summed by E137 group (anchor excluded)."""
    Z = M.design(X, model.cols)
    Zs = pd.DataFrame(model.std_(Z), columns=Z.columns, index=X.index)
    contrib = Zs * model.m_.coef_[0]
    grp = {g: [c for c in fs if c in contrib] for g, fs in F137.GROUPS.items() if g != "anchor"}
    G = pd.DataFrame({g: contrib[c].abs().sum(axis=1) for g, c in grp.items() if c})
    return G.div(G.sum(axis=1).replace(0, np.nan), axis=0)
