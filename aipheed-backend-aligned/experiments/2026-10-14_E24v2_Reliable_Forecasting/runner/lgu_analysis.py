"""E24v2 LGU ranking analysis (FROZEN_EVALUATION_PROTOCOL.md 8; descriptive).  Usage: python -B runner/lgu_analysis.py

Uses the pipeline's own ranking (backend_dev replay record for 2026-Q3, PCF lead-1 province probabilities) and
the identity-verified LGU table.  Answers: does the approved method distinguish LGUs by poverty, or does it only
reflect population density?  Writes LGU_RANKING_VALIDATION.csv and runs/lgu_analysis.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

EXP = guard.EXP
BD = EXP / "backend_dev"


def main():
    rec = json.loads((BD / "data" / "quarterly_runs" / "replays" / "2026-Q3" / "forecast_record.json").read_text(
        encoding="utf-8"))
    rk = pd.DataFrame(rec["forecast"]["lgu_ranking"])
    lg = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    m = rk.merge(lg[["lgu_code", "population_2020", "land_area_km2", "poverty_lgu_estimate", "poverty_source"]],
                 on="lgu_code", validate="one_to_one")
    assert len(m) == 142
    prov = rec["forecast"]["leads"]["1"]["provinces"]
    pp = {v["province"]: v["risk"]["p_high"] for v in prov.values()}
    m["province_probability"] = m["province"].map(pp)
    out = {"lgus": 142, "with_municipal_estimate": int(m["poverty_lgu_estimate"].notna().sum()),
           "province_mean_substitute": int(m["poverty_lgu_estimate"].isna().sum()), "by_province": {}}
    for p, g in m.groupby("province"):
        rho_d = spearmanr(g["vulnerability_index"], g["density"]).statistic
        sub = g[g["poverty_lgu_estimate"].isna()]
        rho_sub = spearmanr(sub["vulnerability_index"], sub["density"]).statistic if len(sub) > 2 else None
        out["by_province"][p] = {"lgus": int(len(g)), "municipal_estimates": int(g["poverty_lgu_estimate"].notna().sum()),
                                 "spearman_vulnerability_vs_density": float(rho_d),
                                 "spearman_vulnerability_vs_density_substitute_rows": rho_sub,
                                 "province_probability_pcf_2026Q3": pp[p]}
    s = m[m["poverty_lgu_estimate"].notna()]
    out["municipal_estimate_rows"] = {
        "n": int(len(s)), "spearman_poverty_vs_density": float(spearmanr(s["poverty_lgu_estimate"], s["density"]).statistic),
        "note": "sign < 0 means denser LGUs are less poor; the approved 0.4 density weight then pushes in the opposite "
                "direction to the 0.6 poverty weight"}
    # How much of the region-wide order is the province probability vs the vulnerability index?
    out["regionwide_spearman_risk_vs_vulnerability"] = float(spearmanr(m["risk_index"], m["vulnerability_index"]).statistic)
    out["regionwide_spearman_risk_vs_province_probability"] = float(
        spearmanr(m["risk_index"], m["province_probability"]).statistic)
    out["province_probability_range"] = [float(min(pp.values())), float(max(pp.values()))]
    # rank stability: competition-rank ties and identical vulnerability values
    out["tied_risk_values"] = int(m["risk_index"].duplicated(keep=False).sum())
    m["ranking_basis"] = np.where(m["poverty_lgu_estimate"].isna(),
                                  "density only within province (poverty term is a labelled province-mean substitute)",
                                  "PSA 2021 municipal poverty estimate + density")
    m["ranking_quarter"] = "2026-Q3 (REPLAY, PCF lead 1; outcome protected)"
    cols = ["lgu_code", "lgu_name", "lgu_type", "province", "population_2020", "land_area_km2", "density",
            "poverty_lgu_estimate", "poverty_value_used", "poverty_value_kind", "poverty_source", "vulnerability_index",
            "province_probability", "risk_index", "rank_region", "rank_in_province", "ranking_basis",
            "ranking_quarter", "limitation"]
    m.sort_values(["rank_region", "lgu_code"])[cols].to_csv(EXP / "LGU_RANKING_VALIDATION.csv", index=False,
                                                            lineterminator="\n")
    (EXP / "runs" / "lgu_analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
