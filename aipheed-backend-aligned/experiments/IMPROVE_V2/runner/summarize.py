"""Markdown tables from out/results.json -> out/summary.md (source of the RESULTS.md tables)."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json

import iv2_lib as V
import run_iv2 as RUN

R = json.loads((V.OUT / "results.json").read_text())


def f(x, n=3):
    return "–" if x is None else f"{x:.{n}f}"


def fails(m):
    return ", ".join(k.split()[0] for k, v in m["rules"].items() if not v["pass"]) or "none"


def main():
    out = [f"plan {R['plan']}", f"max reliable lead: {R['max_reliable_lead']}"]
    names = RUN.ARM_NAMES + RUN.BASELINES + ["ALWAYS-HIGH", "ALWAYS-LOW"]
    for L, x in R["leads"].items():
        v = x["verdict"]
        out.append(f"\n## {L} verdict {v['period']}, {v['n_quarters']} q, HIGH share {v['high_share']:.3f}\n")
        out.append("| Model | q | Acc | Bal | Prec | Rec | F1 | AUC | Brier | TP/FP/FN/TN | Fails | vs REF diff (p) | vs PERSIST diff (p) | fallback | Platt skipped | sigma fb |")
        out.append("|" + "---|" * 16)
        for n in names:
            r = v["models"].get(n)
            if r is None:
                continue
            m = r["metrics"]
            bv = r["brierVs"]
            fl = x["flags"].get(n, {})
            vs = lambda k: f"{bv[k]['brierDiff']:+.3f} ({bv[k]['p_one_sided']:.3f})" if k in bv else ""  # noqa: E731
            out.append(f"| {n} | {r['n_quarters_scored']} | {f(m['accuracy'])} | {f(m['balanced'])} | {f(m['precision'])} | "
                       f"{f(m['recall'])} | {f(m['f1'])} | {f(m.get('auc'))} | {f(m['brier'])} | "
                       f"{m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} | {fails(r)} | {vs('REF')} | {vs('PERSIST')} | "
                       f"{fl.get('fallback', '')} | {fl.get('platt_skipped') if fl.get('platt_skipped') is not None else ''} | "
                       f"{fl.get('sigma_fallback') if fl.get('sigma_fallback') is not None else ''} |")
        out.append("\nRule values for arms:\n")
        for n in RUN.ARM_NAMES:
            r = v["models"][n]["rules"]
            out.append(f"- {n}: " + "; ".join(f"{k.split()[0]} {'PASS' if w['pass'] else 'FAIL'} {w['value']}" for k, w in r.items()))
        for w in ("dev_2010_2022", "block_2023_2026", "news_era", "S1_no_phone_2020", "S2_no_adults_2025Q2plus", "S3_both"):
            y = x[w]
            out.append(f"\n### {L} {w} {y['period']}, {y['n_quarters']} q\n")
            out.append("| Model | q | Acc | Brier | all R1-R7 | fails |\n|---|---|---|---|---|---|")
            for n in names:
                r = y["models"].get(n)
                if r is None:
                    continue
                out.append(f"| {n} | {r['n_quarters_scored']} | {f(r['metrics']['accuracy'])} | {f(r['metrics']['brier'])} | "
                           f"{r['allR1R7']} | {', '.join(r['fails']) or 'none'} |")
        out.append(f"\n### {L} selection: {x['selection']}\n")
        out.append("| Comparator | q | Brier proposed | Brier comparator | diff | p | Holm p |\n|---|---|---|---|---|---|---|")
        for c, o in x["objective4"].items():
            out.append(f"| {c} | {o['n_quarters']} | {f(o['brier_a'])} | {f(o['brier_b'])} | {o['diff']:+.3f} | "
                       f"{o['p_one_sided']:.3f} | {o['p_holm']:.3f} |")
        out.append(f"\n### {L} news ablation (with news minus without)\n")
        out.append("| Arm | full diff (p) | news-era q | news-era diff (p) |\n|---|---|---|---|")
        for a, o in x["news_ablation"].items():
            out.append(f"| {a} | {o['full']['diff']:+.4f} ({o['full']['p_one_sided']:.3f}) | {o['news_era']['n_quarters']} | "
                       f"{o['news_era']['diff']:+.4f} ({o['news_era']['p_one_sided']:.3f}) |")
        out.append(f"\n### {L} SHAP group shares (%)\n")
        groups = list(V.GROUPS)
        out.append("| Arm | rows | " + " | ".join(groups) + " |\n|" + "---|" * (len(groups) + 2))
        for n, o in x["shap"].items():
            s = o["shares"] or {}
            out.append(f"| {n} (SHAP of {o['shap_of']}) | {o['rows']} | " + " | ".join(str(s.get(g, '')) for g in groups) + " |")
    (V.OUT / "summary.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
