"""E56: render E56_results.md from E56_results.json.   python -B backend/experiments/e56/runner/e56_show.py"""
import json
from pathlib import Path

E56 = Path(__file__).resolve().parents[1]
r = json.loads((E56 / "E56_results.json").read_text(encoding="utf-8"))
V = r["variants"]
DESC = {"L0": "median of all published quarters (served)", "L1": "median of the last 8 published quarters",
        "L2": "median of the last 4 published quarters", "L3": "above the five-province median of the same quarter (D only)"}
PROV = ["CALABARZON", "Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
DRV = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
f3 = lambda x: "–" if x is None else f"{x:.3f}"
pc = lambda x: f"{100 * x:.0f}%"
yes = lambda b: "yes" if b else "**no**"
o = ["# E56: label definitions (Eq. 3 variants) with E53-A1, lead 1", "",
     f"Run `{r['run']}`. Experiment only; nothing served changes. S1 = H + 2D in every variant; only the HIGH rule "
     "changes, and every threshold uses only quarters published before the origin. Model, inputs, pool, seed, nested "
     "walk-forward and C2 shrinkage are identical to E53-A1 (no tuning). Scored on the 13 E53 development quarters "
     "(65 rows).", "",
     "| Label | Rule |", "|---|---|"] + [f"| {k} | HIGH if S1 > {DESC[k]} |" if k != "L3" else f"| {k} | HIGH if S1 {DESC[k]} |"
                                        for k in V] + [""]
rep = r["L0_reproduces_E53_A1"]
o += [f"L0 reproduction of E53-A1: accuracy {f3(rep['accuracy'])}, balanced {f3(rep['balanced_accuracy'])}, AUC "
      f"{f3(rep['auc'])}, Brier {f3(rep['brier'])}, Q4 2026 CALABARZON {f3(rep['q4_calabarzon'])} "
      "(E53-A1: 0.785 / 0.836 / 0.880 / 0.150 / 0.789).", ""]
years = sorted({y for v in V.values() for y in v["label_stats"]["share_HIGH_per_year"]})
o += ["## 1. Label statistics", "", "Each labelled province-quarter is labelled at its own lead-1 origin.", "",
      "| Label | " + " | ".join(years) + " | 2024–2026 | quarters all 5 HIGH | LOW rows in the 65 | labels differ from L0 |",
      "|---|" + "---|" * (len(years) + 4)]
for k, v in V.items():
    s = v["label_stats"]
    o.append(f"| {k} | " + " | ".join(pc(s["share_HIGH_per_year"][y]["share"]) if y in s["share_HIGH_per_year"] else "–"
                                       for y in years)
             + f" | {pc(s['share_HIGH_2024_2026'])} | {s['n_quarters_all5_HIGH']} of {s['n_quarters_labelled']} | "
               f"{s['dev_LOW_rows']} | {pc(s['share_labels_differ_from_L0'])} |")
o += ["", "## 2. E53-A1 retrained per label (65 rows)", "",
      "| Label | Accuracy | Balanced | AUC | Brier | LOW caught | Persistence acc / bal | Always-majority (training) acc / bal | Majority (hindsight) acc |",
      "|---|---|---|---|---|---|---|---|---|"]
for k, v in V.items():
    m, p, a, h = v["model"], v["persistence"], v["always_majority_train"], v["always_majority_test"]
    o.append(f"| {k} | {f3(m['accuracy'])} | {f3(m['balanced_accuracy'])} | {f3(m['auc'])} | {f3(m['brier'])} | "
             f"{m['LOW_caught']}/{m['LOW_rows']} | {f3(p['accuracy'])} / {f3(p['balanced_accuracy'])} | "
             f"{f3(a['accuracy'])} / {f3(a['balanced_accuracy'])} | {f3(h['accuracy'])} ({h['class']}) |")
miss = {k: v["missing_dev_quarters"] for k, v in V.items() if v["missing_dev_quarters"]}
if miss:
    o += ["", f"Development quarters the walk-forward could not score: {miss}."]
o += ["", "## 3. Q4 2026 forecast (origin 2026-10-01) and five-driver shares", "",
      "| Label | " + " | ".join(PROV) + " | τ | training HIGH share |", "|---|" + "---|" * (len(PROV) + 2)]
for k, v in V.items():
    q = v["q4_2026"]
    o.append(f"| {k} | " + " | ".join(f3(q["index"][x]) for x in PROV) +
             f" | {f3(q['tau']) if q['tau'] is not None else '–'} | {pc(q['train_HIGH_share'])} |")
o += ["", "Five-driver shares, CALABARZON (%, of the five drivers):", "",
      "| Label | " + " | ".join(DRV) + " |", "|---|" + "---|" * len(DRV)]
for k, v in V.items():
    d = v["q4_2026"]["drivers"]["CALABARZON"]
    o.append(f"| {k} | " + " | ".join(str(d[x]) for x in DRV) + " |")
o += ["", "Per province:", "", "| Label | Province | " + " | ".join(DRV) + " |", "|---|---|" + "---|" * len(DRV)]
for k, v in V.items():
    for p in PROV[1:]:
        d = v["q4_2026"]["drivers"][p]
        o.append(f"| {k} | {p} | " + " | ".join(str(d[x]) for x in DRV) + " |")
o += ["", "## Adoption (rule fixed before results)", "",
      "| Label | (a) HIGH share 2024–26 in 30–70% | (b) bal ≥ 0.75 and ≥ persistence | (c) AUC ≥ 0.75 | (d) keeps H | Eligible |",
      "|---|---|---|---|---|---|"]
for k, v in V.items():
    c = v["adoption"]["criteria"]
    o.append(f"| {k} | {yes(c['a_HIGH_share_2024_2026_30_70'])} | {yes(c['b_bal_ge_0.75_and_ge_persistence'])} | "
             f"{yes(c['c_auc_ge_0.75'])} | {yes(c['d_keeps_H'])} | {yes(v['adoption']['eligible'])} |")
o += ["", f"**Result: {r['adoption']['chosen']}.** L0 is the incumbent and is not re-judged; L3 is reported only.", ""]
(E56 / "E56_results.md").write_text("\n".join(o), encoding="utf-8")
print("\n".join(o))
