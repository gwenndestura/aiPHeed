"""Y0: reproduce P0H4 Lead 1/2 and FIRI Lead 2 exactly, and audit the scoring for bugs.

Checks: the stored evaluation.json criteria; a second, independent rule implementation; confusion-matrix order (sklearn
with explicit labels); probability orientation (AUC of p vs 1 - p); missing values; probabilities exactly at 0.50;
target = origin + lead; product structure P0H4 = pi_H4 * P0_price; label definition y = hunger AND price with hunger =
BL H > 11.3; the hunger term uses only SWS rounds published before the issue date; baselines use issue-time information.
Writes out/y0_audit.json.

    python -B audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p2lib as P  # noqa: E402

R, RV = P.R, P.RV
OUT = Path(__file__).resolve().parent / "out"


def main():
    d = P.load_p0h4()
    ev = json.loads((P.ROOT / "backend" / "data" / "ch1_engine" / "evaluation.json").read_text(encoding="utf-8"))
    res = {"P0H4": {}}
    obs = R.observed()
    for k in (1, 2):
        g = d[d["lead"] == k].copy()
        off = P.official_rules(g, RV.P)
        ind = P.independent_rules(g, RV.P)
        stored = ev["leads"][str(k)]["criteria"]
        st_m = ev["leads"][str(k)]["metrics"]
        checks = {
            "officialEqualsStored": {r.split()[0]: v["pass"] for r, v in off["rules"].items()} == stored,
            "independentEqualsOfficial": {r: v for r, v in ind["rules"].items()} ==
                                         {r.split()[0]: v["pass"] for r, v in off["rules"].items()},
            "cmMatchesStored": (ind["cm"]["TP"], ind["cm"]["FP"], ind["cm"]["FN"], ind["cm"]["TN"]) ==
                               (st_m["tp"], st_m["fp"], st_m["fn"], st_m["tn"]),
            "brierMatchesStored": abs(ind["brier"] - st_m["brier"]) < 1e-9,
            "orientation_auc_p_gt_auc_1mp": ind["auc"] > ind["auc_of_1_minus_p"],
            "missingValues": int(g[[RV.P, "y", "PERSIST-SI_p", "CLIM_p", "ALWAYS-LOW_p", "pi_H4", "P0_price"]].isna().sum().sum()),
            "probsExactlyHalf": int((g[RV.P] == 0.5).sum()),
            "probsWithin1e-3OfHalf": int(((g[RV.P] - 0.5).abs() < 1e-3).sum()),
            "targetEqualsOriginPlusLead": bool(((g["q"] - g["t"]) == k).all()),
            "productStructure_maxAbs": float((g[RV.P] - g["pi_H4"] * g["P0_price"]).abs().max()),
            "labelEqualsHungerAndPrice": bool((g["y"] == (g["hunger"] & g["price"])).all()),
            "hungerLabelEqualsBL>11.3": bool((g["hunger"] == (g["q"].map(lambda q: obs[("BL", int(q))]) > R.H_LINE)
                                              .astype(int)).all()),
            "persistBaselineBinary": sorted(g["PERSIST-SI_p"].round(6).unique().tolist())[:6],
        }
        # the newest SWS reading used by the hunger term was published before the issue date
        lag = []
        for t in sorted(g["t"].unique()):
            kn = R.known("BL", R.issue(int(t)))
            q_last = max(kn)
            rr = R.rounds()[(R.rounds()["area"] == "BL") & (R.rounds()["q"] == q_last)]
            used = rr[rr["published"] < R.issue(int(t))]
            lag.append({"origin": R.qs(int(t)), "issue": str(R.issue(int(t)).date()), "newestSwsQuarter": R.qs(q_last),
                        "roundsUsed": f"{len(used)}/{len(rr)}", "usedValue": round(float(used["H"].mean()), 2),
                        "newestUsedRoundPublished": str(used["published"].max().date()), "trueHorizon": int(t + k - q_last),
                        "publishedBeforeIssue": bool(len(used) and used["published"].max() < R.issue(int(t)))})
        checks["hungerInputsPublishedBeforeIssue"] = all(x["publishedBeforeIssue"] for x in lag)
        res["P0H4"][f"lead{k}"] = {"official": {"failed": off["failed"], "rules": off["rules"]},
                                   "independent": ind, "checks": checks, "timing": lag,
                                   "designEffect": P.design_effect(g, RV.P), "metrics": P.full_metrics(g, RV.P)}

    # FIRI v2 Lead 2 (regional, 17 targets)
    import score_firi_l2 as F
    fr = pd.read_csv(P.EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    fr["q"] = fr["target"].map(R.qi)
    fr["ALWAYS-HIGH"], fr["ALWAYS-LOW"] = 1.0, 0.0
    fres = F.rules(fr)
    m = R.metrics(fr["y"], fr["F2"])
    res["FIRI_L2"] = {"cm": f"{m['TP']}/{m['FP']}/{m['FN']}/{m['TN']}", "metrics": m,
                      "rules": fres["rules"], "failed": [r.split()[0] for r, v in fres["rules"].items() if not v["pass"]],
                      "orientation_auc_p_gt_auc_1mp": m["auc"] > 1 - m["auc"],
                      "labelEqualsBL>11.3": bool((fr["y"] == (fr["H_obs"] > R.H_LINE).astype(int)).all()),
                      "note": "FIRI v2 is a 0-1 index, not a probability; its Brier is computed on the index as stored."}
    OUT.mkdir(exist_ok=True)
    (OUT / "y0_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in (1, 2):
        r = res["P0H4"][f"lead{k}"]
        print(f"P0H4 L{k} CM {r['independent']['cm']} failed {r['official']['failed']} checks {r['checks']}")
        print("   design effect", r["designEffect"])
        print("   CI", r["metrics"]["accuracyCI90"], r["metrics"]["balancedCI90"])
        print("   R5", r["independent"]["R5_detail"])
    print("FIRI", res["FIRI_L2"]["cm"], res["FIRI_L2"]["failed"], res["FIRI_L2"]["labelEqualsBL>11.3"])
    for x in res["P0H4"]["lead2"]["timing"]:
        print("  ", x)


if __name__ == "__main__":
    main()
