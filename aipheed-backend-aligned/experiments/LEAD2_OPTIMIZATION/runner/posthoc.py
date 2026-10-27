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


def phase_cases(fname="predictions.csv", best=None, out="lead2_cases.csv"):
    D = pd.read_csv(OUT / fname, dtype={"province_code": str})
    best = best or _res()["selection"]["adopted"]
    U.setup()
    S = X.add_fe(U.stack(2))
    S = S[S["lead"] == 2][["t", "province_code", "issue_date", "sws_newest_q", "sws_newest_published",
                            "psa_newest_month", "news_latest_published", "true_horizon"] +
                           [c for c in X.fe_cols(True) if c not in ("H1",)]]
    g = D[D["lead"] == 2].merge(S, on=["t", "province_code"], how="left")
    rows = []
    for _, r in g.sort_values(["q", "province_code"]).iterrows():
        def kind(p):
            yh = int(r[p] >= .5)
            return {(1, 1): "TP", (0, 1): "FN", (1, 0): "FP", (0, 0): "TN"}[(yh, int(r["y"]))]
        rows.append({"origin": L.qs(int(r["t"])), "issue_date": r["issue_date"], "target": L.qs(int(r["q"])),
                     "province": L.NAMES[r["province_code"]], "sws_newest_q": r["sws_newest_q"],
                     "sws_newest_published": r["sws_newest_published"], "true_horizon_q": r["true_horizon"],
                     "psa_newest_month": r["psa_newest_month"], "news_latest_published": r["news_latest_published"],
                     "y": int(r["y"]), "hunger_obs": int(r["hunger"]), "price_obs": int(r["price"]), "H_obs": r["H"],
                     "h_last": r["h_last"], "pi_H0": r["H1"], "pi_H1": r["pi_H1"], "pi_H2_sampleb": r["pi_H2"],
                     "P0_price": r["P0_price"], f"{best[:2]}_price": r[f"{best[:2]}_price"],
                     "P0H0_p": r["P0H0_p"], f"{best}_p": r[f"{best}_p"], "P0H0_type": kind("P0H0_p"),
                     f"{best}_type": kind(f"{best}_p"),
                     "threshold": 0.5,
                     **{c: r[c] for c in X.fe_cols(True) if c not in ("H1", "lead")}})
    pd.DataFrame(rows).to_csv(OUT / out, index=False, lineterminator="\n", float_format="%.4g")
    print(pd.DataFrame(rows)[list(dict.fromkeys([f"{best}_type", "P0H0_type"]))].value_counts())


def phase_ablation(best: str | None = None):
    best = best or _res()["selection"]["adopted"]
    arm, hcol = best[:2], {"H0": "H1", "H1": "pi_H1"}[best[2:]]
    U.setup()
    K = RL._K()
    S = X.add_fe(U.stack(K))
    D = pd.read_csv(OUT / "predictions_addendum1.csv", dtype={"province_code": str})
    D = D[D["lead"] <= 3]
    full = X.fe_cols(True) if arm in ("P1", "P2", "P3", "P6") else X.base_cols(True)
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
    FM.write_json(OUT / f"ablation_{best}.json", {"arm": best, "variants": out})


def _price_cols(arm, tr, te, keep):
    """The adopted arm's price model refitted on a column subset (same grid and selection)."""
    if arm == "P0":
        cfg, _ = U.select(tr, keep, True)
        return U.UniPrice(cfg, keep, True).fit(tr).predict(te)
    if arm in ("P4", "P6", "P7"):
        cfg = X.select_prior(tr, keep, X.reg_grid() if arm == "P7" else None)
        return X.PriorModel(cfg, keep).fit(tr, tr["y"].to_numpy(int)).predict(te)
    if arm == "P8":
        cfg = X.select_clf(tr, keep, X.reg_grid())
        return X.Model(cfg, keep).fit(tr, tr["y"].to_numpy(int)).predict(te)
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


def phase_placebo(arm: str = "P0", hcol: str = "H1", n: int = 20):
    """Shuffled-news control: the news columns permuted across issue dates (seed 2029), the arm refitted; permutation
    p = share of shuffles whose Lead-k Brier is <= the real one."""
    U.setup()
    K = RL._K()
    S0 = X.add_fe(U.stack(K))
    D = pd.read_csv(OUT / "predictions_addendum1.csv", dtype={"province_code": str})
    origins = RL._origins()
    rng = np.random.default_rng(2029)
    news = list(U.NEWS_COLS)

    def run(S):
        fr = [f for f in (X.forecast_origin(S, t, (arm,), True) for t in origins) if f is not None]
        A = pd.concat(fr).drop(columns=["H1", "h_last"]).merge(D[["t", "lead", "province_code", "y", hcol]],
                                                               on=["t", "lead", "province_code"])
        return {k: float(np.mean((g[hcol] * g[f"{arm}_price"] - g["y"]) ** 2)) for k, g in A.groupby("lead") if k <= 3}
    real = {k: float(np.mean((g[f"{arm}H0_p"] - g["y"]) ** 2)) for k, g in D.groupby("lead") if k <= 3}
    ts = sorted(S0["t"].unique())
    perms = []
    for i in range(n):
        mp = dict(zip(ts, rng.permutation(ts)))
        src = S0.set_index(["province_code", "t", "lead"])[news]
        S = S0.copy()
        S[news] = src.reindex(list(zip(S["province_code"], S["t"].map(mp), S["lead"]))).to_numpy()
        perms.append(run(S))
        print(i, {k: round(v, 4) for k, v in perms[-1].items()}, flush=True)
    out = {"arm": arm, "real_brier": real, "shuffles": perms,
           "perm_p": {k: float(np.mean([p[k] <= real[k] for p in perms])) for k in real},
           "shuffle_mean": {k: float(np.mean([p[k] for p in perms])) for k in real}}
    FM.write_json(OUT / f"news_placebo_{arm}.json", out)
    print(out["perm_p"], out["shuffle_mean"], real)


def phase_replay(arms=("P0", "P4"), fname="predictions_addendum2.csv"):
    """Historical replay: rebuild the forecast at an origin from a table that contains no later origin, and compare
    it with the scored predictions (same arm, same rows)."""
    U.setup()
    K = RL._K()
    d, x = E.data()
    D = pd.read_csv(OUT / fname, dtype={"province_code": str})
    out = []
    for q in ("2023-Q4", "2024-Q4", "2026-Q1"):
        t = L.qi(q)
        S = X.add_fe(U.stack(K, d, x, t), d)
        assert S["t"].max() == t
        f = X.forecast_origin(S, t, arms, True, d)
        m = f.rename(columns={"target_q": "q"}).merge(D[D["t"] == t], on=["t", "lead", "province_code"],
                                                      suffixes=("_replay", ""))
        diff = {a: float((m[f"{a}_price_replay"] - m[f"{a}_price"]).abs().max()) for a in arms}
        out.append({"origin": q, "rows_compared": int(len(m)), "max_abs_diff": diff})
        print(out[-1], flush=True)
    ok = all(v < 1e-5 for o in out for v in o["max_abs_diff"].values()) and all(o["rows_compared"] for o in out)
    FM.write_json(OUT / "historical_replay.json", {"identical": ok, "arms": list(arms), "origins": out})


if __name__ == "__main__":
    {"cases": phase_cases,
     "ablation": lambda: phase_ablation(sys.argv[2] if len(sys.argv) > 2 else None), "checks": phase_checks, "control": phase_control,
     "placebo": lambda: phase_placebo(sys.argv[2] if len(sys.argv) > 2 else "P0"),
     "replay": lambda: phase_replay(tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("P0", "P4"))}[sys.argv[1]]()
