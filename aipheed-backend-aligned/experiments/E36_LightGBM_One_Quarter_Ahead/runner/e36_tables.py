"""Markdown tables for FINAL_REPORT.md, generated from a run's results.json (no hand-copied numbers).

    python -B runner/e36_tables.py runs/<primary run>   -> docs/TABLES.md
"""
import json
import sys
from pathlib import Path

E36 = Path(__file__).resolve().parents[1]
ARMS = ["E36-LGBM", "B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP",
        "ALWAYS_HIGH", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY", "PCF21"]
FIXED = ["COMPACTxG1", "COMPACTxG4", "COMPACTxG3", "COMPACTxG2", "COMBxG1", "COMBxG4", "COMBxG3", "COMBxG2",
         "COMB_NOYxG1", "GOVxG1", "GOVxG2", "NLPxG1", "NLPxG3"]


def f(x, d=3):
    return "–" if x is None else f"{x:.{d}f}"


def row(name, m):
    ci = m.get("accuracy_ci95") or [None, None]
    return (f"| {name} | {m['correct']}/{m['n']} | {m['HIGH']}/{m['LOW']} | {f(m['accuracy'])} | {f(ci[0])}–{f(ci[1])} | "
            f"{f(m['balanced_accuracy'])} | {f(m['precision'])} | {f(m['recall'])} | {f(m['specificity'])} | "
            f"{f(m['f1'])} | {f(m['roc_auc'])} | {f(m['brier'])} | {f(m['calibration_in_the_large'])} | "
            f"TN {m['TN']} FP {m['FP']} FN {m['FN']} TP {m['TP']} |")


HEAD = ("| Arm | Correct/n | HIGH/LOW | Accuracy | 95% CI (date bootstrap) | Bal. acc. | Precision | Recall | "
        "Specificity | F1 | ROC-AUC | Brier | Calib. in the large | Confusion |\n|" + "---|" * 14)


def main(run_dir):
    r = json.loads((Path(run_dir) / "results.json").read_text(encoding="utf-8"))
    out = [f"# E36 tables (generated from `{Path(run_dir).name}/results.json`)\n"]
    for period in ("all", "P-early", "P-late"):
        out += [f"\n## Lead 1, period {period}\n", HEAD]
        out += [row(a, r["metrics"][period][a]) for a in ARMS if a in r["metrics"][period]]
    out += ["\n## Fixed configurations without selection (optimistic: best-in-hindsight)\n", HEAD]
    out += [row(a, r["metrics"]["all"][a]) for a in FIXED]
    out += ["\n## Existing candidates on their common rows\n"]
    for cand, v in r["common_rows"].items():
        out += [f"\n### {cand} ({v['rows']} rows)\n", HEAD] + [row(a, m) for a, m in v["metrics"].items()]
    out += ["\n## Paired comparisons of E36-LGBM (per-date Brier sign-flip; McNemar on correctness)\n",
            "| Reference | Dates | Rows | Mean Brier gain of E36-LGBM | p (two-sided) | Holm (six baselines) | "
            "Accuracy difference | McNemar: E36 only right / ref only right, p |\n|---|---|---|---|---|---|---|---|"]
    for ref, v in r["paired"]["E36-LGBM"].items():
        mc = v["mcnemar"]
        out.append(f"| {ref} | {v['dates']} | {v['rows']} | {v['mean_brier_gain_vs_ref']:+.4f} | {f(v['p_two_sided'])} | "
                   f"{f(v.get('holm_two_sided_over_six_baselines'))} | {v['accuracy_diff']:+.3f} | "
                   f"{mc['arm_only_correct']} / {mc['ref_only_correct']}, {f(mc['p_two_sided'])} |")
    out += ["\n## Per quarter (E36-LGBM)\n", "| Target quarter | HIGH | Correct/5 | Brier | Mean p |\n|---|---|---|---|---|"]
    for q, v in r["per_quarter"]["E36-LGBM"].items():
        out.append(f"| {q} | {v['HIGH']} | {v['correct']} | {f(v['brier'])} | {f(v['mean_p'])} |")
    out += ["\n## Per province (13 dates)\n", "| Arm | " + " | ".join(r["per_province"]["E36-LGBM"]) + " |",
            "|---|" + "---|" * 5]
    for a in ("E36-LGBM", "B1_PERSISTENCE", "B5_LGBM_GOV", "ALWAYS_HIGH"):
        out.append(f"| {a} | " + " | ".join(f"{v['correct']}/{v['n']} (Brier {v['brier']:.3f})"
                                             for v in r["per_province"][a].values()) + " |")
    out += ["\n## Province discrimination (within-date)\n", "| Arm | Mean SD of p across provinces | Dates with mixed "
            "predicted labels | Within-date AUC (mixed-label dates) |\n|---|---|---|---|"]
    for a in ("E36-LGBM", "B1_PERSISTENCE", "B5_LGBM_GOV", "B2_LR_COMB", "PCF21"):
        d = r["metrics"]["all"][a]["discrimination"]
        out.append(f"| {a} | {f(d['mean_within_date_sd_p'])} | {d['dates_with_mixed_predicted_labels']}/{d['dates']} | "
                   f"{f(d['within_date_auc_mean'])} ({d['dates_with_mixed_observed_labels']} dates) |")
    oc = r["operational_choice"]
    out += [f"\n## Operational choice at {oc['origin']}\n", f"Chosen: **{oc['chosen']}** ({oc['rule']}); prior dates: "
            f"{', '.join(oc['prior_dates'])}.\n", "| Configuration | Mean per-date Brier on prior dates |\n|---|---|"]
    out += [f"| {k} | {v:.4f} |" for k, v in sorted(oc["scores"].items(), key=lambda kv: kv[1])]
    (E36 / "docs" / "TABLES.md").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("docs/TABLES.md written")


if __name__ == "__main__":
    main(sys.argv[1])
