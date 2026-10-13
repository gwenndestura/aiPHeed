"""Objective 3: rebuild all 142 LGU rankings and verify them independently.

* Independent implementation (this file) of: within-province min-max of poverty incidence and population density
  (persons / land km2), vulnerability = 0.6 * poverty_norm + 0.4 * density_norm, risk_index = province
  probability x vulnerability, clamped to [0, 1].
* Compared row by row with the backend's app.ml.inference.disaggregator.Disaggregator (frames injected through
  the guard; no unguarded read).
* Province probabilities: the E23 PROPOSED model's sealed BACKTEST forecast for 2026-Q1 (origin 2026-01-01, lead 1).
  Labelled as a backtest. The 2027-Q1 forecast does not exist (INSUFFICIENT_DATA), so its ranking is unavailable.
Usage: python -B runner/build_rankings.py <E23 run id>"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(guard.AL))
from app.ml.inference.disaggregator import Disaggregator  # noqa: E402

EXP = guard.EXP
PROV_NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
              "PH040400000": "Rizal", "PH040500000": "Batangas"}   # app/ml/corpus/geocoder.py


def independent(cen, pov, probs):
    m = cen.merge(pov[["lgu_code", "poverty_incidence_pct", "source_note"]], on="lgu_code", how="left")
    assert m["poverty_incidence_pct"].notna().all() and len(m) == 142
    m["density"] = m["population_2020"] / m["land_area_km2"]
    for c in ("poverty_incidence_pct", "density"):
        g = m.groupby("province_code")[c]
        rng = (g.transform("max") - g.transform("min")).replace(0, 1)
        m[c + "_norm"] = (m[c] - g.transform("min")) / rng
    m["vulnerability_index"] = 0.6 * m["poverty_incidence_pct_norm"] + 0.4 * m["density_norm"]
    m["province_probability"] = m["province_code"].map(probs)
    m["risk_index"] = (m["province_probability"] * m["vulnerability_index"]).clip(0, 1).round(4)
    m["poverty_is_province_fallback"] = m["source_note"].str.contains("fallback", case=False)
    m = m.sort_values(["risk_index", "lgu_code"], ascending=[False, True]).reset_index(drop=True)
    m["rank_region"] = np.arange(1, len(m) + 1)
    m["rank_in_province"] = m.groupby("province_code")["risk_index"].rank(ascending=False, method="min").astype(int)
    return m


def main():
    run = sys.argv[1]
    sealed = EXP / "runs" / run / "predictions_origin.csv"
    seal = json.loads((EXP / "runs" / run / "SEAL_origin.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(sealed.read_bytes()).hexdigest() == seal["sha256"]
    P = pd.read_csv(sealed, dtype={"province_code": str})
    p = P[(P["model"] == "PROPOSED_lgbm_combined") & (P["lead"] == 1) & (P["target_quarter"] == "2026-Q1")]
    probs = dict(zip(p["province_code"], p["score"]))
    cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet",
                                     ["province_code", "province_name", "lgu_code", "lgu_name", "lgu_type",
                                      "population_2020", "land_area_km2", "density_per_km2"])
    pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet",
                                     ["province_code", "lgu_code", "lgu_name", "year", "poverty_incidence_pct", "source_note"])
    ind = independent(cen, pov, probs)
    d = Disaggregator()
    d._lgu, d._pov = cen.copy(), pov.copy()
    be = d.disaggregate([{"province_code": k, "risk_probability": v, "data_sufficiency_flag": "LIMITED_SIGNAL"}
                         for k, v in probs.items()], "2026-Q1")
    cmp = ind.merge(be[["lgu_code", "risk_index", "vulnerability_index", "poverty_is_province_fallback"]],
                    on="lgu_code", suffixes=("", "_backend"))
    max_risk = float((cmp["risk_index"] - cmp["risk_index_backend"]).abs().max())
    max_vul = float((cmp["vulnerability_index"] - cmp["vulnerability_index_backend"]).abs().max())
    order_same = ind["lgu_code"].tolist() == be.sort_values(["risk_index", "lgu_code"], ascending=[False, True])["lgu_code"].tolist()
    # missing-province behaviour after the fix
    miss = d.disaggregate([{"province_code": k, "risk_probability": v} for k, v in probs.items() if k != "PH040300000"],
                          "2026-Q1")
    q = miss[miss["province_code"] == "PH040300000"]
    out = ind[["rank_region", "rank_in_province", "province_code", "lgu_code", "lgu_name", "lgu_type",
               "province_probability", "poverty_incidence_pct", "poverty_is_province_fallback", "density",
               "vulnerability_index", "risk_index"]].copy()
    out.insert(3, "province", out["province_code"].map(PROV_NAMES))
    out["quarter"] = "2026-Q1 (BACKTEST, origin 2026-01-01)"
    out["disaggregation_label"] = ("Relative ordinal estimate derived from the province forecast; not an official "
                                   "classification or an independent municipal forecast.")
    od = EXP / "rankings"
    od.mkdir(exist_ok=True)
    out.to_csv(od / "lgu_rankings_backtest_2026Q1.csv", index=False, lineterminator="\n")
    ver = {"n_lgus": int(len(ind)), "by_province": ind.groupby("province_code").size().to_dict(),
           "province_probabilities_source": f"E23 run {run}, sealed sha256 {seal['sha256']}",
           "max_abs_diff_risk_index_vs_backend": max_risk, "max_abs_diff_vulnerability_vs_backend": max_vul,
           "same_order_as_backend": order_same,
           "poverty_province_fallback_lgus": int(ind["poverty_is_province_fallback"].sum()),
           "poverty_lgu_specific_lgus": int((~ind["poverty_is_province_fallback"]).sum()),
           "distinct_poverty_values_per_province": ind.groupby("province_code")["poverty_incidence_pct"].nunique().to_dict(),
           "missing_province_after_fix": {"risk_index_all_null": bool(q["risk_index"].isna().all()),
                                          "flag": q["data_sufficiency_flag"].unique().tolist(),
                                          "ranked_last": bool(miss.tail(len(q))["province_code"].eq("PH040300000").all())},
           "ranking_2027Q1": "UNAVAILABLE: no 2027-Q1 province forecast (forecast record status INSUFFICIENT_DATA)"}
    (od / "ranking_verification.json").write_text(json.dumps(ver, indent=1, default=str), encoding="utf-8")
    print(json.dumps(ver, indent=1, default=str))


if __name__ == "__main__":
    main()
