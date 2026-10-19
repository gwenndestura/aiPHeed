"""E61 A3: root cause of every HIGH outcome that E56 forecast below 0.5 (all 8 false negatives; the 6 below 0.2 are
the brief's cases), using only what was published before each issue date for the "known at issue" columns.

For each miss: the E56 model is re-run at its origin (deterministic; reproduction checked against the sealed value),
its exact TreeSHAP attribution is recomputed, and the information available at the issue date (latest food YoY and gap,
recent change, rice wholesale change, latest posted hunger, the base-effect projections) is set beside what happened
afterwards (the quarterly path to the target). The outcome path is read from the full data and is used ONLY to diagnose.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a3_missed_high.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, G, E = X.np, X.pd, X.L, X.F, X.G, X.E


def main():
    X.verify_sealed()
    R = pd.read_csv(X.TABLES / "a2_rows50.csv", dtype={"province_code": str})
    miss = R[(R["HIGH"] == 1) & (R["E56_p"] < 0.5)].copy()
    d, Xf, B = E.load()
    full = d
    Fq = L.quarter_F(full).set_index(["province_code", "q"])["F"]
    Hq = L.quarter_F(full, "all_items").set_index(["province_code", "q"])["F"]
    space = G.search_space()
    rows, cache = [], {}
    for r in miss.itertuples():
        t = int(r.t)
        if t not in cache:
            cache[t] = G.tuned_forecast(d, Xf, B, t, space)
        fx = cache[t]
        i = list(L.PROVS).index(r.province_code)
        rep_err = abs(float(fx["p"][i]) - r.E56_p)
        att = F.attribution(fx, i)
        te = fx["te"].iloc[i]
        cut = d.cut(t)
        Fc = L.quarter_F(cut).set_index(["province_code", "q"])["F"]
        Hc = L.quarter_F(cut, "all_items").set_index(["province_code", "q"])["F"]
        p = r.province_code

        def known(q):
            return (round(float(Fc[(p, q)]), 2), round(float(Fc[(p, q)] - Hc[(p, q)]), 2)) if (p, q) in Fc.index else None

        def actual(q):
            return (round(float(Fq[(p, q)]), 2), round(float(Fq[(p, q)] - Hq[(p, q)]), 2)) if (p, q) in Fq.index else None
        top = sorted(att["per_feature"].items(), key=lambda kv: abs(kv[1]), reverse=True)[:5]
        m = fx["cfg"]["m"]
        rows.append({
            "target": r.target, "province": r.province, "issue_date": str(L.origin(t).date()), "E56_p": r.E56_p,
            "reproduction_error": rep_err, "p_hunger": r.E56_p_hunger, "p_price": r.E56_p_price,
            "config": int(fx["cfg"]["id"]), "drift_m": m, "feature_set": fx["cfg"]["feat"],
            "latest_hunger_posted": r.H_last_known, "hunger_at_target": r.H_all,
            "known_at_issue_q_t-1_foodYoY_gap": known(t - 1), "known_at_issue_q_t-2_foodYoY_gap": known(t - 2),
            "F_now_m0_months": float(te["F_now"]), "gap_now": float(te["gap_now"]), "D_now": float(te["D_now"]),
            "rice_whsl_yoy_t-1": None if pd.isna(te["rice_whsl_yoy"]) else float(te["rice_whsl_yoy"]),
            "projection_foodYoY_selected_m": float(te[f"base_{m}"]), "projection_gap_selected_m": float(te[f"gbase_{m}"]),
            "projection_foodYoY_m1": float(te["base_1.0"]), "projection_gap_m1": float(te["gbase_1.0"]),
            "actual_path_t_t+1_t+2": [actual(t), actual(t + 1), actual(t + 2)],
            "threshold_food": r.thr_food, "threshold_gap": r.thr_gap, "food_margin": r.food_margin,
            "gap_margin": r.gap_margin, "ps_by": r.ps_by,
            "logit_projection_minus_train_mean": att["groups"]["market"] - sum(
                v for k, v in att["per_feature"].items() if E.group_of(k) == "market"),
            "logit_groups": {k: round(v, 3) for k, v in att["groups"].items() if abs(v) > 1e-9},
            "top_tree_features": [(k, round(v, 3)) for k, v in top]})
    out = pd.DataFrame(rows)
    X.write_csv(out.astype({c: str for c in out.columns if out[c].dtype == object}), X.TABLES / "a3_missed_high_cases.csv")
    X.dump(rows, X.OUT / "a3_missed_high.json")
    for r in rows:
        print("\n", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
