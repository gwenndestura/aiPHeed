"""E67 r2 (PROTOCOL 3): coverage and missing-data audit of every trigger-group feature of the E56 frame.

For each feature: geography / source / cadence (E60 FEATURE_AVAILABILITY_AND_TIMING.csv), NaN and exact-zero shares in
the training frames and test rows of the 12 origins, and the value status at the 2027-Q1 origin (issue 2026-10-01).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4/runner/r2_coverage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e67_lib as K  # noqa: E402

H, L, E, F, P2, np, pd = K.H, K.L, K.E, K.F, K.P2, K.np, K.pd
META = K.EXP / "E60_E58_Accuracy_Optimization" / "FEATURE_AVAILABILITY_AND_TIMING.csv"
# how an absent observation is encoded, from the feature builders (e44_classifiers / e46 policy / news aggregation)
ENCODING = {
    "tc_count": "0 = no storm within 300 km; an incomplete quarter (2026-Q3, fetched 2026-09-09) is also 0 (D-E66-5)",
    "tc_count_l1": "0 = no storm in t-1",
    "news_market": "share of the quarter's titles; 0 = no matching title among news_n > 0 titles (measured, thin)",
    "news_climate": "as news_market", "news_fish_kill": "as news_market", "news_employment": "as news_market",
    "news_ofw_remittance": "as news_market",
    "remit_usd_yoy": "NaN after the BSP file ends (2025-Q4); LightGBM learned missing branch, never 0",
    "remit_php_yoy": "as remit_usd_yoy",
    "tariff_yoy_regime": "0 = no order in force (policy calendar, not an observation)",
    "import_suspension_share": "0 = no order in force", "price_ceiling_share": "0 = no order in force",
    "food_emergency_share": "0 = no declaration in force",
}


def main():
    K.verify_protocol()
    d, X, B = E.load()
    meta = pd.read_csv(META).set_index("feature")
    feats = [c for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g]] + list(F.M.POLICY)
    rows = []
    for t in K.EVAL_ORIGINS + K.FORWARD_ORIGINS:
        tr, te = F.frame(d, X, B, t, "AS")
        for c in feats:
            rows.append({"origin_quarter": L.qs(t), "feature": c, "group": K.group_of(c) if not c.startswith("news_") else "news",
                         "train_rows": int(len(tr)), "train_nan": float(tr[c].isna().mean()),
                         "train_zero": float((tr[c] == 0).mean()), "test_nan": float(te[c].isna().mean()),
                         "test_zero": float((te[c] == 0).mean())})
    R = pd.DataFrame(rows)
    ev = R[R["origin_quarter"].isin([L.qs(t) for t in K.EVAL_ORIGINS])]
    last = R[R["origin_quarter"] == "2026-Q3"].set_index("feature")
    summ = []
    for c in feats:
        m = meta.loc[c] if c in meta.index else None
        g = ev[ev["feature"] == c]
        summ.append({"feature": c, "group": g["group"].iloc[0],
                     "source": None if m is None else m["source"], "geography": None if m is None else m["geography"],
                     "period_at_issue": None if m is None else m["period_used_at_issue_O(t)"],
                     "eval_test_nan_share": float(g["test_nan"].mean()), "eval_test_zero_share": float(g["test_zero"].mean()),
                     "train_nan_share_at_2027Q1_origin": float(last.loc[c, "train_nan"]),
                     "test_nan_at_2027Q1_origin": float(last.loc[c, "test_nan"]),
                     "test_zero_at_2027Q1_origin": float(last.loc[c, "test_zero"]),
                     "absent_value_encoding": ENCODING.get(c, "NaN when unobserved (LightGBM missing branch)")})
    S = pd.DataFrame(summ)
    H.write_csv(R, K.TABLES / "r2_coverage_by_origin.csv")
    H.write_csv(S, K.TABLES / "r2_coverage_summary.csv")
    # one row per trigger group for the report
    grp = S.groupby("group").agg(features=("feature", "count"), mean_eval_nan=("eval_test_nan_share", "mean"),
                                 mean_eval_zero=("eval_test_zero_share", "mean"),
                                 nan_at_2027Q1=("test_nan_at_2027Q1_origin", "mean")).reset_index()
    H.write_csv(grp, K.TABLES / "r2_coverage_by_group.csv")
    H.dump({"protocol_sha256": K.verify_protocol(), "features": len(feats),
            "always_zero_in_eval_tests": S.loc[S["eval_test_zero_share"] >= 0.95, "feature"].tolist(),
            "missing_at_2027Q1": S.loc[S["test_nan_at_2027Q1_origin"] > 0, "feature"].tolist()}, K.OUT / "r2_coverage.json")
    print(grp.to_string())
    print(S[["feature", "group", "geography", "eval_test_nan_share", "eval_test_zero_share", "test_nan_at_2027Q1_origin"]].to_string())


if __name__ == "__main__":
    main()
