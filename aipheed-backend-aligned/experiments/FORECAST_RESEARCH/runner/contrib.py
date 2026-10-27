"""Addendum 2 (ADDENDUM_2_FAMILY_CONTRIBUTIONS.md): C1 selected-arm removals, C2 add-one, C3 leave-one-out, C4
permutation, C5 SHAP stability.   python contrib.py   -> out/contributions.json, out/contrib_rows.csv"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

import fr_lib as F
import metrics as M

KEY = ["t", "lead", "province_code"]
N_PERM = 20


def _check():
    F.check_protocol()
    assert F.sha256(F.FR / "ADDENDUM_2_FAMILY_CONTRIBUTIONS.md") == (F.HERE / "ADDENDUM_2_SHA256.txt").read_text().strip()


def cont_cmp(Ca: pd.DataFrame, Cb: pd.DataFrame) -> dict:
    """Continuous squared-error difference a - b by lead (rows with realised CPI), blocks = target quarter."""
    m = Ca.merge(Cb, on=KEY, suffixes=("_a", "_b"))
    out = {}
    for k, g in m.groupby("lead"):
        g = g[g["ef_a"].notna()]
        r = {}
        for e in ("ef", "eg"):
            sa, sb = (g[f"{e}_a"] - g[f"{e}_hat_a"]) ** 2, (g[f"{e}_a"] - g[f"{e}_hat_b"]) ** 2
            b = M.boot_diff(g["target_q_a"], sa, sb)
            r[e] = {"d_mse": b["diff"], "ci90": b["ci90"], "p_less": b["p_less"],
                    "d_rmse": float(np.sqrt(sa.mean()) - np.sqrt(sb.mean())), "n": int(len(g))}
        out[int(k)] = r
    return out


def brier_cmp(E: pd.DataFrame, pa: str, pb: str) -> dict:
    out = {}
    for k, g in E.groupby("lead"):
        r = {}
        pr = M.boot_diff(g["q"], (g[pa] - g["price"]) ** 2, (g[pb] - g["price"]) ** 2)
        r["price"] = {"diff": pr["diff"], "ci90": pr["ci90"], "p_less": pr["p_less"]}
        for sch in ("A", "B"):
            y = g["y"]
            b = M.boot_diff(g["q"], (g[f"pi_H_{sch}"] * g[pa] - y) ** 2, (g[f"pi_H_{sch}"] * g[pb] - y) ** 2)
            r[f"t43c_{sch}"] = {"diff": b["diff"], "ci90": b["ci90"], "p_less": b["p_less"]}
        out[int(k)] = r
    return out


def with_cont(P: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    return P.merge(S[KEY + ["ef", "eg"]], on=KEY, how="left")


def main():
    _check()
    t0 = time.time()
    S = F.stack()
    E = pd.read_csv(F.OUT / "predictions.csv", dtype={"province_code": str})
    base = json.loads((F.OUT / "results.json").read_text())
    origins_all = sorted(S.loc[S["t"] >= E["t"].min(), "t"].unique())
    res = {"C1": {}, "C2": {}, "C3": {}, "C4": {}, "C5": {}, "coverage": {}}

    # ---------------------------------------------------------------- C1: selected arms
    for sch in ("A", "B"):
        arm = base["selection"][sch]["chosen"]
        col = f"{arm}{sch}_p"
        # A1 removal: price climatology by lead (training rows of each origin)
        clim = {}
        for t in E["t"].unique():
            tr = F.price_train(S, int(t))
            tr = tr.merge(F.ps_full()[["province_code", "q", "y"]].rename(columns={"q": "target_q", "y": "yp"}),
                          on=["province_code", "target_q"])
            for k in F.LEADS:
                v = tr.loc[tr["lead"] == k, "yp"]
                clim[(int(t), k)] = float(v.mean()) if len(v) else 0.5
        E[f"noA1_{sch}"] = E[f"pi_H_{sch}"] * [clim[(int(t), int(k))] for t, k in zip(E["t"], E["lead"])]
        Hc = F.attach_hunger(E[KEY], sch, climatology=True)
        E[f"noH1_{sch}"] = Hc["pi_H"].to_numpy() * E[f"{arm}_price"]
        r = {}
        for k, g in E.groupby("lead"):
            r[int(k)] = {name: M.boot_diff(g["q"], (g[c] - g["y"]) ** 2, (g[col] - g["y"]) ** 2)
                         for name, c in (("remove_A1", f"noA1_{sch}"), ("remove_H1", f"noH1_{sch}"))}
        res["C1"][sch] = {"arm": arm, "leads": r}
    print("C1 done", round(time.time() - t0), flush=True)

    # ---------------------------------------------------------------- reference continuous runs
    Z0 = with_cont(F.run_arm("Z0", origins_all), S)
    Z3 = with_cont(F.run_arm("Z3", origins_all), S)
    Ev = E[KEY + ["q", "y", "price", "pi_H_A", "pi_H_B"]].copy()
    Ev = Ev.merge(Z0[KEY + ["pi_P"]].rename(columns={"pi_P": "Z0_pp"}), on=KEY)
    Ev = Ev.merge(Z3[KEY + ["pi_P"]].rename(columns={"pi_P": "Z3_pp"}), on=KEY)
    res["Z3_vs_Z0"] = {"continuous": cont_cmp(Z3, Z0), "brier": brier_cmp(Ev, "Z3_pp", "Z0_pp")}

    # ---------------------------------------------------------------- C2 add-one / C3 leave-one-out
    rows = []
    for f in F.FAMILIES:
        cols1 = F.FAMILY_COLS[f] + ["lead"]
        P1 = with_cont(F.run_arm("Z3", origins_all, cols=cols1), S)
        cols3 = [c for c in F.F12 if c not in F.FAMILY_COLS[f]]
        P3 = with_cont(F.run_arm("Z3", origins_all, cols=cols3), S)
        Ev[f"add_{f}"] = Ev[KEY].merge(P1[KEY + ["pi_P"]], on=KEY)["pi_P"].to_numpy()
        Ev[f"loo_{f}"] = Ev[KEY].merge(P3[KEY + ["pi_P"]], on=KEY)["pi_P"].to_numpy()
        res["C2"][f] = {"continuous": cont_cmp(P1, Z0), "brier": brier_cmp(Ev, f"add_{f}", "Z0_pp")}
        res["C3"][f] = {"continuous": cont_cmp(P3, Z3), "brier": brier_cmp(Ev, f"loo_{f}", "Z3_pp")}
        rows.append(P1.assign(test="add", family=f))
        print("family", f, round(time.time() - t0), "s", flush=True)
    Ev.to_csv(F.OUT / "contrib_eval_rows.csv", index=False, lineterminator="\n", float_format="%.6g")

    # ---------------------------------------------------------------- C4 permutation / C5 SHAP (Z3 full, model fixed)
    rng = np.random.default_rng(F.SEED)
    eval_t = sorted(E["t"].unique())
    Sidx = S.set_index(KEY)
    perm_rows, shap_rows = [], []
    for t in eval_t:
        out = F.price_arm("Z3", S, int(t), return_models=True)
        models, cols = out.attrs["models"], out.attrs["cols"]
        if "ef" not in models:
            continue
        te = S[S["t"] == t].reset_index(drop=True)
        sv = models["ef"].booster_.predict(te[cols].astype(float), pred_contrib=True)
        for f in F.FAMILIES:
            idx = [cols.index(c) for c in F.FAMILY_COLS[f]]
            shap_rows.append({"t": int(t), "family": f, "mean_abs": float(np.abs(sv[:, idx].sum(1)).mean())})
        sf, sg = out["sigma_f"].to_numpy(), out["sigma_g"].to_numpy()

        def pp(X):
            fh = X["A1_food"].to_numpy(float) + models["ef"].predict(X[cols].astype(float))
            gh = X["A1_gap"].to_numpy(float) + models["eg"].predict(X[cols].astype(float))
            return 1 - (1 - norm.cdf(fh / sf)) * (1 - norm.cdf(gh / sg))
        p_full = pp(te)
        for f in F.FAMILIES:
            fc = F.FAMILY_COLS[f]
            for i in range(N_PERM):
                Xp = te.copy()
                others = [o for o in eval_t if o != t]
                src = rng.choice(others, len(te))
                for j, (s_t, p, k) in enumerate(zip(src, te["province_code"], te["lead"])):
                    key = (int(s_t), int(k), p)
                    if key in Sidx.index:
                        Xp.loc[j, fc] = Sidx.loc[key, fc].to_numpy()
                # protect the base projection: permute only the feature copies, not the base
                Xp["A1_food"], Xp["A1_gap"] = (Xp["A1_food"] if f != "A1" else Xp["A1_food"]), Xp["A1_gap"]
                if f == "A1":
                    fh = te["A1_food"].to_numpy(float) + models["ef"].predict(Xp[cols].astype(float))
                    gh = te["A1_gap"].to_numpy(float) + models["eg"].predict(Xp[cols].astype(float))
                    p_perm = 1 - (1 - norm.cdf(fh / sf)) * (1 - norm.cdf(gh / sg))
                else:
                    p_perm = pp(Xp)
                perm_rows.append(pd.DataFrame({"t": int(t), "lead": te["lead"], "province_code": te["province_code"],
                                               "family": f, "draw": i, "p_full": p_full, "p_perm": p_perm}))
    Pm = pd.concat(perm_rows, ignore_index=True).merge(E[KEY + ["q", "y", "price", "pi_H_A", "pi_H_B"]], on=KEY)
    for f, g in Pm.groupby("family"):
        r = {}
        for k, h in g.groupby("lead"):
            d_price = ((h["p_perm"] - h["price"]) ** 2 - (h["p_full"] - h["price"]) ** 2).mean()
            d_a = ((h["pi_H_A"] * h["p_perm"] - h["y"]) ** 2 - (h["pi_H_A"] * h["p_full"] - h["y"]) ** 2).mean()
            per_draw = h.assign(d=(h["p_perm"] - h["price"]) ** 2 - (h["p_full"] - h["price"]) ** 2).groupby("draw")["d"].mean()
            r[int(k)] = {"d_brier_price": float(d_price), "d_brier_t43c_A": float(d_a),
                         "share_draws_worse": float((per_draw > 0).mean())}
        res["C4"][f] = r
    Sh = pd.DataFrame(shap_rows)
    thirds = np.array_split(np.array(sorted(Sh["t"].unique())), 3)
    tab = {f"third{i + 1}": Sh[Sh["t"].isin(th)].groupby("family")["mean_abs"].mean() for i, th in enumerate(thirds)}
    T = pd.DataFrame(tab).reindex(F.FAMILIES)
    res["C5"] = {"mean_abs_shap_food_error": T.round(4).to_dict(),
                 "spearman_1v2": float(spearmanr(T["third1"], T["third2"]).statistic),
                 "spearman_2v3": float(spearmanr(T["third2"], T["third3"]).statistic),
                 "spearman_1v3": float(spearmanr(T["third1"], T["third3"]).statistic)}

    # ---------------------------------------------------------------- coverage
    ev = S.merge(E[KEY], on=KEY)
    for f in F.FAMILIES:
        res["coverage"][f] = {c: float(ev[c].isna().mean()) for c in F.FAMILY_COLS[f]}

    # ---------------------------------------------------------------- classification
    cls = {}
    for f in F.FAMILIES:
        c2 = res["C2"][f]["continuous"]
        good = [k for k in c2 for e in ("ef", "eg") if c2[k][e]["ci90"][1] < 0]
        bad = [k for k in c2 for e in ("ef", "eg") if c2[k][e]["ci90"][0] > 0]
        perm_pos = [k for k in good if res["C4"][f].get(k, {}).get("d_brier_price", 0) > 0]
        any_dir = any(c2[k][e]["d_mse"] < 0 for k in c2 for e in ("ef", "eg")) or any(
            res["C3"][f]["continuous"][k][e]["d_mse"] > 0 for k in res["C3"][f]["continuous"] for e in ("ef", "eg"))
        cls[f] = ("predictive" if good and not bad and perm_pos else
                  "weak evidence" if any_dir else "no demonstrated value")
        cls[f] += f" (sig. worse than Z0 at leads {sorted(set(bad))})" if bad else ""
    res["classification"] = cls
    (F.OUT / "contributions.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(cls, indent=1))
    print("Z3 vs Z0 continuous:", {k: {e: round(v[e]["d_rmse"], 2) for e in v} for k, v in res["Z3_vs_Z0"]["continuous"].items()})
    for f in F.FAMILIES:
        print(f, "add-one dRMSE food", {k: (round(v["ef"]["d_rmse"], 2), [round(x, 2) for x in v["ef"]["ci90"]]) for k, v in res["C2"][f]["continuous"].items()},
              "| price dBrier", {k: round(v["price"]["diff"], 3) for k, v in res["C2"][f]["brier"].items()})
    print("C1", json.dumps({s: {k: {n: round(v["diff"], 3) for n, v in d.items()} for k, d in r["leads"].items()} for s, r in res["C1"].items()}))
    print("C5", res["C5"]["spearman_1v2"], res["C5"]["spearman_2v3"], res["C5"]["spearman_1v3"])
    print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
