"""E46 iteration I10 (ADDENDUM_I10.md): I8 with trigger groups admitted to the residual models by inner validation.

Per price component (F and G) and per origin: start from market + policy inputs; repeatedly try adding each remaining
group (climate, fish_kill, employment, ofw_remittance, news) and keep the one that lowers the embargoed forward-chaining
RMSE of the best of the 15 (drift x ridge) configurations; stop when no group lowers it. "No residual" stays in the
grid, so a component can still end as the pure base-effect projection. Everything else is I8.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_i8 as I8  # noqa: E402  (O'(t) timing)

I7, M, K, L, P2, np, pd = I8.I7, I8.M, I8.K, I8.L, I8.P2, I8.np, I8.pd
START = ["market"]
OPTIONAL = ["climate", "fish_kill", "employment", "ofw_remittance", "news"]


def cols_of(groups):
    return [c for g in groups for c in P2.PRICE_GROUPS[g]] + M.POLICY


def component_groups(tr, te, ycol, bfmt, n_jobs):
    groups = list(START)
    best = I7.component(tr, te, cols_of(groups), ycol, bfmt, False, "forward", False, n_jobs)
    path = [{"groups": list(groups), "rmse": best["rmse"], "cfg": best["cfg"]}]
    while True:
        trials = {g: I7.component(tr, te, cols_of(groups + [g]), ycol, bfmt, False, "forward", False, n_jobs)
                  for g in OPTIONAL if g not in groups}
        if not trials:
            break
        g, c = min(trials.items(), key=lambda kv: (round(kv[1]["rmse"], 10), OPTIONAL.index(kv[0])))
        if round(c["rmse"], 10) >= round(best["rmse"], 10):
            break
        groups.append(g)
        best = c
        path.append({"groups": list(groups), "rmse": c["rmse"], "cfg": c["cfg"]})
    best["groups"], best["path"] = groups, path
    best["cols"] = cols_of(groups) if best["cfg"]["alpha"] is not None else []
    return best


def forecast(d, X, B, t, n_jobs=8):
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    c = d.cut(t)
    F = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = F.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in P2.MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(FG, on=["province_code", "q"])
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    if (tr["q"].nunique() < P2.MIN_PRICE_Q or len(htr) < P2.MIN_H_PAIRS or not len(hte)
            or te[[f"base_{m}" for m in P2.MULTS]].isna().all().all()):
        return None
    fc = component_groups(tr, te, "F_true", "base_{}", n_jobs)
    gc = component_groups(tr, te, "G_true", "gbase_{}", n_jobs)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    hc = P2.hunger_component(htr, hte, hcols)
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    p = hc["p"] * ps
    return {"t": t, "p": np.asarray(p), "threshold": I7.DECISION, "p_hunger": hc["p"], "p_price": ps,
            "F_hat": fc["hat"], "G_hat": gc["hat"], "rho": rho, "H_hat": hc["H_hat"], "food_cfg": fc["cfg"],
            "gap_cfg": gc["cfg"], "food_rmse": fc["rmse"], "gap_rmse": gc["rmse"], "food_groups": fc["groups"],
            "gap_groups": gc["groups"], "food_path": fc["path"], "gap_path": gc["path"], "hunger_alpha": hc["alpha"],
            "hunger_rmse": hc["rmse"], "food_model": fc["model"], "gap_model": gc["model"],
            "hunger_model": hc["model"], "te": te, "hte": hte, "food_cols": fc["cols"], "gap_cols": gc["cols"],
            "pcols": cols_of(START + OPTIONAL), "hcols": hcols, "n_price_train_q": int(tr["q"].nunique())}
