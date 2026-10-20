"""E67 r3 (PROTOCOL 2 effect rule, 4 goal test): every reading and baseline on the same 50 Lead-2 rows, the
pre-registered G1-G5 goal test, the trigger-group effect rule (paired Brier vs A0, Holm), uncertainty, confusion
matrices and per-quarter / per-province results.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4/runner/r3_goal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e67_lib as K  # noqa: E402

H, L, np, pd = K.H, K.L, K.np, K.pd
from scipy.stats import binomtest  # noqa: E402

ROWS50 = K.EXP / "E66_Best_Methodology_Review" / "tables" / "r1_rows50_all_arms.csv"
# G4 coding, frozen in PROTOCOL section 4
G4 = {"E56": "partial", "EW": "no", "BPROJ": "no", "A0": "partial", "X_climate": "partial", "X_fish": "partial",
      "X_employment": "partial", "X_ofw": "partial", "X_news": "partial", "M_only": "partial",
      "PERSIST": "yes (baseline)", "MAJORITY": "yes (baseline)", "CLIM": "yes (baseline)", "PROVCLIM": "yes (baseline)"}
SEED, NB = 67, 2000


def cluster_acc(R, dec, ref_dec=None):
    """Quarter-cluster bootstrap 95% CI of accuracy (or of accuracy minus a reference decision's accuracy)."""
    y = R["HIGH"].to_numpy(int)
    c = (R[dec].to_numpy(int) == y).astype(float)
    if ref_dec is not None:
        c = c - (R[ref_dec].to_numpy(int) == y).astype(float)
    s = pd.Series(c, index=R.index).groupby(R["target"])
    sums, ns = s.sum(), s.size()
    qs = sums.index.to_numpy()
    rng = np.random.default_rng(SEED)
    b = []
    for _ in range(NB):
        pick = rng.choice(qs, len(qs))
        b.append(float(sums[pick].sum() / ns[pick].sum()))
    return float(np.quantile(b, .025)), float(np.quantile(b, .975))


def mcnemar(R, dec, ref_dec):
    y = R["HIGH"].to_numpy(int)
    a, b = R[dec].to_numpy(int) == y, R[ref_dec].to_numpy(int) == y
    n01, n10 = int((a & ~b).sum()), int((~a & b).sum())
    p = binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return n01, n10, float(p)


def main():
    K.verify_protocol()
    W = pd.read_csv(ROWS50, dtype={"province_code": str})
    A = pd.read_csv(K.TABLES / "r1_ablation_predictions.csv", dtype={"province_code": str})
    ev = A[A["t"].isin(K.EVAL_ORIGINS)]
    for arm in K.ARMS:
        s = ev[ev["arm"] == arm][["t", "province_code", "p", "p_price"]].rename(
            columns={"p": f"{arm}_p", "p_price": f"{arm}_p_price"})
        W = W.merge(s, on=["t", "province_code"], how="left")
    assert len(W) == 50 and W[[f"{a}_p" for a in K.ARMS]].notna().all().all()
    assert float((W["A0_p"] - W["E56_p"]).abs().max()) < 1e-6
    # decisions: p >= 0.5, except EW (sealed E58 decision) whose decision column is EW_dec
    W["HIGH"] = W["T43"].astype(int)
    probs = {"E56": "E56_p", "EW": "EW_p", "BPROJ": "BPROJ_p", **{a: f"{a}_p" for a in K.ARMS},
             "PERSIST": "PERSIST_p", "MAJORITY": "MAJORITY_p", "CLIM": "CLIM_p", "PROVCLIM": "PROVCLIM_p"}
    for k, col in probs.items():
        W[f"{k}_dec"] = W["EW_dec"].astype(int) if k == "EW" else (W[col] >= 0.5).astype(int)
    out, conf = [], []
    for k, col in probs.items():
        m = H.metrics(W, col, "HIGH", dec=f"{k}_dec")
        mp = H.metrics(W.assign(HIGH=W["PS"].astype(int)), col, "HIGH", dec=f"{k}_dec")
        lo, hi = cluster_acc(W, f"{k}_dec")
        dmaj = cluster_acc(W, f"{k}_dec", "MAJORITY_dec")
        dper = cluster_acc(W, f"{k}_dec", "PERSIST_dec")
        mc_maj, mc_per = mcnemar(W, f"{k}_dec", "MAJORITY_dec"), mcnemar(W, f"{k}_dec", "PERSIST_dec")
        g1 = m["accuracy"] > 0.75
        g2 = m["balanced_accuracy"] >= 0.70 and m["recall_HIGH"] >= 0.60 and m["recall_LOW"] >= 0.60
        g3 = dmaj[0] > 0 and dper[0] > 0
        g4 = G4[k]
        verdict = ("baseline" if "baseline" in g4 else
                   "GOAL MET on development rows (all G1-G5)" if (g1 and g2 and g3 and g4 == "yes") else
                   "above 75% on development rows only; not a legitimate demonstration" if (g1 and g2 and g3) else
                   "goal not met")
        y = W["HIGH"].to_numpy(int)
        yh = W[f"{k}_dec"].to_numpy(int)
        conf.append({"reading": k, "TP": int(((yh == 1) & (y == 1)).sum()), "FP": int(((yh == 1) & (y == 0)).sum()),
                     "FN": int(((yh == 0) & (y == 1)).sum()), "TN": int(((yh == 0) & (y == 0)).sum())})
        out.append({"reading": k, **{f"T43_{a}": v for a, v in m.items()},
                    "correct": int(round(m["accuracy"] * m["n"])), "acc_cluster_lo": lo, "acc_cluster_hi": hi,
                    "acc_minus_majority_lo": dmaj[0], "acc_minus_majority_hi": dmaj[1],
                    "acc_minus_persistence_lo": dper[0], "acc_minus_persistence_hi": dper[1],
                    "mcnemar_vs_majority_wins_losses_p": f"{mc_maj[0]}/{mc_maj[1]}/{mc_maj[2]:.3f}",
                    "mcnemar_vs_persistence_wins_losses_p": f"{mc_per[0]}/{mc_per[1]}/{mc_per[2]:.3f}",
                    "PS_accuracy": mp["accuracy"], "PS_balanced": mp["balanced_accuracy"], "PS_brier": mp["brier"],
                    "G1_acc_gt_075": g1, "G2_class_sensitive": g2, "G3_beats_trivial": g3, "G4_prespecified": g4,
                    "G5_target_T43": True, "verdict": verdict})
    M = pd.DataFrame(out)
    H.write_csv(M, K.TABLES / "r3_goal_test.csv")
    H.write_csv(pd.DataFrame(conf), K.TABLES / "r3_confusion.csv")
    # trigger-group effect rule: paired Brier of each ablation against A0 on T43, Holm over the six
    P = [H.paired(W, "A0_p", f"{a}_p", "HIGH", seed=67) for a in K.ARMS if a != "A0"]
    worse = [binomtest(p["quarter_losses"], p["quarter_wins"] + p["quarter_losses"], 0.5, alternative="greater").pvalue
             if p["quarter_wins"] + p["quarter_losses"] else 1.0 for p in P]
    hb, hw = H.holm([p["sign_p"] for p in P]), H.holm(worse)
    for p, a, b, w in zip(P, hb, hw, worse):
        p["sign_p_holm"] = a
        p["removal_worse_sign_p"] = float(w)
        p["removal_worse_sign_p_holm"] = b
        p["group_helps"] = bool(p["ci95_lo"] > 0 and b < 0.05)       # removing it is worse
        p["group_hurts"] = bool(p["ci95_hi"] < 0 and a < 0.05)       # removing it is better
        p["effect"] = "helps" if p["group_helps"] else "hurts" if p["group_hurts"] else "not distinguishable from zero"
    H.write_csv(pd.DataFrame(P), K.TABLES / "r3_trigger_group_effects.csv")
    # per quarter / province for the main readings
    bq = []
    for k in ("E56", "EW", "A0", "X_news", "M_only", "MAJORITY", "PERSIST"):
        for q, g in W.groupby("target"):
            bq.append({"reading": k, "target": q, "n": len(g), "HIGH": int(g["HIGH"].sum()),
                       "correct": int((g[f"{k}_dec"] == g["HIGH"]).sum())})
    H.write_csv(pd.DataFrame(bq), K.TABLES / "r3_by_quarter.csv")
    bp = []
    for k in ("E56", "EW", "A0", "MAJORITY", "PERSIST"):
        for pc, g in W.groupby("province_code"):
            bp.append({"reading": k, "province": L.NAMES[pc], "n": len(g), "HIGH": int(g["HIGH"].sum()),
                       "correct": int((g[f"{k}_dec"] == g["HIGH"]).sum()),
                       "brier": float(np.mean((g[probs[k]] - g["HIGH"]) ** 2))})
    H.write_csv(pd.DataFrame(bp), K.TABLES / "r3_by_province.csv")
    H.write_csv(W, K.TABLES / "r3_rows50.csv")
    H.dump({"protocol_sha256": K.verify_protocol(), "rows": 50, "T43_eq_PS_rows": int((W["T43"] == W["PS"]).sum()),
            "verdicts": dict(zip(M["reading"], M["verdict"])),
            "trigger_effects": {p["arm"]: p["effect"] for p in P}}, K.OUT / "r3_goal.json")
    cols = ["reading", "correct", "T43_accuracy", "acc_cluster_lo", "acc_cluster_hi", "T43_balanced_accuracy",
            "T43_recall_HIGH", "T43_recall_LOW", "T43_precision_HIGH", "T43_f1_HIGH", "T43_brier", "T43_auc",
            "T43_false_alarms", "T43_missed_HIGH", "T43_onsets_detected", "acc_minus_majority_lo",
            "acc_minus_persistence_lo", "verdict"]
    pd.set_option("display.width", 300)
    print(M[cols].round(3).to_string())
    print(pd.DataFrame(P)[["arm", "mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "effect"]].round(4).to_string())


if __name__ == "__main__":
    main()
