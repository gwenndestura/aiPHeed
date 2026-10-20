"""E68 r3 (PROTOCOL 2, 3, 5): score the T43 arms (paired Brier vs A0, Holm; G1-G5) and the exploratory T-AFF arms on
their own labels against persistence / always-LOW / always-HIGH; then seal every arm's forward forecasts.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures/runner/r3_score.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e68_lib as R  # noqa: E402

H, L, E, F, np, pd = R.H, R.L, R.E, R.F, R.np, R.pd
sys.path.insert(0, str(R.EXP / "E67_Lead2_Best_Model_Objectives_1_4" / "runner"))
import r3_goal as GT  # noqa: E402   (E67 goal-test helpers: cluster_acc, mcnemar)

T43_ARMS = ["A0", "M1", "N1", "K1", "C1"]


def goal_row(W, k, col, dec, ycol="HIGH"):
    m = H.metrics(W, col, ycol, dec=dec)
    lo, hi = GT.cluster_acc(W.assign(HIGH=W[ycol]), dec)
    dmaj = GT.cluster_acc(W.assign(HIGH=W[ycol]), dec, "MAJ_dec")
    dper = GT.cluster_acc(W.assign(HIGH=W[ycol]), dec, "PER_dec")
    g1 = m["accuracy"] > 0.75
    g2 = m["balanced_accuracy"] >= 0.70 and m["recall_HIGH"] >= 0.60 and m["recall_LOW"] >= 0.60
    g3 = dmaj[0] > 0 and dper[0] > 0
    y, yh = W[ycol].to_numpy(int), W[dec].to_numpy(int)
    return {"reading": k, "label": ycol, **m, "correct": int((y == yh).sum()), "TP": int(((yh == 1) & (y == 1)).sum()),
            "FP": int(((yh == 1) & (y == 0)).sum()), "FN": int(((yh == 0) & (y == 1)).sum()),
            "TN": int(((yh == 0) & (y == 0)).sum()), "false_alarm_rate": float(((yh == 1) & (y == 0)).sum() / max((y == 0).sum(), 1)),
            "acc_cluster_lo": lo, "acc_cluster_hi": hi, "acc_minus_majority_lo": dmaj[0], "acc_minus_majority_hi": dmaj[1],
            "acc_minus_persistence_lo": dper[0], "acc_minus_persistence_hi": dper[1],
            "G1": g1, "G2": g2, "G3": g3, "G4": "partial" if k not in ("PERSIST", "MAJORITY", "ALWAYS_HIGH") else "baseline",
            "goal_met": bool(g1 and g2 and g3 and False)}      # G4 is never "yes" on examined rows (PROTOCOL 5)


def taff_rule(d, X, B):
    """TAFF-RULE: structural projection probability (m = 1.0, E58 B-PROJ form) with the headline channel."""
    out = []
    for t in R.EVAL_ORIGINS + R.FORWARD_ORIGINS:
        tr, te = F.frame(d, X, B, t, "AS")
        tr, te = R.to_taff(tr), R.to_taff(te)
        orig, spec = L.e40_spec, R.taff_spec()
        try:
            L.e40_spec = lambda: spec
            fit1 = tr.dropna(subset=["base_1.0", "gbase_1.0", "F_true", "G_true"])
            p = F._sig(F.struct_logit(te, 1.0, F.struct_scale(fit1, 1.0)))
        finally:
            L.e40_spec = orig
        for i, pc in enumerate(L.PROVS):
            out.append({"t": t, "province_code": pc, "TAFFRULE_p_price": float(p[i])})
    return pd.DataFrame(out)


def main():
    R.verify_protocol()
    d, X, B = E.load()
    A = pd.read_csv(R.TABLES / "r1_arm_predictions.csv", dtype={"province_code": str})
    W = pd.read_csv(R.EXP / "E66_Best_Methodology_Review" / "tables" / "r1_rows50_all_arms.csv", dtype={"province_code": str})
    S = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})[["t", "province_code", "PERSIST_from"]]
    W = W.merge(S, on=["t", "province_code"])
    # E66's own N1/N2 logistic-regression columns share a name with E68's N1 arm: drop them (they are E66 results)
    W = W.drop(columns=[c for c in W.columns if c.split("_")[0] in R.ARMS or c.startswith(("N2_",))])
    for a in R.ARMS:
        s = A[(A["arm"] == a) & A["t"].isin(R.EVAL_ORIGINS)][["t", "province_code", "p", "p_price", "p_hunger"]]
        W = W.merge(s.rename(columns={"p": f"{a}_p", "p_price": f"{a}_p_price", "p_hunger": f"{a}_p_hunger"}),
                    on=["t", "province_code"], how="left")
    assert len(W) == 50 and float((W["A0_p"] - W["E56_p"]).abs().max()) < 1e-6
    Y = R.labels(d).set_index(["province_code", "quarter"])
    W["TAFF"] = [Y.loc[(p, q), "TAFF"] for p, q in zip(W["province_code"], W["target"])]
    W["PER_TAFF"] = [Y.loc[(p, q), "TAFF"] if (p, q) in Y.index else np.nan for p, q in zip(W["province_code"], W["PERSIST_from"])]
    W = W.merge(taff_rule(d, X, B), on=["t", "province_code"], how="left")
    W["TAFFRULE_p"] = W["TAFFRULE_p_price"] * W["A0_p_hunger"]
    W["HIGH"] = W["T43"].astype(int)
    # ---- T43 arms
    W["MAJ_dec"], W["PER_dec"] = 0, (W["PERSIST_p"] >= 0.5).astype(int)
    rows = []
    for a in T43_ARMS:
        W[f"{a}_dec"] = (W[f"{a}_p"] >= 0.5).astype(int)
        rows.append(goal_row(W, a, f"{a}_p", f"{a}_dec"))
        W[f"{a}_ewdec"] = (W[f"{a}_p_price"] >= 0.5).astype(int)     # descriptive: the E58-EW reading of each arm
        rows.append(goal_row(W, f"{a}-EW", f"{a}_p_price", f"{a}_ewdec"))
    for k, col in (("PERSIST", "PERSIST_p"), ("MAJORITY", "MAJORITY_p")):
        W[f"{k}_dec"] = (W[col] >= 0.5).astype(int)
        rows.append(goal_row(W, k, col, f"{k}_dec"))
    T = pd.DataFrame(rows)
    P = [H.paired(W, "A0_p", f"{a}_p", "HIGH", seed=68) for a in T43_ARMS[1:]]
    adj = H.holm([p["sign_p"] for p in P])
    for p, a in zip(P, adj):
        g2_ref = T.set_index("reading").loc["A0"]
        g2 = T.set_index("reading").loc[p["arm"].replace("_p", "")]
        p["sign_p_holm"] = a
        p["better_than_A0_by_rule"] = bool(p["ci95_hi"] < 0 and a < 0.05 and g2["balanced_accuracy"] >= g2_ref["balanced_accuracy"])
    # K1 acts only at origins with El Nino in force: report those rows separately
    kin = pd.read_csv(R.TABLES / "r1_elnino_shift.csv")
    k_or = kin[(kin["arm"] == "K1") & kin["in_force"] & (kin["n_past_rows"] > 0)]["origin_quarter"].tolist()
    Wk = W[W["origin_quarter"].isin(k_or)]
    k1 = {"origins_with_shift": k_or, "rows": int(len(Wk)),
          "A0_brier": float(np.mean((Wk["A0_p"] - Wk["HIGH"]) ** 2)) if len(Wk) else None,
          "K1_brier": float(np.mean((Wk["K1_p"] - Wk["HIGH"]) ** 2)) if len(Wk) else None,
          "A0_correct": int(((Wk["A0_p"] >= .5) == Wk["HIGH"]).sum()), "K1_correct": int(((Wk["K1_p"] >= .5) == Wk["HIGH"]).sum())}
    # ---- T-AFF arms on their own labels
    V = W.copy()
    V["T"] = V["TAFF"].astype(int)
    V["MAJ_dec"] = 0
    V["PER_dec"] = V["PER_TAFF"].fillna(0).astype(int)
    V["PER_TAFF_p"] = V["PER_TAFF"].fillna(0).astype(float)
    V["ALWAYS_HIGH_p"], V["MAJORITY_TAFF_p"] = 1.0, 0.0
    trows = []
    for k, col in (("TAFF-LGBM", "TAFF_p"), ("TAFF-RULE", "TAFFRULE_p"), ("PERSIST", "PER_TAFF_p"),
                   ("MAJORITY", "MAJORITY_TAFF_p"), ("ALWAYS_HIGH", "ALWAYS_HIGH_p")):
        V[f"{k}_d"] = (V[col] >= 0.5).astype(int)
        trows.append(goal_row(V.assign(HIGH=V["T"]), k, col, f"{k}_d", "T"))
    TT = pd.DataFrame(trows)
    PT = [H.paired(V.assign(HIGH=V["T"]), "PER_TAFF_p", c, "HIGH", seed=68) for c in ("TAFF_p", "TAFFRULE_p")] + \
         [H.paired(V.assign(HIGH=V["T"]), "MAJORITY_TAFF_p", c, "HIGH", seed=68) for c in ("TAFF_p", "TAFFRULE_p")]
    H.write_csv(T, R.TABLES / "r3_t43_arms.csv")
    H.write_csv(pd.DataFrame(P), R.TABLES / "r3_t43_paired_vs_A0.csv")
    H.write_csv(TT, R.TABLES / "r3_taff_arms.csv")
    H.write_csv(pd.DataFrame(PT), R.TABLES / "r3_taff_paired_vs_baselines.csv")
    H.write_csv(W, R.TABLES / "r3_rows50.csv")
    # per quarter correct counts for the main readings
    bq = []
    for k, dec, y in (("A0", "A0_dec", "HIGH"), ("M1", "M1_dec", "HIGH"), ("C1", "C1_dec", "HIGH"),
                      ("TAFF-LGBM", "TAFF-LGBM_d", "T"), ("TAFF-RULE", "TAFF-RULE_d", "T")):
        src = V if y == "T" else W
        for q, g in src.groupby("target"):
            bq.append({"reading": k, "target": q, "HIGH": int(g[y].sum()), "correct": int((g[dec] == g[y]).sum())})
    H.write_csv(pd.DataFrame(bq), R.TABLES / "r3_by_quarter.csv")
    # ---- seal the forward forecasts of every arm (2026-Q4, 2027-Q1): the unseen evaluation period
    fwd = A[A["t"].isin(R.FORWARD_ORIGINS)][["arm", "origin_quarter", "issue_date", "target", "province_code", "p",
                                             "p_price", "p_hunger", "config"]].copy()
    tr_ = taff_rule(d, X, B)
    tr_ = tr_[tr_["t"].isin(R.FORWARD_ORIGINS)].assign(target=lambda f: f["t"].map(lambda t: L.qs(t + 2)))
    hun = A[(A["arm"] == "A0") & A["t"].isin(R.FORWARD_ORIGINS)][["t", "province_code", "p_hunger"]]
    tr_ = tr_.merge(hun, on=["t", "province_code"])
    fwd = pd.concat([fwd, pd.DataFrame({"arm": "TAFF-RULE", "origin_quarter": tr_["t"].map(L.qs),
                                        "issue_date": tr_["t"].map(R.issue_date), "target": tr_["target"],
                                        "province_code": tr_["province_code"], "p": tr_["TAFFRULE_p_price"] * tr_["p_hunger"],
                                        "p_price": tr_["TAFFRULE_p_price"], "p_hunger": tr_["p_hunger"], "config": -1})])
    fwd["label_to_score"] = np.where(fwd["arm"].str.startswith("TAFF"), "T-AFF", "T43")
    fwd["province"] = fwd["province_code"].map(L.NAMES)
    fwd = fwd.sort_values(["arm", "target", "province_code"]).reset_index(drop=True)
    seal = R.SEALED / "prospective.csv"
    if seal.exists():
        raise SystemExit("prospective seal already exists; never re-seal")
    H.write_csv(fwd, seal)
    (R.SEALED / "prospective.csv.sha256").write_text(hashlib.sha256(seal.read_bytes()).hexdigest() + "  prospective.csv\n")
    H.dump({"protocol_sha256": R.verify_protocol(), "k1_evaluation_rows": k1, "sealed_rows": int(len(fwd)),
            "sealed_sha256": hashlib.sha256(seal.read_bytes()).hexdigest(),
            "t43_better_than_A0": {p["arm"]: p["better_than_A0_by_rule"] for p in P}}, R.OUT / "r3_score.json")
    pd.set_option("display.width", 300)
    cols = ["reading", "label", "correct", "accuracy", "acc_cluster_lo", "acc_cluster_hi", "balanced_accuracy", "recall_HIGH",
            "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc", "false_alarms", "missed_HIGH", "onsets_detected",
            "acc_minus_majority_lo", "acc_minus_persistence_lo", "G1", "G2", "G3"]
    print(T[cols].round(3).to_string()); print(pd.DataFrame(P)[["arm", "mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins",
                                                              "quarter_losses", "sign_p_holm", "better_than_A0_by_rule"]].round(4).to_string())
    print(k1)
    print(TT[[c for c in cols if c in TT]].round(3).to_string())
    print(pd.DataFrame(PT)[["arm", "reference", "mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "quarter_losses", "sign_p"]].round(4).to_string())


if __name__ == "__main__":
    main()
