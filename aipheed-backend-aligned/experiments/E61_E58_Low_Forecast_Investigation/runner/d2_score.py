"""E61 addendum-1 step 2: score the SEALED addendum candidates (PROTOCOL_ADDENDUM_1.md sections 1-6).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/d2_score.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2_score as S  # noqa: E402  (block, paired, onset, rates; main() guarded)

X, np, pd, L = S.X, S.np, S.pd, S.L
SEALED = X.SEALED_DIR / "addendum1.csv"
ARMS = ["C0", "D1", "D2", "D3", "K1", "K2", "FA-rice", "FA-emp", "FA-ofw"]
FAMILIES = {"drift": ["D1", "D2", "D3"], "combination": ["K1", "K2"]}


def verify():
    want = (X.E61 / "runner" / "ADDENDUM_1_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((X.E61 / "PROTOCOL_ADDENDUM_1.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() != want:
        raise SystemExit("PROTOCOL_ADDENDUM_1.md changed after freezing")
    if X.sha(SEALED) != (SEALED.parent / "addendum1.csv.sha256").read_text().split()[0]:
        raise SystemExit("sealed addendum changed")
    X.verify_sealed()


def supported(pr):
    ci_ex = pr["ci95"][0] > 0 or pr["ci95"][1] < 0
    sign = pr["sign_test_p"] is not None and pr["sign_test_p"] < 0.05
    return "supported" if ci_ex and sign else ("suggestive, not established" if ci_ex or sign else "no difference shown")


def main():
    verify()
    A = pd.read_csv(SEALED, dtype={"province_code": str}).rename(columns=lambda c: c.replace("-", "_"))
    arms = [a.replace("-", "_") for a in ARMS]
    R0 = pd.read_csv(X.TABLES / "a2_rows50.csv", dtype={"province_code": str})
    R = A.merge(R0[["t", "province_code", "HIGH", "ONSET", "H_all", "PS"]], on=["t", "province_code"])
    assert len(R) == 50
    R["split"] = np.where(R["target"].isin(S.DEV), "DEV", "TEST")
    for a in arms:
        if f"{a}_p_price" in R:
            R[f"{a}_warn"] = (R[f"{a}_p_price"] >= 0.5).astype(int)
    R["C0_warn"] = (R["C0_p_price"] >= 0.5).astype(int)
    R["K3_dec"] = ((R["p_hunger"] >= 0.5) & (R["C0_p_price"] >= 0.5)).astype(int)
    res = {"rows": {}, "dev": {}, "test": {}, "paired_vs_C0": {}}
    for key, sub in (("rows", R), ("dev", R[R["split"] == "DEV"]), ("test", R[R["split"] == "TEST"])):
        for a in arms:
            res[key][a] = S.block(sub, f"{a}_p")
            if f"{a}_warn" in sub:
                res[key][a + "_warn"] = {**S.block(sub, None, f"{a}_warn"), "onset": S.onset(sub, f"{a}_warn")}
        res[key]["K3"] = {**S.block(sub, None, "K3_dec"), "onset": S.onset(sub, "K3_dec")}
    for a in arms[1:]:
        pr = S.paired(R, f"{a}_p")
        pr["verdict"] = supported(pr)
        res["paired_vs_C0"][a] = pr
    # restate C1-C4 under the addendum significance rule
    C = pd.read_csv(X.TABLES / "c2_rows.csv", dtype={"province_code": str})
    res["C1_C4_restated"] = {a: {**(pr := S.paired(C, f"{a}_p")), "verdict": supported(pr)} for a in ("C1", "C2", "C3", "C23", "C4")}
    # family selection
    res["selection"] = {}
    for fam, cand in FAMILIES.items():
        best = min(cand, key=lambda a: (round(res["dev"][a]["brier"], 10), cand.index(a)))
        crit = {"a_dev_brier_gain_ge_0.005": res["dev"]["C0"]["brier"] - res["dev"][best]["brier"] >= 0.005,
                "b_paired_ci_upper_lt_0": res["paired_vs_C0"][best]["ci95"][1] < 0,
                "c_balanced_acc_ge_C0_minus_0.02": res["rows"][best]["balanced_accuracy"] >= res["rows"]["C0"]["balanced_accuracy"] - 0.02,
                "d_onset_recall_ge_C0": (res["rows"].get(best + "_warn", {}).get("onset", {}).get("recall", 1.0)
                                         >= res["rows"]["C0_warn"]["onset"]["recall"]),
                "e_statistically_supported": res["paired_vs_C0"][best]["verdict"] == "supported"}
        res["selection"][fam] = {"candidate": best, "criteria": crit, "improvement": all(crit.values())}
    res["selection"]["K3_display"] = {"balanced_accuracy_K3": res["rows"]["K3"]["balanced_accuracy"],
                                      "balanced_accuracy_K0": res["rows"]["C0"]["balanced_accuracy"],
                                      "recommended": res["rows"]["K3"]["balanced_accuracy"] >= res["rows"]["C0"]["balanced_accuracy"]}
    res["feature_signal"] = {a: res["paired_vs_C0"][a]["verdict"] + (" (removal worse)" if res["paired_vs_C0"][a]["mean_diff"] > 0 else " (removal better)")
                             for a in ("FA_rice", "FA_emp", "FA_ofw")}
    # parts scored separately
    hq = R.groupby("target").agg(p_h=("p_hunger", "first"), H=("H_all", "first")).reset_index()
    res["parts"] = {"P_price_vs_PS": S.block(R.assign(HIGH=R["PS"]), "C0_p_price"),
                    "P_hunger_vs_H_above_11.3": {"quarters": int(len(hq)), "H_high_quarters": int((hq["H"] > 11.3).sum()),
                                                  "brier": float(np.mean((hq["p_h"] - (hq["H"] > 11.3)) ** 2)),
                                                  "min_p_hunger": float(hq["p_h"].min())}}
    # hunger variants (continuous)
    hv = R.groupby("target").first().reset_index()
    hres = {}
    for h in ("H0", "H1", "H2"):
        e = hv[f"{h}_H_hat"] - hv["H_all"]
        hres[h] = {"rmse": float(np.sqrt(np.mean(e ** 2))), "mean_error": float(e.mean()), "n": int(e.notna().sum()),
                   "brier_vs_H_above_11.3": float(np.mean((hv[f"{h}_p_hunger"] - (hv["H_all"] > 11.3)) ** 2))}
    for h in ("H1", "H2"):
        hres[h]["targets_better_than_H0"] = int(((hv[f"{h}_H_hat"] - hv["H_all"]).abs() < (hv["H0_H_hat"] - hv["H_all"]).abs()).sum())
        hres[h]["replaces_H0"] = hres[h]["rmse"] < hres["H0"]["rmse"] and hres[h]["targets_better_than_H0"] >= 6
    res["hunger_variants"] = hres
    X.write_csv(hv[["target", "H_all", "H0_H_base", "H0_H_hat", "H1_H_hat", "H2_H_hat", "H0_p_hunger", "H1_p_hunger", "H2_p_hunger"]],
                X.TABLES / "d2_hunger_variants.csv")
    # split counts
    sp = pd.read_csv(X.SEALED_DIR / "addendum1_c0_split_counts.csv")
    agg = sp.groupby("feature").agg(total_splits=("splits", "sum"), origins_offered=("origin", "nunique"),
                                    origins_used=("splits", lambda s: int((s > 0).sum()))).reset_index().sort_values("total_splits", ascending=False)
    X.write_csv(agg, X.TABLES / "d2_c0_split_counts.csv")
    res["split_counts"] = agg.to_dict("records")
    summ = []
    for key in ("rows", "dev", "test"):
        for a, v in res[key].items():
            summ.append({"set": key, "arm": a, **{k: v.get(k) for k in ("n", "HIGH", "TP", "TN", "accuracy", "balanced_accuracy",
                         "HIGH_recall", "HIGH_precision", "brier", "log_loss", "slope")}, "slope_ci95": v.get("slope_ci95"),
                         "onset_detected": (v.get("onset") or {}).get("detected"), "onsets": (v.get("onset") or {}).get("onsets")})
    X.write_csv(pd.DataFrame(summ), X.TABLES / "d2_model_comparison.csv")
    perq = []
    for q, g in R.groupby("target"):
        r = {"target": q, "HIGH": int(g["HIGH"].sum())}
        for a in arms:
            r[f"{a}_brier"] = float(np.mean((g[f"{a}_p"] - g["HIGH"]) ** 2))
            r[f"{a}_acc"] = float(((g[f"{a}_p"] >= 0.5) == g["HIGH"]).mean())
        perq.append(r)
    X.write_csv(pd.DataFrame(perq), X.TABLES / "d2_by_quarter.csv")
    X.dump(res, X.OUT / "d2_score.json")
    pd.set_option("display.width", 250)
    print(pd.DataFrame(summ)[lambda f: f["set"] == "rows"].round(3).to_string())
    for a, v in res["paired_vs_C0"].items():
        print("paired", a, round(v["mean_diff"], 4), [round(x, 4) for x in v["ci95"]], v["quarters_better"], v["quarters_worse"],
              None if v["sign_test_p"] is None else round(v["sign_test_p"], 3), v["verdict"])
    for a, v in res["C1_C4_restated"].items():
        print("restated", a, round(v["mean_diff"], 4), [round(x, 4) for x in v["ci95"]], v["quarters_better"], v["quarters_worse"],
              None if v["sign_test_p"] is None else round(v["sign_test_p"], 3), v["verdict"])
    print("selection", res["selection"])
    print("parts", res["parts"]["P_hunger_vs_H_above_11.3"], {k: round(res["parts"]["P_price_vs_PS"][k], 3) for k in ("brier", "accuracy")})
    print("hunger", hres)
    print(agg.head(15).to_string())


if __name__ == "__main__":
    main()
