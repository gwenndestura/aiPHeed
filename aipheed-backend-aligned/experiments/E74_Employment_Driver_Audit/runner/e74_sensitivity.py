"""E74: how much the employment indicator changes the served FIRI v2, and where its own-history percentile turns an
improving labour market into "risk". Reads out/trace_rows.json (built from the serving code). Diagnostic only: no served
value is changed.

  * rows where E1 < 0 (unemployment still falling year on year) but its score > 0.5 (it raised the index);
  * FIRI recomputed without the household-economy domain (weights renormalised over the other available domains,
    the same rule the index uses for any missing domain), and the class changes that produces.
"""
import json
from pathlib import Path

E74 = Path(__file__).resolve().parents[1]
rows = json.loads((E74 / "out" / "trace_rows.json").read_text())
flips, inverted, deltas = [], [], []
for r in rows:
    x, s = r["indicator_x"].get("E1"), r["indicator_score"].get("E1")
    if x is not None and s is not None and x < 0 and s > 0.5:
        inverted.append({"target": r["target"], "province": r["province"], "E1_change_points": round(x, 3), "E1_score": round(s, 3),
                         "E1_push": round(r["indicator_push"]["E1"], 4)})
    w = r["w"]
    if "E" not in w:
        continue
    # domain scores from the indicator scores (mean of observed indicators in the domain)
    dom = {}
    for k, v in r["indicator_score"].items():
        if v is not None and r["indicator_push"].get(k) is not None:
            dom.setdefault(k[0], []).append(v)
    dom = {d: sum(v) / len(v) for d, v in dom.items() if d in w}
    others = {d: v for d, v in dom.items() if d != "E"}
    tot = sum(w[d] for d in others)
    firi_noE = sum(w[d] * v for d, v in others.items()) / tot
    cls, cls_noE = r["class"], ("HIGH" if firi_noE >= 0.5 else "LOW")
    deltas.append(r["firi"] - firi_noE)
    if cls != cls_noE:
        flips.append({"target": r["target"], "province": r["province"], "firi": round(r["firi"], 4), "firi_without_employment": round(firi_noE, 4),
                      "class": cls, "class_without_employment": cls_noE})
fc = [r for r in rows if r["kind"] == "forecast"]
out = {"rows_with_employment": len(deltas), "mean_effect_of_employment_on_index": sum(deltas) / len(deltas),
       "max_effect": max(deltas), "class_changes_without_employment": flips,
       "improving_labour_market_scored_as_risk": inverted, "inverted_rows": len(inverted),
       "forecast_2027Q1_E1": [{"province": r["province"], "E1_change_points": r["indicator_x"]["E1"], "E1_score": r["indicator_score"]["E1"]} for r in fc],
       "interpretation": ("E1 is scored as a percentile of its own earlier values. Those were mostly large post-pandemic "
                          "falls in unemployment (2022-24), so from 2024-Q4 to 2025-Q4 a still-falling unemployment rate "
                          "scored above the historical middle and raised the index. This is a property of the FIRI v2 "
                          "normalisation (own-history percentile over a recovery period), not an arithmetic error.")}
(E74 / "out" / "employment_sensitivity.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k not in ("improving_labour_market_scored_as_risk",)}, indent=1))
print("inverted rows:", len(inverted), sorted({i["target"] for i in inverted}))
