"""E52 report tables from the frozen run and the built record (no model is fitted here).

    backend/venv/Scripts/python.exe -B runner/e52_tables.py
      -> tables/per_quarter.csv, tables/metrics.csv, tables/trigger_audit.csv, tables/explanation_examples.md
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import pandas as pd

E52 = Path(__file__).resolve().parents[1]
RUN = sorted((E52 / "runs").glob("2026*"))[0]
REC = E52.parents[2] / "backend" / "data" / "e52" / "e52_record.json"
OUT = E52 / "tables"
ARMS = ["E52PS", "B1_PERSIST", "B2_LR_GOV", "B3_LGBM_GOV", "B4_LR_NLP", "B5_LGBM_NLP", "B6_LR_COMB", "B7_E38PROC",
        "CLIM", "HIGH", "LOW"]


def main():
    OUT.mkdir(exist_ok=True)
    R = pd.read_csv(RUN / "rows.csv", dtype={"province_code": str})
    res = json.loads((RUN / "results.json").read_text())
    rows = []
    for q, f in R.groupby("target"):
        r = {"target_quarter": q, "rows": len(f), "observed_HIGH": int(f["y"].sum())}
        for a in ("E52PS", "B1_PERSIST", "CLIM"):
            r[f"{a}_accuracy"] = round(float((f[f"{a}_yhat"] == f["y"]).mean()), 3)
            r[f"{a}_brier"] = round(float(((f[f"{a}_p"] - f["y"]) ** 2).mean()), 3)
        rows.append(r)
    pd.DataFrame(rows).to_csv(OUT / "per_quarter.csv", index=False)
    keys = ("accuracy", "balanced_accuracy", "recall_HIGH", "recall_LOW", "precision_HIGH", "f1_HIGH", "brier", "auc")
    pd.DataFrame([{"arm": a, **{k: (None if res["metrics"][a].get(k) is None else round(res["metrics"][a][k], 3))
                                for k in keys}} for a in ARMS]).to_csv(OUT / "metrics.csv", index=False)

    rec = json.loads(REC.read_text(encoding="utf-8"))
    cnt, mx, first, n = collections.Counter(), collections.defaultdict(float), collections.Counter(), 0
    entries = []
    for code, v in rec["provinces"].items():
        for q, e in list(v["pastDrivers"].items()) + [(rec["targetQuarter"], v)]:
            n += 1
            entries.append((v["name"], q, e))
            for g, s in e["triggerStatus"].items():
                cnt[(g, s["status"])] += 1
                c = e["fiveTriggerContributions"][g]
                mx[g] = max(mx[g], abs(c["foodInflationPoints"]), abs(c["gapPoints"]))
            d = e["drivers"]["drivers"][0]
            first[d["driver_group"] if d["group_shap"] else "none"] += 1
    groups = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
    pd.DataFrame([{"group": g, "province_quarters": n, "contributes": cnt[(g, "contributes")],
                   "no_effect": cnt[(g, "no_effect")], "insufficient_data": cnt[(g, "insufficient_data")],
                   "largest_effect_points": round(mx[g], 3), "ranked_first": first[g]} for g in groups]
                 ).to_csv(OUT / "trigger_audit.csv", index=False)

    def example(name, q, e):
        lines = [f"### {name}, {q}", ""]
        p = e.get("forecast", {}).get("probability", e.get("probability"))
        lines.append(f"- Probability of food-price pressure: {p:.3f}")
        for d in e["drivers"]["drivers"]:
            g = d["driver_group"]
            c = e["fiveTriggerContributions"][g]
            st = e["triggerStatus"][g]
            lines.append(f"- {d['driver_label']}: {st['status']}, log-odds {c['logOddsEffect']:+.3f} "
                         f"(food {c['foodInflationPoints']:+.2f} pts, gap {c['gapPoints']:+.2f} pts). "
                         f"Evidence: {st['evidenceNote']}")
        return "\n".join(lines + [""])
    pick = [x for x in entries if x[1] == rec["targetQuarter"] and x[0] == "Quezon"]
    for g in ("climate", "employment", "ofw_remittance"):      # one distinct example where each minor group counts
        pick += [x for x in entries if x[2]["triggerStatus"][g]["status"] == "contributes" and x not in pick][:1]
    (OUT / "explanation_examples.md").write_text(
        "# E52 explanation examples (from data/e52/e52_record.json)\n\n"
        "Log-odds effect = change in logit P(price signal) when the group's inputs are set to their training mean "
        "(E50 method). Status 'contributes' when the group moves food inflation or the gap by at least 0.1 points.\n\n"
        + "\n".join(example(*x) for x in pick), encoding="utf-8")
    print((OUT / "trigger_audit.csv").read_text())
    print((OUT / "per_quarter.csv").read_text())


if __name__ == "__main__":
    main()
