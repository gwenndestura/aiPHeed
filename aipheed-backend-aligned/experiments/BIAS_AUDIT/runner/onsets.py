"""Why Lead 2 misses every new HIGH onset (served P0H4): each onset row (province LOW in q-1, HIGH in q) and each
sustained-HIGH row, with the component that failed and what was published before the issue date.

    python onsets.py   # out/onsets.csv, out/onsets.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402

U, C, FM, E, L, np, pd = X.U, X.C, X.FM, X.E, X.L, X.np, X.pd
OUT = HERE.parent / "out"


def main():
    U.setup()
    D = pd.read_csv(EXP / "LEAD2_OPTIMIZATION" / "out" / "predictions_addendum3.csv", dtype={"province_code": str})
    cases = pd.read_csv(EXP / "LEAD2_ONE_MODEL" / "out" / "p0h4_lead2_cases.csv")
    lab = C.labels().set_index(["province_code", "q"])
    hq = C.bl_quarters()
    g = D[D["lead"] == 2].copy()
    g["prev_y"] = [lab["y"].get((p, q - 1), np.nan) for p, q in zip(g["province_code"], g["q"])]
    g["prev_hunger"] = [lab["hunger"].get((p, q - 1), np.nan) for p, q in zip(g["province_code"], g["q"])]
    g["prev_price"] = [lab["price"].get((p, q - 1), np.nan) for p, q in zip(g["province_code"], g["q"])]
    g = g[g["y"] == 1].copy()
    g["event"] = np.where(g["prev_y"] == 0, "onset", np.where(g["prev_y"] == 1, "sustained HIGH", "no previous label"))
    # which condition switched on: hunger, price or both
    g["switched_on"] = np.select([(g["prev_hunger"] == 0) & (g["prev_price"] == 1),
                                  (g["prev_hunger"] == 1) & (g["prev_price"] == 0),
                                  (g["prev_hunger"] == 0) & (g["prev_price"] == 0)],
                                 ["hunger", "price", "both"], "none (previous LOW without label)")
    g["missed_by"] = np.where(g["P0H4_p3"] >= .5, "caught",
                              np.where(g["pi_H4"] < .5, np.where(g["P0_price"] < .5, "both components", "hunger component"),
                                       np.where(g["P0_price"] < .5, "price component", "product of two >= .5")))
    g["hunger_obs_target"] = g["q"].map(hq)
    g["target"], g["origin"], g["province"] = g["q"].map(L.qs), g["t"].map(L.qs), g["province_code"].map(L.NAMES)
    g = g.merge(cases[["target", "province", "issue_date", "sws_newest_q", "sws_newest_published", "A1_food",
                       "A1_gap", "pattern"]], on=["target", "province"], how="left")
    cols = ["event", "switched_on", "origin", "issue_date", "target", "province", "sws_newest_q", "sws_newest_published",
            "h_last", "hunger_obs_target", "pi_H4", "P0_price", "P0H4_p3", "A1_food", "A1_gap", "missed_by", "pattern"]
    g = g[cols].sort_values(["event", "target", "province"])
    g.to_csv(OUT / "onsets.csv", index=False, lineterminator="\n", float_format="%.3g")
    lines = ["Lead-2 HIGH rows of the served P0H4 (65 rows, 13 target quarters 2023-Q2..2026-Q3; 17 HIGH)",
             g.to_string(index=False), "",
             "onsets by what switched on x component that missed:",
             pd.crosstab(g[g["event"] == "onset"]["switched_on"], g[g["event"] == "onset"]["missed_by"]).to_string(),
             "", "sustained HIGH by component:", g[g["event"] == "sustained HIGH"]["missed_by"].value_counts().to_string()]
    (OUT / "onsets.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
