"""E70 library (PROTOCOL.md section 4): the reference E56-TUNED arm (R0) and the pre-registered E70 arms, all built on
the E63 lead-h generalisation of the E56 code path.

The model library is read-only from AIPHEED_EXP, which must point at the experiments folder of a clean
`git archive 089bdf2` export (PROTOCOL header). There is deliberately no default: the main checkout has uncommitted
edits and must not be used.

Every arm keeps the I7 regional hunger component and P = P_hunger x P_price; only the price component differs:
  R0  E56-TUNED (configuration chosen per origin by inner forward log-loss)
  A1  STABLE: configuration chosen by the mean inner log-loss over all eligible origins <= t of the same lead
  A2  SHRINK: R0's configuration with a training-only logit shrinkage toward the training PS rate
  S0  STRUCT: the base-effect CPI projection probability alone (no trees)
  ABL-g, ONLY-g: Lead-2 ablations and single-group models
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if not os.environ.get("AIPHEED_EXP"):
    raise SystemExit("set AIPHEED_EXP to the clean library export (PROTOCOL header); no default is allowed")
EXP = Path(os.environ["AIPHEED_EXP"])
E70 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "E63_Lead_Time_Study" / "runner"))
import e63_lib as H  # noqa: E402

G, F, E, I7, L, P2, M, np, pd = H.G, H.F, H.E, H.I7, H.L, H.P2, H.M, H.np, H.pd
MAIN_ARMS = ["R0", "A1", "A2", "S0"]
ABL_GROUPS = ["climate", "fish_kill", "employment", "ofw_remittance", "news", "policy", "poverty"]
ONLY_GROUPS = ["market", "climate", "fish_kill", "employment", "ofw_remittance", "news"]
ONLY_CFG = dict(num_leaves=2, max_depth=1, n_estimators=40, learning_rate=0.05, min_child_samples=10, reg_lambda=10.0)
B_MIN, B_MAX, MIN_OOF = 0.25, 1.0, 10


def _sig(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, float)))


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def _ll(y, p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _fit_rows(tr, m):
    return tr.dropna(subset=[f"base_{m}", f"gbase_{m}", "F_true", "G_true"])


# ================================================================================================ search scores
def _inner_drop(args):
    """e63_lib._inner_h with feature groups removed (drop = () reproduces it exactly)."""
    tr, c, h, drop = args
    cols = G.cols_for(c, drop)
    ll, n = 0.0, 0
    for q, fq in H.folds_h(tr["q"].unique(), h):
        fit = _fit_rows(tr[tr["q"].isin(fq)], c["m"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = G.PriceLGB2(cols, c).fit(fit).predict(hold)
        ll += _ll(hold["PS"], p)
        n += len(hold)
    return ll / n if n else float("inf")


def search(tr, h, space, drop=(), n_jobs=8):
    from joblib import Parallel, delayed
    if not drop:
        return Parallel(n_jobs=n_jobs, backend="loky")(delayed(H._inner_h)((tr, c, h)) for c in space)
    return Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner_drop)((tr, c, h, drop)) for c in space)


def pick(space, scores):
    return min(range(len(space)), key=lambda i: (round(scores[i], 10), G.simplicity(space[i])))


def space_for(drop):
    """ABL-poverty = the E56 space restricted to configurations without the poverty column."""
    sp = G.search_space()
    return [c for c in sp if c["pov"] is None] if "poverty" in drop else sp


# ================================================================================================ A2 shrinkage
def logistic_slope(z, y, iters=100):
    """Unpenalised logistic regression y ~ a + b z by Newton-Raphson; returns b (nan if it does not converge)."""
    z, y = np.asarray(z, float), np.asarray(y, float)
    X = np.column_stack([np.ones_like(z), z])
    w = np.zeros(2)
    for _ in range(iters):
        p = _sig(X @ w)
        g = X.T @ (y - p)
        Hm = (X * (p * (1 - p))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(Hm, g)
        w = w + step
        if np.max(np.abs(step)) < 1e-10:
            return float(w[1])
    return float("nan")


def shrink_factor(tr, c, h, drop=()):
    """b from the training-fold OOF predictions of configuration c (PROTOCOL section 4, A2)."""
    cols = G.cols_for(c, drop)
    zs, ys = [], []
    for q, fq in H.folds_h(tr["q"].unique(), h):
        fit = _fit_rows(tr[tr["q"].isin(fq)], c["m"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        zs.append(_logit(G.PriceLGB2(cols, c).fit(fit).predict(hold)))
        ys.append(hold["PS"].to_numpy(float))
    if not zs:
        return 1.0, 0
    z, y = np.concatenate(zs), np.concatenate(ys)
    if len(y) < MIN_OOF or len(set(y)) < 2:
        return 1.0, int(len(y))
    b = logistic_slope(z, y)
    if not np.isfinite(b):
        return 1.0, int(len(y))
    return float(min(max(b, B_MIN), B_MAX)), int(len(y))


# ================================================================================================ S0 structural
def struct_forecast(tr, te, h):
    best = None
    for m in P2.MULTS:
        ll, n = 0.0, 0
        for q, fq in H.folds_h(tr["q"].unique(), h):
            fit = _fit_rows(tr[tr["q"].isin(fq)], m)
            hold = tr[tr["q"] == q].dropna(subset=[f"base_{m}", f"gbase_{m}"])
            if not len(hold) or len(fit) < 3:
                continue
            p = _sig(F.struct_logit(hold, m, F.struct_scale(fit, m)))
            ll += _ll(hold["PS"], p)
            n += len(hold)
        s = ll / n if n else float("inf")
        if best is None or round(s, 10) < round(best[1], 10):
            best = (m, s)
    m = best[0]
    fit = _fit_rows(tr, m)
    return _sig(F.struct_logit(te, m, F.struct_scale(fit, m))), m


# ================================================================================================ ONLY-g
def only_group(tr, te, g):
    import lightgbm as lgb
    cols = list(P2.PRICE_GROUPS[g])
    y = tr["PS"].to_numpy(int)
    if len(set(y)) < 2:
        return np.full(len(te), float(y.mean()))
    kw = dict(F.LGB_BASE, **ONLY_CFG)
    mdl = lgb.LGBMClassifier(objective="binary", **kw)
    mdl.fit(tr[cols].astype(float), y)
    return mdl.predict_proba(te[cols].astype(float))[:, 1]


# ================================================================================================ one origin
def origin_frames(d, X, B, t, h):
    tr, te = H.frame_h(d, X, B, t, h, "AS")
    if not E.ok(tr, te):
        return None
    hc = H.hunger_h(d, X, t, h)
    if hc is None:
        return None
    return tr, te, hc


def main_arms(d, X, B, t, h, space, history, n_jobs=8):
    """R0, A1, A2, S0 at origin t, lead h. history: list of earlier same-lead score vectors (appended here)."""
    fr = origin_frames(d, X, B, t, h)
    if fr is None:
        return None
    tr, te, hc = fr
    scores = search(tr, h, space, (), n_jobs)
    history.append(np.asarray(scores, float))
    out = {"t": t, "h": h, "p_hunger": float(hc["p"]), "H_hat": float(hc["H_hat"]),
           "n_train_rows": None, "n_train_q": int(tr["q"].nunique())}
    # R0: exactly e63_lib.tuned_forecast_h
    i0 = pick(space, scores)
    c0 = space[i0]
    fit0 = _fit_rows(tr, c0["m"])
    m0 = G.PriceLGB2(G.cols_for(c0), c0).fit(fit0)
    pp0 = m0.predict(te)
    out["R0"] = {"p_price": pp0, "cfg": int(c0["id"]), "inner": float(scores[i0])}
    out["n_train_rows"] = int(len(fit0))
    # A1: cumulative mean inner log-loss over eligible same-lead origins <= t
    cum = np.mean(np.vstack(history), axis=0)
    i1 = pick(space, list(cum))
    c1 = space[i1]
    pp1 = G.PriceLGB2(G.cols_for(c1), c1).fit(_fit_rows(tr, c1["m"])).predict(te)
    out["A1"] = {"p_price": pp1, "cfg": int(c1["id"]), "inner": float(scores[i1])}
    # A2: shrink R0's price log-odds toward the training PS rate
    b, n_oof = shrink_factor(tr, c0, h)
    z0 = float(_logit(min(max(float(fit0["PS"].mean()), 0.02), 0.98)))
    pp2 = _sig(z0 + b * (_logit(pp0) - z0))
    out["A2"] = {"p_price": pp2, "cfg": int(c0["id"]), "b": b, "n_oof": n_oof}
    # S0: structural projection only
    pps, ms = struct_forecast(tr, te, h)
    out["S0"] = {"p_price": pps, "cfg": f"m={ms}"}
    for a in MAIN_ARMS:
        out[a]["p"] = hc["p"] * np.asarray(out[a]["p_price"], float)
    return out


def ablation_arms(d, X, B, t, h=2, n_jobs=8):
    fr = origin_frames(d, X, B, t, h)
    if fr is None:
        return None
    tr, te, hc = fr
    out = {}
    for g in ABL_GROUPS:
        drop = (g,)
        sp = space_for(drop)
        dcols = () if g == "poverty" else drop
        sc = search(tr, h, sp, dcols, n_jobs)
        i = pick(sp, sc)
        c = sp[i]
        pp = G.PriceLGB2(G.cols_for(c, dcols), c).fit(_fit_rows(tr, c["m"])).predict(te)
        out[f"ABL_{g}"] = {"p": hc["p"] * pp, "cfg": int(c["id"])}
    for g in ONLY_GROUPS:
        pp = only_group(tr, te, g)
        out[f"ONLY_{g}"] = {"p": hc["p"] * pp, "cfg": "fixed"}
    return out


def eligible_origins(h: int) -> list[int]:
    import json
    el = json.loads((H.E63 / "out" / "eligibility.json").read_text())
    return [L.qi(q) for q in el[f"lead{h}"]["origins"]]


PROSPECTIVE = {1: [L.qi("2026-Q3")], 2: [L.qi("2026-Q2"), L.qi("2026-Q3")]}
