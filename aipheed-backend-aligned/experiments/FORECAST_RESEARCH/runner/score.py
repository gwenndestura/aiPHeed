"""FORECAST_RESEARCH scoring (PROTOCOL sections 5-6): arms Z0-Z3 x schedules A/B on the FINAL_ARCHITECTURE rows,
oracle decomposition (FR1), continuous error RMSE, reliability per lead, selection.

    python score.py      # out/predictions.csv, out/results.json
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

import fr_lib as F
import metrics as M

ARMS = ["Z0", "Z1", "Z2", "Z3"]
KEY = ["t", "lead", "province_code"]


def build():
    E = F.eval_rows().copy()
    origins = sorted(E["t"].unique())
    S = F.stack()
    allt = sorted(S.loc[S["t"] >= origins[0], "t"].unique())   # every origin, for continuous RMSE on all quarters
    t0 = time.time()
    cont = []
    for a in ARMS:
        P = F.run_arm(a, allt)
        P = P.merge(S[KEY + ["ef", "eg", "target_q"]].drop(columns="target_q"), on=KEY, how="left")
        P["arm"] = a
        cont.append(P)
        print(a, "done", round(time.time() - t0), "s", flush=True)
    C = pd.concat(cont, ignore_index=True)
    C.to_csv(F.OUT / "price_arms_all_origins.csv", index=False, lineterminator="\n", float_format="%.6g")
    for sch in ("A", "B"):
        H = F.attach_hunger(E[KEY].copy(), sch)
        E[f"pi_H_{sch}"] = H["pi_H"].to_numpy()
        E[f"issue_{sch}"] = H["issue_date"].to_numpy()
        E[f"warn_days_{sch}"] = H["warning_days"].to_numpy()
        E[f"true_h_{sch}"] = H["true_h"].to_numpy()
        E[f"PERSIST_{sch}"] = F.persistence(E, sch)
    for a in ARMS:
        P = C[C["arm"] == a][KEY + ["pi_P", "F_ex_hat", "G_ex_hat"]].rename(
            columns={"pi_P": f"{a}_price", "F_ex_hat": f"{a}_Fhat", "G_ex_hat": f"{a}_Ghat"})
        E = E.merge(P, on=KEY, how="left")
        for sch in ("A", "B"):
            E[f"{a}{sch}_p"] = E[f"pi_H_{sch}"] * E[f"{a}_price"]
    for sch in ("A", "B"):
        E[f"P0H4{sch}_p"] = E[f"pi_H_{sch}"] * E["P0_price"]   # served price part with the schedule's hunger term
    E.to_csv(F.OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    return E, C


def main():
    F.check_protocol()
    assert json.loads((F.OUT / "audit.json").read_text())["passed"], "run audit.py first"
    E, C = build()
    res = {"protocol_sha256": F.sha256(F.FR / "PROTOCOL_FORECAST_RESEARCH.md"),
           "persist_A_vs_served_max_abs": float((E["PERSIST_A"] - E["PERSIST-SI_p"]).abs().max()),
           "issue_B": {F.qs(int(t)): g["issue_B"].iloc[0] for t, g in E.groupby("t")},
           "continuous": {}, "oracle": {}, "arms": {}, "selection": {}}
    # continuous error RMSE (all origins with realised CPI, leads 1-4) and on the evaluation origins only
    for a in ARMS:
        g = C[(C["arm"] == a) & C["ef"].notna()]
        res["continuous"][a] = {int(k): {"rmse_food": float(np.sqrt(np.mean((h["ef"] - h["ef_hat"]) ** 2))),
                                         "rmse_gap": float(np.sqrt(np.mean((h["eg"] - h["eg_hat"]) ** 2))),
                                         "bias_food": float(np.mean(h["ef"] - h["ef_hat"])), "n": int(len(h)),
                                         "n_quarters": int(h["t"].nunique())}
                                for k, h in g.groupby("lead")}
    # FR1 oracle decomposition (schedule A and B hunger; Z0 price as the structural reference)
    for sch in ("A", "B"):
        for pc in ("Z0_price", "Z1_price", "P0_price"):
            for k, g in E.groupby("lead"):
                res["oracle"].setdefault(f"{sch}|{pc}", {})[int(k)] = {
                    "forecast_x_forecast": M.cls(g["y"], g[f"pi_H_{sch}"] * g[pc]),
                    "true_hunger_x_forecast_price": M.cls(g["y"], g["hunger"] * g[pc]),
                    "forecast_hunger_x_true_price": M.cls(g["y"], g[f"pi_H_{sch}"] * g["price"])}
    for sch in ("A", "B"):
        for name in ARMS + ["P0H4"]:
            col = f"{name}{sch}_p"
            dec = {}
            for k, g in E.groupby("lead"):
                d = F.evaluate(g, col, f"PERSIST_{sch}")
                d["dev"] = M.cls(g.loc[g["q"] <= F.DEV_LAST, "y"], g.loc[g["q"] <= F.DEV_LAST, col])
                d["conf"] = M.cls(g.loc[g["q"] > F.DEV_LAST, "y"], g.loc[g["q"] > F.DEV_LAST, col])
                pcol = f"{name}_price" if name != "P0H4" else "P0_price"
                d["price_term"] = M.cls(g["price"], g[pcol])
                d["vs_served_P0H4"] = M.boot_diff(g["q"], (g[col] - g["y"]) ** 2, (g["P0H4_p3"] - g["y"]) ** 2)
                d["calibration"] = M.calibration(g["y"], g[col])
                d["warning_days_median"] = float(g[f"warn_days_{sch}"].median())
                d["n_eff"] = M.n_eff(g["q"], g["y"])
                dec[int(k)] = d
            dev_brier = float(np.mean([dec[k]["dev"]["brier"] for k in (1, 2, 3)]))
            res["arms"][f"{name}{sch}"] = {"leads": dec, "dev_brier_L1_3": dev_brier, "max_reliable_lead": F.max_reliable(dec)}
        sc = {a: res["arms"][f"{a}{sch}"]["dev_brier_L1_3"] for a in ARMS}
        best = min(ARMS, key=lambda a: (round(sc[a], 9), ARMS.index(a)))
        chosen = "Z3" if sc["Z3"] - sc[best] <= 0.002 else best
        res["selection"][sch] = {"dev_brier": sc, "best": best, "chosen": chosen,
                                 "lightgbm_adds_no_dev_value": sc["Z3"] - min(sc[a] for a in ("Z0", "Z1", "Z2")) > -1e-9}
    F.OUT.joinpath("results.json").write_text(json.dumps(res, indent=1, default=float))
    report(res)


def report(res):
    print("persist A reproduces served:", res["persist_A_vs_served_max_abs"])
    print("continuous RMSE food (all origins):")
    for a, r in res["continuous"].items():
        print(f"  {a}", " ".join(f"L{k}:{v['rmse_food']:.2f}(bias {v['bias_food']:+.2f})/gap {v['rmse_gap']:.2f}" for k, v in r.items()))
    for name, r in res["arms"].items():
        print(f"{name:7s} dev {r['dev_brier_L1_3']:.4f} maxrel {r['max_reliable_lead']} |", " | ".join(
            f"L{k} acc {d['metrics']['accuracy']:.3f} bal {d['metrics']['balanced_accuracy']:.3f} P {d['metrics']['precision']:.2f} "
            f"R {d['metrics']['recall']:.2f} Br {d['metrics']['brier']:.3f} pr-AUC {d['price_term']['auc']:.2f} fail {d['failed']}"
            for k, d in r["leads"].items() if k <= 3))
    print("selection", res["selection"])


if __name__ == "__main__":
    main()
