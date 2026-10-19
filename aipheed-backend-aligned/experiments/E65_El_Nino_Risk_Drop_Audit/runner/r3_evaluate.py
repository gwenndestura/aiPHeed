"""E65 r3 (PROTOCOL section 4): controlled rolling-origin comparison of the frozen E56 (A), climate corrected (B1),
official PAGASA status added (B3), both (B2), climate removed (C), a transparent PAGASA El Nino rule (D1), the CPI
projection-only baseline (D2), persistence and majority, on the 50 E57 rows; plus exploratory forward forecasts.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit/runner/r3_evaluate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e65_lib as H  # noqa: E402

L, np, pd = H.L, H.np, H.pd
from scipy.stats import binomtest  # noqa: E402

MODEL_ARMS = ["A", "B1", "B3", "B2", "C"]


def metrics(R: pd.DataFrame, col: str) -> dict:
    y, p = R["HIGH"].to_numpy(int), R[col].to_numpy(float)
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    on, rp = R["ONSET"] == 1, R["RISEP"] == 1
    q_acc = R.assign(c=(yh == y)).groupby("target")["c"].mean()
    return {"n": int(len(R)), "quarters": int(R["target"].nunique()), "HIGH": int(y.sum()),
            "accuracy": (tp + tn) / len(y), "accuracy_wilson95": H.wilson(tp + tn, len(y)),
            "balanced_accuracy": 0.5 * (tp / max(tp + fn, 1) + tn / max(tn + fp, 1)),
            "HIGH_recall": tp / max(tp + fn, 1), "LOW_recall": tn / max(tn + fp, 1),
            "false_alarms": fp, "missed_HIGH": fn, "brier": float(np.mean((p - y) ** 2)),
            "onsets_detected": f"{int((yh[on] == 1).sum())}/{int(on.sum())}",
            "rising_detected": f"{int((yh[rp] == 1).sum())}/{int(rp.sum())}",
            "quarters_acc_ge_0.75": int((q_acc >= 0.75).sum())}


def paired(R: pd.DataFrame, a: str, b: str, n_boot=2000, seed=65) -> dict:
    """Brier(b) - Brier(a): quarter-cluster bootstrap CI and quarter sign test of Brier wins of b over a."""
    y = R["HIGH"].to_numpy(float)
    d = (R[b] - y) ** 2 - (R[a] - y) ** 2
    dq = d.groupby(R["target"]).mean()
    rng = np.random.default_rng(seed)
    qs = dq.index.to_numpy()
    nq = R.groupby("target").size()
    boots = []
    for _ in range(n_boot):
        pick = rng.choice(qs, len(qs))
        boots.append(float((dq[pick] * nq[pick]).sum() / nq[pick].sum()))
    wins, losses = int((dq < -1e-12).sum()), int((dq > 1e-12).sum())
    p = binomtest(wins, wins + losses, 0.5, alternative="greater").pvalue if wins + losses else 1.0
    lo, hi = float(np.quantile(boots, .025)), float(np.quantile(boots, .975))
    return {"arm": b, "vs": a, "mean_diff": float(d.mean()), "ci95": [lo, hi], "quarter_wins": wins,
            "quarter_losses": losses, "quarter_ties": int(len(dq) - wins - losses), "sign_test_p": float(p),
            "rows_decision_changed": int(((R[a] >= .5) != (R[b] >= .5)).sum()),
            "improves_by_rule": bool(hi < 0 and p < 0.05)}


def main():
    H.verify_protocol()
    sealed = H.verify_sealed()
    d, X, B = H.E.load()
    X = H.add_climate_variants(X)
    space = H.G.search_space()
    runs = {a: pd.DataFrame(H.run_arm(d, X, B, a, H.EVAL_ORIGINS + H.FORWARD_ORIGINS, space)) for a in MODEL_ARMS}
    allp = pd.concat(runs.values())
    H.write_csv(allp, H.TABLES / "r3_arm_predictions.csv")

    R = H.rows50()
    for a, df in runs.items():
        R = R.merge(df[["t", "province_code", "p", "p_price", "p_hunger", "config"]].rename(
            columns={"p": f"{a}_p", "p_price": f"{a}_p_price", "p_hunger": f"{a}_p_hunger", "config": f"{a}_config"}),
            on=["t", "province_code"], how="left")
    repro = float((R["A_p"] - R["E56_p"]).abs().max())
    if repro > 1e-6:
        raise SystemExit(f"arm A does not reproduce the sealed E56 forecasts (max diff {repro})")
    R["D1_p"] = R["t"].map(lambda t: 1.0 if H.official_status(t) >= 1 else 0.0)
    R["pagasa_status"] = R["t"].map(lambda t: H.PAGASA_STATUS[str(L.origin(t).date())][1])
    cols = {"A (frozen E56)": "A_p", "B1 ENSO intensity corrected": "B1_p", "B3 PAGASA status added": "B3_p",
            "B2 B1 + B3": "B2_p", "C climate removed": "C_p", "D1 PAGASA El Nino rule": "D1_p",
            "D2 CPI projection only": "BPROJ_p", "Persistence": "PERSIST_p", "Majority (as-of)": "MAJORITY_p"}
    M = pd.DataFrame([{"model": k, **metrics(R, v)} for k, v in cols.items()])
    H.write_csv(M, H.TABLES / "r3_metrics_50rows.csv")
    P = pd.DataFrame([paired(R, "A_p", v) for k, v in cols.items() if v != "A_p"])
    H.write_csv(P, H.TABLES / "r3_paired_vs_A.csv")
    H.write_csv(R, H.TABLES / "r3_rows50.csv")
    # El Nino-relevant rows: targets whose issue date had a PAGASA El Nino Alert/Advisory in force
    sub = R[R["D1_p"] == 1]
    Msub = pd.DataFrame([{"model": k, **metrics(sub, v)} for k, v in cols.items()]) if len(sub) else pd.DataFrame()
    H.write_csv(Msub, H.TABLES / "r3_metrics_el_nino_issue_rows.csv")
    # forward what-if forecasts
    fw = allp[allp["t"].isin(H.FORWARD_ORIGINS)].pivot_table(index=["target", "province"], columns="arm",
                                                            values=["p", "p_price", "p_hunger"]).round(4)
    fw.columns = [f"{a}_{v}" for v, a in fw.columns]
    fw = fw.reset_index()
    H.write_csv(fw, H.TABLES / "r3_forward_whatif.csv")
    # features each arm's selected model actually used at the 2027-Q1 origin
    use = {}
    with_models = {}
    for a in MODEL_ARMS:
        with H.arm_groups(a):
            fx = H.G.tuned_forecast(d, X, B, H.FORWARD_ORIGINS[-1], space)
        bst = fx["model"].model.booster_
        imp = dict(zip(bst.feature_name(), bst.feature_importance("split").tolist()))
        hm = fx["hc"]["model"]
        use[a] = {"config": int(fx["cfg"]["id"]), "price_splits": {k: v for k, v in imp.items() if v},
                  "hunger_alpha": fx["hc"]["alpha"], "hunger_cols": list(hm.cols) if hm is not None else [],
                  "H_hat": fx["H_hat"], "p_hunger": float(fx["p_hunger"])}
        with_models[a] = fx
    out = {"protocol_sha256": H.verify_protocol(), "sealed": sealed, "arm_A_reproduction_max_abs_diff": repro,
           "metrics": M.to_dict("records"), "paired_vs_A": P.to_dict("records"),
           "el_nino_issue_rows": Msub.to_dict("records") if len(Msub) else [],
           "forward_whatif": fw.to_dict("records"), "model_use_2027Q1_origin": use}
    H.dump(out, H.OUT / "r3_evaluation.json")
    pd.set_option("display.width", 250)
    print(M.to_string(index=False))
    print(P.to_string(index=False))
    print(fw.to_string(index=False))
    print({a: (u["config"], u["price_splits"]) for a, u in use.items()})


if __name__ == "__main__":
    main()
