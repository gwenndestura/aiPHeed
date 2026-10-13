"""Generate RESULTS_TABLES.md from the sealed E23 and E23-B outputs (no typed numbers).
Usage: python -B runner/build_results_md.py <E23 run> <E23B run>"""
import json
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
MODELS = ["PROPOSED_lgbm_combined", "B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only",
          "B5_lgbm_gov_only", "B6_lgbm_nlp_only", "S_lr_psa_only"]


def f(x, d=3):
    return "—" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def main():
    a, b = sys.argv[1], sys.argv[2]
    R = json.loads((EXP / "runs" / a / "results.json").read_text(encoding="utf-8"))
    B = json.loads((EXP / "runs" / b / "results_e23b.json").read_text(encoding="utf-8"))
    L = [f"# Results tables (generated from runs {a} and {b})", ""]
    for mode, title in (("origin", "PRIMARY target (training-window median threshold)"),
                        ("fixed", "SENSITIVITY target (fixed 14.6; carries full-period information; never decisive)"),
                        ("origin_excluding_2026_targets", "PRIMARY target, 2026 targets excluded")):
        r = R[mode]
        L += [f"## E23 — {title}", "", f"Evaluable leads: {r['evaluable_leads'] or 'none'} · maximum reliable lead: "
              f"{r['max_reliable_lead'] or 'none'}", ""]
        for k, v in r["by_lead"].items():
            if not v.get("n_origins"):
                L += [f"**Lead {k}:** no origin with ≥ 8 published training quarters.", ""]
                continue
            L += [f"**Lead {k}** — {v['n_origins']} origins ({v['target_quarters'][0]}…{v['target_quarters'][-1]}), "
                  f"test HIGH {v['test_HIGH']} / LOW {v['test_LOW']}, evaluable: {'yes' if v['evaluable'] else 'no'}", "",
                  "| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Brier | TP/FP/FN/TN |",
                  "|---|---|---|---|---|---|---|---|"]
            for m in MODELS:
                x = v["metrics"][m]
                L.append(f"| {m} | {f(x['accuracy'])} | {f(x['precision'])} | {f(x['recall'])} | {f(x['F1'])} | "
                         f"{f(x['ROC_AUC'])} | {f(x['Brier'])} | {x['TP']}/{x['FP']}/{x['FN']}/{x['TN']} |")
            L += ["", "| Proposed vs | ΔAUC | p (AUC, one-sided) | Holm | ΔBrier | p (Brier) | Holm | origins better/worse |",
                  "|---|---|---|---|---|---|---|---|"]
            for m, t in v["paired_tests"].items():
                L.append(f"| {m} | {f(t['auc'].get('auc_diff'))} | {f(t['auc'].get('p_one_sided'))} | "
                         f"{f(t['auc'].get('p_holm'))} | {f(t['brier']['mean_diff'], 4)} | {f(t['brier']['p_one_sided'])} | "
                         f"{f(t['brier'].get('p_holm'))} | {t['brier']['origins_better']}/{t['brier']['origins_worse']} |")
            if v.get("proposed_auc_ci"):
                c = v["proposed_auc_ci"]
                L.append(f"\nProposed AUC origin-cluster bootstrap 95% CI: {f(c['ci_low'])}–{f(c['ci_high'])}")
            L.append("")
        h = r["hypotheses"]
        L += ["**Hypothesis decisions:** " + "; ".join(f"{k} {h[k]['decision']}" for k in ("H1", "H2", "H3", "H4", "H5")), ""]
        if "conditions" in h.get("H1", {}):
            L += ["H1 detail: " + json.dumps(h["H1"]["conditions"]), "",
                  "SHAP top 10 (mean |SHAP|): " + ", ".join(f"{n} {v:.3f}" for n, v in h["H1"]["shap_rank_top10"]), ""]
    L += ["## E23-B improvement (selected LightGBM, accuracy primary)", ""]
    for mode in ("origin", "fixed"):
        L += [f"### {mode}", "", "| Lead | Origins | HIGH/LOW | E23-B accuracy | Always-HIGH | Strongest baseline | Its accuracy | Beats it | > 75% | E23-B AUC | E23-B Brier | sign-flip p | McNemar p |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, v in B[mode].items():
            t = v["tests"][v["strongest_baseline"]]
            L.append(f"| {k} | {v['n_origins']} | {v['HIGH']}/{v['LOW']} | {f(v['accuracy']['IMP_lgbm_selected'])} | "
                     f"{f(v['accuracy']['REF_always_HIGH'])} | {v['strongest_baseline']} | {f(v['accuracy'][v['strongest_baseline']])} | "
                     f"{'yes' if v['beats_strongest'] else 'no'} | {'yes' if v['exceeds_75'] else 'no'} | "
                     f"{f(v['imp_metrics']['ROC_AUC'])} | {f(v['imp_metrics']['Brier'])} | {f(t['signflip_p'])} | {f(t['mcnemar_exact_p'])} |")
        L.append("")
    lq = json.loads((EXP / "runs" / a / "loqo.json").read_text(encoding="utf-8"))
    L += ["## Leave-one-quarter-out (NON-chronological; descriptive only)", "",
          f"Global-median threshold {lq['threshold_global_median']:.3f}; AUC proposed {f(lq['auc_proposed'])}, "
          f"combined LR {f(lq['auc_lr_combined'])}. Uses future quarters for training, so it cannot support any forecasting claim.", ""]
    (EXP / "RESULTS_TABLES.md").write_text("\n".join(L), encoding="utf-8")
    print("written", len(L))


if __name__ == "__main__":
    main()
