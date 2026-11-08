"""Lead-1 cross-quarter generalization (criteria: ../GENERALIZATION_CRITERIA.md, committed before this ran).
Run from backend/:  python ../aipheed-backend-aligned/experiments/Lead1_Objectives_Assessment/runner/quarter_generalization.py
Writes ../quarter_metrics.csv and ../generalization_results.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E83_Deep_Reconstruction" / "runner"))
import e83_lib as E  # noqa: E402

L, np, pd = E.L, E.np, E.pd
from scipy.stats import binomtest  # noqa: E402

E84P = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z" / "predictions_k1.csv"
E88P = EXP / "E88_Accuracy_Optimization" / "runs"
ARMS = {"S-SIM": "S-SIM", "LightGBM": "M-GB-ALL", "HYB-GBA-SIM": "HYB-GBA-SIM", "ENS-ROLL": "S-ENS-ROLL",
        "Persistence": "B-PERSIST", "PSA-only": "B-PSA", "NLP-only": "B-NLP", "LogReg": "M-LR-ALL",
        "Climatology": "B-CLIM", "Always-LOW": "B-AL"}
EARLY = set(f"{y}-Q{q}" for y in (2023, 2024) for q in (1, 2, 3, 4))


def qmetrics(y, p):
    ok = p.notna()
    y, yh = y[ok].astype(int), (p[ok] >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n = len(y)
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    return {"n": n, "correct": tp + tn, "wrong": fp + fn, "actual_high": int(y.sum()), "pred_high": int(yh.sum()),
            "TP": tp, "TN": tn, "FP": fp, "FN": fn, "accuracy": (tp + tn) / n if n else None,
            "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "precision_high": prec, "recall_high": rec,
            "f1_high": 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if tp + fn else None),
            "brier": float(np.mean((p[ok] - y) ** 2)) if n else None}


def block_bootstrap(P, col, fn, B=2000, seed=7):
    rng = np.random.default_rng(seed)
    qs = P["target_q"].unique()
    g = {q: P[P["target_q"] == q] for q in qs}
    vals = []
    for _ in range(B):
        S = pd.concat([g[q] for q in rng.choice(qs, len(qs))])
        v = fn(S, col)
        if v is not None and np.isfinite(v):
            vals.append(v)
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def acc(S, col):
    ok = S[col].notna()
    return float(((S.loc[ok, col] >= 0.5).astype(int) == S.loc[ok, "y"]).mean()) if ok.any() else None


def main():
    d, _ = E.data()
    P = pd.read_csv(E84P, dtype={"province_code": str})
    P["HYB-GBA-SIM"] = P["NA-GB"].fillna(P["S-SIM"])
    e88 = sorted(E88P.glob("*/predictions_k1.csv"))[-1]
    P = P.merge(pd.read_csv(e88, dtype={"province_code": str})[["t", "province_code", "S-ENS-ROLL"]], on=["t", "province_code"])
    # labels: price condition and regional hunger, to show what the label measures in each quarter
    lab = E.labels_all(d)
    th = L.e40_spec()
    lab["price_hi"] = ((lab["F"] > lab["province_code"].map(th["food"])) | ((lab["F"] - lab["HL"]) > lab["province_code"].map(th["gap"]))).astype(int)
    lab["target_q"] = lab["q"].map(L.qs)
    P = P.merge(lab[["province_code", "target_q", "H", "price_hi"]], on=["province_code", "target_q"])
    rows = []
    for q, G in P.groupby("target_q", sort=True):
        for name, col in ARMS.items():
            m = qmetrics(G["y"], G[col])
            rows.append({"target_q": q, "period": "early" if q in EARLY else "late", "model": name,
                         "regional_hunger": float(G["H"].iloc[0]), "hunger_above_11_3": bool(G["H"].iloc[0] > 11.3),
                         "label_equals_price_condition": float((G["y"] == G["price_hi"]).mean()),
                         "issued": int(G[col].notna().sum()), **m})
    Q = pd.DataFrame(rows)
    Q.to_csv(HERE.parent / "quarter_metrics.csv", index=False)

    out = {"pooled": {}, "periods": {}, "changing_risk": {}, "vs_persistence": {}, "bootstrap_acc_ci95_by_quarter": {},
           "repeat_previous_label": {}, "regional_hunger_component": {}}
    for name, col in ARMS.items():
        ok = P[col].notna()
        out["pooled"][name] = qmetrics(P.loc[ok, "y"], P.loc[ok, col]) | {"issued": int(ok.sum())}
        out["bootstrap_acc_ci95_by_quarter"][name] = block_bootstrap(P[ok], col, acc)
        for per in ("early", "late"):
            S = P[ok & P["target_q"].map(lambda q: (q in EARLY) == (per == "early"))]
            out["periods"].setdefault(name, {})[per] = qmetrics(S["y"], S[col]) if len(S) else None
        known = P["B-PERSIST"]
        for kind, mask in (("rising", (known == 0) & (P["y"] == 1)), ("falling", (known == 1) & (P["y"] == 0)),
                           ("stable", known == P["y"])):
            S = P[mask & ok]
            out["changing_risk"].setdefault(name, {})[kind] = {"n": int(len(S)), "accuracy": acc(S, col) if len(S) else None}
        same = ((P.loc[ok, col] >= 0.5).astype(int) == P.loc[ok, "B-PERSIST"]).mean()
        out["repeat_previous_label"][name] = round(float(same), 3)
    # quarter-by-quarter vs persistence (S-SIM primary; also LightGBM on its quarters)
    for name in ("S-SIM", "LightGBM", "ENS-ROLL", "HYB-GBA-SIM"):
        a = Q[Q["model"] == name].set_index("target_q")
        b = Q[Q["model"] == "Persistence"].set_index("target_q")
        common = [q for q in a.index if a.loc[q, "issued"] > 0]
        diff = [(a.loc[q, "accuracy"] - b.loc[q, "accuracy"]) for q in common]
        wins, losses = sum(x > 0 for x in diff), sum(x < 0 for x in diff)
        out["vs_persistence"][name] = {"quarters": len(common), "wins": wins, "losses": losses, "ties": len(common) - wins - losses,
                                       "sign_test_p_one_sided": binomtest(wins, wins + losses, 0.5, alternative="greater").pvalue if wins + losses else None}
    # independent outcome: regional hunger above 11.3% (one value per quarter) vs the S-SIM hunger component
    X = pd.read_csv(E84P.parent / "features_k1.csv", dtype={"province_code": str})
    hc = X.groupby("t")["sim_p_hunger"].first()
    R = P.drop_duplicates("target_q")[["t", "target_q", "H"]].copy()
    R["p_hunger"] = R["t"].map(hc)
    R["obs"] = (R["H"] > 11.3).astype(int)
    hq = L.h_quarters(d)
    R["persist"] = [int(float(L.h_quarters(d.cut(int(t))).sort_values("q")["H"].iloc[-1]) > 11.3) for t in R["t"]]
    out["regional_hunger_component"] = {
        "quarters": int(len(R)), "observed_above_11_3": int(R["obs"].sum()),
        "S-SIM_hunger_part_accuracy": float(((R["p_hunger"] >= 0.5).astype(int) == R["obs"]).mean()),
        "persistence_accuracy": float((R["persist"] == R["obs"]).mean()),
        "always_above_accuracy": float(R["obs"].mean()),
        "by_quarter": R[["target_q", "H", "obs", "p_hunger", "persist"]].round(3).to_dict("records")}
    # verdict for S-SIM under the pre-set rules
    s = Q[Q["model"] == "S-SIM"]
    a_share = float((s["accuracy"] >= 0.6).mean())
    per = out["periods"]["S-SIM"]
    vp = out["vs_persistence"]["S-SIM"]
    pooled = out["pooled"]["S-SIM"]
    caught = {k: (v["TP"] > 0 if v and v["actual_high"] else None) for k, v in per.items()}
    ch = out["changing_risk"]["S-SIM"]
    chg_n = ch["rising"]["n"] + ch["falling"]["n"]
    chg_acc = ((ch["rising"]["accuracy"] or 0) * ch["rising"]["n"] + (ch["falling"]["accuracy"] or 0) * ch["falling"]["n"]) / chg_n if chg_n else None
    crit = {"a_majority_quarters_share": round(a_share, 3), "a_pass_80": a_share >= 0.8,
            "b_early_acc": per["early"]["accuracy"], "b_late_acc": per["late"]["accuracy"],
            "b_pass": per["early"]["accuracy"] >= 0.75 and per["late"]["accuracy"] >= 0.75,
            "c_wins_losses": [vp["wins"], vp["losses"]], "c_p": vp["sign_test_p_one_sided"],
            "c_pass": vp["wins"] > vp["losses"] and (vp["sign_test_p_one_sided"] or 1) < 0.10,
            "d_recall_pooled": pooled["recall_high"], "d_caught_each_period": caught,
            "d_pass": (pooled["recall_high"] or 0) >= 0.5 and all(v in (True, None) for v in caught.values()),
            "e_changing_rows": chg_n, "e_accuracy": chg_acc, "e_pass": chg_acc is not None and chg_acc >= 0.5}
    allp = crit["a_pass_80"] and crit["b_pass"] and crit["c_pass"] and crit["d_pass"] and crit["e_pass"]
    crit["verdict"] = ("Consistent across quarters" if allp else
                       "Partially generalized" if a_share >= 0.6 else "Not demonstrated to generalize")
    out["S-SIM_verdict"] = crit
    (HERE.parent / "generalization_results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 250)
    show = Q[Q["model"].isin(["S-SIM", "LightGBM", "ENS-ROLL", "Persistence", "PSA-only", "Always-LOW"])]
    print(show.pivot_table(index=["target_q", "regional_hunger", "label_equals_price_condition"], columns="model",
                           values="accuracy").round(2).to_string())
    print(Q[Q.model == "S-SIM"][["target_q", "n", "correct", "actual_high", "pred_high", "TP", "FP", "FN", "recall_high", "precision_high"]].to_string(index=False))
    print(json.dumps({k: out[k] for k in ("vs_persistence", "repeat_previous_label", "changing_risk", "bootstrap_acc_ci95_by_quarter")}, default=float))
    print(json.dumps(out["periods"]["S-SIM"], default=float))
    print(json.dumps({k: v for k, v in out["regional_hunger_component"].items() if k != "by_quarter"}, default=float))
    print(json.dumps(crit, default=float))


if __name__ == "__main__":
    main()
