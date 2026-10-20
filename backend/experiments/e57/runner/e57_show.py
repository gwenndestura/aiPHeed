"""E57: append the results to E57_results.md, keeping the pre-registration section unchanged.
    python -B backend/experiments/e57/runner/e57_show.py"""
import json
from pathlib import Path

E57 = Path(__file__).resolve().parents[1]
r = json.loads((E57 / "E57_results.json").read_text(encoding="utf-8"))
md = E57 / "E57_results.md"
pre = md.read_text(encoding="utf-8").split("\n## Results")[0].rstrip()
V = r["variants"]
f3 = lambda x: "–" if x is None else f"{x:.3f}"
yes = lambda b: "yes" if b else "**no**"
PROV = ["CALABARZON", "Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
o = [pre, "", "## Results", "",
     f"Run `{r['run']}`. V0 reproduces E53-A1: **{r['V0_reproduces_E53_A1']}**. Protected md5s identical at start and "
     f"end: **{r['md5_start'] == r['md5_end']}**.", "",
     "| Variant | Rows | Accuracy | Balanced | AUC | Brier | LOW caught | HIGH share 2024–26 | Persistence acc / bal | Flips | Flips caught |",
     "|---|---|---|---|---|---|---|---|---|---|---|"]
for k, v in V.items():
    m, p = v["model"], v["persistence"]
    o.append(f"| {k} | {m['n']} | {f3(m['accuracy'])} | {f3(m['balanced_accuracy'])} | {f3(m['auc'])} | {f3(m['brier'])} | "
             f"{m['LOW_caught']}/{m['LOW_rows']} | {100 * m['HIGH_share_2024_2026']:.0f}% | "
             f"{f3(p['accuracy'])} / {f3(p['balanced_accuracy'])} | {m['flips']} | {m['flips_caught']} |")
o += ["", "Flips = rows whose label differs from y_last; flips caught = those the model called correctly.", ""]
for k, v in V.items():
    if v["missing_dev_quarters"]:
        o.append(f"{k} not scored on {', '.join(v['missing_dev_quarters'])}.")
if "V2" in V:
    o += ["", "V2 deviation from the pre-registered 50 rows: 2023-Q1, 2026-Q2 and 2026-Q3 have no V2 label (S1 missing "
          "for 2022-Q1, 2025-Q2, 2025-Q3), as pre-registered. In addition, 2023-Q2 and 2023-Q3 were skipped by the "
          "unchanged E36 walk-forward rule (needs >= 10 training rows; V2 has only 5 there, because the first comparable "
          "quarters are 2022-Q2..Q4). So V2 is scored on 40 rows, and persistence on the same 40."]
o += ["", "### Q4 2026 probabilities (origin 2026-10-01)", "", "| Variant | " + " | ".join(PROV) + " |",
      "|---|" + "---|" * len(PROV)]
for k, v in V.items():
    o.append(f"| {k} | " + " | ".join(f3(v["q4_2026"][x]) for x in PROV) + " |")
o += ["", "### Adoption", "", "| Variant | (a) bal ≥ 0.75 and > persistence | (b) AUC ≥ 0.75 | (c) keeps H | (d) V2 HIGH share 30–70% | Eligible |",
      "|---|---|---|---|---|---|"]
for k in ("V1", "V2"):
    c = V[k]["adoption"]["criteria"]
    d = c.get("d_HIGH_share_2024_2026_30_70")
    o.append(f"| {k} | {yes(c['a_bal_ge_0.75_and_gt_persistence'])} | {yes(c['b_auc_ge_0.75'])} | {yes(c['c_keeps_H'])} | "
             f"{'n/a' if d is None else yes(d)} | {yes(V[k]['adoption']['eligible'])} |")
o += ["", f"**Verdict: {r['adoption']['verdict']}**", "", "### Leakage check", ""]
for k, v in V.items():
    lk = v["leakage"]
    o.append(f"- {k}: {lk['checks']} (origin, quarter) checks for y_last and the V2 comparison; "
             f"{len(lk['violations'])} used a quarter not fully posted before its origin.")
md.write_text("\n".join(o) + "\n", encoding="utf-8")
print("\n".join(o[o.index("## Results"):]))
