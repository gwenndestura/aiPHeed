"""E53 report tables from the committed runs and the built record (no model is fitted here).

    backend/venv/Scripts/python.exe -B runner/e53_tables.py
      -> tables/metrics_all_arms.csv, per_quarter.csv, confusion_by_quarter.csv, reliability.csv,
         trigger_ablation.csv, trigger_attribution.csv, explanation_examples.md
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pandas as pd

E53 = Path(__file__).resolve().parents[1]
RUN1 = E53 / "runs" / "20261017T140057Z"
RUNI2 = E53 / "runs" / "i2_20261017T140757Z"
E52REC = E53.parents[2] / "backend" / "data" / "e52" / "e52_record.json"
E53REC = E53.parents[2] / "backend" / "data" / "e53" / "e53_record.json"
OUT = E53 / "tables"
KEYS = ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc")
ARMS = ["R0", "C1", "C2", "C3", "C4", "LGB-R", "LGB-RL", "LGB-C", "LGB-R2", "LGB-C2", "B1_PERSIST", "B2_LR_GOV",
        "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC", "CLIM", "HIGH", "LOW"]
ABL = ["A-climate", "A-fish_kill", "A-employment", "A-ofw_remittance", "A-news", "A-policy", "A-mkt"]


def main():
    OUT.mkdir(exist_ok=True)
    r1, r2 = (json.loads((r / "results.json").read_text()) for r in (RUN1, RUNI2))
    M = {**r1["metrics"], **r2["metrics"]}
    cal = {**r1["calibration"], **r2["calibration"]}
    loqo = {**r1["leave_one_quarter_out"], **r2["leave_one_quarter_out"]}
    crit = {**r1["criteria"], **r2["criteria"]}
    rows = []
    for a in ARMS + ABL:
        m = M[a]
        rows.append({"arm": a, "round": "I2" if a in r2["metrics"] else "run1",
                     **{k: None if m.get(k) is None else round(m[k], 3) for k in KEYS},
                     "acc_ci_low": round(m["accuracy_ci95"][0], 3), "acc_ci_high": round(m["accuracy_ci95"][1], 3),
                     "citl": None if a not in cal else round(cal[a]["citl"], 3),
                     "cal_slope": None if a not in cal or cal[a]["slope"] is None else round(cal[a]["slope"], 3),
                     "min_loqo": None if a not in loqo else round(min(loqo[a].values()), 3),
                     **({c: crit[a][c] for c in ("A1", "A2", "A3", "A4", "A5", "K1", "K2")} if a in crit else {}),
                     **m["confusion"]})
    pd.DataFrame(rows).to_csv(OUT / "metrics_all_arms.csv", index=False)

    R = pd.read_csv(RUN1 / "rows.csv").merge(
        pd.read_csv(RUNI2 / "rows.csv")[["target", "province_code"] + [f"{a}_{s}" for a in ("C3", "C4", "LGB-R2", "LGB-C2")
                                                                     for s in ("p", "yhat")]],
        on=["target", "province_code"])
    pq, cq = [], []
    for q, g in R.groupby("target"):
        r = {"target": q, "observed_HIGH": int(g["y"].sum()), "mean_p_R0": round(g["R0_p"].mean(), 3)}
        for a in ("R0", "C1", "C3", "LGB-R", "LGB-R2", "LGB-C", "B1_PERSIST"):
            r[f"{a}_acc"] = round(float((g[f"{a}_yhat"] == g["y"]).mean()), 2)
        pq.append(r)
        for a in ("R0", "LGB-R", "LGB-R2", "B1_PERSIST"):
            cq.append({"target": q, "arm": a, "TP": int(((g[f"{a}_yhat"] == 1) & (g["y"] == 1)).sum()),
                       "TN": int(((g[f"{a}_yhat"] == 0) & (g["y"] == 0)).sum()),
                       "FP": int(((g[f"{a}_yhat"] == 1) & (g["y"] == 0)).sum()),
                       "FN": int(((g[f"{a}_yhat"] == 0) & (g["y"] == 1)).sum())})
    pd.DataFrame(pq).to_csv(OUT / "per_quarter.csv", index=False)
    pd.DataFrame(cq).to_csv(OUT / "confusion_by_quarter.csv", index=False)
    rel = [{"arm": a, **b} for a in ("R0", "C1", "C2", "C3", "C4", "LGB-R", "LGB-R2") for b in cal[a]["reliability"]]
    pd.DataFrame(rel).to_csv(OUT / "reliability.csv", index=False)
    pb = r1["paired_brier_vs_R0"]
    pd.DataFrame([{"ablation": a, "brier": round(M[a]["brier"], 4), "accuracy": M[a]["accuracy"],
                   "brier_change_vs_R0": round(pb[a]["diff"], 4), "ci_low": round(pb[a]["ci95"][0], 4),
                   "ci_high": round(pb[a]["ci95"][1], 4), "adds_reliable_information": pb[a]["ci95"][0] > 0}
                  for a in ABL]).to_csv(OUT / "trigger_ablation.csv", index=False)

    tally = []
    for name, path in (("E52 record (before D-1)", E52REC), ("E53 record (D-1)", E53REC)):
        rec = json.loads(path.read_text(encoding="utf-8"))
        cnt, first, n, other = collections.Counter(), collections.Counter(), 0, []
        for v in rec["provinces"].values():
            for e in list(v["pastDrivers"].values()) + [v]:
                n += 1
                for g, s in e["triggerStatus"].items():
                    cnt[(g, s["status"])] += 1
                    if s.get("inputsPresent", 1) < 1:
                        cnt[(g, "partial_inputs")] += 1
                d = e["drivers"]["drivers"][0]
                first[d["driver_group"] if d["group_shap"] else "none"] += 1
                other.append(e["drivers"]["other_pct"])
        for g in ("market", "climate", "fish_kill", "employment", "ofw_remittance"):
            tally.append({"record": name, "group": g, "province_quarters": n, "contributes": cnt[(g, "contributes")],
                          "no_effect": cnt[(g, "no_effect")], "insufficient_data": cnt[(g, "insufficient_data")],
                          "partial_inputs": cnt[(g, "partial_inputs")], "ranked_first": first[g],
                          "median_other_pct": round(float(pd.Series(other).median()), 1),
                          "max_other_pct": round(float(max(other)), 1)})
    pd.DataFrame(tally).to_csv(OUT / "trigger_attribution.csv", index=False)

    rec = json.loads(E53REC.read_text(encoding="utf-8"))
    lines = ["# E53 explanation examples (backend/data/e53/e53_record.json, D-1 attribution)", "",
             "Log-odds effect = change in logit of the served probability when the group's inputs are set to their "
             "training mean. 'contributes' = moves food inflation or the gap by at least 0.1 points. Model attributions, "
             "not causes.", ""]
    picks = [("Quezon", rec["targetQuarter"]), ("Cavite", rec["targetQuarter"]), ("Laguna", "2025-Q4"), ("Batangas", "2026-Q3")]
    for name, q in picks:
        v = next(x for x in rec["provinces"].values() if x["name"] == name)
        e = v if q == rec["targetQuarter"] else v["pastDrivers"][q]
        p = v["forecast"]["probability"] if q == rec["targetQuarter"] else e["probability"]
        lines += [f"## {name}, {q} (issued {e.get('origin', rec['origin'])})", "",
                  f"- P(food-price pressure) = {p:.3f} -> {'HIGH' if p >= 0.5 else 'LOW'}"]
        for d in e["drivers"]["drivers"]:
            g = d["driver_group"]
            c, s = e["fiveTriggerContributions"][g], e["triggerStatus"][g]
            lines.append(f"- {d['driver_label']}: {s['status']}, inputs present {s['inputsPresent']:.0%}, log-odds "
                         f"{c['logOddsEffect']:+.3f} (food {c['foodInflationPoints']:+.2f}, gap {c['gapPoints']:+.2f} pts). "
                         f"{s['evidenceNote']}")
        o = e["otherContribution"]
        lines += [f"- Other (total news volume): log-odds {o['logOddsEffect']:+.3f}; other share {e['drivers']['other_pct']}%",
                  f"- Checks: {', '.join(f'{k} {v:.1e}' for k, v in e['checks'].items())}", ""]
    (OUT / "explanation_examples.md").write_text("\n".join(lines), encoding="utf-8")
    print(pd.DataFrame(rows)[["arm", "accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier", "auc", "citl",
                               "min_loqo"]].to_string(index=False))
    print(pd.DataFrame(tally).to_string(index=False))


if __name__ == "__main__":
    main()
