"""E99-F Q7: H4 ranking-agreement task (Chapter I H4: LGU rankings consistent with DA Region IV-A evaluators).

`build`: the fixed LGU sets. For each province, the 6 LGUs at the served within-province vulnerability ranks of
quantiles 0, 0.2, 0.4, 0.6, 0.8 and 1 (position round(q * (n - 1)) in the served order; ties by PSGC), shown to
evaluators in alphabetical order, without aiPHeed's order. Vulnerability = 0.6 x poverty_norm + 0.4 x density_norm
within province (the served, static index), so the set does not change with the quarter.
`score`: long-format responses (respondent_id, agency, consent, province, lgu_code, evaluator_rank; 1 = most
vulnerable). Per evaluator: Spearman rho between their ranks and aiPHeed's. H4 null REJECTED only if >= 10 eligible
evaluators, median rho >= 0.40 and a one-sided Wilcoxon signed-rank test of rho > 0 gives p < 0.05.
Run from backend/:  py -3.13 .../h4_ranking.py build | score responses.csv [out.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SETS = HERE / "h4_lgu_sets.csv"
QUANTILES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
DA = re.compile(r"^\s*(DA\s*(RFO)?\s*(Region)?\s*IV-?A|Department of Agriculture.*(IV-?A|CALABARZON))\s*$", re.I)


def build() -> pd.DataFrame:
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    v["density"] = v["population_2024"] / v["land_area_km2"]
    out = []
    for prov, g in v.groupby("province"):
        mm = lambda s: (s - s.min()) / ((s.max() - s.min()) or 1)  # noqa: E731
        g = g.assign(vulnerability=0.6 * mm(g["poverty_value_used"]) + 0.4 * mm(g["density"]))
        g = g.sort_values(["vulnerability", "lgu_code"], ascending=[False, True]).reset_index(drop=True)
        g["aipheed_rank_in_province"] = np.arange(1, len(g) + 1)
        pos = sorted({round(q * (len(g) - 1)) for q in QUANTILES})
        s = g.loc[pos, ["province", "lgu_code", "lgu_name", "aipheed_rank_in_province", "vulnerability", "poverty_source"]]
        s["substituted_poverty"] = s["poverty_source"].str.contains("substitute|province value", case=False)
        out.append(s.drop(columns="poverty_source"))
    S = pd.concat(out).sort_values(["province", "lgu_name"]).reset_index(drop=True)
    S.to_csv(SETS, index=False)
    return S


def score(path: Path) -> dict:
    from scipy.stats import spearmanr, wilcoxon
    S = pd.read_csv(SETS, dtype={"lgu_code": str})
    R = pd.read_csv(path, dtype={"lgu_code": str, "respondent_id": str})
    R = R.dropna(how="all")
    if R.empty:
        return {"status": "NO_RESPONSES", "eligible_evaluators": 0, "required_minimum": 10}
    rhos, excluded = {}, []
    for rid, g in R.groupby("respondent_id"):
        prov = g["province"].iloc[0]
        want = set(S.loc[S["province"] == prov, "lgu_code"])
        why = (None if DA.match(str(g["agency"].iloc[0])) else "agency is not DA Region IV-A")
        why = why or (None if str(g["consent"].iloc[0]).strip().lower() == "yes" else "no recorded consent")
        why = why or (None if set(g["lgu_code"]) == want and g["evaluator_rank"].nunique() == len(want)
                      else "incomplete or tied ranking of the province set")
        if why:
            excluded.append({"respondent_id": rid, "reason": why})
            continue
        m = g.merge(S[["lgu_code", "aipheed_rank_in_province"]], on="lgu_code")
        rhos[rid] = {"province": prov, "rho": float(spearmanr(m["evaluator_rank"], m["aipheed_rank_in_province"]).statistic)}
    r = np.array([x["rho"] for x in rhos.values()])
    out = {"eligible_evaluators": len(r), "excluded": excluded, "per_evaluator": rhos}
    if len(r) < 10:
        out.update({"status": "INSUFFICIENT", "h4_decision": "not decidable (fewer than 10 eligible evaluators)"})
        return out
    p = float(wilcoxon(r, alternative="greater").pvalue)
    med = float(np.median(r))
    out.update({"status": "SCORED", "median_rho": med, "wilcoxon_p_one_sided": p,
                "h4_decision": "H4 rejected (rankings consistent with evaluators)" if med >= 0.40 and p < 0.05 else "H4 not rejected"})
    return out


if __name__ == "__main__":
    if sys.argv[1] == "build":
        print(build().to_string())
    else:
        res = score(Path(sys.argv[2]))
        txt = json.dumps(res, indent=1)
        if len(sys.argv) > 3:
            Path(sys.argv[3]).write_text(txt, encoding="utf-8")
        print(txt)
