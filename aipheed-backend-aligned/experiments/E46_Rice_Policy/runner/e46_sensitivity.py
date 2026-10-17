"""E46 sensitivity of the I8 procedure (O'(t) timing): drop each trigger group from the price residuals, drop each group
from the hunger ridge, and a random-walk hunger component. Diagnostics only (nothing is selected from them).
The full variant must reproduce I8's committed probabilities exactly.

    backend/venv/Scripts/python.exe -B runner/e46_sensitivity.py  -> runs/sensitivity_i8.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_i8 as I8  # noqa: E402
import e46_evaluate_i7 as V7  # noqa: E402

I7, M, K, L, P2, np, pd = I8.I7, I8.M, I8.K, I8.L, I8.P2, I8.np, I8.pd
E4 = V7.E4
RUN8 = M.E46 / "runs" / "i8_20261017T001227Z"
OPER = L.qi("2026-Q3")
GROUPS = ["market", "climate", "fish_kill", "employment", "ofw_remittance", "news"]


def forecast(d, X, B, t, price_groups=P2.ALL_GROUPS, hunger_groups=P2.ALL_GROUPS, hunger_rw=False):
    pcols = [c for g in price_groups for c in P2.PRICE_GROUPS[g]] + M.POLICY
    hcols = [] if hunger_rw else [c for g in hunger_groups if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
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
    fc = I7.component(tr, te, pcols, "F_true", "base_{}", False, "forward", False, 8)
    gc = I7.component(tr, te, pcols, "G_true", "gbase_{}", False, "forward", False, 8)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    hc = P2.hunger_component(htr, hte, hcols)
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    return hc["p"] * ps, hc["p"], ps


def main():
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    origins = list(range(L.qi("2021-Q3"), OPER + 1))
    X = M.features(d, x, origins, ev)
    B = P2.bases(d, origins)
    variants = {"full": {}, "hunger_random_walk": {"hunger_rw": True}}
    for g in GROUPS:
        variants[f"price_drop_{g}"] = {"price_groups": [h for h in P2.ALL_GROUPS if h != g]}
        if g in P2.HUNGER_GROUPS:
            variants[f"hunger_drop_{g}"] = {"hunger_groups": [h for h in P2.ALL_GROUPS if h != g]}
    rows = []
    for t in origins:
        for nm, kw in variants.items():
            r = forecast(d, X, B, t, **kw)
            if r is None:
                continue
            rows.append(pd.DataFrame({"t": t, "province_code": L.PROVS, "variant": nm, "p": r[0], "p_hunger": r[1],
                                      "p_price": r[2]}))
    V = pd.concat(rows, ignore_index=True)
    P8 = pd.read_csv(RUN8 / "predictions_i8.csv", dtype={"province_code": str})
    full = V[V["variant"] == "full"].merge(P8[["t", "province_code", "I8_p"]], on=["t", "province_code"])
    assert np.allclose(full["p"], full["I8_p"], atol=1e-12), "full variant does not reproduce I8"
    P1 = pd.read_csv(V7.RUN1 / "predictions.csv", dtype={"province_code": str})[["t", "province_code", "target_q", "y"]]
    req = pd.read_csv(V7.RUN1 / "predictions.csv", dtype={"province_code": str})
    s44 = req[req["y"].notna() & (req["target_q"] <= OPER)].dropna(
        subset=[f"{a}_p" for a in E4.ITER + list(E4.VARIANTS) + E4.COMPARATORS])[["t", "province_code"]]
    out = {}
    base = V[V["variant"] == "full"].set_index(["t", "province_code"])["p"]
    for nm in variants:
        v = V[V["variant"] == nm].merge(P1, on=["t", "province_code"])
        S = v.merge(s44, on=["t", "province_code"])
        S = S.assign(**{f"{nm}_p": S["p"], f"{nm}_yhat": (S["p"] >= 0.5).astype(int)})
        m = E4.block(S, nm)
        o = v[v["t"] == OPER].set_index("province_code")["p"]
        vv = v.set_index(["t", "province_code"])["p"]
        out[nm] = {"S44_accuracy": m["accuracy"], "S44_balanced": m["balanced_accuracy"], "S44_recall_HIGH": m["recall_HIGH"],
                   "S44_brier": m["brier"], "S44_auc": m.get("roc_auc"),
                   "mean_abs_shift_vs_full_all_origins": float((vv - base.loc[vv.index]).abs().mean()),
                   "p_2027Q1": {L.NAMES[p]: round(float(o[p]), 4) for p in L.PROVS},
                   "shift_2027Q1_vs_full": {L.NAMES[p]: round(float(o[p] - base.loc[(OPER, p)]), 4) for p in L.PROVS}}
    (M.E46 / "runs" / "sensitivity_i8.json").write_text(json.dumps(out, indent=1))
    for nm, r in out.items():
        print(f"{nm:28s} acc {r['S44_accuracy']:.3f} bal {r['S44_balanced']} recH {r['S44_recall_HIGH']} brier "
              f"{r['S44_brier']:.3f} auc {r['S44_auc']}  |shift| {r['mean_abs_shift_vs_full_all_origins']:.4f} "
              f"2027Q1 shift {list(r['shift_2027Q1_vs_full'].values())}")


if __name__ == "__main__":
    main()
