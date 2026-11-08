"""FINAL_THESIS_OBJECTIVES Addendum 2: does better news coverage (regional FSSI-v3, N1R) improve the Chapter I risk
forecast? CH1-LGBM with the audited inputs + N1R vs the audited-input CH1-LGBM (rerun_predictions_lead{k}.csv).

    python news_coverage.py      # out/n1r_predictions_lead{k}.csv, out/news_coverage.json
"""
from __future__ import annotations

import functools
import sys

import rerun_ch1 as R

A, C, FM, E, L, np, pd = R.A, R.C, R.FM, R.E, R.L, R.np, R.pd
OUT = R.OUT
CH1 = R.CH1


@functools.lru_cache(maxsize=64)
def n1r(t: int) -> float:
    from app.news import pipeline_v3 as P
    sc = P.intensities()
    q = f"{t // 4}-Q{t % 4 + 1}"
    vals = [sc[a["article_key"]] for a in P.asof(t) if a.get("quarter") == q and a["article_key"] in sc]
    return float(np.mean(vals)) if len(vals) >= 5 else float("nan")


def main():
    want = (CH1 / "runner" / "ADDENDUM_2_SHA256.txt").read_text().strip()
    assert FM.sha256(CH1 / "ADDENDUM_2_NEWS_COVERAGE.md") == want, "Addendum 2 changed after freezing"
    R.use_corrected()
    base_build = C.build_X

    def build_X(k, d=None, x=None, origins=None):
        X = base_build(k, d, x, origins)
        X["N1R"] = [n1r(int(t)) for t in X["t"]]
        return X
    C.build_X = build_X
    C.COLS = C.COLS + ["N1R"]
    C.NEWS_COLS = C.NEWS_COLS + ["N1R"]
    C.GOV_COLS = [c for c in C.COLS if c not in C.NEWS_COLS]
    C.FAMILY_OF["N1R"] = "N1"
    res, ps = {"leads": {}}, {}
    for k in C.LEADS:
        D = C.run_lead(k)
        D.to_csv(OUT / f"n1r_predictions_lead{k}.csv", index=False, lineterminator="\n", float_format="%.6g")
        P0 = pd.read_csv(OUT / f"rerun_predictions_lead{k}.csv", dtype={"province_code": str})
        j = D[["province_code", "q", "y", "CH1_p"]].merge(P0[["province_code", "q", "CH1_p"]], on=["province_code", "q"],
                                                          suffixes=("_n1r", "_base"))
        y = j["y"].astype(int).to_numpy()
        b = FM.boot_diff(j, (j["CH1_p_n1r"] - y) ** 2, (j["CH1_p_base"] - y) ** 2)
        dec = C.decide(D)
        res["leads"][k] = {"n": len(j), "acc_n1r": float(((j["CH1_p_n1r"] >= .5).astype(int) == y).mean()),
                           "acc_base": float(((j["CH1_p_base"] >= .5).astype(int) == y).mean()),
                           "brier_diff": b, "reliable_n1r": dec["reliable"], "criteria_n1r": dec["criteria"],
                           "n1r_coverage": float(D["shap_N1R"].notna().mean()) if "shap_N1R" in D else None}
        ps[k] = b["p_two"]
        print(k, round(res["leads"][k]["acc_n1r"], 3), round(res["leads"][k]["acc_base"], 3), round(b["diff"], 4),
              round(b["p_two"], 3))
    h = FM.holm(ps)
    for k in res["leads"]:
        res["leads"][k]["holm_p"] = h[k]
    res["coverage_quarters_with_n1r"] = int(sum(np.isfinite(n1r(t)) for t in range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1)))
    res["news_coverage_adds_value"] = any(res["leads"][k]["brier_diff"]["diff"] < 0 and res["leads"][k]["holm_p"] < 0.05
                                          for k in res["leads"])
    FM.write_json(OUT / "news_coverage.json", res)
    print("adds value:", res["news_coverage_adds_value"], "| quarters with N1R:", res["coverage_quarters_with_n1r"])


if __name__ == "__main__":
    main()
