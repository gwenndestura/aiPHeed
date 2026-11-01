"""Shared code for X1-X3 (EXPERIMENT_PLAN.md): the four-area SWS panel with publication dates, the hunger models
RW / CLIM / MR / MRF, and metrics. Read-only on every input."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import functools  # noqa: E402
import hashlib  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
OUT = HERE.parent / "out"
LONG = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long"
H_LINE, SIG_FLOOR, B, SEED = 11.3, 0.5, 5000, 2036
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
MIN_PAIRS, MIN_PAIRS_F = 8, 20


def frozen_ok() -> None:
    want = (HERE / "PLAN_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((HERE.parent / "EXPERIMENT_PLAN.md").read_bytes()).hexdigest()
    assert got == want, "EXPERIMENT_PLAN.md changed after freezing"


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{int(i) // 4}-Q{int(i) % 4 + 1}"


def issue(t: int) -> pd.Timestamp:
    """First day of quarter t + 1."""
    n = t + 1
    return pd.Timestamp(year=n // 4, month=3 * (n % 4) + 1, day=1)


def m0(t: int) -> int:
    """Month 2 of quarter t as year * 12 + month - 1."""
    return (t // 4) * 12 + 3 * (t % 4) + 1


# ------------------------------------------------------------------------------------------------ panel
@functools.lru_cache(maxsize=1)
def rounds() -> pd.DataFrame:
    a = pd.read_csv(LONG / "sws_area_rounds_full.csv")
    a["published"] = pd.to_datetime(a["published"])
    rows = []
    for _, r in a.iterrows():
        for area, col in AREAS.items():
            if area == "BL" and r["quarter"] >= "2021-Q1":
                continue                                          # BL 2021+ comes from the production series
            if pd.notna(r[col]):
                moe = r["area_moe_bl"] if area == "BL" else r.get("area_moe_other", np.nan)
                rows.append({"area": area, "q": qi(r["quarter"]), "H": float(r[col]), "published": r["published"],
                             "moe": float(moe) if pd.notna(moe) else np.nan})
    p = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv")
    p = p[p["quarter"] >= "2021-Q1"]
    moe_bl = a.set_index("quarter")["area_moe_bl"].groupby(level=0).first()
    for _, r in p.iterrows():
        rows.append({"area": "BL", "q": qi(r["quarter"]), "H": float(r["H"]), "published": pd.Timestamp(r["published"]),
                     "moe": float(moe_bl.get(r["quarter"], 4.0 if r["quarter"] >= "2024-Q1" else 6.0))})
    return pd.DataFrame(rows)


def observed() -> dict[tuple[str, int], float]:
    """Final (all rounds) quarterly mean per area: the outcome."""
    return rounds().groupby(["area", "q"])["H"].mean().to_dict()


@functools.lru_cache(maxsize=4096)
def known(area: str, iss: pd.Timestamp) -> dict[int, float]:
    r = rounds()
    k = r[(r["area"] == area) & (r["published"] < iss)]
    return k.groupby("q")["H"].mean().to_dict()


@functools.lru_cache(maxsize=1)
def food_yoy() -> dict[int, float]:
    c = pd.read_csv(LONG / "cov_cpi.csv")
    c = c[(c["geolocation"] == "PHILIPPINES") & (c["commodity_description"] == "01.1 - FOOD")]
    return {int(k): float(v) for k, v in zip(c["ym"], c["yoy"]) if pd.notna(v)}


def pairs(areas: tuple[str, ...], iss: pd.Timestamp, h: int) -> pd.DataFrame:
    out = []
    for a in areas:
        d = known(a, iss)
        if not d:
            continue
        ma = float(np.mean(list(d.values())))
        for q0, v0 in d.items():
            if q0 + h in d:
                out.append({"area": a, "q0": q0, "y0": v0, "y1": d[q0 + h], "m": ma,
                            "F": food_yoy().get(m0(q0 + 1), np.nan)})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ models
def prob(mu: float, sig: float) -> float:
    return float(norm.cdf((mu - H_LINE) / max(sig, SIG_FLOOR)))


def forecast(area: str, t: int, k: int, fit_areas: tuple[str, ...]) -> dict | None:
    """RW, CLIM, MR, MRF probabilities and means for one area / origin / lead (EXPERIMENT_PLAN section 3)."""
    iss = issue(t)
    d = known(area, iss)
    if not d:
        return None
    q_last = max(d)
    h = (t + k) - q_last
    pr = pairs(fit_areas, iss, h)
    if len(pr) < MIN_PAIRS:
        return None
    assert h >= 1
    m_a = float(np.mean(list(d.values())))
    x_last = d[q_last]
    out = {"h": h, "q_last": q_last, "x_last": x_last, "pairs": len(pr)}
    rw_sig = math.sqrt(float(np.mean((pr["y1"] - pr["y0"]) ** 2)))
    out.update(RW_mu=x_last, RW=prob(x_last, rw_sig))
    out["CLIM"] = float(np.mean([v > H_LINE for v in d.values()]))
    x, z = (pr["y0"] - pr["m"]).to_numpy(), (pr["y1"] - pr["m"]).to_numpy()
    beta = float(np.clip(np.dot(x, z) / np.dot(x, x), 0, 1)) if np.dot(x, x) > 0 else 1.0
    sig = math.sqrt(float(np.mean((z - beta * x) ** 2)))
    mu = m_a + beta * (x_last - m_a)
    out.update(MR_mu=mu, MR=prob(mu, sig), beta=beta)
    f_now = food_yoy().get(m0(t), np.nan)
    pf = pr.dropna(subset=["F"])
    if len(pf) >= MIN_PAIRS_F and not math.isnan(f_now):
        fbar = float(pf["F"].mean())
        X = np.column_stack([(pf["y0"] - pf["m"]).to_numpy(), (pf["F"] - fbar).to_numpy()])
        zf = (pf["y1"] - pf["m"]).to_numpy()
        coef = np.linalg.lstsq(X, zf, rcond=None)[0]
        sf = math.sqrt(float(np.mean((zf - X @ coef) ** 2)))
        muf = m_a + coef[0] * (x_last - m_a) + coef[1] * (f_now - fbar)
        out.update(MRF_mu=float(muf), MRF=prob(float(muf), sf), gamma=float(coef[1]), MRF_fallback=False)
    else:
        out.update(MRF_mu=mu, MRF=out["MR"], gamma=None, MRF_fallback=True)
    return out


# ------------------------------------------------------------------------------------------------ metrics
def metrics(y, p, mu=None, level=None, onset=None) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    out = {"n": int(len(y)), "pos": int(y.sum()), "neg": int((1 - y).sum()), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
           "accuracy": r(tp + tn, len(y)), "balanced": None if rec is None or spec is None else (rec + spec) / 2,
           "precision": prec, "recall": rec, "specificity": spec,
           "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
           "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
           "brier": float(np.mean((p - y) ** 2))}
    if mu is not None and level is not None:
        out["mae"] = float(np.mean(np.abs(np.asarray(mu, float) - np.asarray(level, float))))
    if onset is not None:
        o = np.asarray(onset, bool)
        out["onsets"] = f"{int((yh[o] == 1).sum())}/{int(o.sum())}"
    return out


def brier_vs(d: pd.DataFrame, a: str, b: str, cluster: str = "target") -> dict:
    """Mean Brier(a) - Brier(b), one-sided quarter-cluster bootstrap p (H0: a not better)."""
    d = d.assign(_l=(d[a] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2)
    g = d.groupby(cluster)["_l"].agg(["sum", "size"])
    s, n = g["sum"].to_numpy(), g["size"].to_numpy()
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), size=(B, len(g)))
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"diff": round(float(d["_l"].mean()), 5), "p_one_sided": float(np.mean(bs >= 0)), "clusters": int(len(g))}
