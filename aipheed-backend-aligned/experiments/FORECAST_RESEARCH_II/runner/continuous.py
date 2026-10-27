"""Continuous food-inflation error of the pre-registered arms (PROTOCOL 6.1 metric), with paired quarter-block CIs by
DEV/CONF; plus ONE clearly labelled POST-HOC exploratory arm J2S (anchored drift J2 with its sigma rescaled to its own
track record, shrinking allowed), written for prospective testing only - never used for selection.

    python continuous.py        # out/continuous.json, out/j2s_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import ii_lib as L
import price_arms as PA
from contrib_ii import boot

F, M, KEY = L.F, L.M, L.KEY


def main():
    L.check_protocol()
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    S = F.stack()
    E = pd.read_csv(L.OUT / "predictions_ii.csv", dtype={"province_code": str})
    origins = sorted(E["t"].unique())
    R = S[S["t"].isin(origins) & S["F"].notna()][KEY + ["target_q", "F", "A1_food"]].copy()
    R["Z0_F"] = R["A1_food"] + R["province_code"].map(F.TH_F)
    for a in ("J0", "J1", "J2", "J3"):
        R = R.merge(A[A["arm"] == a][KEY + ["F_mean"]].rename(columns={"F_mean": f"{a}_F"}), on=KEY, how="left")
    out = {"label": "continuous error of pre-registered arms; J2S is POST-HOC exploratory", "rmse": {}, "J2_vs_Z0": {}}
    for blk, m in (("all", R["target_q"] > 0), ("DEV", R["target_q"] <= F.DEV_LAST), ("CONF", R["target_q"] > F.DEV_LAST)):
        G = R[m]
        out["rmse"][blk] = {int(k): {a: float(np.sqrt(np.mean((g[f"{a}_F"] - g["F"]) ** 2))) for a in ("Z0", "J0", "J1", "J2", "J3")}
                            | {"n": int(len(g)), "quarters": int(g["target_q"].nunique())} for k, g in G.groupby("lead")}
        out["J2_vs_Z0"][blk] = {int(k): boot(g["target_q"], (g["Z0_F"] - g["F"]) ** 2, (g["J2_F"] - g["F"]) ** 2)
                                for k, g in G.groupby("lead")}                       # > 0 = J2 better
    for blk in ("all", "DEV", "CONF"):
        print(blk, {k: {a: round(v, 2) for a, v in d.items()} for k, d in out["rmse"][blk].items()})
        print("   J2 better than Z0 (dMSE, CI):", {k: (round(v["diff"], 2), [round(c, 2) for c in v["ci90"]]) for k, v in out["J2_vs_Z0"][blk].items()})
    # -------------------------------------------------------------- POST-HOC J2S
    draws = {}
    for t in sorted(S["t"].unique()):
        for (arm, p, k), v in PA.simulate(int(t)).items():
            if arm == "J2":
                draws[(int(t), p, k)] = v
    J2 = A[A["arm"] == "J2"].copy()
    rows = []
    for t in sorted(J2["t"].unique()):
        tr = J2[(J2["t"] < t) & (J2["target_q"] <= t - 1) & J2["F"].notna()]
        sk = {}
        for k in F.LEADS:
            g = tr[tr["lead"] == k]
            sk[k] = (float(np.sqrt(np.mean((g["F"] - g["F_mean"]) ** 2)) / np.median(g["F_sd"]))
                     if g["target_q"].nunique() >= 4 else 1.0)
        for _, r in J2[J2["t"] == t].iterrows():
            Fd, Hd = draws[(int(t), r["province_code"], int(r["lead"]))]
            s = max(sk[int(r["lead"])], 0.25)
            Fs, Hs = Fd.mean() + s * (Fd - Fd.mean()), Hd.mean() + s * (Hd - Hd.mean())
            rows.append({"t": int(t), "lead": int(r["lead"]), "province_code": r["province_code"], "J2S_price": PA.prob(Fs, Hs, r["province_code"]),
                         "scale": s})
    J = pd.DataFrame(rows)
    J.to_csv(L.OUT / "j2s_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    E = E.merge(J[KEY + ["J2S_price"]], on=KEY, how="left")
    E["J2S_p"] = E["pi_H_AB"] * E["J2S_price"]
    dec = {}
    for k, g in E.groupby("lead"):
        d = F.evaluate(g, "J2S_p", "PERS_AB")
        d["price_term"] = M.cls(g["price"], g["J2S_price"])
        d["vs_FINAL"] = M.boot_diff(g["q"], (g["J2S_p"] - g["y"]) ** 2, (g["Z0_p"] - g["y"]) ** 2)
        dv = g["q"] <= F.DEV_LAST
        d["dev"] = M.cls(g.loc[dv, "y"], g.loc[dv, "J2S_p"])
        dec[int(k)] = d
    out["J2S_posthoc"] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec),
                          "dev_brier_L1_3": float(np.mean([dec[k]["dev"]["brier"] for k in (1, 2, 3)])),
                          "scale_by_lead": J.groupby("lead")["scale"].median().to_dict()}
    print("J2S POST-HOC maxrel", out["J2S_posthoc"]["max_reliable_lead"], "dev", round(out["J2S_posthoc"]["dev_brier_L1_3"], 4), "|", " | ".join(
        f"L{k} {d['metrics']['accuracy']:.3f}/{d['metrics']['balanced_accuracy']:.2f} P{d['metrics']['precision']:.2f} R{d['metrics']['recall']:.2f} "
        f"Br{d['metrics']['brier']:.3f} pB{d['price_term']['brier']:.3f} vsZ0 {d['vs_FINAL']['diff']:+.4f}(p{d['vs_FINAL']['p_two']:.2f}) {''.join(d['failed'])}"
        for k, d in dec.items()), out["J2S_posthoc"]["scale_by_lead"])
    L.dump("continuous.json", out)


if __name__ == "__main__":
    main()
