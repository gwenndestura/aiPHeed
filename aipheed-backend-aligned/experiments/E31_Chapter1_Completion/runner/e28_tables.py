"""Render the E28 evaluation into markdown tables (runs/e28_tables.md). Reads runs/e28_eval only."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
EXP = guard28.EXP
r = json.loads((EXP / "runs" / "e28_eval" / "results.json").read_text(encoding="utf-8"))
d = json.loads((EXP / "runs" / "e28_eval" / "E28_DETERMINATION.json").read_text(encoding="utf-8"))
ARMS = ["B1", "B1p_E25", "ALWAYS_HIGH", "CLIM", "MAJ", "PSA_LR", "PSA_LGBM", "NLP_LR", "NLP_LGBM", "LR_COMB",
        "PROPOSED", "PROPOSED_NESTED", "PROPOSED_PERSIST", "LR_STRUCT", "PROPOSED_E25", "PCF21_E25", "M4_21_E25"]


def f(x):
    return "–" if x is None else f"{x:.3f}"


def flag(m, k):
    fl = m["flags"].get(k, "OK")
    v = m.get(k)
    if fl == "NOT_ESTIMABLE":
        return "n/e"
    return f(v) + ("" if fl == "OK" else "†")


out = []
for tg in ("T1_A", "T2"):
    S = r["summary"][tg]
    for lead in ("1", "2", "3"):
        b = S["B1"]["by_lead"].get(lead)
        if not b:
            continue
        out.append(f"\n### {tg}, lead {lead}: {b['n']} rows, {b['dates']} dates, {b['HIGH']} HIGH / {b['LOW']} LOW\n")
        out.append("| Arm | Acc [95% CI] | Bal. acc | Precision | Recall | F1 | ROC-AUC [95% CI] | PR-AUC | Brier [95% CI] | ECE | TP/FP/TN/FN | % pred. HIGH |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a in ARMS:
            if a not in S or lead not in S[a]["by_lead"]:
                continue
            m = S[a]["by_lead"][lead]
            ac = m["accuracy_ci95"]
            bc = m["brier_ci95"]
            au = m["auc_ci95"]
            out.append(f"| {a} | {f(m['accuracy'])} [{f(ac[0])}, {f(ac[1])}] | {flag(m, 'balanced_accuracy')} | "
                       f"{flag(m, 'precision')} | {flag(m, 'recall')} | {flag(m, 'f1')} | {flag(m, 'roc_auc')}"
                       f"{'' if not au or m['roc_auc'] is None else f' [{f(au[0])}, {f(au[1])}]'} | {flag(m, 'pr_auc')} | "
                       f"{f(m['brier'])} [{f(bc[0])}, {f(bc[1])}] | {f(m['ece_3bin'])} | "
                       f"{m['TP']}/{m['FP']}/{m['TN']}/{m['FN']} | {100 * m['share_predicted_HIGH']:.0f}% |")
    out.append(f"\n### {tg}, pooled over leads 1–6 (per-date paired tests, Holm across references)\n")
    out.append("| Arm | Pooled acc | Pooled Brier | vs B1: Brier diff (Holm p) | vs ALWAYS_HIGH: Brier diff (Holm p) | vs CLIM | qualifies (E27 rule) | furthest reliable lead (C6) |")
    out.append("|---|---|---|---|---|---|---|---|")
    T = r["paired_pooled"][tg]
    for a in ARMS:
        if a not in S:
            continue
        p = S[a]["pooled"]
        t = T.get(a, {})

        def cmp(ref):
            x = t.get(ref)
            return "–" if not x else f"{x['brier_diff_mean']:+.3f} ({f(x['holm_brier'])})"
        out.append(f"| {a} | {f(p['accuracy'])} | {f(p['brier'])} | {cmp('B1')} | {cmp('ALWAYS_HIGH')} | {cmp('CLIM')} | "
                   f"{d[tg]['qualifies_E27_rule_pooled'].get(a)} | {d[tg]['furthest_reliable_horizon'].get(a)} |")
    out.append(f"\nReachability ({tg}): " + "; ".join(
        f"lead {L}: {v['dates']} dates, {v['HIGH']} HIGH / {v['LOW']} LOW, C6 evaluable possible = {v['C6_evaluable_possible']}"
        for L, v in d[tg]["reachability_by_lead"].items() if v))
out.append("\n† = UNSTABLE (minority class < 5 rows or < 8 dates); n/e = NOT_ESTIMABLE (a class absent or nothing predicted).")
nested = r["nested_selection"]["T1_A"]
cfgs = {}
for n in nested:
    k = json.dumps(n["cfg"], sort_keys=True)
    cfgs[k] = cfgs.get(k, 0) + 1
out.append("\nPROPOSED_NESTED configurations chosen on inner folds (T1): " + "; ".join(f"{v}x {k}" for k, v in cfgs.items()))
rel = d["T2"]["reliability_detail"]
out.append("\nT2 lead-1 C6 detail: " + "; ".join(
    f"{a}: AUC lower {f(rel[a]['1']['auc_lower'])}, Brier vs B1 p={f(rel[a]['1']['brier_vs_B1'].get('p_brier'))}, reliable={rel[a]['1']['reliable']}"
    for a in ("PROPOSED", "PROPOSED_NESTED", "PROPOSED_PERSIST", "LR_STRUCT", "M4_21_E25", "PSA_LGBM", "NLP_LGBM", "LR_COMB")
    if a in rel))
txt = "\n".join(out)
(EXP / "runs" / "e28_tables.md").write_text(txt, encoding="utf-8")
print(txt)
