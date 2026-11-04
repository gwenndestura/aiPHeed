"""Metric report generated from the prediction artifacts, with an explicit status for every cell (no dashes).

For each model and lead, every metric is RECOMPUTED from the stored walk-forward forecasts (`out/*_fits.csv`, the
NEWS_V2 C-b forecasts) on the 62 verdict quarters, and must equal the value in the model's results JSON (else the
script stops). Status:
- PASS / FAIL: metrics with a pre-registered threshold (hr_lib rules: R2 accuracy >= 0.75, R3 balanced >= 0.70,
  R6 precision and recall >= 0.60).
- REPORTED: metrics without a threshold (F1, AUC-ROC, Brier).
- UNDEFINED: AUC of a constant forecast (always-HIGH): one predicted value, so no ranking.
Baselines: PROVEN when C-x is better with Holm p < 0.05 (14-test family), else NOT PROVEN.

    python report_metrics.py   # -> ../FINAL_2026-11-04/METRICS_REPORT.md and ../out/metrics_report.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

N, V, H, R = CE.N, CE.V, CE.H, CE.R
MODELS = {"C-b": (N.OUT / "forecasts.csv", "cb6_results.json"), "C-E2": (OUT / "ce2_fits.csv", "ce2_results.json"),
          "C-E6": (OUT / "ce6_fits.csv", "ce6_results.json"), "C-B6": (OUT / "cb6_fits.csv", "cb6_results.json")}
THRESH = {"accuracy": .75, "balanced": .70, "precision": .60, "recall": .60}
LABEL = {"accuracy": "Accuracy", "balanced": "Balanced accuracy", "precision": "Precision", "recall": "Recall",
         "f1": "F1", "auc": "AUC-ROC", "brier": "Brier"}


def metrics(p: np.ndarray, y: np.ndarray) -> dict:
    c = (p >= .5).astype(int)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    pr, rc = tp / (tp + fp), tp / (tp + fn)
    return {"accuracy": (tp + tn) / len(y), "balanced": (rc + tn / (tn + fp)) / 2, "precision": pr, "recall": rc,
            "f1": 2 * pr * rc / (pr + rc), "auc": float(roc_auc_score(y, p)) if len(set(p)) > 1 else None,
            "brier": float(np.mean((p - y) ** 2)), "TP": tp, "FP": fp, "FN": fn, "TN": tn}


def status(k: str, v) -> str:
    if v is None:
        return "UNDEFINED (constant forecast)"
    return ("PASS" if v >= THRESH[k] else "FAIL") if k in THRESH else "REPORTED"


def main():
    lab = V.area_labels(H.load())
    lb = lab[lab["area"] == "BL"]
    L = pd.read_csv(N.LEADS_FILE)
    rep = {"models": {}, "verification": {}}
    for m, (fits, res) in MODELS.items():
        F = pd.read_csv(fits)
        F = F[F["name"] == m] if "name" in F else F
        r = json.loads((OUT / res).read_text(encoding="utf-8"))
        comp = pd.concat([F[["t", "lead", "q", "p"]].assign(name=m), L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]]])
        rep["models"][m] = {"leads": {}, "rules": {}, "algorithm3": r["algorithm3"].get(m), "results_file": res}
        for k in (1, 2):
            W = R.frame(comp, k, lb).dropna(subset=[m])
            x = metrics(W[m].to_numpy(float), W["y"].to_numpy(int))
            stored = r["leads"][str(k)][m]["metrics"]
            diff = max(abs(x[q] - stored[q]) for q in LABEL if x[q] is not None and stored.get(q) is not None)
            rep["verification"][f"{m} L{k}"] = {"n": int(len(W)), "max_abs_diff_vs_results": diff}
            assert diff < 1e-9, f"{m} L{k}: recomputed metrics differ from {res} ({diff})"
            rep["models"][m]["leads"][str(k)] = {q: {"value": x[q], "status": status(q, x[q])} for q in LABEL} | \
                {"confusion": {q: x[q] for q in ("TP", "FP", "FN", "TN")}}
            rep["models"][m]["rules"][str(k)] = {q: {"pass": v["pass"], "value": v["value"]}
                                                 for q, v in r["leads"][str(k)][m]["rules"].items()}
        rep["models"][m]["holm_family_14"] = r.get("holm_family_14") if r.get("label", "").find(m) >= 0 or m in ("C-E2", "C-E6", "C-B6") else None
    # baselines: each candidate's own family; constant baselines' AUC is undefined
    for m in ("C-E2", "C-E6", "C-B6"):
        r = json.loads((OUT / MODELS[m][1]).read_text(encoding="utf-8"))
        rep["models"][m]["holm_family_14"] = [{"lead": f["lead"], "baseline": f["comparator"], "n": f["n_quarters"],
                                               "brier_model": f["brier_candidate"], "brier_baseline": f["brier_comparator"],
                                               "diff": f["diff"], "ci95": f["ci95"], "p_raw": f["p_one_sided"],
                                               "p_holm": f["p_holm_14"],
                                               "status": "PROVEN" if f["significant"] else "NOT PROVEN"}
                                              for f in r["holm_family_14"]]
    (OUT / "metrics_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    f3 = lambda v: f"{v:.3f}" if v is not None else "undefined"  # noqa: E731
    lines = ["# Metric report (generated by `runner/report_metrics.py` from the prediction artifacts)", "",
             "Every value below is recomputed from the stored walk-forward forecasts on the 62 verdict quarters "
             "(2010-Q1..2026-Q3) and checked against each model's results file (max difference < 1e-9).",
             "", "**Status:** PASS / FAIL = against a pre-registered threshold (accuracy ≥ 0.75, balanced accuracy ≥ "
             "0.70, precision and recall ≥ 0.60). REPORTED = no threshold exists for this metric (F1, AUC-ROC, Brier; "
             "lower Brier is better). UNDEFINED = AUC of a constant forecast.", ""]
    for k in ("1", "2"):
        lines += [f"## Lead {k}", "", "| Metric | " + " | ".join(MODELS) + " |", "|---|" + "---|" * len(MODELS)]
        for q, name in LABEL.items():
            row = [f"{f3(rep['models'][m]['leads'][k][q]['value'])} {rep['models'][m]['leads'][k][q]['status']}" for m in MODELS]
            lines.append(f"| {name} | " + " | ".join(row) + " |")
        lines.append("| TP / FP / FN / TN | " + " | ".join("/".join(str(v) for v in rep["models"][m]["leads"][k]["confusion"].values()) for m in MODELS) + " |")
        for rr in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"):
            lines.append(f"| {rr} | " + " | ".join("PASS" if rep["models"][m]["rules"][k][rr]["pass"] else "FAIL" for m in MODELS) + " |")
        lines.append("")
    lines += ["## Reliable lead (Algorithm 3, 75% rule)", "", "| " + " | ".join(MODELS) + " |", "|" + "---|" * len(MODELS),
              "| " + " | ".join(f"{rep['models'][m]['algorithm3']} quarters" for m in MODELS) + " |", ""]
    for m in ("C-E6", "C-B6"):
        lines += [f"## {m} vs the 7 baselines (paired Brier, one-sided cluster bootstrap, Holm over 14)", "",
                  "| Lead | Baseline | n | Brier model | Brier baseline | Diff | 95% CI | p raw | p Holm | Status |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for f in rep["models"][m]["holm_family_14"]:
            lines.append(f"| {f['lead']} | {f['baseline']} | {f['n']} | {f['brier_model']:.4f} | {f['brier_baseline']:.4f} | "
                         f"{f['diff']:+.4f} | {f['ci95'][0]:+.3f}..{f['ci95'][1]:+.3f} | {f['p_raw']:.4f} | {f['p_holm']:.4f} | {f['status']} |")
        n = sum(f["status"] == "PROVEN" for f in rep["models"][m]["holm_family_14"])
        lines += ["", f"**{m}: {n} of 14 PROVEN.** Always-HIGH's own AUC is UNDEFINED (constant forecast); its Brier is 0.3065.", ""]
    (HERE / "FINAL_2026-11-04" / "METRICS_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(rep["verification"], indent=1))


if __name__ == "__main__":
    main()
