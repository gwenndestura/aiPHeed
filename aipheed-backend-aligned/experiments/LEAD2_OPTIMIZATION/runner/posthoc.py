"""Post-hoc analyses (PROTOCOL_LEAD2.md section 5; cannot change the adopted arm).

    python posthoc.py cases      # every Lead-2 row of P0H0 and the adopted arm, with inputs and outcome type
    python posthoc.py ablation   # news and per-family ablation of the adopted price arm (refits), Leads 1-3
    python posthoc.py checks     # calibration bins, chronological blocks, survey-design periods
    python posthoc.py control    # positive control for the leakage audit (perturb data published BEFORE O(t))
"""
from __future__ import annotations

import dataclasses
import json
import sys

import l2_lib as X
import run_l2 as RL

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT


def _res():
    return json.loads((OUT / "results.json").read_text())


def _D():
    return pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})


def phase_cases():
    D, best = _D(), _res()["selection"]["adopted"]
    U.setup()
    S = X.add_fe(U.stack(2))
    S = S[S["lead"] == 2][["t", "province_code"] + X.fe_cols(True)]
    g = D[D["lead"] == 2].merge(S, on=["t", "province_code"], how="left")
    rows = []
    for _, r in g.sort_values(["q", "province_code"]).iterrows():
        def kind(p):
            yh = int(r[p] >= .5)
            return {(1, 1): "TP", (0, 1): "FN", (1, 0): "FP", (0, 0): "TN"}[(yh, int(r["y"]))]
        rows.append({"origin": L.qs(int(r["t"])), "target": L.qs(int(r["q"])), "province": L.NAMES[r["province_code"]],
                     "y": int(r["y"]), "hunger_obs": int(r["hunger"]), "price_obs": int(r["price"]), "H_obs": r["H"],
                     "h_last": r["h_last"], "pi_H0": r["H1"], "pi_H1": r["pi_H1"], "pi_H2_sampleb": r["pi_H2"],
                     "P0_price": r["P0_price"], f"{best[:2]}_price": r[f"{best[:2]}_price"],
                     "P0H0_p": r["P0H0_p"], f"{best}_p": r[f"{best}_p"], "P0H0_type": kind("P0H0_p"),
                     f"{best}_type": kind(f"{best}_p"),
                     **{c: r[c] for c in ("A1_food", "A1_gap", "A1_food_d", "A1_gap_d", "F_ex", "G_ex", "A3",
                                          "R_rice_yoy", "W_rice_yoy", "N1")}})
    pd.DataFrame(rows).to_csv(OUT / "lead2_cases.csv", index=False, lineterminator="\n", float_format="%.4g")
    print(pd.DataFrame(rows)[[f"{best}_type", "P0H0_type"]].value_counts())


def phase_ablation():
    res = _res()
    best = res["selection"]["adopted"]
    arm, hcol = best[:2], {"H0": "H1", "H1": "pi_H1"}[best[2:]]
    U.setup()
    K = RL._K()
    S = X.add_fe(U.stack(K))
    D = _D()
    D = D[D["lead"] <= 3]
    full = X.fe_cols(True) if arm != "P0" else X.base_cols(True)
    fams = sorted({X.FAMILY_OF[c] for c in full} - {"lead"})
    out = {}
    variants = {"no_news": list(U.NEWS_COLS)}
    for f in fams:
        variants[f"drop_{f}"] = [c for c in full if X.FAMILY_OF[c] == f]
    for name, drop in variants.items():
        keep = [c for c in full if c not in drop]
        fr = []
        for t in RL._origins():
            tr, te = U.train_rows(S, t), S[S["t"] == t]
            if not B.eligible(tr) or not len(te):
                continue
            p = _price_cols(arm, tr, te, keep)
            fr.append(te[["t", "lead", "province_code"]].assign(p_abl=p))
        A = pd.concat(fr).merge(D, on=["t", "lead", "province_code"])
        A["abl_p"] = A[hcol] * A["p_abl"]
        out[name] = {}
        for k, g in A.groupby("lead"):
            y = g["y"].astype(int).to_numpy()
            bd = FM.boot_diff(g, (g[f"{best}_p"] - y) ** 2, (g["abl_p"] - y) ** 2)
            out[name][int(k)] = {"dropped": drop, "acc_full": float(((g[f"{best}_p"] >= .5) == y).mean()),
                                 "acc_ablated": float(((g["abl_p"] >= .5) == y).mean()),
                                 "brier_full_minus_ablated": bd["diff"], "p_two": bd["p_two"]}
        print(name, {k: (round(v["acc_ablated"], 3), round(v["brier_full_minus_ablated"], 4), round(v["p_two"], 3))
                     for k, v in out[name].items()}, flush=True)
    hp = FM.holm({(n, k): out[n][k]["p_two"] for n in out for k in out[n]})
    for (n, k), p in hp.items():
        out[n][k]["holm_p"] = p
    FM.write_json(OUT / "ablation.json", {"arm": best, "variants": out})


def _price_cols(arm, tr, te, keep):
    """The adopted arm's price model refitted on a column subset (same grid and selection)."""
    if arm == "P0":
        cfg, _ = U.select(tr, keep, True)
        return U.UniPrice(cfg, keep, True).fit(tr).predict(te)
    if arm in ("P1", "P2"):
        cfg = X.select_clf(tr, keep, X.uni_grid() if arm == "P1" else X.wide_grid())
        return X.Model(cfg, keep).fit(tr, tr["y"].to_numpy(int)).predict(te)
    yf, yg = X._excess(tr)
    cf, sf = X.select_reg(tr, keep, 0)
    cg, sg = X.select_reg(tr, keep, 1)
    pf = X.norm.cdf(X.Model(cf, keep, reg=True).fit(tr, yf).predict(te) / sf)
    pg = X.norm.cdf(X.Model(cg, keep, reg=True).fit(tr, yg).predict(te) / sg)
    return 1 - (1 - pf) * (1 - pg)


def phase_checks():
    res, D = _res(), _D()
    best = res["selection"]["adopted"]
    out = {}
    for a in dict.fromkeys(["P0H0", best]):
        out[a] = {}
        for k in (1, 2, 3):
            g = D[D["lead"] == k]
            y, p = g["y"].astype(int).to_numpy(), g[f"{a}_p"].to_numpy(float)
            bins = np.clip((p * 5).astype(int), 0, 4)
            cal = [{"bin": f"{b / 5:.1f}-{(b + 1) / 5:.1f}", "n": int((bins == b).sum()),
                    "mean_p": float(p[bins == b].mean()) if (bins == b).any() else None,
                    "obs_rate": float(y[bins == b].mean()) if (bins == b).any() else None} for b in range(5)]
            blocks = {}
            for name, m in {"2023": g["q"] < L.qi("2024-Q1"), "2024": (g["q"] >= L.qi("2024-Q1")) & (g["q"] < L.qi("2025-Q1")),
                            "2025": (g["q"] >= L.qi("2025-Q1")) & (g["q"] < L.qi("2026-Q1")), "2026": g["q"] >= L.qi("2026-Q1"),
                            "dev_le_2024Q4": g["q"] <= U.DEV_LAST, "confirm_2025Q2_2026Q3": g["q"].isin(U.CONFIRM),
                            "household_heads_base_lt_2025Q2": g["q"] < L.qi("2025-Q2"),
                            "adult_base_ge_2025Q2": g["q"] >= L.qi("2025-Q2")}.items():
                h = g[m]
                if len(h):
                    yy = h["y"].astype(int).to_numpy()
                    yh = (h[f"{a}_p"] >= .5).astype(int).to_numpy()
                    blocks[name] = {"rows": int(len(h)), "quarters": int(h["q"].nunique()), "high": int(yy.sum()),
                                    "acc": float((yh == yy).mean()), "always_low": float((yy == 0).mean()),
                                    "tp": int(((yh == 1) & (yy == 1)).sum()), "fn": int(((yh == 0) & (yy == 1)).sum()),
                                    "fp": int(((yh == 1) & (yy == 0)).sum())}
            out[a][k] = {"calibration": cal, "blocks": blocks,
                         "acc_ci90_cluster": C.acc_ci(g.assign(CH1_p=g[f"{a}_p"]), "CH1_p")}
            print(a, k, {n: (b["acc"], b["always_low"], b["high"], b["tp"]) for n, b in blocks.items()})
    FM.write_json(OUT / "posthoc_checks.json", out)


def phase_control():
    """Positive control: changing CPI or SWS values published BEFORE O(t) must change the forecast."""
    U.setup()
    K = 4
    d, x = E.data()
    out = []
    for q in ("2023-Q4", "2025-Q3"):
        t = L.qi(q)
        m0 = L.m0_of(t)
        S0 = X.add_fe(U.stack(K, d, x, t))
        f0 = X.forecast_origin(S0, t, ("P1",), True, d)
        ix = d.idx.copy()
        ix.loc[ix["ym"] == m0, "index"] *= 1.05
        yo = d.yoy.copy()
        yo.loc[yo["ym"] == m0, "yoy"] += 5
        dp = dataclasses.replace(d, idx=ix, yoy=yo)
        E._CACHE.pop(("X",), None)
        S1 = X.add_fe(U.stack(K, dp, x, t), dp)
        f1 = X.forecast_origin(S1, t, ("P1",), True, dp)
        out.append({"origin": q, "max_abs_change_P1": float((f0["P1_price"] - f1["P1_price"]).abs().max())})
        print(out[-1])
    FM.write_json(OUT / "leakage_positive_control.json", {"changed": all(o["max_abs_change_P1"] > 0 for o in out),
                                                           "origins": out})


if __name__ == "__main__":
    {"cases": phase_cases, "ablation": phase_ablation, "checks": phase_checks, "control": phase_control}[sys.argv[1]]()
