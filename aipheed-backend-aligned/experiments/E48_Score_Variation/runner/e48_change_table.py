"""E48: per province and quarter - issue date, model, raw probability, displayed score, category, inputs (E38) or the
trigger evidence reference (e46), whether the score / inputs changed from the previous quarter; unchanged counts.

    (from backend/) venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E48_Score_Variation/runner/e48_change_table.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "runs"
api = json.loads((OUT / "api_scores_by_quarter.json").read_text())
e36 = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
e46 = json.loads(Path("data/e46/e46_record.json").read_text(encoding="utf-8"))
MEANINGFUL = 0.02          # a change below 2 percentage points is treated as not meaningful
NAMES = {v["name"]: c for c, v in e46["provinces"].items()}
rows, summary = [], {}
# E38 (production default): the E36/E38 record
for prov in NAMES:
    prev = None
    for q in e36["quarters"]:
        v = next(x for x in q["provinces"].values() if x["province"] == prov)
        x = {d["key"]: d["value"] for d in v.get("drivers", [])}
        shown = api["e38"].get(q["quarter"], {}).get("scores", {}).get(prov)
        r = {"mode": "e38", "province": prov, "quarter": q["quarter"], "issue": q["origin"], "lead": q["lead"],
             "model": q.get("model_id") or e36["served_engine"]["name"], "p_raw": v["p_high"], "displayed": shown,
             "category": "high" if (shown or 0) >= 0.5 else "low", "inputs": x,
             "observed_label": v.get("observed_label")}
        if prev:
            r["score_identical_to_previous"] = r["p_raw"] == prev["p_raw"]
            r["score_change"] = round(r["p_raw"] - prev["p_raw"], 4)
            r["inputs_changed"] = {k: x.get(k) != prev["inputs"].get(k) for k in x}
        rows.append(r)
        prev = r
# e46 (experimental, served when AIPHEED_LEAD2_MODEL=e46): candidate's own backtests / forecasts
for prov, code in NAMES.items():
    v = e46["provinces"][code]
    series = {x["targetQuarter"]: x for x in v["pastForecasts"] + v["earlierForecasts"]}
    series[e46["targetQuarter"]] = {"probability": v["forecast"]["probability"], "origin": e46["origin"]}
    prev = None
    for qid in sorted(series, key=lambda s: (int(s[:4]), int(s[-1]))):
        x = series[qid]
        shown = api["e46"].get(qid, {}).get("scores", {}).get(prov)
        pd_ = v.get("pastDrivers", {}).get(qid)
        r = {"mode": "e46", "province": prov, "quarter": qid, "issue": x.get("origin") or (pd_ or {}).get("origin"),
             "lead": 2, "model": "E46-I7", "p_raw": x["probability"], "displayed": shown,
             "category": "high" if (shown or 0) >= 0.5 else "low",
             "inputs": "triggerStatus evidence: e46_record pastDrivers[%s]" % qid if pd_ else "forecast triggerStatus",
             "observed_label": None if x.get("observedHigh") is None else ("HIGH" if x["observedHigh"] else "LOW")}
        if prev:
            r["score_identical_to_previous"] = r["p_raw"] == prev["p_raw"]
            r["score_change"] = round(r["p_raw"] - prev["p_raw"], 4)
        rows.append(r)
        prev = r
for mode in ("e38", "e46"):
    for prov in NAMES:
        rs = [r for r in rows if r["mode"] == mode and r["province"] == prov and "score_change" in r]
        same = sum(r["score_identical_to_previous"] for r in rs)
        small = sum(abs(r["score_change"]) < MEANINGFUL for r in rs)
        summary.setdefault(mode, {})[prov] = {"pairs": len(rs), "identical": same, "identical_pct": round(100 * same / len(rs), 1),
                                              "below_2pp": small, "below_2pp_pct": round(100 * small / len(rs), 1),
                                              "displayed_equals_record": all(abs((r["displayed"] or -1) - r["p_raw"]) < 5e-4
                                                                             for r in rows if r["mode"] == mode and r["province"] == prov
                                                                             and r["displayed"] is not None)}
    s = [r for r in rows if r["mode"] == mode and r["quarter"] >= "2025-Q4"]
    summary[mode]["_since_2025Q4"] = {"rows": len(s), "share_ge_0.95": round(sum((r["p_raw"] or 0) >= 0.95 for r in s) / len(s), 3)}
lab = [r for r in rows if r["mode"] == "e38" and r["observed_label"]]
summary["e38"]["_observed_v1_labels"] = {"HIGH": sum(r["observed_label"] == "HIGH" for r in lab), "LOW": sum(r["observed_label"] == "LOW" for r in lab),
                                         "HIGH_since_2023Q4": sum(r["observed_label"] == "HIGH" for r in lab if r["quarter"] >= "2023-Q4"),
                                         "rows_since_2023Q4": sum(1 for r in lab if r["quarter"] >= "2023-Q4")}
(OUT / "score_change_table.json").write_text(json.dumps({"meaningful_change_threshold": MEANINGFUL, "rows": rows,
                                                         "summary": summary}, indent=1, default=str))
print(json.dumps(summary, indent=1))
