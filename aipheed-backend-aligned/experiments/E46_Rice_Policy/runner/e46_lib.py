"""E46 library: as-of rice-policy features and the I6 / I6b component models (PROTOCOL.md).

A policy event enters the forecast issued at origin O(t) only if it was ANNOUNCED before O(t); its effect on the
target quarter t+2 is described by the share of the target's three months that fall in the announced period.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
E46 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E46.parent / "E44_Five_Trigger_Optimization" / "runner"))
import e44_components as P2  # noqa: E402

C, K, L, np, pd = P2.C, P2.K, P2.L, P2.np, P2.pd
EVENTS = E46 / "data" / "rice_policy_events.csv"
POLICY = ["tariff_yoy_regime", "import_suspension_share", "price_ceiling_share", "food_emergency_share"]


def _ym(date: str) -> int:
    return int(date[:4]) * 12 + int(date[5:7]) - 1


def load_events() -> pd.DataFrame:
    e = pd.read_csv(EVENTS)
    for c in ("announcement_date", "effective_start", "effective_end"):
        e[c] = pd.to_datetime(e[c])
    assert (e["announcement_date"] >= "2021-01-01").all() and (e["effective_start"] >= e["announcement_date"]).all()
    return e


def policy_features(events: pd.DataFrame, t: int) -> dict:
    """National, so identical for all provinces; only events announced before O(t)."""
    O = L.origin(t)
    known = events[events["announcement_date"] < O]
    months = L.target_months(t, 2)
    out = {k: 0.0 for k in POLICY}
    for e in known.itertuples():
        a, b = _ym(str(e.effective_start.date())), _ym(str(e.effective_end.date()))
        if e.feature == "tariff_yoy_regime":
            # YoY of a target month compares a post-cut month with a pre-cut base for 12 months after the cut
            out["tariff_yoy_regime"] = max(out["tariff_yoy_regime"],
                                           float(np.mean([(m >= a) and (m - 12 < a) for m in months])))
        else:
            out[e.feature] = max(out[e.feature], float(np.mean([a <= m <= b for m in months])))
    return out


def features(d, x, origins, events=None) -> pd.DataFrame:
    events = load_events() if events is None else events
    X = P2.features(d, x, origins)
    pf = pd.DataFrame([{"t": t, **policy_features(events, t)} for t in origins])
    return X.merge(pf, on="t", how="left")


def forecast(d, X, B, t, price_groups=P2.ALL_GROUPS, hunger_groups=P2.ALL_GROUPS, policy=True, hunger_rw=False,
             n_jobs=8):
    """E44 I2 (e44_components.forecast) with separate price/hunger groups and the policy block in the price model."""
    from scipy.stats import norm
    pcols = [c for g in price_groups for c in P2.PRICE_GROUPS[g]] + (POLICY if policy else [])
    hcols = [] if hunger_rw else [c for g in hunger_groups if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    F = L.quarter_F(d.cut(t)).rename(columns={"q": "qF", "F": "F_true"})
    XB = X.merge(B, on=["t", "province_code"])
    tr = XB[XB["t"] + 2 <= t - 1].assign(qF=lambda f: f["t"] + 2).merge(F, on=["province_code", "qF"])
    tr = tr.rename(columns={"qF": "q"})
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    if (tr["q"].nunique() < P2.MIN_PRICE_Q or len(htr) < P2.MIN_H_PAIRS or not len(hte)
            or te[[f"base_{m}" for m in P2.MULTS]].isna().all().all()):
        return None
    pc = P2.price_component(tr, te, pcols, n_jobs)
    hc = P2.hunger_component(htr, hte, hcols)
    pp = P2.p_price(pc["F_hat"], pc["HL_hat"], pc["rmse"], te["province_code"])
    p_joint = hc["p"] * pp
    lab = K.available_labels(d, t)
    o = pc["oof"].merge(hc["oof"].groupby("q")["H_hat"].first().rename("H_hat").reset_index(), on="q")
    o = o.merge(tr[["province_code", "q", f"hl_{pc['cfg']['mult']}"]], on=["province_code", "q"])
    o = o.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"])
    thr, platt, p_cal = 0.5, None, p_joint
    if len(o) and o["y"].nunique() == 2:
        ph = 1 - norm.cdf((L.e40_spec()["H"] - o["H_hat"]) / max(hc["rmse"], 1e-6))
        po = ph * P2.p_price(o["F_hat"], o[f"hl_{pc['cfg']['mult']}"], pc["rmse"], o["province_code"])
        if o["y"].sum() >= 3:
            platt = C.platt_fit(po, o["y"])
            po = C.platt_apply(platt, po)
            p_cal = C.platt_apply(platt, p_joint)
        thr = max(C.THRESHOLDS, key=lambda th: (round(C.balanced(o["y"], po >= th), 10), th == 0.5, th))
    return {"t": t, "p": np.asarray(p_cal), "p_raw": p_joint, "p_hunger": hc["p"], "p_price": pp, "threshold": thr,
            "F_hat": pc["F_hat"], "H_hat": hc["H_hat"], "price_cfg": pc["cfg"], "price_rmse": pc["rmse"],
            "hunger_alpha": hc["alpha"], "hunger_rmse": hc["rmse"], "platt": platt is not None,
            "price_model": pc["model"], "hunger_model": hc["model"], "te": te, "hte": hte, "pcols": pcols,
            "hcols": hcols}
