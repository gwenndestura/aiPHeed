"""E66 r1 + r3 (PROTOCOL 2.1, 2.3, 3): one scorer for every sealed arm of E55-E65 and the E66 new arms, on the same
rows and labels; paired Brier tests with Holm; late-regime split; the price layer scored against PS.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r1_scoreboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e66_lib as H  # noqa: E402

np, pd = H.np, H.pd
KEY = ["t", "province_code"]


def load_rows() -> pd.DataFrame:
    ev = pd.read_csv(H.EVENTS, dtype={"province_code": str})
    S57 = pd.read_csv(H.SEALED["E57"], dtype={"province_code": str})
    R = S57[KEY + ["target", "origin_quarter", "province", "E56_p", "E56_p_price", "E56_p_hunger", "E56_config",
                   "PERSIST_p", "MAJORITY_p", "CLIM_p", "PROVCLIM_p"]].merge(
        ev[KEY + ["HIGH", "ONSET", "RISEP", "last_known_T43"]], on=KEY, how="left")
    S58 = pd.read_csv(H.SEALED["E58"], dtype={"province_code": str})
    R = R.merge(S58[KEY + ["BPROJ_p", "C3_p", "C4_p_rise"]], on=KEY, how="left")
    for exp, arms in (("E60", ["A", "B", "C", "D"]), ("E64", ["D", "E", "A-S", "D-S", "B"])):
        S = pd.read_csv(H.SEALED[exp], dtype={"province_code": str})
        R = R.merge(S[KEY + [f"{a}_p" for a in arms] + [f"{a}_p_price" for a in arms]].rename(
            columns={**{f"{a}_p": f"{exp}_{a}_p" for a in arms}, **{f"{a}_p_price": f"{exp}_{a}_p_price" for a in arms}}),
            on=KEY, how="left")
    E65 = pd.read_csv(H.E65_ROWS, dtype={"province_code": str})
    R = R.merge(E65[KEY + ["B1_p", "B2_p", "B3_p", "C_p", "D1_p"]].rename(
        columns={c: f"E65_{c}" for c in ["B1_p", "B2_p", "B3_p", "C_p", "D1_p"]}), on=KEY, how="left")
    N = pd.read_csv(H.TABLES / "r2_new_arm_predictions.csv", dtype={"province_code": str})
    R = R.merge(N[KEY + ["N1_p", "N1_p_price", "N2_p", "N2_p_price", "N3_p"]], on=KEY, how="left")
    lab = pd.read_csv(H.LABELS, dtype={"province_code": str})[["province_code", "quarter", "PS", "T43"]]
    R = R.merge(lab.rename(columns={"quarter": "target"}), on=["province_code", "target"], how="left")
    # warning decision (E58-EW form): P_price >= 0.5
    R["EW_dec"] = (R["E56_p_price"] >= 0.5).astype(int)
    R["EW_p"] = R["E56_p_price"]
    assert len(R) == 50, len(R)
    assert (R["T43"] == R["HIGH"]).all(), "E64 T43 labels disagree with the E58 event labels"
    assert R.drop(columns=["C4_p_rise"]).notna().all().all(), R.columns[R.isna().any()].tolist()
    return R


ARMS50 = {   # label: (column, decision column or None, family)
    "E56-TUNED LightGBM (proposed, E57 frozen)": ("E56_p", None, "proposed"),
    "E58-EW warning (P_price >= 0.5)": ("EW_p", "EW_dec", "proposed + warning"),
    "E60-A gov-only LightGBM": ("E60_A_p", None, "ablation"),
    "E60-C gov + improved news (E60)": ("E60_C_p", None, "ablation"),
    "E60-D gov + improved news + history": ("E60_D_p", None, "ablation"),
    "E64-D gov + news v3 (N3)": ("E64_D_p", None, "ablation"),
    "E64-E gov + news v3 + history": ("E64_E_p", None, "ablation"),
    "E64-A-S stable configuration": ("E64_A-S_p", None, "stability fix"),
    "E65-B1 ENSO intensity": ("E65_B1_p", None, "climate-aware"),
    "E65-B3 PAGASA status input": ("E65_B3_p", None, "climate-aware"),
    "E65-B2 B1 + B3": ("E65_B2_p", None, "climate-aware"),
    "E65-C climate removed": ("E65_C_p", None, "climate-aware"),
    "E65-D1 PAGASA El Nino rule": ("E65_D1_p", None, "rule"),
    "CPI-projection rule (B-PROJ)": ("BPROJ_p", None, "rule"),
    "N1 L2-LR matched inputs (new)": ("N1_p", None, "statistical"),
    "N2 L2-LR projection only (new)": ("N2_p", None, "statistical"),
    "N3 E56 price x random-walk hunger (new)": ("N3_p", None, "hunger variant"),
    "E60-B improved news only (LR)": ("E60_B_p", None, "news only"),
    "E64-B news v3 only (LR)": ("E64_B_p", None, "news only"),
    "Persistence": ("PERSIST_p", None, "baseline"),
    "Majority (as-of, always LOW)": ("MAJORITY_p", None, "baseline"),
    "Climatology (as-of rate)": ("CLIM_p", None, "baseline"),
    "Province climatology": ("PROVCLIM_p", None, "baseline"),
}
E55_ARMS = {"B1_PERSIST_p": "Ch.I baseline I persistence (E55)", "B2_LR_GOV_p": "Ch.I baseline II PSA-only LR (E55)",
            "B3_LGBM_GOV_p": "PSA-only LightGBM (E55)", "B4_LR_NLP_p": "Ch.I baseline III NLP-only LR (E55)",
            "B5_LGBM_NLP_p": "NLP-only LightGBM (E55)", "B6_LR_COMB_p": "Ch.I baseline IV LR combined (E55)",
            "B7_E38PROC_p": "E38 procedure refitted on T43 (E55)"}


def score_set(R, arms, ycol="HIGH"):
    out = []
    for name, (col, dec, fam) in arms.items():
        out.append({"arm": name, "family": fam, "column": col, **H.metrics(R, col, ycol, dec)})
    return pd.DataFrame(out)


def paired_table(R, ref, arms, ycol="HIGH"):
    P = pd.DataFrame([H.paired(R, ref, col, ycol) | {"arm_name": name}
                      for name, (col, _, _) in arms.items() if col != ref])
    P["sign_p_holm"] = H.holm(P["sign_p"].tolist())
    P["better_by_rule_holm"] = (P["ci95_hi"] < 0) & (P["sign_p_holm"] < 0.05)
    return P


def main():
    proto = H.verify_protocol()
    sealed = H.verify_sealed()
    R = load_rows()
    H.write_csv(R, H.TABLES / "r1_rows50_all_arms.csv")

    # reproduction checks against earlier reports
    chk = {"E56_brier": float(np.mean((R["E56_p"] - R["HIGH"]) ** 2)),
           "E56_acc": float(((R["E56_p"] >= .5) == R["HIGH"]).mean()),
           "EW_acc": float((R["EW_dec"] == R["HIGH"]).mean()),
           "E60A_acc": float(((R["E60_A_p"] >= .5) == R["HIGH"]).mean())}

    M50 = score_set(R, ARMS50)
    H.write_csv(M50, H.TABLES / "r1_metrics_50rows.csv")
    P_e56 = paired_table(R, "E56_p", ARMS50)
    H.write_csv(P_e56, H.TABLES / "r1_paired_vs_E56.csv")
    P_per = paired_table(R, "PERSIST_p", ARMS50)
    H.write_csv(P_per, H.TABLES / "r1_paired_vs_persistence.csv")
    P_clim = paired_table(R, "CLIM_p", ARMS50)
    H.write_csv(P_clim, H.TABLES / "r1_paired_vs_climatology.csv")

    # regime split
    early, late = R[R["target"] < H.LATE_FROM], R[R["target"] >= H.LATE_FROM]
    Mreg = pd.concat([score_set(early, ARMS50).assign(regime="2024-Q2..2025-Q3"),
                      score_set(late, ARMS50).assign(regime="2025-Q4..2026-Q3")])
    H.write_csv(Mreg, H.TABLES / "r1_metrics_by_regime.csv")

    # per quarter and per province for the main arms
    main_cols = {"E56": "E56_p", "EW": "EW_p", "BPROJ": "BPROJ_p", "N1": "N1_p", "PERSIST": "PERSIST_p",
                 "MAJORITY": "MAJORITY_p"}
    pq = []
    for (tq), g in R.groupby("target"):
        r = {"target": tq, "HIGH": int(g["HIGH"].sum())}
        for k, c in main_cols.items():
            dec = g["EW_dec"] if k == "EW" else (g[c] >= .5).astype(int)
            r[f"{k}_acc"] = float((dec == g["HIGH"]).mean())
            r[f"{k}_brier"] = float(((g[c] - g["HIGH"]) ** 2).mean())
        pq.append(r)
    H.write_csv(pd.DataFrame(pq), H.TABLES / "r1_by_quarter.csv")
    pp = []
    for prov, g in R.groupby("province"):
        r = {"province": prov, "HIGH": int(g["HIGH"].sum()), "n": len(g)}
        for k, c in main_cols.items():
            dec = g["EW_dec"] if k == "EW" else (g[c] >= .5).astype(int)
            r[f"{k}_acc"] = float((dec == g["HIGH"]).mean())
            r[f"{k}_brier"] = float(((g[c] - g["HIGH"]) ** 2).mean())
        pp.append(r)
    H.write_csv(pd.DataFrame(pp), H.TABLES / "r1_by_province.csv")

    # 45-row set with the Chapter I baselines (E55 B1-B7)
    Bl = pd.read_csv(H.E55_BASELINES, dtype={"province_code": str})
    R45 = R.merge(Bl.rename(columns={"y": "y_e55"})[["target", "province_code", "y_e55"] + list(E55_ARMS)],
                  on=["target", "province_code"], how="inner")
    assert len(R45) == 45 and (R45["y_e55"] == R45["HIGH"]).all()
    arms45 = {**{k: v for k, v in ARMS50.items()}, **{n: (c, None, "Chapter I baseline (E55)") for c, n in E55_ARMS.items()}}
    M45 = score_set(R45, arms45)
    H.write_csv(M45, H.TABLES / "r1_metrics_45rows_with_chapter1_baselines.csv")
    P45 = paired_table(R45, "E56_p", {n: (c, None, "") for c, n in E55_ARMS.items()} | {"Persistence": ("PERSIST_p", None, "")})
    H.write_csv(P45, H.TABLES / "r1_paired_45rows_E56_vs_chapter1_baselines.csv")

    # r3: price layer against PS (provincial food-price pressure)
    price = {"E56 P_price": ("E56_p_price", None, "proposed price layer"),
             "E58-EW (P_price >= 0.5)": ("EW_p", "EW_dec", "warning"),
             "E60-A gov-only P_price": ("E60_A_p_price", None, "ablation"),
             "E60-C gov + improved news P_price": ("E60_C_p_price", None, "ablation"),
             "E64-D gov + news v3 P_price": ("E64_D_p_price", None, "ablation"),
             "CPI-projection rule": ("BPROJ_p", None, "rule"),
             "N1 L2-LR matched P_price": ("N1_p_price", None, "statistical"),
             "N2 L2-LR projection P_price": ("N2_p_price", None, "statistical"),
             "E60-B news-only P_price": ("E60_B_p_price", None, "news only"),
             "Persistence of PS": ("PS_PERSIST", None, "baseline"),
             "Climatology of PS (as-of rate)": ("PS_CLIM", None, "baseline")}
    lab = pd.read_csv(H.LABELS, dtype={"province_code": str})
    lab["qi"] = lab["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    R["tqi"] = R["target"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    # PS of the target quarter is known about 1 month after it ends; at issue (start of t) the latest complete
    # CPI quarter is t-1, i.e. target-3 for lead 2 -> persistence uses PS(target-3); climatology = mean PS up to then
    R["oqi"] = R["tqi"] - 2

    def ps_at(code, qi):
        v = lab[(lab["province_code"] == code) & (lab["qi"] == qi)]["PS"]
        return float(v.iloc[0]) if len(v) else np.nan

    R["PS_PERSIST"] = [ps_at(c, o - 1) for c, o in zip(R["province_code"], R["oqi"])]
    R["PS_CLIM"] = [float(lab[lab["qi"] <= o - 1]["PS"].mean()) for o in R["oqi"]]
    Mps = score_set(R, price, "PS")
    H.write_csv(Mps, H.TABLES / "r3_price_layer_vs_PS.csv")
    Pps = paired_table(R, "E56_p_price", price, "PS")
    H.write_csv(Pps, H.TABLES / "r3_price_layer_paired_vs_E56.csv")
    Pps2 = paired_table(R, "PS_PERSIST", price, "PS")
    H.write_csv(Pps2, H.TABLES / "r3_price_layer_paired_vs_persistence.csv")

    H.dump({"protocol_sha256": proto, "sealed": sealed, "reproduction": chk,
            "metrics50": M50.to_dict("records"), "paired_vs_E56": P_e56.to_dict("records"),
            "paired_vs_persistence": P_per.to_dict("records"), "metrics45": M45.to_dict("records"),
            "price_layer_vs_PS": Mps.to_dict("records"), "price_paired_vs_E56": Pps.to_dict("records"),
            "price_paired_vs_persistence": Pps2.to_dict("records")}, H.OUT / "r1_scoreboard.json")
    pd.set_option("display.width", 260, "display.max_columns", 30)
    show = ["arm", "accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "false_alarms", "missed_HIGH", "brier",
            "auc", "cal_slope", "onsets_detected", "quarters_acc_ge_0.75"]
    print(chk)
    print(M50[show].round(3).to_string(index=False))
    print(P_e56[["arm_name", "mean_brier_diff", "ci95_lo", "ci95_hi", "quarter_wins", "sign_p", "sign_p_holm",
                 "better_by_rule_holm"]].round(4).to_string(index=False))
    print(P_per[["arm_name", "mean_brier_diff", "ci95_hi", "sign_p_holm", "better_by_rule_holm"]].round(4).to_string(index=False))
    print(P_clim[["arm_name", "mean_brier_diff", "ci95_hi", "sign_p", "better_by_rule"]].round(4).to_string(index=False))
    print(Mreg[["regime"] + show[:8]].round(3).to_string(index=False))
    print(M45[show[:9]].round(3).to_string(index=False))
    print(P45[["arm_name", "mean_brier_diff", "ci95_lo", "ci95_hi", "sign_p_holm"]].round(4).to_string(index=False))
    print(Mps[show[:10]].round(3).to_string(index=False))
    print(Pps[["arm_name", "mean_brier_diff", "ci95_lo", "ci95_hi", "sign_p_holm", "better_by_rule_holm"]].round(4).to_string(index=False))
    print(Pps2[["arm_name", "mean_brier_diff", "ci95_hi", "sign_p_holm", "better_by_rule_holm"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
