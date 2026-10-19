"""E61 step C2 (PROTOCOL sections 3-4): score the SEALED candidates and baselines on identical rows, apply the frozen
selection rule, and report calibration, per-quarter/per-province results, paired Brier CIs and ONSET detection.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/c2_score.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L = X.np, X.pd, X.L
SEALED = X.SEALED_DIR / "candidates.csv"
ARMS = ["C0", "C1", "C2", "C3", "C23", "C4"]
DEV = [f"{y}-Q{q}" for y, q in ((2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3))]


def verify():
    want = (X.E61 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((X.E61 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    if X.sha(SEALED) != (SEALED.parent / "candidates.csv.sha256").read_text().split()[0]:
        raise SystemExit("sealed candidates changed")
    X.verify_sealed()


def rates(y, yhat):
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    rh = tp / (tp + fn) if tp + fn else None
    rl = tn / (tn + fp) if tn + fp else None
    return {"n": int(len(y)), "HIGH": int(y.sum()), "TP": tp, "TN": tn, "FP": fp, "FN": fn,
            "accuracy": (tp + tn) / len(y), "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2,
            "HIGH_recall": rh, "LOW_recall": rl, "HIGH_precision": tp / (tp + fp) if tp + fp else None}


def block(R, p_col, decision_col=None):
    y = R["HIGH"].to_numpy()
    out = {}
    if p_col:
        p = R[p_col].to_numpy(float)
        out.update(rates(y, p >= 0.5))
        c = X.calib(y, p, clusters=R["target"].to_numpy(), n_boot=1000)
        out.update({k: c[k] for k in ("brier", "log_loss", "citl", "slope", "intercept")})
        out["slope_ci95"] = c.get("ci95", {}).get("slope")
    else:
        out.update(rates(y, R[decision_col].to_numpy()))
        out["brier"] = float(np.mean((R[decision_col] - y) ** 2))
    return out


def paired(R, a, b="C0_p", n=4000, seed=61):
    """Brier(a) - Brier(b), quarter-cluster bootstrap CI and quarter-level sign test."""
    from scipy.stats import binomtest
    d = (R[a] - R["HIGH"]) ** 2 - (R[b] - R["HIGH"]) ** 2
    rng = np.random.default_rng(seed)
    qs = R["target"].unique()
    per_q = d.groupby(R["target"]).mean()
    boots = [float(np.mean(np.concatenate([d[R["target"] == q].to_numpy() for q in rng.choice(qs, len(qs))]))) for _ in range(n)]
    wins, losses = int((per_q < -1e-12).sum()), int((per_q > 1e-12).sum())
    return {"mean_diff": float(d.mean()), "ci95": [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))],
            "quarters_better": wins, "quarters_worse": losses,
            "sign_test_p": float(binomtest(wins, wins + losses).pvalue) if wins + losses else None}


def onset(R, warn_col):
    s = R["ONSET"] == 1
    return {"onsets": int(s.sum()), "detected": int(R.loc[s, warn_col].sum()),
            "recall": float(R.loc[s, warn_col].mean()) if s.any() else None}


def main():
    verify()
    S = pd.read_csv(SEALED, dtype={"province_code": str})
    R0 = pd.read_csv(X.TABLES / "a2_rows50.csv", dtype={"province_code": str})
    R = S.merge(R0[["t", "province_code", "HIGH", "ONSET", "BPROJ_p", "PERSIST_p", "CLIM_p"]], on=["t", "province_code"])
    assert len(R) == 50
    assert np.allclose(R["C0_p"], R0.set_index(["t", "province_code"]).loc[list(zip(R["t"], R["province_code"])), "E56_p"])
    R["B_MAJ"] = 0.0
    R["B_HIGH"] = 1.0
    R["B_PROJ_P"] = R["p_hunger"] * R["BPROJ_p"]
    for a in ARMS:
        R[f"{a}_warn"] = (R[f"{a}_p_price"] >= 0.5).astype(int)
    R["split"] = np.where(R["target"].isin(DEV), "DEV", "TEST")
    res = {"rows": {}, "dev": {}, "test": {}}
    for a in ARMS:
        for key, sub in (("rows", R), ("dev", R[R["split"] == "DEV"]), ("test", R[R["split"] == "TEST"])):
            res[key][a] = block(sub, f"{a}_p")
            res[key][a + "_warn"] = {**block(sub, None, f"{a}_warn"), "onset": onset(sub, f"{a}_warn")}
    for b, col in (("B_PROJ", "B_PROJ_P"), ("B_CLIM", "CLIM_p"), ("B_MAJ", "B_MAJ"), ("B_HIGH", "B_HIGH")):
        for key, sub in (("rows", R), ("dev", R[R["split"] == "DEV"]), ("test", R[R["split"] == "TEST"])):
            res[key][b] = block(sub, col) if b in ("B_PROJ", "B_CLIM") else block(sub, None, col)
    for b in ("PERSIST_p", "B_NOW"):
        for key, sub in (("rows", R), ("dev", R[R["split"] == "DEV"]), ("test", R[R["split"] == "TEST"])):
            res[key][b] = {**block(sub, None, b), "onset": onset(sub, b)}
    res["paired_vs_C0"] = {a: paired(R, f"{a}_p") for a in ARMS[1:]}
    res["paired_vs_C0"]["B_PROJ"] = paired(R, "B_PROJ_P")
    res["news_test_C0_minus_C4"] = paired(R, "C0_p", "C4_p")

    # ---- frozen selection rule (PROTOCOL section 4)
    cands = ["C1", "C2", "C3", "C23", "C4"]
    best = min(cands, key=lambda a: (round(res["dev"][a]["brier"], 10), cands.index(a)))
    crit = {"a_dev_brier_gain_ge_0.005": res["dev"]["C0"]["brier"] - res["dev"][best]["brier"] >= 0.005,
            "b_paired_ci_upper_lt_0": res["paired_vs_C0"][best]["ci95"][1] < 0,
            "c_balanced_acc_ge_C0_minus_0.02": res["rows"][best]["balanced_accuracy"] >= res["rows"]["C0"]["balanced_accuracy"] - 0.02,
            "d_onset_recall_ge_C0": res["rows"][best + "_warn"]["onset"]["recall"] >= res["rows"]["C0_warn"]["onset"]["recall"]}
    c0s, c1s = res["rows"]["C0"]["slope_ci95"], res["rows"]["C1"]["slope_ci95"]
    res["selection"] = {"candidate": best, "criteria": crit, "improvement": all(crit.values()),
                        "calibration_claim_C1": bool(c1s and c0s and c1s[0] <= 1 <= c1s[1] and not (c0s[0] <= 1 <= c0s[1])
                                                     and res["rows"]["C1"]["brier"] <= res["rows"]["C0"]["brier"]),
                        "news_adds_value": res["news_test_C0_minus_C4"]["ci95"][1] < 0}
    perq = []
    for q, g in R.groupby("target"):
        r = {"target": q, "split": g["split"].iloc[0], "HIGH": int(g["HIGH"].sum())}
        for a in ARMS:
            r[f"{a}_acc"] = float(((g[f"{a}_p"] >= 0.5) == g["HIGH"]).mean())
            r[f"{a}_warn_acc"] = float((g[f"{a}_warn"] == g["HIGH"]).mean())
            r[f"{a}_brier"] = float(np.mean((g[f"{a}_p"] - g["HIGH"]) ** 2))
        perq.append(r)
    perp = []
    for p, g in R.groupby("province"):
        r = {"province": p, "HIGH": int(g["HIGH"].sum())}
        for a in ARMS:
            r[f"{a}_acc"] = float(((g[f"{a}_p"] >= 0.5) == g["HIGH"]).mean())
            r[f"{a}_brier"] = float(np.mean((g[f"{a}_p"] - g["HIGH"]) ** 2))
        perp.append(r)
    X.write_csv(pd.DataFrame(perq), X.TABLES / "c2_by_quarter.csv")
    X.write_csv(pd.DataFrame(perp), X.TABLES / "c2_by_province.csv")
    X.write_csv(R, X.TABLES / "c2_rows.csv")
    summ = []
    for key in ("rows", "dev", "test"):
        for a, v in res[key].items():
            summ.append({"set": key, "arm": a, **{k: v.get(k) for k in ("n", "HIGH", "accuracy", "balanced_accuracy",
                         "HIGH_recall", "LOW_recall", "HIGH_precision", "brier", "log_loss", "slope")},
                         "slope_ci95": v.get("slope_ci95"), "onset_recall": (v.get("onset") or {}).get("recall")})
    X.write_csv(pd.DataFrame(summ), X.TABLES / "c2_model_comparison.csv")
    X.dump(res, X.OUT / "c2_score.json")
    pd.set_option("display.width", 250)
    print(pd.DataFrame(summ).round(3).to_string())
    print("paired vs C0:", {k: (round(v["mean_diff"], 4), [round(x, 4) for x in v["ci95"]], v["quarters_better"], v["quarters_worse"])
                            for k, v in res["paired_vs_C0"].items()})
    print("news C0-C4:", res["news_test_C0_minus_C4"])
    print("selection:", res["selection"])
    print(pd.DataFrame(perq).round(2).to_string())


if __name__ == "__main__":
    main()
