"""E64 step C2 (PROTOCOL sections 6-7): score the sealed candidates and the references on the 50 rows, apply the DEV-only
selection rule, test the frozen claims, and write every table.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/c2_score.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

sys.dont_write_bytecode = True
E64 = Path(__file__).resolve().parents[1]
EXP = E64.parent
sys.path.insert(0, str(E64 / "runner"))
SEALED = E64 / "sealed" / "candidates.csv"
S57 = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
S58 = EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv"
S60 = EXP / "E60_E58_Accuracy_Optimization" / "sealed" / "candidates.csv"
S61A = EXP / "E61_E58_Low_Forecast_Investigation" / "sealed" / "addendum1.csv"
EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
LAB = EXP / "E62_Final_System_Audit" / "tables" / "r1_labels_independent.csv"
DEV = ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3"]
SIMPLER = ["A", "A-S", "C", "D", "D-S", "E"]
RNG = np.random.default_rng(64)


def check(p: Path):
    want = (p.parent / (p.name + ".sha256")).read_text().split()[0]
    if hashlib.sha256(p.read_bytes()).hexdigest() != want:
        raise SystemExit(f"{p} does not match its seal")


def wilson(k, n, z=1.96):
    if not n:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def metrics(y, p, q, onset):
    yh = (p >= 0.5).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n, pos = len(y), int(y.sum())
    pe = np.clip(p, 1e-6, 1 - 1e-6)
    prec_h = tp / (tp + fp) if tp + fp else None
    rec_h = tp / pos if pos else None
    prec_l = tn / (tn + fn) if tn + fn else None
    rec_l = tn / (n - pos) if n - pos else None
    f1 = 2 * prec_h * rec_h / (prec_h + rec_h) if prec_h and rec_h else 0.0
    uq = np.unique(q)
    accb, brb = [], []
    for _ in range(4000):
        idx = np.concatenate([np.where(q == u)[0] for u in RNG.choice(uq, len(uq))])
        accb.append(float((yh[idx] == y[idx]).mean()))
        brb.append(float(np.mean((p[idx] - y[idx]) ** 2)))
    out = {"n": n, "HIGH": pos, "correct": tp + tn, "accuracy": round((tp + tn) / n, 3),
           "accuracy_cluster95": [round(float(np.quantile(accb, .025)), 3), round(float(np.quantile(accb, .975)), 3)],
           "balanced_accuracy": round(0.5 * ((rec_h or 0) + (rec_l or 0)), 3) if pos and n - pos else None,
           "precision_HIGH": None if prec_h is None else round(prec_h, 3), "recall_HIGH": None if rec_h is None else round(rec_h, 3),
           "precision_LOW": None if prec_l is None else round(prec_l, 3), "recall_LOW": None if rec_l is None else round(rec_l, 3),
           "f1_HIGH": round(f1, 3), "confusion": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
           "brier": round(float(np.mean((p - y) ** 2)), 4),
           "brier_cluster95": [round(float(np.quantile(brb, .025)), 4), round(float(np.quantile(brb, .975)), 4)],
           "log_loss": round(float(-np.mean(y * np.log(pe) + (1 - y) * np.log(1 - pe))), 4),
           "onsets_detected": f"{int(yh[onset == 1].sum())}/{int((onset == 1).sum())}",
           "quarters_acc_ge_075": int(sum((yh[q == u] == y[q == u]).mean() >= 0.75 for u in uq))}
    try:
        from sklearn.linear_model import LogisticRegression
        z = np.log(pe / (1 - pe)).reshape(-1, 1)
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(z, y)
        out["calibration_slope"], out["calibration_intercept"] = round(float(lr.coef_[0][0]), 3), round(float(lr.intercept_[0]), 3)
    except Exception:
        out["calibration_slope"] = None
    out["citl"] = round(float(y.mean() - p.mean()), 4)
    try:
        from sklearn.metrics import roc_auc_score
        out["auc"] = round(float(roc_auc_score(y, p)), 3)
    except Exception:
        out["auc"] = None
    return out


def paired(R, a, b):
    y, q = R["y"].to_numpy(), R["target"].to_numpy()
    da, db = (R[a].to_numpy() - y) ** 2, (R[b].to_numpy() - y) ** 2
    uq = np.unique(q)
    perq = np.array([db[q == u].mean() - da[q == u].mean() for u in uq])
    bs = []
    for _ in range(4000):
        idx = np.concatenate([np.where(q == u)[0] for u in RNG.choice(uq, len(uq))])
        bs.append(float(db[idx].mean() - da[idx].mean()))
    better, worse = int((perq < -1e-12).sum()), int((perq > 1e-12).sum())
    ps = float(binomtest(better, better + worse).pvalue) if better + worse else 1.0
    ci = [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]
    return {"reference": a, "candidate": b, "delta_brier": round(float(db.mean() - da.mean()), 4), "cluster95": ci,
            "quarters_better": better, "quarters_worse": worse, "sign_p": round(ps, 3),
            "supported_improvement": bool(ci[1] < 0 and ps < 0.05), "supported_worse": bool(ci[0] > 0 and ps < 0.05)}


def jumps(R, col):
    """Mean |change| of P(HIGH) between consecutive origins per province (forecast stability)."""
    out = []
    for _, g in R.sort_values("t").groupby("province_code"):
        out += list(np.abs(np.diff(g[col].to_numpy())))
    return round(float(np.mean(out)), 4)


def main():
    for p in (SEALED, S57, S58, S60, S61A):
        check(p)
    C = pd.read_csv(SEALED, dtype={"province_code": str})
    s57 = pd.read_csv(S57, dtype={"province_code": str})[["t", "province_code", "province", "E56_p", "E56_p_price",
                                                          "PERSIST_p", "MAJORITY_p", "CLIM_p", "PROVCLIM_p", "E56_config"]]
    s58 = pd.read_csv(S58, dtype={"province_code": str})[["t", "province_code", "BPROJ_p"]]
    s60 = pd.read_csv(S60, dtype={"province_code": str})[["t", "province_code", "A_p", "C_p"]].rename(
        columns={"A_p": "E60A_p", "C_p": "E60C_p"})
    s61 = pd.read_csv(S61A, dtype={"province_code": str})[["t", "province_code", "H2_p_hunger"]]
    ev = pd.read_csv(EVENTS, dtype={"province_code": str})[["t", "province_code", "ONSET"]]
    lab = pd.read_csv(LAB, dtype={"province_code": str}).rename(columns={"quarter": "target"})
    R = C.merge(s57, on=["t", "province_code"], how="left").merge(s58, on=["t", "province_code"], how="left") \
         .merge(s60, on=["t", "province_code"], how="left").merge(s61, on=["t", "province_code"], how="left") \
         .merge(ev, on=["t", "province_code"], how="left") \
         .merge(lab[["target", "province_code", "T43"]], on=["target", "province_code"], how="left")
    OP = R[R["T43"].isna()].copy()
    R = R[R["T43"].notna()].copy()
    assert len(R) == 50, len(R)
    R["y"] = R["T43"].astype(int)
    R["EW_p"] = R["E56_p_price"]                     # E58-EW warning form: decision on P_price
    for k in ("A", "C", "D", "E", "A-S", "D-S", "B"):
        R[f"{k}_W"] = R[f"{k}_p_price"]               # warning form of each candidate (reported separately)
    arms = {"E64-A": "A_p", "E64-C": "C_p", "E64-D": "D_p", "E64-E": "E_p", "E64-A-S": "A-S_p", "E64-D-S": "D-S_p",
            "E64-B news-only": "B_p", "E56 (sealed)": "E56_p", "E60-A (sealed)": "E60A_p", "E60-C (sealed)": "E60C_p",
            "Price projection (B-PROJ)": "BPROJ_p", "Persistence": "PERSIST_p", "Majority as-of": "MAJORITY_p",
            "Climatology as-of": "CLIM_p", "Province climatology as-of": "PROVCLIM_p",
            "E58-EW warning form (P_price)": "EW_p", "E64-A warning form": "A_W", "E64-D warning form": "D_W",
            "E64-E warning form": "E_W", "E64-D-S warning form": "D-S_W"}
    y, q, on = R["y"].to_numpy(), R["target"].to_numpy(), R["ONSET"].fillna(0).to_numpy()
    M = {name: metrics(y, R[c].to_numpy(float), q, on) for name, c in arms.items()}
    dev = R[R["target"].isin(DEV)]
    test = R[~R["target"].isin(DEV)]
    devb = {k: round(float(np.mean((dev[f"{k}_p"] - dev["y"]) ** 2)), 4) for k in SIMPLER}
    best = min(SIMPLER, key=lambda k: (devb[k], SIMPLER.index(k)))
    final = best if devb[best] <= devb["A"] - 0.005 else "A"
    sel = {"dev_brier": devb, "lowest": best, "final": final,
           "rule": "lowest DEV Brier; must beat A's DEV Brier by >= 0.005, else the simpler candidate (A)"}
    claims = {"news_D_vs_A": paired(R, "A_p", "D_p"), "news_DS_vs_AS": paired(R, "A-S_p", "D-S_p"),
              "news_E_vs_A": paired(R, "A_p", "E_p"), "original_news_C_vs_A": paired(R, "A_p", "C_p"),
              "stable_AS_vs_A": paired(R, "A_p", "A-S_p"), "stable_DS_vs_D": paired(R, "D_p", "D-S_p"),
              "final_vs_E56": paired(R, "E56_p", f"{final}_p"),
              **{f"final_vs_{b}": paired(R, b, f"{final}_p") for b in ("PERSIST_p", "MAJORITY_p", "CLIM_p", "PROVCLIM_p")}}
    jump = {k: jumps(pd.concat([R, OP]), f"{k}_p") for k in ("A", "A-S", "D", "D-S", "C", "E")}
    jump["E56"] = jumps(R, "E56_p")
    sels = json.loads((E64 / "sealed" / "selections.json").read_text())
    switches = {}
    for k in ("A", "A-S", "C", "D", "D-S", "E"):
        cfgs = [sels[o][k]["cfg"] for o in sorted(sels, key=lambda s: (int(s[:4]), int(s[-1])))]
        switches[k] = {"distinct_configs": len(set(cfgs)), "switches": int(sum(a != b for a, b in zip(cfgs, cfgs[1:]))),
                       "configs": cfgs}
    n3use = {o: {k: sels[o][k].get("n3_splits") for k in ("D", "D-S", "E")} for o in sels}
    # hunger component: served ridge vs E61 random walk (component result only)
    hc = R.drop_duplicates("target")[["target", "E56_p_price"]].copy()
    hun = {}
    for name, ph in (("served ridge", R[f"{final}_p_hunger"]), ("random walk (E61 H2)", R["H2_p_hunger"])):
        pp = ph.to_numpy() * R[f"{final}_p_price"].to_numpy()
        hun[name] = {"brier_P(HIGH)": round(float(np.mean((pp - y) ** 2)), 4), "accuracy": round(float(((pp >= .5) == y).mean()), 3)}
    byq = R.groupby("target").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["y"].sum()), "final_correct": int(((g[f"{final}_p"] >= .5) == g["y"]).sum()),
        "E56_correct": int(((g["E56_p"] >= .5) == g["y"]).sum()), "final_mean_p": round(g[f"{final}_p"].mean(), 3),
        "final_brier": round(float(((g[f"{final}_p"] - g["y"]) ** 2).mean()), 4)}), include_groups=False).reset_index()
    byp = R.groupby("province").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["y"].sum()), "final_correct": int(((g[f"{final}_p"] >= .5) == g["y"]).sum()),
        "E56_correct": int(((g["E56_p"] >= .5) == g["y"]).sum()),
        "final_brier": round(float(((g[f"{final}_p"] - g["y"]) ** 2).mean()), 4)}), include_groups=False).reset_index()
    test_m = {k: metrics(test["y"].to_numpy(), test[c].to_numpy(float), test["target"].to_numpy(),
                         test["ONSET"].fillna(0).to_numpy()) for k, c in (("final", f"{final}_p"), ("E56", "E56_p"),
                                                                          ("Majority", "MAJORITY_p"))}
    rel = []
    for k, c in (("final", f"{final}_p"), ("E56", "E56_p")):
        p = R[c].to_numpy()
        for lo, hi in zip((0, .1, .2, .3, .5, .7), (.1, .2, .3, .5, .7, 1.0001)):
            s = (p >= lo) & (p < hi)
            rel.append({"arm": k, "bin": f"[{lo},{min(hi, 1)})", "n": int(s.sum()), "mean_p": round(float(p[s].mean()), 3) if s.any() else None,
                        "observed_HIGH": int(y[s].sum()), "rate": round(float(y[s].mean()), 3) if s.any() else None,
                        "wilson95": wilson(int(y[s].sum()), int(s.sum()))})
    res = {"selection": sel, "metrics_50": M, "claims": claims, "mean_abs_jump": jump, "config_switching": switches,
           "n3_split_counts_by_origin": n3use, "hunger_component": hun, "test_only": test_m,
           "operational": OP[["target", "province", "A_p", "C_p", "D_p", "E_p", "A-S_p", "D-S_p", "B_p"]].round(4).to_dict("records")}
    T = pd.DataFrame([{"arm": k, **{kk: (json.dumps(vv) if isinstance(vv, (list, dict)) else vv) for kk, vv in v.items()}}
                      for k, v in M.items()])
    T.to_csv(E64 / "tables" / "c2_model_comparison_50rows.csv", index=False, lineterminator="\n")
    byq.to_csv(E64 / "tables" / "c2_by_quarter.csv", index=False, lineterminator="\n")
    byp.to_csv(E64 / "tables" / "c2_by_province.csv", index=False, lineterminator="\n")
    pd.DataFrame(rel).assign(wilson95=lambda f: f["wilson95"].map(json.dumps)).to_csv(
        E64 / "tables" / "c2_reliability.csv", index=False, lineterminator="\n")
    R.to_csv(E64 / "tables" / "c2_rows50.csv", index=False, float_format="%.6g", lineterminator="\n")
    (E64 / "out" / "c2_score.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    show = ["correct", "accuracy", "accuracy_cluster95", "balanced_accuracy", "recall_HIGH", "precision_HIGH", "recall_LOW",
            "f1_HIGH", "brier", "brier_cluster95", "log_loss", "auc", "calibration_slope", "onsets_detected", "quarters_acc_ge_075"]
    pd.set_option("display.width", 300)
    print(T.set_index("arm")[show].to_string())
    print(json.dumps({"selection": sel, "claims": claims, "jump": jump,
                      "switching": {k: (v["distinct_configs"], v["switches"]) for k, v in switches.items()},
                      "hunger": hun}, indent=1))
    print(byq.to_string()); print(byp.to_string())
    print(json.dumps(res["operational"], indent=0))


if __name__ == "__main__":
    main()
