"""E57 step 2 (PROTOCOL sections 3-5): score the SEALED rolling-origin forecasts against the observed T43 labels.

    backend/venv/Scripts/python.exe -B runner/e57_score.py  -> runs/<UTC stamp>/{rows.csv, results.json}, tables/*.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E57 = Path(__file__).resolve().parents[1]
EXP = E57.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
SEALED = E57 / "sealed" / "predictions.csv"
P56 = EXP / "E56_LightGBM_Optimization" / "runs" / "20261018T132444Z" / "predictions.csv"
P55 = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "20261017T153947Z" / "predictions.csv"
P38 = EXP / "E38_Lead2_Diagnosis_Tuning" / "runs" / "20261015T033922Z" / "predictions.csv"
MODELS = ["E56", "E55", "PERSIST", "MAJORITY", "CLIM", "PROVCLIM"]
EARLY = ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2"]


def verify():
    want = (E57 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((E57 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    seal = (E57 / "sealed" / "predictions.csv.sha256").read_text().split()[0]
    if hashlib.sha256(SEALED.read_bytes()).hexdigest() != seal:
        raise SystemExit("sealed predictions changed")


def m(y, yhat, p):
    y, yhat, p = np.asarray(y, int), np.asarray(yhat, int), np.asarray(p, float)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    div = lambda a, b: a / b if b else None  # noqa: E731
    rh, rl = div(tp, tp + fn), div(tn, tn + fp)
    from sklearn.metrics import roc_auc_score
    return {"n": int(len(y)), "actual_HIGH": int(y.sum()), "actual_LOW": int((y == 0).sum()),
            "pred_HIGH": int(yhat.sum()), "pred_LOW": int((yhat == 0).sum()), "correct": tp + tn, "incorrect": fp + fn,
            "accuracy": (tp + tn) / len(y), "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2,
            "recall_HIGH": rh, "precision_HIGH": div(tp, tp + fp), "recall_LOW": rl, "precision_LOW": div(tn, tn + fn),
            "f1_HIGH": (2 * tp / (2 * tp + fp + fn)) if tp else (0.0 if fp + fn else None),
            "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "TP": tp, "TN": tn, "FP": fp, "FN": fn}


def boot(R, a, kind, B=2000, seed=57):
    rng = np.random.default_rng(seed)
    qs = sorted(R["target"].unique())
    acc_q = {q: (R[R["target"] == q][f"{a}_yhat"] == R[R["target"] == q]["y"]).to_numpy() for q in qs}
    vals = []
    for _ in range(B):
        if kind == "cluster":
            pick = rng.choice(qs, len(qs))
        else:                                   # moving-block bootstrap of consecutive quarters, block 2
            starts = rng.integers(0, len(qs) - 1, size=int(np.ceil(len(qs) / 2)))
            pick = [qs[s + j] for s in starts for j in (0, 1)][:len(qs)]
        vals.append(float(np.mean(np.concatenate([acc_q[q] for q in pick]))))
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def main():
    verify()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = E57 / "runs" / stamp
    out.mkdir(parents=True)
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    d = L.load()
    Y = F.t43_labels(d)
    lab = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["T43"]) if v == v}
    Hq = pd.read_csv(L.SWS_FILE).assign(q=lambda f: f["quarter"].map(L.qi)).groupby("q")["H"].mean()
    S["y"] = [lab[(p, t + 2)] for p, t in zip(S["province_code"], S["t"])]
    # reproduction of the committed E56 forecasts (PROTOCOL 2.5)
    p56 = pd.read_csv(P56, dtype={"province_code": str}).set_index(["t", "province_code"])["p"]
    repro = float(np.max(np.abs(S["E56_p"].to_numpy() - np.array([p56.loc[(t, p)] for t, p in zip(S["t"], S["province_code"])]))))
    p55 = pd.read_csv(P55, dtype={"province_code": str})
    p55 = p55[p55["arm"] == "E55-LGBM"].set_index(["t", "province_code"])["p"]
    S["E55_p"] = [float(p55.loc[(t, p)]) for t, p in zip(S["t"], S["province_code"])]
    for a in MODELS:
        S[f"{a}_yhat"] = (S[f"{a}_p"] >= 0.5).astype(int)
    p38 = pd.read_csv(P38, dtype={"province_code": str})
    p38 = p38[p38["arm"] == "E38-LGBM"].set_index(["target_quarter", "province_code"])
    S["E38_p"] = [float(p38.loc[(q, p), "p"]) if (q, p) in p38.index else np.nan for q, p in zip(S["target"], S["province_code"])]
    S["E38_thr"] = [float(p38.loc[(q, p), "threshold"]) if (q, p) in p38.index else np.nan for q, p in zip(S["target"], S["province_code"])]
    S["E38_yhat"] = (S["E38_p"] >= S["E38_thr"]).astype(int)
    # strata (outcomes used only to group rows)
    last_q = {t: g["PERSIST_from"].iloc[0] for t, g in S.groupby("t")}
    hi_target = S.groupby("target")["y"].sum()
    hi_last = {q: sum(lab.get((p, L.qi(q)), 0) for p in L.PROVS) for q in set(last_q.values())}
    S["stress_direction"] = [("rising" if hi_target[q] > hi_last[last_q[t]] else "falling" if hi_target[q] < hi_last[last_q[t]]
                              else "stable") for q, t in zip(S["target"], S["t"])]
    S["hunger_direction"] = ["up" if Hq[t + 2] > h else "down" for t, h in zip(S["t"], S["H_last_known"])]
    S["period"] = np.where(S["target"].isin(EARLY), "early (2024-Q2..2025-Q2)", "late (2025-Q3..2026-Q3)")
    S.to_csv(out / "rows.csv", index=False, float_format="%.12g")

    pooled = {a: m(S["y"], S[f"{a}_yhat"], S[f"{a}_p"]) for a in MODELS}
    for a in MODELS:
        pooled[a]["acc_ci_cluster"] = boot(S, a, "cluster")
        pooled[a]["acc_ci_block2"] = boot(S, a, "block")
    s38 = S[S["E38_p"].notna()]
    pooled["E38 (Eq.3 target, non-equivalent)"] = m(s38["y"], s38["E38_yhat"], s38["E38_p"]) | {
        "rows_note": f"{len(s38)} rows; no E38 forecast for 2025-Q2/Q3"}
    qrows = []
    for q, g in S.groupby("target"):
        r = {"issue_quarter": g["origin_quarter"].iloc[0], "issue_date": g["issue_date"].iloc[0], "target": q}
        for a in ("E56", "PERSIST", "MAJORITY", "E55"):
            mm = m(g["y"], g[f"{a}_yhat"], g[f"{a}_p"])
            if a == "E56":
                r.update({k: mm[k] for k in ("n", "actual_HIGH", "actual_LOW", "pred_HIGH", "pred_LOW", "correct", "incorrect",
                                             "accuracy", "balanced_accuracy", "precision_HIGH", "recall_HIGH",
                                             "precision_LOW", "recall_LOW", "brier", "auc")})
            else:
                r[f"{a}_accuracy"], r[f"{a}_brier"] = mm["accuracy"], mm["brier"]
        r["E56_config"] = int(g["E56_config"].iloc[0])
        r["data_status"] = ("OFW remittances missing at issue" if g["ofw_inputs_missing"].any() else "complete") + \
            ("; poverty (POV-AS) in selected config" if g["E56_pov_in_config"].any() else "")
        r["stress_direction"], r["hunger_direction"] = g["stress_direction"].iloc[0], g["hunger_direction"].iloc[0]
        qrows.append(r)
    Q = pd.DataFrame(qrows)
    qa = Q["accuracy"]
    qsum = {"quarters": int(len(Q)), "mean": float(qa.mean()), "median": float(qa.median()), "min": float(qa.min()),
            "max": float(qa.max()), "quarters_ge_0.75": int((qa >= 0.75).sum()), "share_ge_0.75": float((qa >= 0.75).mean()),
            "worst_quarters": Q.nsmallest(3, "accuracy")[["target", "accuracy"]].to_dict("records")}
    strata = {}
    for col in ("province", "period", "stress_direction", "hunger_direction"):
        strata[col] = {str(k): {a: m(g["y"], g[f"{a}_yhat"], g[f"{a}_p"]) for a in ("E56", "PERSIST", "MAJORITY")}
                       for k, g in S.groupby(col)}
    cal = E.calibration(S["y"], S["E56_p"])
    consist = {}
    for b in ("PERSIST", "MAJORITY", "CLIM", "E55"):
        wins = losses = ties = 0
        for _, g in S.groupby("target"):
            d56, db = np.mean((g["E56_p"] - g["y"]) ** 2), np.mean((g[f"{b}_p"] - g["y"]) ** 2)
            wins += d56 < db - 1e-12
            losses += d56 > db + 1e-12
            ties += abs(d56 - db) <= 1e-12
        from scipy.stats import binomtest
        n = wins + losses
        pb = E.paired_brier(S, "E56", b, seed=57)
        consist[b] = {"quarters_E56_better_brier": int(wins), "quarters_worse": int(losses), "ties": int(ties),
                      "sign_test_p": float(binomtest(wins, n, 0.5).pvalue) if n else None, "paired_brier": pb}
    # province discrimination
    spread = {}
    for a in ("E56", "PROVCLIM", "E55", "PERSIST"):
        S2 = S.rename(columns={f"{a}_p": "X_p", f"{a}_yhat": "X_yhat"})
        sp = G.province_spread(S2[["target", "y", "X_p", "X_yhat"]], "X")
        rhos = []
        for _, g in S.groupby("target"):
            if g["y"].nunique() == 2 and g[f"{a}_p"].nunique() > 1:
                from scipy.stats import spearmanr
                rhos.append(float(spearmanr(g[f"{a}_p"], g["y"]).correlation))
        sp["mean_spearman_p_vs_outcome"] = float(np.mean(rhos)) if rhos else None
        sp["quarters_all_same_decision"] = int(sp["quarters"] - sp["quarters_with_mixed_decisions"])
        spread[a] = sp
    ranks = S.pivot_table(index="target", columns="province", values="E56_p").rank(axis=1)
    k, n = ranks.shape
    Rj = ranks.sum(axis=0)
    W = float(12 * ((Rj - Rj.mean()) ** 2).sum() / (k ** 2 * (n ** 3 - n)))
    prov = S.groupby("province").agg(mean_p=("E56_p", "mean"), observed_HIGH_share=("y", "mean"),
                                     times_ranked_highest=("E56_p", lambda s: 0)).reset_index()
    top = S.loc[S.groupby("target")["E56_p"].idxmax(), "province"].value_counts()
    prov["times_ranked_highest"] = prov["province"].map(top).fillna(0).astype(int)
    pooled_e56 = pooled["E56"]
    reliable = {"pooled_acc_ge_0.75": pooled_e56["accuracy"] >= 0.75,
                "cluster_lower_bound_ge_0.75": pooled_e56["acc_ci_cluster"][0] >= 0.75,
                "share_quarters_ge_0.75_at_least_75pct": qsum["share_ge_0.75"] >= 0.75}
    res = {"run_utc": stamp, "sealed_sha256": hashlib.sha256(SEALED.read_bytes()).hexdigest(),
           "e56_reproduction_max_abs_diff": repro, "rows": int(len(S)), "quarters": int(S["target"].nunique()),
           "pooled": pooled, "quarter_summary": qsum, "strata": strata, "calibration_E56": cal,
           "consistency_vs_baselines": consist, "province_discrimination": spread,
           "province_rank_kendall_W": W, "province_table": prov.to_dict("records"),
           "reliability_rule": reliable, "reliable_for_future_forecasting": all(reliable.values())}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=float))
    tdir = E57 / "tables"
    tdir.mkdir(exist_ok=True)
    Q.round(4).to_csv(tdir / "quarter_by_quarter.csv", index=False)
    pd.DataFrame(pooled).T.round(4).to_csv(tdir / "pooled_models.csv")
    pd.DataFrame([{"stratum": c, "group": g, **{k2: v for k2, v in mm["E56"].items()}, "PERSIST_accuracy": mm["PERSIST"]["accuracy"],
                   "MAJORITY_accuracy": mm["MAJORITY"]["accuracy"]} for c, gg in strata.items() for g, mm in gg.items()]) \
        .round(4).to_csv(tdir / "strata.csv", index=False)
    prov.round(4).to_csv(tdir / "province_table.csv", index=False)
    print("reproduction max diff vs E56:", repro)
    print(Q[["issue_quarter", "target", "n", "actual_HIGH", "pred_HIGH", "correct", "accuracy", "balanced_accuracy",
             "brier", "auc", "PERSIST_accuracy", "MAJORITY_accuracy", "E55_accuracy", "stress_direction", "data_status"]]
          .round(3).to_string())
    for a, mm in pooled.items():
        print(f"  {a:36s} acc {mm['accuracy']:.3f} bal {mm['balanced_accuracy'] and round(mm['balanced_accuracy'], 3)} "
              f"recH {mm['recall_HIGH'] and round(mm['recall_HIGH'], 3)} recL {mm['recall_LOW'] and round(mm['recall_LOW'], 3)} "
              f"brier {mm['brier']:.3f} ci {[round(x, 2) for x in mm.get('acc_ci_cluster', [])]} {[round(x, 2) for x in mm.get('acc_ci_block2', [])]}")
    print("quarter summary", qsum)
    print("consistency", {b: (v["quarters_E56_better_brier"], v["quarters_worse"], round(v["sign_test_p"], 3) if v["sign_test_p"] is not None else None, [round(x, 3) for x in v["paired_brier"]["ci95"]]) for b, v in consist.items()})
    print("strata", {c: {g: round(v["E56"]["accuracy"], 3) for g, v in gg.items()} for c, gg in strata.items()})
    print("spread", {a: (v["within_quarter_auc"] and round(v["within_quarter_auc"], 3), v["quarters_all_same_decision"], v["mean_spearman_p_vs_outcome"] and round(v["mean_spearman_p_vs_outcome"], 3)) for a, v in spread.items()}, "W", round(W, 3))
    print(prov.round(3).to_string())
    print("calibration", round(cal["citl"], 3), round(cal["slope"], 3), "reliable", reliable)


if __name__ == "__main__":
    main()
