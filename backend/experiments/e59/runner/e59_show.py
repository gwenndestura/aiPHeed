"""E59: append the results to E59_results.md below the unchanged pre-registration.
    python -B backend/experiments/e59/runner/e59_show.py"""
import json
from pathlib import Path

E59 = Path(__file__).resolve().parents[1]
r = json.loads((E59 / "E59_results.json").read_text(encoding="utf-8"))
md = E59 / "E59_results.md"
pre = md.read_text(encoding="utf-8").split("\n## Results")[0].rstrip()
f3 = lambda x: "–" if x is None else f"{x:.3f}"
o = [pre, "", "## Results", "",
     f"Run `{r['run']}`. k = 1 reproduces E49 (accuracy 0.846, balanced 0.841, AUC 0.855): **{r['k1_reproduces_E49']}**. "
     f"Protected md5s identical at start and end: **{r['md5_start'] == r['md5_end']}**.", "",
     "| k | Dates | Rows | LOW rows | Evaluable | Accuracy (95% CI) | Balanced | Precision | Recall | F1 | AUC | Brier | "
     "Persistence acc / bal / Brier |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for x in r["leads"]:
    m, p = x.get("model") or {}, x.get("persistence") or {}
    ci = m.get("accuracy_ci95")
    acc = f"{f3(m.get('accuracy'))} ({f3(ci[0])}-{f3(ci[1])})" if ci else f3(m.get("accuracy"))
    ev = "yes" if x["evaluable"] else f"**no** ({x.get('reason')})"
    o.append(f"| {x['k']} | {x['n_dates']} | {x['n_rows']} | {x.get('LOW_rows', '–')} | {ev} | {acc} | "
             f"{f3(m.get('balanced_accuracy'))} | {f3(m.get('precision'))} | {f3(m.get('recall'))} | {f3(m.get('f1'))} | "
             f"{f3(m.get('auc'))} | {f3(m.get('brier'))} | {f3(p.get('accuracy'))} / {f3(p.get('balanced_accuracy'))} / "
             f"{f3(p.get('brier'))} |")
o += ["", "Target quarters scored per lead:", ""]
for x in r["leads"]:
    o.append(f"- k = {x['k']}: {', '.join(x.get('target_quarters') or []) or 'none'}")
for key, title in (("algorithm3", "Algorithm 3 (mean fold accuracy >= 0.75)"),
                   ("algorithm3_ci", "CI version (95% lower bound >= 0.75)")):
    a = r[key]
    steps = "; ".join(f"k = {s['k']}: {'pass' if s['pass'] else 'stop'}"
                      + (f" ({s['value']:.3f})" if s.get("value") is not None else f" ({s.get('why')})")
                      for s in a["trail"])
    o += ["", f"**{title}:** {steps}. **Maximum Reliable Lead Time = {a['maximum_reliable_lead_time'] or 'none'} "
              f"quarter(s).**"]
o += ["", "### Reading", "",
      "- The search halts at k = 2: accuracy 0.709, below 75% and below persistence (0.800). The **Maximum Reliable "
      "Lead Time is one quarter** under both rules. At k = 1 the CI lower bound (0.769) also clears 75%.",
      "- Leads 3-6 are reported only for information: the search has already halted. Their accuracy (0.73-0.96) "
      "is not skill. With only 1-3 LOW rows each, balanced accuracy is at or below 0.5 and AUC falls to 0.25-0.82, "
      "the pattern of predicting HIGH almost everywhere when nearly every target quarter is HIGH.",
      "- Leads 7 and 8 have 3 and 1 scored dates (fewer than 4): not evaluable.",
      "- Development evidence only (all scored quarters were examined during development); different leads score "
      "different quarters."]
md.write_text("\n".join(o) + "\n", encoding="utf-8")
print("\n".join(o[o.index("## Results"):]))
