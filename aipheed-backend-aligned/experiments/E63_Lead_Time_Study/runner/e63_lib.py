"""E63 library (PROTOCOL.md): the E56-TUNED procedure generalised from lead 2 to lead h in {1, 2, 3, 4}.

The E56 code path is imported READ-ONLY from the experiments folder of the main checkout (AIPHEED_EXP, default below):
e56_lib -> e55_lib -> e53_lib -> e46_i7 / e46_lib -> e44_components -> e44_classifiers -> e43_lib -> e41_lib.
In that chain the two-quarter horizon is a literal "2" in six places; each is re-implemented here with the lead h as
a parameter and nothing else changed:

  H1  F_hat_M1 feature            e41_lib.features             m1_point(d, t, 2, p)         -> m1_point(d, t, h, p)
  H2  rice-policy shares          e46_lib.policy_features      target_months(t, 2)          -> target_months(t, h)
  H3  base-effect projections     e44_components.proj          target_months(t, 2)          -> target_months(t, h)
  H4  price training pairs        e53_lib.frame                t' + 2 <= t - 1, q = t' + 2  -> t' + h <= t - 1, q = t' + h
  H5  hunger training pairs       e44_components.hunger_frame  tp + 2                       -> tp + h
  H6  inner-fold embargo          e46_i7.folds                 EMBARGO = 3                  -> EMBARGO = h + 1

At h = 2 every function below is identical to its E56 original; the predict step checks that the lead-2 forecasts
equal the sealed E57 forecasts within 1e-9 before anything is written.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E63 = Path(__file__).resolve().parents[1]
EXP = Path(os.environ.get("AIPHEED_EXP", r"C:\Users\admin\aipheed\aipheed-backend-aligned\experiments"))
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

F, E, I7, L, P2, M, np, pd = G.F, G.E, G.I7, G.L, G.P2, G.M, G.np, G.pd
K = E.K
LEADS = [1, 2, 3, 4]
FIRST_ORIGIN, LAST_FEATURE_ORIGIN = L.qi("2021-Q3"), L.qi("2026-Q3")      # e53_lib.load feature origins, unchanged
LAST_TARGET = L.qi("2026-Q3")                                              # latest quarter with an observed T43 label
E57_SEALED = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"


# ================================================================================================ H1-H3: inputs at lead h
def policy_features_h(events: pd.DataFrame, t: int, h: int) -> dict:
    """e46_lib.policy_features with the target quarter t+h."""
    O = L.origin(t)
    known = events[events["announcement_date"] < O]
    months = L.target_months(t, h)
    out = {k: 0.0 for k in M.POLICY}
    for e in known.itertuples():
        a, b = M._ym(str(e.effective_start.date())), M._ym(str(e.effective_end.date()))
        if e.feature == "tariff_yoy_regime":
            out["tariff_yoy_regime"] = max(out["tariff_yoy_regime"],
                                           float(np.mean([(m >= a) and (m - 12 < a) for m in months])))
        else:
            out[e.feature] = max(out[e.feature], float(np.mean([a <= m <= b for m in months])))
    return out


def features_h(d, x, origins, events, h: int) -> pd.DataFrame:
    """e46_lib.features (all E56 inputs) with the two lead-dependent inputs recomputed for target t+h."""
    X = M.features(d, x, origins, events)
    fh = {(t, p): L.m1_point(d.cut(t), t, h, p)["F_hat"] for t in origins for p in L.PROVS}
    X["F_hat_M1"] = [fh[(t, p)] for t, p in zip(X["t"], X["province_code"])]
    pf = pd.DataFrame([{"t": t, **policy_features_h(events, t, h)} for t in origins])
    return X.drop(columns=M.POLICY).merge(pf, on="t", how="left")


def proj_h(d_cut, t, p, mult, commodity, h: int):
    """e44_components.proj with the target quarter t+h."""
    m0 = L.m0_of(t)
    I = L._series(d_cut, p, commodity)
    if m0 not in I.index:
        return np.nan
    lnI = np.log(I)
    g, _, n = L.drift_sigma(lnI, m0)
    ms = L.target_months(t, h)
    if n < 6 or any((m - 12) not in I.index for m in ms):
        return np.nan
    return float(np.mean([100 * (math.exp(lnI[m0] + g * mult * (m - m0)) / I[m - 12] - 1) for m in ms]))


def bases_h(d, origins, h: int) -> pd.DataFrame:
    rows = []
    for t in origins:
        c = d.cut(t)
        for p in L.PROVS:
            r = {"t": t, "province_code": p}
            for m in P2.MULTS:
                r[f"base_{m}"] = proj_h(c, t, p, m, "food", h)
                r[f"hl_{m}"] = proj_h(c, t, p, m, "all_items", h)
            rows.append(r)
    return pd.DataFrame(rows)


def load_raw():
    return L.load(), K.load_extra(), M.load_events()


def inputs_h(raw, h: int):
    """e53_lib.load at lead h (same files, same feature origins 2021-Q3..2026-Q3)."""
    d, x, ev = raw
    allo = list(range(FIRST_ORIGIN, LAST_FEATURE_ORIGIN + 1))
    return d, features_h(d, x, allo, ev, h), bases_h(d, allo, h)


# ================================================================================================ H4-H6: frames at lead h
def frame_h(d, X, B, t, h: int, pov=None):
    """e53_lib.frame (+ e55_lib.frame poverty column) with training targets t'+h <= t-1."""
    c = d.cut(t)
    Fq = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = Fq.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in P2.MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    th = L.e40_spec()
    for m in P2.MULTS:
        XB[f"dfood_{m}"] = XB[f"base_{m}"] - XB["province_code"].map(th["food"])
        XB[f"dgap_{m}"] = XB[f"gbase_{m}"] - XB["province_code"].map(th["gap"])
    tr = XB[XB["t"] + h <= t - 1].assign(q=lambda f: f["t"] + h).merge(FG, on=["province_code", "q"])
    tr["PS"] = ((tr["F_true"] > tr["province_code"].map(th["food"]))
                | (tr["G_true"] > tr["province_code"].map(th["gap"]))).astype(int)
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    if pov is not None:
        tr, te = F.add_poverty(tr, pov), F.add_poverty(te, pov)
    return tr, te


def hunger_frame_h(X, hs, t, cols, h: int):
    """e44_components.hunger_frame with regional pairs (t', H(t'+h)), t'+h <= t-1, H posted before O(t)."""
    hc = sorted(set(c for g in P2.HUNGER_GROUPS.values() for c in g))
    reg = X.groupby("t")[hc + ["H_last"]].mean().reset_index().rename(columns={"H_last": "H_base"})
    reg["H_true"] = reg["t"].map(lambda tp: hs.get(tp + h, np.nan))
    htr = reg[(reg["t"] + h <= t - 1) & reg["H_true"].notna() & reg["H_base"].notna()].assign(q=lambda f: f["t"] + h)
    hte = reg[reg["t"] == t].copy()
    if len(hte):
        latest = hs[hs.index <= t]
        hte["H_base"] = float(latest.iloc[-1]) if len(latest) else np.nan
    return htr, hte


def hunger_h(d, X, t, h: int):
    """e55_lib.hunger at lead h: P(H(t+h) > 11.3) from approved rounds posted before O(t)."""
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    htr, hte = hunger_frame_h(X, P2.h_series(d, t, False), t, hcols, h)
    if len(htr) < P2.MIN_H_PAIRS or not len(hte):
        return None
    return P2.hunger_component(htr, hte, hcols)


def folds_h(qs, h: int):
    """e46_i7.folds ('forward') with embargo h+1: an inner fold at target q (inner origin q-h) is fitted only on
    targets <= q-h-1, whose outcomes were published before that inner origin."""
    qs = sorted(qs)
    out = []
    for q in qs:
        fit = [x for x in qs if x <= q - (h + 1)]
        if len(fit) >= I7.MIN_EARLIER:
            out.append((q, fit))
    return out[-I7.N_FORWARD:]


# ================================================================================================ E56-TUNED at lead h
def _inner_h(args):
    tr, c, h = args
    cols = G.cols_for(c)
    ll, n = 0.0, 0
    for q, fq in folds_h(tr["q"].unique(), h):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(G.PriceLGB2(cols, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def eligible(d, X, B, t, h: int) -> dict:
    """E57 eligibility (without the poverty column): >= 6 price-training quarters, a test base, >= 6 hunger pairs."""
    tr0, te0 = frame_h(d, X, B, t, h, None)
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    htr, _ = hunger_frame_h(X, P2.h_series(d, t, False), t, hcols, h)
    return {"price_q": int(tr0["q"].nunique()), "hunger_pairs": int(len(htr)),
            "ok": bool(E.ok(tr0, te0) and hunger_h(d, X, t, h) is not None)}


def tuned_forecast_h(d, X, B, t, h: int, space=None, n_jobs=8):
    """e56_lib.tuned_forecast at lead h (same 72 configurations, same selection and tie-break)."""
    from joblib import Parallel, delayed
    tr, te = frame_h(d, X, B, t, h, "AS")
    if not E.ok(tr, te):
        return None
    hc = hunger_h(d, X, t, h)
    if hc is None:
        return None
    g = space or G.search_space()
    scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner_h)((tr, c, h)) for c in g)
    best = min(range(len(g)), key=lambda i: (round(scores[i], 10), G.simplicity(g[i])))
    c = g[best]
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = G.PriceLGB2(G.cols_for(c), c).fit(fit)
    pp = mdl.predict(te)
    return {"t": t, "h": h, "p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "H_hat": hc["H_hat"], "cfg": c,
            "inner_logloss": scores[best], "te": te, "n_train_rows": int(len(fit)),
            "n_train_q": int(fit["q"].nunique()), "n_train_HIGH": int(fit["PS"].sum())}


# ================================================================================================ as-of baselines (E57)
def known_labels(d, t):
    """T43 labels known at O(t): quarters <= t-1 whose SWS rounds were all posted before O(t), CPI from d.cut(t)."""
    r = pd.read_csv(L.SWS_FILE)
    r["q"] = r["quarter"].map(L.qi)
    r["published"] = pd.to_datetime(r["published"])
    complete = {q for q, g in r.groupby("q") if (g["published"] < L.origin(t)).all()}
    Y = F.t43_labels(d.cut(t))
    return Y[Y["q"].isin(complete) & (Y["q"] <= t - 1) & Y["T43"].notna()]


# ================================================================================================ score-free label existence
def label_exists(d) -> set:
    """Quarters for which a T43 label CAN be formed (an SWS round exists and all five provinces have three published
    monthly food and all-items YoY values), up to 2026-Q3. Reads no label value."""
    r = pd.read_csv(L.SWS_FILE)
    sws_q = set(r["quarter"].map(L.qi))
    fq = L.quarter_F(d).groupby("q").size()
    hq = L.quarter_F(d, "all_items").groupby("q").size()
    cpi_q = {q for q in fq.index if fq[q] == 5 and hq.get(q, 0) == 5}
    return {q for q in sws_q & cpi_q if q <= LAST_TARGET}
