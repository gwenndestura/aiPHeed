"""PROTOCOL sections 3-5: candidates C0-C5 (one unified LightGBM, all 12 families) x pi_H on the S-AB schedule, the
frozen DEV selection, cause tests CT1-CT6, before/after metrics, per-class and per-quarter results.

    python candidates.py        # ../out/candidates.csv, ../out/candidates.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
NEW_C1 = ["N1_reg"]
NEW_C2 = ["PC_now", "PC_hist4", "dF_ex", "dG_ex"]
CANDS = {"C0": T.U2, "C1": T.U2 + NEW_C1, "C2": T.U2 + NEW_C2, "C3": T.U2 + NEW_C1 + NEW_C2, "C4": T.U2, "C5": T.U2}


def add_features(S: pd.DataFrame) -> pd.DataFrame:
    S = S.copy()
    a = pd.read_csv(T.EXP / "FINAL_SYSTEM_SELECTION" / "annotation" / "model_inputs" / "fssi_articles.csv")
    a["q"] = a["quarter"].str[:4].astype(int) * 4 + a["quarter"].str[-1].astype(int) - 1
    a["pub"] = pd.to_datetime(a["published_ph"].str[:19])
    reg = {}
    for t in S["t"].unique():
        g = a[(a["q"] == t) & (a["pub"] < pd.Timestamp(F.origin(int(t))))]
        reg[int(t)] = float(g["intensity"].mean()) if len(g) >= 5 else np.nan
    S["N1_reg"] = S["t"].map(reg)
    S["PC_now"] = np.where(S["F_ex"].isna() | S["G_ex"].isna(), np.nan, ((S["F_ex"] > 0) | (S["G_ex"] > 0)).astype(float))
    kp = T.known_price()
    hist = {}
    for (t, p), g in kp.groupby(["t", "province_code"]):
        g = g.sort_values("q")
        hist[(int(t), p)] = float(g["y_price"].tail(4).mean()) if len(g) >= 4 else np.nan
    S["PC_hist4"] = [hist.get((int(t), p), np.nan) for t, p in zip(S["t"], S["province_code"])]
    o = S.drop_duplicates(["t", "province_code"]).set_index(["t", "province_code"])
    S["dF_ex"] = [o["F_ex"].get((t, p), np.nan) - o["F_ex"].get((t - 1, p), np.nan) for t, p in zip(S["t"], S["province_code"])]
    S["dG_ex"] = [o["G_ex"].get((t, p), np.nan) - o["G_ex"].get((t - 1, p), np.nan) for t, p in zip(S["t"], S["province_code"])]
    return S


def run_c4(S, origins):
    grid = [dict(c, cw="balanced") for c in T.GRID[::2]]
    for i, c in enumerate(grid):
        c["id"] = i
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg, _ = T.select(tr, T.U2, True, grid)
        out.append(te[KEY].assign(pi_P=T.Uni(cfg, T.U2).fit(tr).predict(te), cfg=f"b{cfg['id']}"))
    return pd.concat(out, ignore_index=True)


def run_c5(S, origins):
    from sklearn.linear_model import LogisticRegression
    out = []
    for t in origins:
        tr = T.train_rows(S, int(t))
        te = S[S["t"] == t]
        if not T.eligible(tr) or not len(te):
            continue
        cfg, _ = T.select(tr, T.U2)
        p = T.Uni(cfg, T.U2).fit(tr).predict(te)
        ys, ps = [], []
        for o in sorted(tr["t"].unique())[-4:]:
            f, h = tr[tr["q"] <= o - 1], tr[tr["t"] == o]
            if f["q"].nunique() < 3 or f["y"].nunique() < 2 or not len(h):
                continue
            c, _ = T.select(f, T.U2)
            ps.append(T.Uni(c, T.U2).fit(f).predict(h))
            ys.append(h["y"].to_numpy(int))
        tag = "nocal"
        if ys and len(set(np.concatenate(ys).tolist())) == 2:
            lg = lambda v: np.log(np.clip(v, 1e-4, 1 - 1e-4) / (1 - np.clip(v, 1e-4, 1 - 1e-4)))  # noqa: E731
            lr = LogisticRegression(C=1e6).fit(lg(np.concatenate(ps)).reshape(-1, 1), np.concatenate(ys))
            p = lr.predict_proba(lg(p).reshape(-1, 1))[:, 1]
            tag = f"platt{lr.coef_[0][0]:.2f}"
        out.append(te[KEY].assign(pi_P=p, cfg=tag))
    return pd.concat(out, ignore_index=True)


def per_class(y, p):
    m = M.cls(y, p)
    f1h = 2 * m["precision"] * m["recall"] / (m["precision"] + m["recall"]) if m["tp"] else 0.0
    pl = m["tn"] / (m["tn"] + m["fn"]) if m["tn"] + m["fn"] else float("nan")
    rl = m["specificity"]
    f1l = 2 * pl * rl / (pl + rl) if pl + rl else 0.0
    return {"HIGH": {"precision": m["precision"], "recall": m["recall"], "f1": f1h, "support": m["high"]},
            "LOW": {"precision": pl, "recall": rl, "f1": f1l, "support": m["n"] - m["high"]}}


def main():
    T.check_protocol()
    S = add_features(T.stack())
    S.to_csv(T.OUT / "stack_features.csv", index=False, lineterminator="\n", float_format="%.8g")
    E = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "predictions_ii.csv", dtype={"province_code": str})
    E = E[KEY + ["q", "y", "price", "hunger", "H", "pi_H_A", "pi_H_B", "pi_H_AB", "PERS_AB", "PERSIST_A", "CLIM_p",
                 "ALWAYS-LOW_p", "P0_price", "P0H4U_p", "P0H4_p3", "Z0_p", "warn_days_B"]]
    origins = sorted(E["t"].unique())
    preds = {}
    for c, cols in CANDS.items():
        if c == "C4":
            P = run_c4(S, origins)
        elif c == "C5":
            P = run_c5(S, origins)
        else:
            P = T.run(cols, origins, S)
        preds[c] = P
        E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": f"{c}_price", "cfg": f"{c}_cfg"}), on=KEY, how="left")
        assert E[f"{c}_price"].notna().all(), c
        E[f"{c}_p"] = E["pi_H_AB"] * E[f"{c}_price"]
        print(c, "done", flush=True)
    assert float((E["C0_price"] - E["P0_price"]).abs().max()) < 1e-6, "C0 must reproduce the served P0"
    res = {"protocol_sha256": T.sha256(T.LT / "PROTOCOL_LEAD2_FIVE_TRIGGER.md"),
           "C0_reproduces_served_max_abs": float((E["C0_price"] - E["P0_price"]).abs().max()),
           "feature_coverage": {c: float(S.loc[S["t"].isin(origins), c].notna().mean()) for c in NEW_C1 + NEW_C2 + ["N1"]},
           "cands": {}}
    for c in CANDS:
        dec = {}
        for k, g in E.groupby("lead"):
            d = F.evaluate(g, f"{c}_p", "PERS_AB")
            dv, cf = g["q"] <= F.DEV_LAST, g["q"] > F.DEV_LAST
            d["dev"], d["conf"] = M.cls(g.loc[dv, "y"], g.loc[dv, f"{c}_p"]), M.cls(g.loc[cf, "y"], g.loc[cf, f"{c}_p"])
            d["per_class"] = per_class(g["y"], g[f"{c}_p"])
            d["price_term"] = M.cls(g["price"], g[f"{c}_price"])
            d["vs_C0"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["C0_p"] - g["y"]) ** 2)
            d["calibration"] = M.calibration(g["y"], g[f"{c}_p"])
            d["n_eff"] = M.n_eff(g["q"], g["y"])
            d["by_quarter"] = {F.qs(int(q)): {"n": int(len(h)), "high": int(h["y"].sum()),
                                              "correct": int(((h[f"{c}_p"] >= .5).astype(int) == h["y"]).sum())}
                               for q, h in g.groupby("q")}
            dec[int(k)] = d
        res["cands"][c] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec),
                           "dev_L1": dec[1]["dev"]["brier"], "dev_L2": dec[2]["dev"]["brier"]}
    # ---------------------------------------------------------------- selection (frozen rule)
    c0 = res["cands"]["C0"]
    ok = [c for c in CANDS if res["cands"][c]["dev_L1"] <= c0["dev_L1"] + 0.005]
    best = min(ok, key=lambda c: (round(res["cands"][c]["dev_L2"], 9), list(CANDS).index(c)))
    final = best if c0["dev_L2"] - res["cands"][best]["dev_L2"] >= 0.005 else "C0"
    res["selection"] = {"eligible": ok, "best_dev_L2": best, "FINAL": final,
                        "dev_L2": {c: res["cands"][c]["dev_L2"] for c in CANDS}, "dev_L1": {c: res["cands"][c]["dev_L1"] for c in CANDS}}
    # ---------------------------------------------------------------- cause tests
    g = E[E["lead"] == 2]
    fn = g[(g["y"] == 1) & (g["C0_p"] < .5)]
    cls = np.where((fn["pi_H_AB"] < .5) & (fn["C0_price"] < .5), "both",
                   np.where(fn["pi_H_AB"] < .5, "hunger", np.where(fn["C0_price"] < .5, "price", "product")))
    res["CT1"] = {"lead2_missed_HIGH": int(len(fn)), "by_cause": pd.Series(cls).value_counts().to_dict(),
                  "cases": [{"province": T.F.qs(0) if False else p, "target": F.qs(int(q)), "pi_H": float(h), "pi_P": float(pp),
                             "price_margin_known": None} for p, q, h, pp in zip(fn["province_code"], fn["q"], fn["pi_H_AB"], fn["C0_price"])],
                  "confirmed": int(((fn["pi_H_AB"] >= .5) & (fn["C0_price"] < .5)).sum()) >= 4}
    d2 = {c: c0["dev_L2"] - res["cands"][c]["dev_L2"] for c in CANDS}
    res["CT2"] = {"dev_L2_gain_C1": d2["C1"], "confirmed": d2["C1"] >= .005}
    res["CT3"] = {"dev_L2_gain_C2": d2["C2"], "confirmed": d2["C2"] >= .005}
    r0, r4 = c0["leads"][2]["metrics"]["recall"], res["cands"]["C4"]["leads"][2]["metrics"]["recall"]
    res["CT4"] = {"recall_C0": r0, "recall_C4": r4, "dev_L2_gain_C4": d2["C4"], "confirmed": (r4 - r0) * 17 >= 2 - 1e-9 and d2["C4"] >= 0}
    res["CT5"] = {"dev_L2_gain_C5": d2["C5"], "confirmed": d2["C5"] >= .005}
    res["CT6"] = {c: {"lead2_price_auc": res["cands"][c]["leads"][2]["price_term"]["auc"],
                      "lead1_price_auc": res["cands"][c]["leads"][1]["price_term"]["auc"],
                      "lead2_R5_p_vs_clim": res["cands"][c]["leads"][2]["brier_vs_clim"]["p_less"]} for c in ("C0", final)}
    res["CT6"]["confirmed"] = all(v["lead2_price_auc"] < .80 and v["lead2_R5_p_vs_clim"] > .10 for k, v in res["CT6"].items() if k != "confirmed")
    E.to_csv(T.OUT / "candidates.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("candidates.json").write_text(json.dumps(res, indent=1, default=float))
    for c, r in res["cands"].items():
        print(f"{c} maxrel {r['max_reliable_lead']} devL1 {r['dev_L1']:.4f} devL2 {r['dev_L2']:.4f} |", " | ".join(
            f"L{k} {d['metrics']['accuracy']:.3f}/{d['metrics']['balanced_accuracy']:.2f} P{d['metrics']['precision']:.2f} "
            f"R{d['metrics']['recall']:.2f} Br{d['metrics']['brier']:.3f} vsC0 {d['vs_C0']['diff']:+.4f} {''.join(d['failed'])}"
            for k, d in r["leads"].items() if k <= 3))
    print("selection", res["selection"])
    for k in ("CT1", "CT2", "CT3", "CT4", "CT5", "CT6"):
        print(k, {a: b for a, b in res[k].items() if a != "cases"})
    print("coverage", res["feature_coverage"])


if __name__ == "__main__":
    main()
