"""PROTOCOL section 6: every price part x pi_H(S-AB) on the FR evaluation rows; R1-R7; the one DEV selection rule;
comparisons with P0H4 / P0H4-U / baselines (Holm); hypotheses H1-H3; online selection (H7); component reliability (H6).

    python score_ii.py          # out/predictions_ii.csv, out/results_ii.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ii_lib as L

F, M, KEY = L.F, L.M, L.KEY
ARMS = ["Z0", "P0", "J0", "J1", "J2", "J3", "J3T", "JB3", "CMB", "LJ"]
LGBM = ("P0", "LJ")


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def frame() -> pd.DataFrame:
    E = pd.read_csv(F.OUT / "predictions.csv", dtype={"province_code": str})
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    for a in ("J0", "J1", "J2", "J3", "J3T", "JB3", "LJ"):
        P = A[A["arm"] == a][KEY + ["pi_P"]].rename(columns={"pi_P": f"{a}_price"})
        E = E.merge(P, on=KEY, how="left")
        jm = A[A["arm"] == a][KEY + ["F_mean"]].rename(columns={"F_mean": f"{a}_Fmean"}) if a != "LJ" else None
        if jm is not None:
            E = E.merge(jm, on=KEY, how="left")
    E["CMB_price"] = 0.5 * (E["Z0_price"] + E["J3T_price"])
    E["pi_H_AB"] = np.where(E["lead"] == 1, E["pi_H_A"], E["pi_H_B"])
    E["PERS_AB"] = np.where(E["lead"] == 1, E["PERSIST_A"], E["PERSIST_B"])
    E["P0H4U_p"] = np.where(E["lead"] == 1, E["P0H4A_p"], E["P0H4B_p"])
    for a in ARMS:
        assert E[f"{a}_price"].notna().all(), a
        E[f"{a}_p"] = E["pi_H_AB"] * E[f"{a}_price"]
        E[f"{a}A_p"] = E["pi_H_A"] * E[f"{a}_price"]
    E["F_real"] = E["price"]
    return E


def lead_eval(E: pd.DataFrame, col: str, pcol: str, pers: str = "PERS_AB") -> dict:
    dec = {}
    for k, g in E.groupby("lead"):
        d = F.evaluate(g, col, pers)
        dv, cf = g["q"] <= F.DEV_LAST, g["q"] > F.DEV_LAST
        d["dev"], d["conf"] = M.cls(g.loc[dv, "y"], g.loc[dv, col]), M.cls(g.loc[cf, "y"], g.loc[cf, col])
        d["price_term"] = M.cls(g["price"], g[pcol])
        d["price_dev"] = M.cls(g.loc[dv, "price"], g.loc[dv, pcol])
        d["vs_P0H4U"] = M.boot_diff(g["q"], (g[col] - g["y"]) ** 2, (g["P0H4U_p"] - g["y"]) ** 2)
        d["vs_P0H4"] = M.boot_diff(g["q"], (g[col] - g["y"]) ** 2, (g["P0H4_p3"] - g["y"]) ** 2)
        d["calibration"] = M.calibration(g["y"], g[col])
        d["n_eff"] = M.n_eff(g["q"], g["y"])
        dec[int(k)] = d
    return dec


def online(E: pd.DataFrame) -> pd.Series:
    out = pd.Series(index=E.index, dtype=float)
    pick = {}
    for t in sorted(E["t"].unique()):
        hist = E[(E["t"] < t) & (E["q"] <= t - 1)]
        if hist["q"].nunique() < 4:
            ch = "P0"
        else:
            sc = {a: float(np.mean((hist[f"{a}_price"] - hist["price"]) ** 2)) for a in ARMS}
            ch = min(ARMS, key=lambda a: (round(sc[a], 10), ARMS.index(a)))
        pick[F.qs(int(t))] = ch
        m = E["t"] == t
        out[m] = E.loc[m, f"{ch}_price"]
    return out, pick


def price_component(chosen: str) -> dict:
    """H6: the price condition alone, on every evaluation-origin row with a realised CPI quarter."""
    S = F.stack()
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    Z = pd.read_csv(F.OUT / "price_arms_all_origins.csv", dtype={"province_code": str})
    E0 = F.eval_rows()
    origins = sorted(E0["t"].unique())
    R = S[S["t"].isin(origins) & S["F"].notna()][KEY + ["target_q", "F", "HL", "F_ex", "G_ex"]].copy()
    R["y"] = (((R["F"] - R["province_code"].map(F.TH_F)) > 0) | ((R["F"] - R["HL"] - R["province_code"].map(F.TH_G)) > 0)).astype(int)
    R["q"] = R["target_q"]
    R["PERS"] = ((R["F_ex"] > 0) | (R["G_ex"] > 0)).astype(float)
    R.loc[R["F_ex"].isna() | R["G_ex"].isna(), "PERS"] = np.nan
    allS = S[S["F"].notna()].copy()
    allS["yp"] = (((allS["F"] - allS["province_code"].map(F.TH_F)) > 0) | ((allS["F"] - allS["HL"] - allS["province_code"].map(F.TH_G)) > 0)).astype(int)
    clim = []
    for t, k in zip(R["t"], R["lead"]):
        tr = allS[(allS["t"] < t) & (allS["target_q"] <= t - 1) & (allS["lead"] == k)]
        clim.append(float(tr["yp"].mean()) if len(tr) else 0.5)
    R["CLIM_p"] = clim
    R["PERS"] = R["PERS"].fillna(R["CLIM_p"])
    R["ALWAYS-LOW_p"] = 0.0
    for a in ("J0", "J1", "J2", "J3", "J3T", "JB3", "LJ"):
        R = R.merge(A[A["arm"] == a][KEY + ["pi_P"]].rename(columns={"pi_P": f"{a}_price"}), on=KEY, how="left")
    R = R.merge(Z[Z["arm"] == "Z0"][KEY + ["pi_P"]].rename(columns={"pi_P": "Z0_price"}), on=KEY, how="left")
    R["CMB_price"] = 0.5 * (R["Z0_price"] + R["J3T_price"])
    out = {"rows_by_lead": R.groupby("lead").size().to_dict(), "quarters_by_lead": R.groupby("lead")["q"].nunique().to_dict()}
    arms = [a for a in ARMS if a != "P0"]
    for a in arms:
        dec = {}
        for k, g in R.groupby("lead"):
            g = g[g[f"{a}_price"].notna()]
            dec[int(k)] = F.evaluate(g, f"{a}_price", "PERS")
        out[a] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec)}
    R.to_csv(L.OUT / "price_component_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    return out


def hunger_component() -> dict:
    E = F.eval_rows().drop_duplicates(["t", "lead"])[["t", "lead", "q", "hunger"]].copy()
    out = {}
    for sch in ("A", "AB"):
        rows = []
        for t, k, q, h in zip(E["t"], E["lead"], E["q"], E["hunger"]):
            s = "A" if (sch == "A" or k == 1) else "B"
            iss = F.issue(int(t), s)
            ph = F.pi_h(iss, int(q))["pi_H"]
            kn = F.known(iss, "BL")
            rows.append({"t": t, "lead": k, "q": q, "y": int(h), "pi": ph, "PERS": float(kn[-1][1] > F.H_LINE),
                         "CLIM_p": F.hunger_climatology(iss), "ALWAYS-LOW_p": 0.0})
        H = pd.DataFrame(rows)
        H["pi"] = H["pi"].fillna(H["CLIM_p"])
        dec = {int(k): F.evaluate(g, "pi", "PERS") for k, g in H.groupby("lead")}
        out[sch] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec)}
    return out


def main():
    L.check_protocol()
    E = frame()
    res = {"protocol_sha256": L.sha256(L.II / "PROTOCOL_FORECAST_RESEARCH_II.md"),
           "inputs": {"fr_predictions": L.sha256(F.OUT / "predictions.csv"), "price_arms_ii": L.sha256(L.OUT / "price_arms_ii.csv")},
           "arms": {}, "arms_A": {}}
    for a in ARMS:
        dec = lead_eval(E, f"{a}_p", f"{a}_price")
        res["arms"][a] = {"leads": dec, "dev_brier_L1_3": float(np.mean([dec[k]["dev"]["brier"] for k in (1, 2, 3)])),
                          "max_reliable_lead": F.max_reliable(dec)}
        decA = lead_eval(E, f"{a}A_p", f"{a}_price", "PERSIST_A")
        res["arms_A"][a] = {"max_reliable_lead": F.max_reliable(decA),
                            "acc": {k: decA[k]["metrics"]["accuracy"] for k in decA}, "brier": {k: decA[k]["metrics"]["brier"] for k in decA}}
    for ref, col in (("P0H4", "P0H4_p3"), ("P0H4U", "P0H4U_p")):
        pers = "PERSIST_A" if ref == "P0H4" else "PERS_AB"
        dec = lead_eval(E, col, "P0_price", pers)
        res["arms"][ref] = {"leads": dec, "dev_brier_L1_3": float(np.mean([dec[k]["dev"]["brier"] for k in (1, 2, 3)])),
                            "max_reliable_lead": F.max_reliable(dec)}
    # ---------------------------------------------------------------- selection (6.3)
    dev = {a: res["arms"][a]["dev_brier_L1_3"] for a in ARMS}
    best = min(ARMS, key=lambda a: (round(dev[a], 9), ARMS.index(a)))
    best_lgbm = min(LGBM, key=lambda a: (round(dev[a], 9), ARMS.index(a)))
    chosen = best_lgbm if dev[best_lgbm] - dev[best] <= 0.002 else best
    adopt = dev[chosen] < res["arms"]["P0H4U"]["dev_brier_L1_3"] and not any(
        res["arms"][chosen]["leads"][k]["vs_P0H4U"]["diff"] > 0 and res["arms"][chosen]["leads"][k]["vs_P0H4U"]["p_two"] < .10
        for k in F.LEADS)
    res["selection"] = {"dev_brier": dev, "best": best, "best_lightgbm": best_lgbm, "chosen_FINAL": chosen,
                        "lightgbm_adds_no_dev_value": bool(dev[best_lgbm] - dev[best] > 0.002),
                        "P0H4U_dev": res["arms"]["P0H4U"]["dev_brier_L1_3"], "FINAL_replaces_P0H4U": bool(adopt and chosen != "P0")}
    # Holm comparisons of FINAL
    fc = f"{chosen}_p"
    hc = {}
    for k, g in E.groupby("lead"):
        bs = (g[fc] - g["y"]) ** 2
        comp = {"P0H4": M.boot_diff(g["q"], bs, (g["P0H4_p3"] - g["y"]) ** 2),
                "P0H4U": M.boot_diff(g["q"], bs, (g["P0H4U_p"] - g["y"]) ** 2),
                "persistence": M.boot_diff(g["q"], bs, (g["PERS_AB"] - g["y"]) ** 2),
                "climatology": M.boot_diff(g["q"], bs, (g["CLIM_p"] - g["y"]) ** 2),
                "always_low": M.boot_diff(g["q"], bs, (g["ALWAYS-LOW_p"] - g["y"]) ** 2)}
        hp = holm({c: v["p_less"] for c, v in comp.items()})
        hc[int(k)] = {c: {**v, "holm_p_less": hp[c]} for c, v in comp.items()}
    res["FINAL_comparisons"] = hc
    # ---------------------------------------------------------------- hypotheses H1-H3
    h1 = {}
    for a in ("J1", "J2", "J3"):
        pdv = {k: res["arms"][a]["leads"][k]["price_dev"]["brier"] for k in (1, 2, 3)}
        ref = {k: min(res["arms"]["Z0"]["leads"][k]["price_dev"]["brier"], res["arms"]["J0"]["leads"][k]["price_dev"]["brier"]) for k in (1, 2, 3)}
        g1 = E[E["lead"] == 1]
        l1 = M.boot_diff(g1["q"], (g1[f"{a}_price"] - g1["price"]) ** 2, (g1["Z0_price"] - g1["price"]) ** 2)
        h1[a] = {"price_dev_brier": pdv, "best_of_Z0_J0": ref, "lead1_vs_Z0": l1,
                 "supported": bool(pdv[2] < ref[2] and pdv[3] < ref[3] and not (l1["diff"] > 0 and l1["p_two"] < .10))}
    res["H1"] = {"by_arm": h1, "supported": any(v["supported"] for v in h1.values())}
    ll = {k: (res["arms"]["J0"]["leads"][k]["price_term"]["log_loss"], res["arms"]["Z0"]["leads"][k]["price_term"]["log_loss"]) for k in (1, 2, 3)}
    res["H2"] = {"price_log_loss_J0_vs_Z0": ll, "supported": sum(a < b for a, b in ll.values()) >= 2}
    l3 = {k: (res["arms"]["JB3"]["leads"][k]["metrics"]["log_loss"], res["arms"]["J3"]["leads"][k]["metrics"]["log_loss"]) for k in (1, 2, 3)}
    res["H3"] = {"T43c_log_loss_JB3_vs_J3": l3, "supported": sum(a < b for a, b in l3.values()) >= 2}
    # continuous RMSE of the J means (evaluation rows)
    res["continuous_rmse_food"] = {a: {int(k): float(np.sqrt(np.mean((g[f"{a}_Fmean"] - (g["price"] * 0 + g["F_tgt"])) ** 2)))
                                       for k, g in E.assign(F_tgt=E.merge(F.ps_full()[["province_code", "q", "F"]], on=["province_code", "q"], how="left")["F"].to_numpy()).groupby("lead")}
                                   for a in ("J0", "J1", "J2", "J3", "JB3")}
    # ---------------------------------------------------------------- online selection (H7)
    E["ONL_price"], picks = online(E)
    E["ONL_p"] = E["pi_H_AB"] * E["ONL_price"]
    dec = lead_eval(E, "ONL_p", "ONL_price")
    vs = {}
    for k, g in E.groupby("lead"):
        vs[int(k)] = M.boot_diff(g["q"], (g["ONL_p"] - g["y"]) ** 2, (g[fc] - g["y"]) ** 2)
    res["ONL"] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec), "picks": picks, "vs_FINAL": vs,
                  "H7_supported": not any(vs[k]["diff"] > 0 and vs[k]["p_two"] < .10 for k in (1, 2, 3))}
    # ---------------------------------------------------------------- components (H6)
    res["component_price"] = price_component(chosen)
    res["component_hunger"] = hunger_component()
    pc = res["component_price"][chosen if chosen != "P0" else "Z0"]["max_reliable_lead"]
    res["H6"] = {"price_component_max_reliable": pc, "T43c_FINAL_max_reliable": res["arms"][chosen]["max_reliable_lead"],
                 "supported": pc > res["arms"][chosen]["max_reliable_lead"]}
    E.to_csv(L.OUT / "predictions_ii.csv", index=False, lineterminator="\n", float_format="%.6g")
    L.dump("results_ii.json", res)
    report(res)


def report(res):
    for a, r in res["arms"].items():
        print(f"{a:6s} dev {r['dev_brier_L1_3']:.4f} maxrel {r['max_reliable_lead']} |", " | ".join(
            f"L{k} {d['metrics']['accuracy']:.3f}/{d['metrics']['balanced_accuracy']:.2f} P{d['metrics']['precision']:.2f} "
            f"R{d['metrics']['recall']:.2f} Br{d['metrics']['brier']:.3f} pB{d['price_term']['brier']:.3f} {''.join(d['failed'])}"
            for k, d in r["leads"].items()))
    print("A-only maxrel", {a: v["max_reliable_lead"] for a, v in res["arms_A"].items()})
    print("selection", res["selection"])
    for k, c in res["FINAL_comparisons"].items():
        print("FINAL L", k, {n: (round(v["diff"], 4), round(v["holm_p_less"], 3)) for n, v in c.items()})
    print("H1", {a: (v["supported"], {k: round(x, 4) for k, x in v["price_dev_brier"].items()}) for a, v in res["H1"]["by_arm"].items()},
          "ref", res["H1"]["by_arm"]["J1"]["best_of_Z0_J0"])
    print("H2", res["H2"])
    print("H3", res["H3"])
    print("RMSE", res["continuous_rmse_food"])
    o = res["ONL"]
    print("ONL maxrel", o["max_reliable_lead"], o["picks"], {k: (round(v["diff"], 4), round(v["p_two"], 3)) for k, v in o["vs_FINAL"].items()},
          " | ".join(f"L{k} {d['metrics']['accuracy']:.3f} Br{d['metrics']['brier']:.3f} {''.join(d['failed'])}" for k, d in o["leads"].items()))
    for a in ("Z0", "J0", "J1", "J2", "J3", "J3T", "JB3", "CMB", "LJ"):
        r = res["component_price"][a]
        print("PRICE", a, r["max_reliable_lead"], " | ".join(
            f"L{k} {d['metrics']['accuracy']:.3f}/{d['metrics']['balanced_accuracy']:.2f} R{d['metrics']['recall']:.2f} "
            f"Br{d['metrics']['brier']:.3f} {''.join(d['failed'])}" for k, d in r["leads"].items()))
    for s, r in res["component_hunger"].items():
        print("HUNGER", s, r["max_reliable_lead"], " | ".join(
            f"L{k} {d['metrics']['accuracy']:.3f} n{d['metrics']['n']} Br{d['metrics']['brier']:.3f} {''.join(d['failed'])}" for k, d in r["leads"].items()))
    print("H6", res["H6"])


if __name__ == "__main__":
    main()
