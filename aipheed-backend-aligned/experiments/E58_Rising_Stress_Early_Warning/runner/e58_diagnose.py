"""E58 step 1: diagnosis of every E56 HIGH-risk miss in the E57 rolling-origin rows (already-scored E57 outcomes; this
step is analysis, not model selection). For each of the 50 rows it decomposes the forecast into the hunger part and the
price part, reconstructs what was known at the issue date, and compares it with what happened in the target quarter.

    backend/venv/Scripts/python.exe -B runner/e58_diagnose.py  -> tables/diagnosis_rows.csv, tables/diagnosis_summary.json
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E58 = Path(__file__).resolve().parents[1]
EXP = E58.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
E57_ROWS = sorted((EXP / "E57_E56_Rolling_Origin_Test" / "runs").glob("2026*"))[0] / "rows.csv"
COLS = ["F_now", "gap_now", "mom3", "D_now", "rice_whsl_yoy", "tc_count", "enso", "palay_yoy", "fish_yoy", "ur_yoy",
        "remit_usd_yoy", "news_n", "news_market", "tariff_yoy_regime", "import_suspension_share", "price_ceiling_share"]


def main():
    R = pd.read_csv(E57_ROWS, dtype={"province_code": str})
    d, X, B = E.load()
    Y = F.t43_labels(d)
    th = L.e40_spec()
    Hq = pd.read_csv(L.SWS_FILE).assign(q=lambda f: f["quarter"].map(L.qi)).groupby("q")["H"].mean()
    out = []
    for r in R.itertuples():
        t, p = int(r.t), r.province_code
        _, te = F.frame(d, X, B, t, None)
        row = te[te["province_code"] == p].iloc[0]
        yt = Y[(Y["province_code"] == p) & (Y["q"] == t + 2)].iloc[0]
        ylast = Y[(Y["province_code"] == p) & (Y["q"] == L.qi(r.PERSIST_from))].iloc[0] if isinstance(r.PERSIST_from, str) else None
        out.append({
            "target": r.target, "origin": r.origin_quarter, "province": r.province, "y": r.y, "E56_p": r.E56_p,
            "E56_p_price": r.E56_p_price, "E56_p_hunger": r.E56_p_hunger, "decision": int(r.E56_p >= 0.5),
            "outcome": ("TP" if r.y and r.E56_p >= 0.5 else "FN" if r.y else "FP" if r.E56_p >= 0.5 else "TN"),
            "latest_known_label_quarter": r.PERSIST_from, "latest_known_T43": r.PERSIST_p,
            "onset": int(r.y == 1 and r.PERSIST_p == 0),
            "H_last_known": r.H_last_known, "H_target": float(Hq[t + 2]),
            "F_target": float(yt["F"]), "G_target": float(yt["F"] - yt["HL"]),
            "food_thr": th["food"][p], "gap_thr": th["gap"][p],
            "F_last_known_q": None if ylast is None else float(ylast["F"]),
            "F_base_m1": float(row["base_1.0"]), "F_base_m0": float(row["base_0.0"]),
            "cpi_months_known_through": L.ym_s(L.m0_of(t)),
            "months_from_last_cpi_to_target_end": (L.qi(r.target) // 4 * 12 + (L.qi(r.target) % 4) * 3 + 2) - L.m0_of(t),
            **{c: (None if pd.isna(row.get(c)) else float(row.get(c))) for c in COLS},
        })
    D = pd.DataFrame(out)
    D["projection_error_F"] = D["F_target"] - D["F_base_m0"]
    D["price_part_missed"] = (D["y"] == 1) & (D["E56_p_price"] < 0.5)
    D["hunger_part_missed"] = (D["y"] == 1) & (D["E56_p_hunger"] < 0.5)
    tdir = E58 / "tables"
    tdir.mkdir(exist_ok=True)
    D.round(4).to_csv(tdir / "diagnosis_rows.csv", index=False)
    fn, tp = D[D["outcome"] == "FN"], D[D["outcome"] == "TP"]
    summ = {
        "HIGH": int(D["y"].sum()), "TP": len(tp), "FN": len(fn), "onset_events": int(D["onset"].sum()),
        "onset_missed": int(((D["onset"] == 1) & (D["outcome"] == "FN")).sum()),
        "FN_by_cause": {"hunger_part_below_0.5": int((fn["E56_p_hunger"] < 0.5).sum()),
                        "price_part_below_0.5_only": int(((fn["E56_p_hunger"] >= 0.5) & (fn["E56_p_price"] < 0.5)).sum()),
                        "both_parts_above_0.5_but_product_below": int(((fn["E56_p_hunger"] >= 0.5) & (fn["E56_p_price"] >= 0.5)).sum())},
        "FN_p_bins": {"<0.2": int((fn["E56_p"] < 0.2).sum()), "0.2-0.333": int(((fn["E56_p"] >= 0.2) & (fn["E56_p"] < 1 / 3)).sum()),
                      "0.333-0.5": int((fn["E56_p"] >= 1 / 3).sum())},
        "mean_projection_error_F": {"FN": float(fn["projection_error_F"].mean()), "TP": float(tp["projection_error_F"].mean()),
                                    "TN/FP": float(D[D["y"] == 0]["projection_error_F"].mean())},
        "mean_features": {k: {c: float(g[c].mean()) for c in COLS if g[c].notna().any()} for k, g in D.groupby("outcome")},
        "hunger_gap_at_issue": {"median_quarters_between_last_known_H_and_target": 3,
                                "note": "SWS rounds are posted 1-2 months after the survey quarter; at O(t) the latest round is t-1 "
                                        "(or t-2), so the target t+2 is 3-4 quarters after the last observed hunger value"},
        "cpi_lag_months_to_target_end": int(D["months_from_last_cpi_to_target_end"].iloc[0]),
    }
    (tdir / "diagnosis_summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print(fn[["target", "province", "E56_p", "E56_p_price", "E56_p_hunger", "latest_known_T43", "onset", "H_last_known", "H_target",
              "F_last_known_q", "F_base_m0", "F_target", "food_thr", "G_target", "gap_thr", "mom3", "rice_whsl_yoy",
              "tc_count", "news_n"]].round(2).to_string())
    print(json.dumps({k: v for k, v in summ.items() if k != "mean_features"}, indent=1, default=float))
    print(pd.DataFrame(summ["mean_features"]).round(2).to_string())


if __name__ == "__main__":
    main()
