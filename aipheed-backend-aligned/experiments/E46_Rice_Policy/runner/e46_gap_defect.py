"""E46 gap-defect (D1) trace and quantification on identical data and rows.

Original calculation (E44 I2 / E46 I6, e44_components.forecast):
    raw CPI index -> base-effect projections base_m (food) and hl_m (all items) at the selected drift multiplier m
    -> F_hat = base_m + residual model (food only)            [headline stays hl_m]
    -> P(price) = 1 - Phi((min(c_food, c_gap + hl_m) - F_hat) / s_F)   i.e. implied gap = F_hat - hl_m
Corrected calculation (E46 I7, e46_i7.forecast):
    F_hat = base_m + residual_F (no intercept);  G_hat = (base_m' - hl_m') + residual_G (no intercept)
    -> P(price) = 1 - Phi2((c_food - F_hat)/s_F, (c_gap - G_hat)/s_G; rho)

Both runs use the same data, origins (information cut at O(t) = day 1), targets and rows.

    backend/venv/Scripts/python.exe -B runner/e46_gap_defect.py  -> runs/gap_defect_quantification.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_lib as M  # noqa: E402

L, P2, np, pd = M.L, M.P2, M.np, M.pd
RUN6 = M.E46 / "runs" / "20261016T225203Z"
RUN7 = M.E46 / "runs" / "i7_20261017T000111Z"
RUN1 = M.E46.parent / "E44_Five_Trigger_Optimization" / "runs" / "20261015T150213Z"


def frame():
    d = L.load()
    th = L.e40_spec()
    origins = list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1))
    B = P2.bases(d, origins)
    P6 = pd.read_csv(RUN6 / "predictions.csv", dtype={"province_code": str})
    P7 = pd.read_csv(RUN7 / "predictions_i7.csv", dtype={"province_code": str})
    P1 = pd.read_csv(RUN1 / "predictions.csv", dtype={"province_code": str})[["t", "province_code", "target_q", "y"]]
    sel = json.loads((RUN6 / "selections.json").read_text())["I6"]
    F = L.quarter_F(d)
    HL = L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    Y = F.merge(HL, on=["province_code", "q"]).assign(G=lambda f: f["F"] - f["HL"]).rename(columns={"q": "target_q"})
    P = (P1.merge(P6, on=["t", "province_code"]).merge(P7, on=["t", "province_code"])
         .merge(B, on=["t", "province_code"]).merge(Y, on=["province_code", "target_q"]))
    P = P.dropna(subset=["I6_F_hat", "I7_F_hat"])
    P["mult"] = P["t"].map(lambda t: sel[L.qs(int(t))]["price_cfg"]["mult"])
    P["hl_sel"] = [r[f"hl_{m}"] for m, r in zip(P["mult"], P.to_dict("records"))]
    P["base_sel"] = [r[f"base_{m}"] for m, r in zip(P["mult"], P.to_dict("records"))]
    P["G_implied_I6"] = P["I6_F_hat"] - P["hl_sel"]
    P["ps"] = ((P["F"] > P["province_code"].map(th["food"])) | (P["G"] > P["province_code"].map(th["gap"]))).astype(int)
    return P


def main():
    P = frame()
    lab = P[P["y"].notna()]
    s44 = lab[lab["target_q"] >= L.qi("2024-Q3")]
    out = {"rows_all_evaluable": int(len(P)), "targets": [L.qs(int(P["target_q"].min())), L.qs(int(P["target_q"].max()))],
           "I6_selected_multipliers": sorted(set(P["mult"])),
           "bias": {nm: {"residual_correction_to_F": float((D["I6_F_hat"] - D["base_sel"]).mean()),
                         "headline_projection_bias": float((D["hl_sel"] - D["HL"]).mean()),
                         "gap_bias_I6_implied": float((D["G_implied_I6"] - D["G"]).mean()),
                         "gap_bias_uncorrected_bases": float((D["base_sel"] - D["hl_sel"] - D["G"]).mean()),
                         "gap_bias_I7": float((D["I7_G_hat"] - D["G"]).mean()),
                         "food_bias_I6": float((D["I6_F_hat"] - D["F"]).mean()),
                         "food_bias_I7": float((D["I7_F_hat"] - D["F"]).mean())}
                    for nm, D in (("all_evaluable", P), ("S44_rows", s44))},
           "price_probability_mean": {"I6_p_price": float(P["I6_p_price"].mean()), "I7_p_price": float(P["I7_p_price"].mean()),
                                      "observed_price_signal_rate": float(P["ps"].mean())}}
    ch = {}
    for nm, D in (("all_labelled", lab), ("S44_rows", s44)):
        a, b = D["I6_yhat"].astype(int), D["I7_yhat"].astype(int)
        y = D["y"].astype(int)
        ch[nm] = {"rows": int(len(D)), "decisions_changed": int((a != b).sum()),
                  "HIGH_to_LOW": int(((a == 1) & (b == 0)).sum()), "LOW_to_HIGH": int(((a == 0) & (b == 1)).sum()),
                  "changes_that_fixed_an_error": int(((a != b) & (b == y)).sum()),
                  "changes_that_created_an_error": int(((a != b) & (a == y)).sum()),
                  "false_positives_I6": int(((a == 1) & (y == 0)).sum()), "false_positives_I7": int(((b == 1) & (y == 0)).sum()),
                  "false_negatives_I6": int(((a == 0) & (y == 1)).sum()), "false_negatives_I7": int(((b == 0) & (y == 1)).sum()),
                  "accuracy_I6": float((a == y).mean()), "accuracy_I7": float((b == y).mean())}
    out["decision_changes_I6_to_I7"] = ch
    out["note"] = ("I7 also changes the decision layer (fixed p >= 0.5 instead of a per-origin Platt + threshold refit) and "
                   "the residual (ridge without intercept, forward-chaining selection); the decision counts are the total "
                   "effect of D1-D3, the bias rows isolate D1.")
    (M.E46 / "runs" / "gap_defect_quantification.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
