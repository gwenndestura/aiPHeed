"""E61 A2: calibration of the sealed E56/E58 probabilities, the low-probability cases, and the joint-probability
assumption behind P(HIGH) = P_hunger x P_price.

Inputs (read-only, hash-verified): E57/E58 sealed rolling-origin forecasts (50 rows, targets 2024-Q2..2026-Q3), the
E58 events file (outcomes), and the CPI/SWS data through the authorized limit (outcome values and margins).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a2_calibration_joint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, E = X.np, X.pd, X.L, X.F, X.E


def outcome_values(d) -> pd.DataFrame:
    """Observed food YoY, gap and hunger for each target, the province thresholds, and which condition set PS."""
    Y = F.t43_labels(d)
    th = L.e40_spec()
    Y["G"] = Y["F"] - Y["HL"]
    Y["thr_food"] = Y["province_code"].map(th["food"])
    Y["thr_gap"] = Y["province_code"].map(th["gap"])
    Y["food_margin"] = Y["F"] - Y["thr_food"]
    Y["gap_margin"] = Y["G"] - Y["thr_gap"]
    Y["ps_by"] = np.select([(Y["food_margin"] > 0) & (Y["gap_margin"] > 0), Y["food_margin"] > 0, Y["gap_margin"] > 0],
                           ["both", "food", "gap"], "none")
    Y["target"] = Y["q"].map(L.qs)
    return Y


def joint_audit(Y: pd.DataFrame) -> dict:
    """Is P(PS | H > 11.3) = P(PS)? Quarters are the unit for H (one regional value per quarter)."""
    from scipy.stats import fisher_exact
    Z = Y[Y["T43"].notna()].copy()
    Z["Hhigh"] = (Z["H_all"] > 11.3).astype(int)
    tab = pd.crosstab(Z["Hhigh"], Z["PS"])
    ps_h = float(Z.loc[Z["Hhigh"] == 1, "PS"].mean())
    ps_l = float(Z.loc[Z["Hhigh"] == 0, "PS"].mean())
    odds, p_row = fisher_exact(tab.to_numpy())
    qtab = Z.groupby("target").agg(H=("H_all", "first"), Hhigh=("Hhigh", "first"), PS_share=("PS", "mean")).reset_index()
    from scipy.stats import mannwhitneyu
    a, b = qtab.loc[qtab["Hhigh"] == 1, "PS_share"], qtab.loc[qtab["Hhigh"] == 0, "PS_share"]
    mw = mannwhitneyu(a, b) if len(a) and len(b) else None
    return {"rows": int(len(Z)), "quarters": int(Z["target"].nunique()),
            "crosstab_Hhigh_by_PS": {f"H{'>' if i else '<='}11.3": {f"PS={j}": int(tab.loc[i, j]) for j in tab.columns}
                                     for i in tab.index},
            "P(PS|H>11.3)": ps_h, "P(PS|H<=11.3)": ps_l, "P(PS)": float(Z["PS"].mean()),
            "fisher_rows_odds_ratio": float(odds), "fisher_rows_p": float(p_row),
            "quarter_level_PS_share_H_high_vs_low_mannwhitney_p": None if mw is None else float(mw.pvalue),
            "quarters_H_high": int((qtab["Hhigh"] == 1).sum()), "quarters_H_low": int((qtab["Hhigh"] == 0).sum()),
            "by_quarter": qtab.round(3).to_dict("records")}


def main():
    seals = X.verify_sealed()
    d, _, _ = E.load()
    Y = outcome_values(d)
    R = X.rows50()
    R = R.merge(Y[["province_code", "target", "F", "HL", "G", "H_all", "PS", "T43", "thr_food", "thr_gap", "food_margin",
                   "gap_margin", "ps_by"]], on=["province_code", "target"], how="left")
    assert (R["T43"] == R["HIGH"]).all(), "E58 events disagree with recomputed T43"
    assert (R["H_all"] > 11.3).all()
    R["EW_warn"] = (R["E56_p_price"] >= 0.5).astype(int)
    R["E56_yhat"] = (R["E56_p"] >= 0.5).astype(int)

    # ---- calibration (P(HIGH) vs HIGH; P_price vs PS; on these rows PS == HIGH)
    y = R["HIGH"].to_numpy()
    cal = {}
    for name, col in (("E56_P_HIGH", "E56_p"), ("E56_P_price", "E56_p_price"), ("projection_only_BPROJ", "BPROJ_p"),
                      ("climatology", "CLIM_p")):
        p = R[col].to_numpy(float)
        cal[name] = {**X.calib(y, p, clusters=R["target"].to_numpy()), "reliability": X.reliability(y, p)}
    excl = R["target"] != "2024-Q2"
    cal["E56_P_HIGH_excluding_2024Q2"] = X.calib(R.loc[excl, "HIGH"], R.loc[excl, "E56_p"], clusters=R.loc[excl, "target"])
    lowcut = {}
    for c in (0.1, 0.2, 0.3):
        for col in ("E56_p", "E56_p_price"):
            s = R[col] < c
            k, n = int(R.loc[s, "HIGH"].sum()), int(s.sum())
            lowcut[f"{col}<{c}"] = {"n": n, "observed_HIGH": k, "rate": k / n if n else None, "wilson95": X.wilson(k, n),
                                    "mean_p": float(R.loc[s, col].mean()) if n else None}
    perq = R.groupby("target").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["HIGH"].sum()), "mean_p": g["E56_p"].mean(), "mean_p_price": g["E56_p_price"].mean(),
        "p_hunger": g["E56_p_hunger"].iloc[0], "brier": float(np.mean((g["E56_p"] - g["HIGH"]) ** 2)),
        "acc_E56": float((g["E56_yhat"] == g["HIGH"]).mean()), "acc_EW": float((g["EW_warn"] == g["HIGH"]).mean())}),
        include_groups=False).reset_index()
    perp = R.groupby("province").apply(lambda g: pd.Series({
        "n": len(g), "HIGH": int(g["HIGH"].sum()), "mean_p": g["E56_p"].mean(),
        "brier": float(np.mean((g["E56_p"] - g["HIGH"]) ** 2)), "acc_E56": float((g["E56_yhat"] == g["HIGH"]).mean()),
        "acc_EW": float((g["EW_warn"] == g["HIGH"]).mean())}), include_groups=False).reset_index()

    # ---- the low-probability cases (E56 P(HIGH) < 0.2)
    low = R[R["E56_p"] < 0.2].sort_values(["target", "province"]).copy()
    low["outcome"] = np.where(low["HIGH"] == 1, "HIGH", "LOW")
    keep = ["target", "origin_quarter", "province", "E56_p", "E56_p_hunger", "E56_p_price", "EW_warn", "outcome", "H_all",
            "H_last_known", "F", "thr_food", "food_margin", "G", "thr_gap", "gap_margin", "ps_by", "last_known_T43", "ONSET"]
    X.write_csv(low[keep], X.TABLES / "a2_low_probability_cases.csv")
    X.write_csv(R[["target", "province"] + [c for c in R.columns if c not in ("target", "province")]], X.TABLES / "a2_rows50.csv")
    X.write_csv(perq, X.TABLES / "a2_calibration_by_quarter.csv")
    X.write_csv(perp, X.TABLES / "a2_calibration_by_province.csv")

    # ---- label sensitivity: HIGH rows whose deciding margin is small
    hi = R[R["HIGH"] == 1]
    margin = np.maximum(hi["food_margin"], hi["gap_margin"])
    ja = joint_audit(Y)
    X.dump({"sealed_inputs_verified": seals, "n_rows": int(len(R)), "n_HIGH": int(R["HIGH"].sum()),
            "calibration": cal, "low_probability_cutoffs": lowcut,
            "HIGH_rows_deciding_margin_points": {"min": float(margin.min()), "median": float(margin.median()),
                                                 "n_below_0.5": int((margin < 0.5).sum()), "n": int(len(hi))},
            "ps_condition_on_HIGH_rows": hi["ps_by"].value_counts().to_dict(),
            "joint_probability_audit": ja}, X.OUT / "a2_calibration_joint.json")
    print(low[keep].round(2).to_string())
    for k, v in cal.items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk not in ("reliability", "ci95")},
              v.get("ci95", {}).get("slope"))
    for r in cal["E56_P_HIGH"]["reliability"]:
        print("  ", r)
    print({k: (v["n"], v["observed_HIGH"], None if v["rate"] is None else round(v["rate"], 2), v["wilson95"]) for k, v in lowcut.items()})
    print("joint:", {k: v for k, v in ja.items() if k != "by_quarter"})
    print(perq.round(3).to_string())
    print(perp.round(3).to_string())


if __name__ == "__main__":
    main()
