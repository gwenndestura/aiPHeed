"""Quarter-level evidence (Addendum 3, verification analyses): one observation per target quarter, so the five
province rows that share one regional hunger value are not counted as independent outcomes.

For each lead and comparator: quarters where CH1-LGBM has more correct province calls, fewer, or the same; an exact
one-sided sign test on the quarters that differ; and sensitivities for the two verification findings (the one
rounding-sensitive label and the threshold window that ends after the first Lead-1 issue date).

    python quarter_tests.py     # out/verify_quarter_level.json
"""
from __future__ import annotations

import json
from math import comb

from common import FM, OUT, np, pd

COMPS = ["ALWAYS-LOW", "PERSIST-SI", "CLIM", "LGBM-GOV", "STRUCT"]


def sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    return float(sum(comb(n, i) for i in range(wins, n + 1)) / 2 ** n) if n else 1.0


def main():
    out = {}
    for k in range(1, 9):
        D = pd.read_csv(OUT / f"horizon_predictions_lead{k}.csv", dtype={"province_code": str})
        c = lambda col: ((D[col] >= .5).astype(int) == D["y"]).groupby(D["q"]).sum()  # noqa: E731
        ch = c("CH1_p")
        res = {"quarters": int(len(ch)), "quarters_with_a_high": int((D.groupby("q")["y"].sum() > 0).sum())}
        for b in COMPS:
            o = c(f"{b}_p")
            w, l_ = int((ch > o).sum()), int((ch < o).sum())
            res[b] = {"ch1_better_quarters": w, "ch1_worse_quarters": l_, "ties": int((ch == o).sum()),
                      "sign_test_p_one_sided": sign_p(w, l_)}
        out[k] = res
        print(k, {b: (res[b]["ch1_better_quarters"], res[b]["ch1_worse_quarters"],
                      round(res[b]["sign_test_p_one_sided"], 3)) for b in COMPS})
    # sensitivities at Lead 1 (descriptive)
    D = pd.read_csv(OUT / "horizon_predictions_lead1.csv", dtype={"province_code": str})
    ok = ((D["CH1_p"] >= .5).astype(int) == D["y"])
    lab = json.loads((OUT / "verify_labels.json").read_text(encoding="utf-8"))
    flip = {(r["province_code"], r["target_quarter"]) for r in lab["leads"]["1"]["label_disagreements"]}
    y2 = [1 - y if (p, q) in flip else y for p, q, y in zip(D["province_code"], D["target_quarter"], D["y"])]
    ok2 = ((D["CH1_p"] >= .5).astype(int) == np.array(y2))
    late = pd.to_datetime(D["issue_date"]) >= pd.Timestamp("2023-04-01")
    out["lead1_sensitivity"] = {
        "reported": {"correct": int(ok.sum()), "n": int(len(D)), "accuracy": float(ok.mean())},
        "index_recomputed_label": {"flipped_rows": sorted(f"{p} {q}" for p, q in flip), "correct": int(ok2.sum()),
                                   "accuracy": float(ok2.mean())},
        "issue_after_threshold_window_published": {"rule": "issue date >= 2023-04-01 (2022-Q4 SWS published "
                                                           "2023-01-19; December 2022 CPI early January 2023)",
                                                   "n": int(late.sum()), "correct": int(ok[late].sum()),
                                                   "accuracy": float(ok[late].mean())}}
    print(out["lead1_sensitivity"])
    FM.write_json(OUT / "verify_quarter_level.json", out)


if __name__ == "__main__":
    main()
