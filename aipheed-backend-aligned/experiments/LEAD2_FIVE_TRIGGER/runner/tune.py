"""PROTOCOL_LEAD2_TUNING: candidates N0/N1/N2 (nested search over 360 configurations, base / F1 / F2 features) and
G0 (one configuration chosen on DEV rows), scored against B0 = P0H4-U and the served P0H4 with the unchanged rule.

    python tune.py              # ../out/tune.json, tune_rows.csv, tune_configs.csv, tune_dev_configs.csv
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

import final as FN
import lt_lib as T
import tune_lib as U
from features_v5 import F1, F2

F, M, KEY = T.F, T.M, T.KEY
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
FEATS = {"N0": T.U2, "N1": T.U2 + F1, "N2": T.U2 + F2}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def headroom(g: pd.DataFrame, col: str) -> dict:
    """Best accuracy over all cuts meeting R6 (None if no cut does): is the ordering good enough for R6 at all?"""
    best = None
    for c in sorted(set(g[col].round(9))):
        tp = int(((g[col] >= c) & (g["y"] == 1)).sum())
        fp = int(((g[col] >= c) & (g["y"] == 0)).sum())
        if tp / g["y"].sum() >= .6 and tp / max(1, tp + fp) >= .6:
            acc = float(((g[col] >= c).astype(int) == g["y"]).mean())
            if best is None or acc > best["accuracy"]:
                best = {"cut": float(c), "tp": tp, "fp": fp, "accuracy": acc}
    return {"r6_feasible_cut": best, "auc": M.auc(g["y"], g[col])}


def brier(y, p) -> float:
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def main():
    proto = T.LT / "PROTOCOL_LEAD2_TUNING.md"
    assert T.sha256(proto) == (T.HERE / "TUNING_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    S = pd.read_csv(T.DATA / "stack_v5.csv", dtype={"province_code": str})
    R = pd.read_csv(T.OUT / "final_rows.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = R[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p"]].copy()
    E = E.merge(C[KEY + ["P0H4_p3", "P0_price"]].rename(columns={"P0H4_p3": "P0H4_p", "P0_price": "P0H4_price"}), on=KEY)
    origins = sorted(E["t"].unique())
    dev = E["q"] <= F.DEV_LAST
    cfgs = []
    # ------------------------------------------------------------ nested candidates
    for c, cols in FEATS.items():
        P = U.nested(S, cols, FN.DIRS, origins)
        E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": f"{c}_price", "cfg": f"{c}_cfg"}), on=KEY, how="left")
        assert E[f"{c}_price"].notna().all(), c
        E[f"{c}_p"] = E["pi_H_AB"] * E[f"{c}_price"]
        cfgs.append(P.drop_duplicates("t")[["t", "cfg"]].assign(candidate=c))
        log(c, "done")
    # ------------------------------------------------------------ G0: every configuration walk-forward, chosen on DEV
    A = U.all_configs(S, T.U2, FN.DIRS, origins)
    log("all configs done")
    A = E[KEY + ["q", "y", "pi_H_AB", "B0_p"]].merge(A, on=KEY)
    names = [U.cfg_id(s, k) for s in U.STRUCT for k in U.CKPT]
    D = A[A["q"] <= F.DEV_LAST]
    b0_l1 = brier(D.loc[D["lead"] == 1, "y"], D.loc[D["lead"] == 1, "B0_p"])
    rows = []
    for n in names:
        r = {"cfg": n}
        for k in (1, 2):
            g = D[D["lead"] == k]
            p = g["pi_H_AB"] * g[n]
            r[f"dev_L{k}_brier"] = brier(g["y"], p)
            r[f"dev_L{k}_recall"] = float(((p >= .5) & (g["y"] == 1)).sum() / g["y"].sum())
        rows.append(r)
    DC = pd.DataFrame(rows)
    sid = DC["cfg"].str.extract(r"s(\d+)\|k(\d+)").astype(int)
    st = pd.DataFrame(U.STRUCT).set_index("sid")
    for col in ("depth", "min_child", "ff", "l2", "cw"):
        DC[col] = st.loc[sid[0], col].to_numpy()
    DC["rounds"] = sid[1].to_numpy()
    DC.to_csv(T.OUT / "tune_dev_configs.csv", index=False, lineterminator="\n", float_format="%.6g")
    ok = DC[DC["dev_L1_brier"] <= b0_l1 + 0.005]
    g0 = ok.sort_values(["dev_L2_brier", "cfg"]).iloc[0]["cfg"]
    E = E.merge(A[KEY + [g0]].rename(columns={g0: "G0_price"}), on=KEY)
    E["G0_p"], E["G0_cfg"] = E["pi_H_AB"] * E["G0_price"], g0
    cfgs.append(pd.DataFrame({"t": origins, "cfg": g0, "candidate": "G0"}))
    # ------------------------------------------------------------ evaluation
    cands = ["P0H4", "B0", "N0", "N1", "N2", "G0"]
    res = {"protocol_sha256": T.sha256(proto), "G0_cfg": g0, "G0_struct": U.STRUCT[int(g0[1:].split("|")[0])],
           "cands": {c: FN.lead_eval(E, c) for c in cands}}
    for c in cands:
        for k, g in E.groupby("lead"):
            d = res["cands"][c]["leads"][int(k)]
            d["vs_P0H4"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["P0H4_p"] - g["y"]) ** 2)
            d["headroom"] = headroom(g, f"{c}_p")
            d["by_province"] = {NAMES[p]: {"acc": float(((h[f"{c}_p"] >= .5).astype(int) == h["y"]).mean()),
                                           "high": int(h["y"].sum()), "tp": int(((h[f"{c}_p"] >= .5) & (h["y"] == 1)).sum()),
                                           "fp": int(((h[f"{c}_p"] >= .5) & (h["y"] == 0)).sum())}
                                for p, h in g.groupby("province_code")}
    b = res["cands"]["B0"]["leads"]
    cand = ["N0", "N1", "N2", "G0"]
    elig = [c for c in cand if res["cands"][c]["leads"][1]["dev"]["brier"] <= b[1]["dev"]["brier"] + 0.005]
    strongest = min(elig, key=lambda c: (round(res["cands"][c]["leads"][2]["dev"]["brier"], 9), cand.index(c))) if elig else None
    rule = FN.adoption_rule(b, res["cands"][strongest]["leads"]) if strongest else {}
    if strongest == "G0":
        k2 = res["cands"]["G0"]["leads"][2]
        rule["G0_conf_brier_not_worse"] = k2["conf"]["brier"] <= b[2]["conf"]["brier"] + 1e-12
        rule["G0_conf_accuracy_not_lower"] = k2["conf"]["accuracy"] >= b[2]["conf"]["accuracy"] - 1e-12
    adopt = bool(rule) and all(rule.values())
    final = strongest if adopt else "B0"
    res["selection"] = {"eligible_1b": elig, "dev_L2_brier": {c: res["cands"][c]["leads"][2]["dev"]["brier"] for c in ["B0"] + cand},
                        "dev_L1_brier": {c: res["cands"][c]["leads"][1]["dev"]["brier"] for c in ["B0"] + cand},
                        "strongest": strongest, "rule": rule, "adopted": adopt, "FINAL": final,
                        "lead2_reliable": res["cands"][final]["leads"][2]["reliable"],
                        "lead2_failed": res["cands"][final]["leads"][2]["failed"],
                        "strongest_lead2_failed": res["cands"][strongest]["leads"][2]["failed"] if strongest else None,
                        "max_reliable_lead": res["cands"][final]["max_reliable_lead"]}
    # ------------------------------------------------------------ diagnostics (DEV only)
    piv = DC.assign(base=DC["cfg"].map(lambda n: n)).copy()
    piv["key"] = piv.apply(lambda r: (r["depth"], r["min_child"], r["ff"], r["l2"], r["rounds"]), axis=1)
    a, bb = piv[piv["cw"].isna()].set_index("key"), piv[piv["cw"] == "balanced"].set_index("key")
    j = a.join(bb, lsuffix="_none", rsuffix="_bal", how="inner")
    res["class_weight_dev"] = {"pairs": int(len(j)),
                               "mean_dev_L2_brier_none": float(j["dev_L2_brier_none"].mean()),
                               "mean_dev_L2_brier_balanced": float(j["dev_L2_brier_bal"].mean()),
                               "mean_dev_L2_recall_none": float(j["dev_L2_recall_none"].mean()),
                               "mean_dev_L2_recall_balanced": float(j["dev_L2_recall_bal"].mean()),
                               "share_balanced_higher_recall": float((j["dev_L2_recall_bal"] > j["dev_L2_recall_none"]).mean()),
                               "share_balanced_worse_brier": float((j["dev_L2_brier_bal"] > j["dev_L2_brier_none"]).mean())}
    res["dev_config_spread"] = {"L2_brier_min": float(DC["dev_L2_brier"].min()), "L2_brier_median": float(DC["dev_L2_brier"].median()),
                                "L2_brier_max": float(DC["dev_L2_brier"].max()), "L2_recall_max": float(DC["dev_L2_recall"].max()),
                                "B0_dev_L2_brier": b[2]["dev"]["brier"]}
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    L = E[KEY + ["q", "y"]].merge(lab[["province_code", "q", "m_food", "m_gap", "H"]], on=["province_code", "q"])
    L["real"] = L[["m_food", "m_gap"]].max(axis=1)
    res["label_audit"] = {int(k): {"rows": int(len(g)), "high": int(g["y"].sum()), "high_share": float(g["y"].mean()),
                                   "price_margin_within_0.10": int((g["real"].abs() <= .10).sum()),
                                   "price_margin_within_0.50": int((g["real"].abs() < .50).sum())}
                          for k, g in L.groupby("lead")}
    pd.concat(cfgs).to_csv(T.OUT / "tune_configs.csv", index=False, lineterminator="\n")
    E.to_csv(T.OUT / "tune_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("tune.json").write_text(json.dumps(res, indent=1, default=float))
    for c in cands:
        print(c, "max reliable lead", res["cands"][c]["max_reliable_lead"])
        for k in (1, 2):
            d = res["cands"][c]["leads"][k]
            m = d["metrics"]
            print(f"  L{k} acc {m['accuracy']:.3f} {[round(x, 2) for x in d['acc_ci90']]} bal {m['balanced_accuracy']:.3f} "
                  f"P {m['precision']:.3f} R {m['recall']:.3f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} Br {m['brier']:.4f} "
                  f"vsB0 {d['vs_B0']['diff']:+.4f} vsP0H4 {d['vs_P0H4']['diff']:+.4f} devBr {d['dev']['brier']:.4f} "
                  f"conf acc {d['conf']['accuracy']:.3f} confBr {d['conf']['brier']:.4f} thirds {[round(x, 2) for x in d['acc_thirds']]} "
                  f"loqo {d['loqo_min']:.3f} AUC {d['headroom']['auc']:.3f} R6cut {d['headroom']['r6_feasible_cut']} fail {d['failed']}")
    print(json.dumps(res["selection"], indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("G0_cfg", "G0_struct", "class_weight_dev", "dev_config_spread", "label_audit")}, indent=1, default=float))


if __name__ == "__main__":
    sys.exit(main())
