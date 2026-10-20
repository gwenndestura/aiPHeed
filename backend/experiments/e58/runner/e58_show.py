"""E58: append the results to E58_results.md below the unchanged pre-registration.
    python -B backend/experiments/e58/runner/e58_show.py"""
import json
from pathlib import Path

E58 = Path(__file__).resolve().parents[1]
r = json.loads((E58 / "E58_results.json").read_text(encoding="utf-8"))
md = E58 / "E58_results.md"
pre = md.read_text(encoding="utf-8").split("\n## Results")[0].rstrip()
f3, f4 = (lambda x: "–" if x is None else f"{x:.3f}"), (lambda x: "–" if x is None else f"{x:.4f}")
PROV = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
ARMS = ["C2", "T", "P"]
yes = lambda b: "yes" if b else "**no**"
o = [pre, "", "## Results", "",
     f"Run `{r['run']}`. C2 reproduces E53-A1 and the served record: **{r['C2_reproduces_E53_A1']}** "
     f"(lead 1 max |C2 - record| {r['leads']['1']['C2_vs_served_record_max_abs_diff']:.1e} over "
     f"{r['leads']['1']['C2_rows_compared_with_record']} served values; lead 2, 2027-Q1: "
     f"{r['leads']['2']['C2_vs_served_record_max_abs_diff']:.1e}). Protected md5s, the e53 record and its "
     f"calibration file are identical at start and end: **{r['md5_unchanged']}**. Platt lambda = {r['lambda_platt']}.", ""]
for k, title in (("1", "Lead 1 (E53-A1, 65 rows): adoption is judged here"), ("2", "Lead 2 (E55, 55 rows): reported only")):
    Lk = r["leads"][k]
    o += [f"### {title}", "",
          "| Arm | Accuracy | Balanced | AUC | Brier | Log loss | LOW caught | Share >= 0.5 | min p | max p |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for a in ARMS:
        m = Lk["arms"][a]["metrics"]
        o.append(f"| {a} | {f3(m['accuracy'])} | {f3(m['balanced_accuracy'])} | {f4(m['auc'])} | {f4(m['brier'])} | "
                 f"{f4(m['log_loss'])} | {m['LOW_caught']}/{m['LOW_rows']} | {100 * m['HIGH_share_pred']:.0f}% | "
                 f"{f3(m['min_p'])} | {f3(m['max_p'])} |")
    o += ["", "Reliability (5 bins: n, mean predicted, observed HIGH share):", "",
          "| Arm | " + " | ".join(b["bin"] for b in Lk["arms"]["C2"]["metrics"]["reliability_5bin"]) + " |",
          "|---|" + "---|" * 5]
    for a in ARMS:
        cells = [f"{b['n']}: {f3(b['mean_p'])} / {f3(b['observed_HIGH'])}" if b["n"] else "0"
                 for b in Lk["arms"][a]["metrics"]["reliability_5bin"]]
        o.append(f"| {a} | " + " | ".join(cells) + " |")
    o += ["", "Province probabilities per quarter (spread = max - min; ties = provinces sharing a 2-decimal value):", "",
          "| Quarter | Arm | " + " | ".join(PROV) + " | index | spread | ties |", "|---|---|" + "---|" * (len(PROV) + 3)]
    for q in next(iter(Lk["arms"].values()))["quarters"]:
        for a in ["raw"] + ARMS:
            qq = Lk["arms"]["C2" if a == "raw" else a]["quarters"][q]
            ps = qq["raw"] if a == "raw" else qq["provinces"]
            vals = list(ps.values())
            r2 = [round(v, 2) for v in vals]
            ties = sum(1 for v in r2 if r2.count(v) > 1)
            o.append(f"| {q} | {a} | " + " | ".join(f4(ps[p]) for p in PROV)
                     + f" | {sum(vals) / 5:.4f} | {max(vals) - min(vals):.4f} | {ties} |")
    o += ["", "Fitted parameters by target quarter (null = fewer than 3 eligible dates, raw probability used):", "",
          "| Target | C2 a | T | P A | P B | dates used |", "|---|---|---|---|---|---|"]
    for q, n in Lk["fit_dates_per_origin"].items():
        c2, t, p = (Lk["arms"][a]["params"].get(q) for a in ARMS)
        o.append(f"| {q} | {'–' if not c2 else c2['a']} | {'–' if not t else f3(t['T'])} | "
                 f"{'–' if not p else f3(p['A'])} | {'–' if not p else f3(p['B'])} | {n} |")
    o += ["", f"Leakage check: {len(Lk['leakage_violations'])} fitting dates with a target after the origin's "
          "published quarters.", ""]
o += ["### Adoption (lead 1, rule fixed before results)", "",
      "| Arm | (a) Brier and log loss <= C2 | (b) balanced >= 0.826 and AUC within 0.005 | (c) leakage | AUC - C2 AUC | Eligible |",
      "|---|---|---|---|---|---|"]
for a in ("T", "P"):
    ad = r["adoption"]["arms"][a]
    c = ad["criteria"]
    o.append(f"| {a} | {yes(c['a_brier_and_logloss_le_C2'])} | {yes(c['b_bal_ge_0.826_and_auc_within_0.005'])} | "
             f"{yes(c['c_leakage_check'])} | {ad['auc_diff']:+.4f}{' (exactly equal)' if ad['auc_exactly_equal'] else ''} | "
             f"{yes(ad['eligible'])} |")
o += ["", f"**Verdict: {r['adoption']['verdict']}**", "", "### What the dashboard shows now vs each arm", "",
      "| Quarter | Version | CALABARZON | " + " | ".join(PROV) + " |", "|---|---|---|" + "---|" * len(PROV)]
for q, row in r["dashboard_comparison"].items():
    for v, vals in row.items():
        if vals:
            o.append(f"| {q} | {v.replace('current_served', 'served now')} | {f4(vals['index'])} | "
                     + " | ".join(f4(vals[p]) for p in PROV) + " |")
md.write_text("\n".join(o) + "\n", encoding="utf-8")
print("\n".join(o[o.index("## Results"):]))
