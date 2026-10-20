"""E67 shared library (PROTOCOL.md): protocol check, the E56-TUNED procedure with trigger groups removed from both the
price and the hunger part, and per-group TreeSHAP / split counts.

E67 reads E56-E66 files and never writes into them; outputs go under E67/out and E67/tables.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E67 = Path(__file__).resolve().parents[1]
EXP = E67.parent
sys.path.insert(0, str(EXP / "E66_Best_Methodology_Review" / "runner"))
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e66_lib as H  # noqa: E402
import e56_lib as G  # noqa: E402

F, L, E, P2, I7, np, pd = G.F, G.L, G.E, G.P2, G.I7, G.np, G.pd
OUT, TABLES = E67 / "out", E67 / "tables"
EVAL_ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1))
FORWARD_ORIGINS = [L.qi("2026-Q2"), L.qi("2026-Q3")]
TRIGGERS = ["climate", "fish_kill", "employment", "ofw_remittance", "news"]
ARMS = {"A0": (), "X_climate": ("climate",), "X_fish": ("fish_kill",), "X_employment": ("employment",),
        "X_ofw": ("ofw_remittance",), "X_news": ("news",), "M_only": tuple(TRIGGERS)}


def verify_protocol() -> str:
    want = (E67 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E67 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("E67 PROTOCOL.md changed after freezing")
    return got


def group_of(col: str) -> str:
    if col in F.M.POLICY:
        return "market"
    for g, cs in P2.PRICE_GROUPS.items():
        if col in cs:
            return g
    return "other"


def hunger_cols(drop=()) -> list[str]:
    return [c for g in P2.ALL_GROUPS if g not in drop and g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]


def hunger(d, X, t, drop=()):
    hc = hunger_cols(drop)
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hc)
    if len(htr) < P2.MIN_H_PAIRS or not len(hte):
        return None
    return P2.hunger_component(htr, hte, hc)


def _inner(args):
    tr, c, drop = args
    cols = G.cols_for(c, drop)
    ll, n = 0.0, 0
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(G.PriceLGB2(cols, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def tuned_forecast(d, X, B, t, drop=(), n_jobs=8):
    """E56-TUNED at origin t with the groups in `drop` removed from both parts (drop=() is E56-TUNED itself)."""
    from joblib import Parallel, delayed
    tr, te = F.frame(d, X, B, t, "AS")
    if not E.ok(tr, te):
        return None
    hc = hunger(d, X, t, drop)
    if hc is None:
        return None
    g = G.search_space()
    scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner)((tr, c, drop)) for c in g)
    best = min(range(len(g)), key=lambda i: (round(scores[i], 10), G.simplicity(g[i])))
    c = g[best]
    cols = G.cols_for(c, drop)
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = G.PriceLGB2(cols, c).fit(fit)
    pp = mdl.predict(te)
    return {"t": t, "p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "cfg": c, "model": mdl, "te": te,
            "cols": cols, "n_train_rows": int(len(fit))}


def group_attribution(res: dict) -> dict:
    """Mean |TreeSHAP| per group over the five test rows and tree split counts per group (price part)."""
    mdl = res["model"]
    out = {g: {"mean_abs_shap": 0.0, "splits": 0} for g in ["market"] + TRIGGERS}
    if getattr(mdl, "model", None) is None or mdl.const is not None:
        return out
    C = mdl.contributions(res["te"])
    imp = dict(zip(mdl.feat, mdl.model.booster_.feature_importance("split")))
    for col in mdl.feat:
        g = group_of(col)
        if g in out:
            out[g]["mean_abs_shap"] += float(C[col].abs().mean())
            out[g]["splits"] += int(imp.get(col, 0))
    return out
