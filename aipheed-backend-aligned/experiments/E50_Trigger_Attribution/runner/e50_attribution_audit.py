"""E50 audit of the E46 (I7) five-trigger attribution, on the fixed fitted models (no retraining for the attribution).

At every issue date served on the dashboard (past quarters' origins and the 2027-Q1 origin) the I7 model is refitted
exactly as in the served record (reproduction asserted) and, per province, the log-odds effect of each group is
computed three ways:
  A. SERVED: remove the group's ridge-residual contributions only (the base-effect CPI projection and the latest SWS
     level are the reference and are attributed to nobody) - the method the dashboard uses today;
  B. FULL REFERENCE: every input moved to its training mean - the market group also includes the base-effect food and
     gap projections (the model's price inputs), and "hunger level" (latest SWS round) is reported separately;
  C. REFIT-DROP: the I7 procedure refitted without the group's residual inputs (diagnostic of predictive dependence;
     it cannot remove the base projection, which is not a trigger input of the residual).
Synthetic perturbations (diagnostic only): each province's market inputs and climate inputs moved by +/-1 SD.

    backend/venv/Scripts/python.exe -B runner/e50_attribution_audit.py  -> runs/attribution_audit.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E50 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E50.parent / "E46_Rice_Policy" / "runner"))
import e46_i7 as I7  # noqa: E402

M, K, L, P2, np, pd = I7.M, I7.K, I7.L, I7.P2, I7.np, I7.pd
G = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
REC = Path(r"C:\Users\admin\aipheed\backend\data\e46\e46_record.json")
th = L.e40_spec()


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def joint(fx, i, F, Gp, H):
    ph = 1 - I7.norm.cdf((th["H"] - H) / max(fx["hunger_rmse"], 1e-6))
    return ph * P2.p_price_biv([F], [Gp], fx["food_rmse"], fx["gap_rmse"], fx["rho"], [fx["te"]["province_code"].iloc[i]])[0]


def grp(con, cols, i):
    if con is None:
        return 0.0
    c = [k for k in cols if k in con.columns]
    return float(con.iloc[i][c].sum()) if c else 0.0


def training_means(d, X, B, t, fx):
    """Training-set means of the selected food and gap base projections and of the hunger base (the references)."""
    c = d.cut(t)
    F = L.quarter_F(c)
    XB = X.merge(B, on=["t", "province_code"])
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(F, on=["province_code", "q"])
    mf, mg = fx["food_cfg"]["mult"], fx["gap_cfg"]["mult"]
    hcols = fx["hcols"]
    htr, _ = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    return (float(tr[f"base_{mf}"].mean()), float((tr[f"base_{mg}"] - tr[f"hl_{mg}"]).mean()), float(htr["H_base"].mean()))


def main():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    oper = L.qi(rec["originQuarter"])
    origins = sorted({L.qi(q) - 2 for v in rec["provinces"].values() for q in v["pastDrivers"]} | {oper})
    allo = list(range(L.qi("2021-Q3"), oper + 1))
    X = M.features(d, x, allo, ev)
    B = P2.bases(d, allo)
    out = []
    for t in origins:
        fx = I7.forecast(d, X, B, t, n_jobs=8)
        q = L.qs(t + 2)
        drop = {g: I7.forecast(d, X, B, t, groups=[h for h in P2.ALL_GROUPS if h != g], n_jobs=8) for g in G}
        mF, mG, mH = training_means(d, X, B, t, fx)
        tex = fx["te"]
        fc = fx["food_model"].contributions(tex) if fx["food_model"] is not None else None
        gc = fx["gap_model"].contributions(tex) if fx["gap_model"] is not None else None
        hc = fx["hunger_model"].contributions(fx["hte"]) if fx["hunger_model"] is not None else None
        sdF = {c: float(X[X["t"] <= t - 3][c].std()) for c in P2.PRICE_GROUPS["market"] + P2.PRICE_GROUPS["climate"]}
        for i, p in enumerate(L.PROVS):
            Fh, Gh, Hh = float(fx["F_hat"][i]), float(fx["G_hat"][i]), float(fx["H_hat"])
            base = joint(fx, i, Fh, Gh, Hh)
            served, full = {}, {}
            for g in G:
                dF, dG = grp(fc, P2.PRICE_GROUPS[g], i), grp(gc, P2.PRICE_GROUPS[g], i)
                dH = grp(hc, P2.HUNGER_GROUPS.get(g, []), 0)
                served[g] = logit(base) - logit(joint(fx, i, Fh - dF, Gh - dG, Hh - dH))
                if g == "market":                       # plus the base-effect price projections, moved to training mean
                    dF += float(fx["F_base"][i]) - mF
                    dG += float(fx["G_base"][i]) - mG
                full[g] = logit(base) - logit(joint(fx, i, Fh - dF, Gh - dG, Hh - dH))
            Hb = float(fx["hte"]["H_base"].iloc[0])
            hunger_level = logit(base) - logit(joint(fx, i, Fh, Gh, Hh - (Hb - mH)))
            refit = {g: logit(base) - logit(float(drop[g]["p"][i])) for g in G}
            pert = {}
            for grp_name in ("market", "climate"):
                cols = [c for c in P2.PRICE_GROUPS[grp_name] if c in tex.columns and np.isfinite(sdF.get(c, np.nan))]
                resp = []
                for sgn in (-1, 1):
                    te2 = tex.copy()
                    for c in cols:
                        te2.loc[i, c] = te2.loc[i, c] + sgn * sdF[c] if pd.notna(te2.loc[i, c]) else te2.loc[i, c]
                    F2 = float(fx["F_base"][i]) + (fx["food_model"].predict(te2)[i] if fx["food_model"] is not None else 0.0)
                    G2 = float(fx["G_base"][i]) + (fx["gap_model"].predict(te2)[i] if fx["gap_model"] is not None else 0.0)
                    resp.append(joint(fx, i, F2, G2, Hh))
                pert[grp_name] = {"p_minus_1sd": round(resp[0], 4), "p_plus_1sd": round(resp[1], 4)}
            rank = lambda e: max(e, key=lambda k: abs(e[k]))  # noqa: E731
            out.append({"target": q, "origin": str(L.origin(t).date()), "province": L.NAMES[p], "p": round(base, 4),
                        "food_cfg": fx["food_cfg"], "gap_cfg": fx["gap_cfg"],
                        "served_logodds": {g: round(v, 4) for g, v in served.items()},
                        "full_reference_logodds": {g: round(v, 4) for g, v in full.items()},
                        "hunger_level_logodds": round(hunger_level, 4),
                        "refit_drop_logodds": {g: round(v, 4) for g, v in refit.items()},
                        "top_served": rank(served), "top_full": rank(full), "top_refit_drop": rank(refit),
                        "base_projection": {"food_base": round(float(fx["F_base"][i]), 3), "food_base_train_mean": round(mF, 3),
                                            "gap_base": round(float(fx["G_base"][i]), 3), "gap_base_train_mean": round(mG, 3)},
                        "perturbation_1sd": pert})
    from collections import Counter
    summ = {k: dict(Counter(r[k] for r in out)) for k in ("top_served", "top_full", "top_refit_drop")}
    share = {g: round(float(np.mean([abs(r["full_reference_logodds"][g]) / max(sum(abs(v) for v in r["full_reference_logodds"].values()), 1e-12)
                                     for r in out])), 3) for g in G}
    shareS = {g: round(float(np.mean([abs(r["served_logodds"][g]) / max(sum(abs(v) for v in r["served_logodds"].values()), 1e-12)
                                      for r in out])), 3) for g in G}
    res = {"rows": len(out), "quarters": sorted({r["target"] for r in out}), "rank1_counts": summ,
           "mean_share_served": shareS, "mean_share_full_reference": share, "detail": out}
    (E50 / "runs").mkdir(exist_ok=True)
    (E50 / "runs" / "attribution_audit.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("rows", "rank1_counts", "mean_share_served", "mean_share_full_reference")}, indent=1))
    for r in out:
        if r["province"] == "Quezon":
            print(r["target"], "served", r["served_logodds"], "| full", r["full_reference_logodds"], "| refit", r["refit_drop_logodds"],
                  "| hunger lvl", r["hunger_level_logodds"], "| pert", r["perturbation_1sd"])


if __name__ == "__main__":
    main()
