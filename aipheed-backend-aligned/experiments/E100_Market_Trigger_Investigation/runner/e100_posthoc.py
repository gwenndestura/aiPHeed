"""E100 POST-HOC sensitivity (NOT pre-registered; written after e100_run.py showed that the drop-one arms are
computable on only 8 quarters under the >= 4 domain rule). Same arms with a >= 3 domain minimum for the drop-one arms,
and the regional price / hunger series used to explain the sign of the affordability evidence. Writes ../out/posthoc_*.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e100_run as R  # noqa: E402

np, pd = R.np, R.pd


def main():
    R.verify()
    H = R.load_history()
    out_h = R.outcome_series()
    LV = R.level_indicator()
    R.MIN_DOMAINS = 3                                     # the post-hoc change
    arms = {"FULL3": R.build_arm(H, R.DOMS)[0]}
    for d in R.DOMS:
        arms[f"NO-{d}"] = R.build_arm(H, [x for x in R.DOMS if x != d])[0]
    ev = H[(H["t"] <= R.qi(R.EVAL_LAST_ORIGIN)) & H["target"].isin(out_h)]
    targets = sorted(ev["target"].unique(), key=R.qi)
    Q = pd.DataFrame({"target": targets})
    Q["H_obs"] = Q["target"].map(out_h)
    Q["y"] = (Q["H_obs"] > R.HUNGER_LINE).astype(int)
    for a, vals in arms.items():
        Q[a] = [np.mean([vals[(q, p)] for p in R.PROVS if vals.get((q, p)) is not None])
                if any(vals.get((q, p)) is not None for p in R.PROVS) else np.nan for q in targets]
    res = {"note": "post-hoc, not pre-registered", "arms": {}}
    for a in arms:
        g = Q.dropna(subset=["FULL3", a])
        m = R.metrics(g["y"], g[a])
        m["quarters"] = int(len(g))
        if a != "FULL3":
            m["vs_FULL3"] = R.paired(g["y"].to_numpy(float), g[a].to_numpy(float), g["FULL3"].to_numpy(float))
        res["arms"][a] = m
    # regional series: issue-time price indicators (raw x) and the outcome two quarters later
    rows = []
    lv = LV.groupby("t")["L"].mean().to_dict()
    for q in sorted(H["target"].unique(), key=R.qi):
        g = H[H["target"] == q]
        x = lambda k: np.nanmean([r[k]["x"] if r[k]["x"] is not None else np.nan for r in g["ind"]])  # noqa: E731
        t = R.qi(q) - 2
        rows.append({"target": q, "origin": R.qs(t), "A2_headline_above_usual": x("A2"), "A3_rice_yoy": x("A3"),
                     "A1_price_model": x("A1"), "L_food_level_since_2021Q1": lv.get(t), "H_target": out_h.get(q),
                     "dom_A": float(g["dom_A"].mean()) if g["dom_A"].notna().any() else None})
    S = pd.DataFrame(rows)
    S.to_csv(R.OUT / "posthoc_regional_series.csv", index=False, lineterminator="\n")
    (R.OUT / "posthoc_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for a, m in res["arms"].items():
        v = m.get("vs_FULL3") or {}
        print(a, m["quarters"], round(m["accuracy"], 3), round(m["brier"], 3),
              "" if not v else (round(v["mean_brier_diff_arm_minus_FULL"], 3), [round(c, 3) for c in v["ci95"]],
                                v["arm_better_quarters"], v["arm_worse_quarters"], round(v["sign_p"], 3)))
    print(S.round(2).to_string())


if __name__ == "__main__":
    main()
