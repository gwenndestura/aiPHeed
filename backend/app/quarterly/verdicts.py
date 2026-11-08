"""
app/quarterly/verdicts.py
--------------------------
The 75% target verdict, composed from the stored numbers so the sentence can never disagree with them (E57 objectives
audit: the E49 record's stored sentence said "not demonstrated" while its own interval, 0.769-0.923, cleared 75%).

Used at serving time (app.services.dashboard.e31_model_performance) and by scripts/build_record_e36.py.
"""
from __future__ import annotations

TARGET = 0.75


def compose_75pct_verdict(*, correct: int, n: int, accuracy: float, ci95: list[float], n_dates: int,
                          first_quarter: str, last_quarter: str, balanced_accuracy: float,
                          always_high_accuracy: float, persistence_accuracy: float,
                          holm_p: dict[str, float | None] | None = None) -> dict:
    """Return {"point_met", "demonstrated", "verdict"}. Demonstrated = the 95% date-bootstrap lower bound >= 75%."""
    lo, hi = ci95
    point, demonstrated = accuracy >= TARGET, lo >= TARGET
    parts = [f"One-quarter-ahead accuracy of the proposed LightGBM on {n} development estimates ({n_dates} quarters, "
             f"{first_quarter} to {last_quarter}): {correct}/{n} = {accuracy:.3f}."]
    if demonstrated:
        parts.append(f"The 95% date-bootstrap interval ({lo:.3f} to {hi:.3f}) stays above 75%, so the target is "
                     f"demonstrated on development dates.")
    elif point:
        parts.append(f"The point estimate is above 75%, but the 95% date-bootstrap interval ({lo:.3f} to {hi:.3f}) "
                     f"reaches below 75%, so the target is not demonstrated.")
    else:
        parts.append(f"The point estimate is below 75% (95% date-bootstrap interval {lo:.3f} to {hi:.3f}), so the "
                     f"target is not met.")
    parts.append(f"Always-HIGH reaches {always_high_accuracy:.3f} and persistence {persistence_accuracy:.3f}.")
    parts.append(f"Unlike always-HIGH, the model identifies LOW quarters (balanced accuracy {balanced_accuracy:.3f}).")
    if holm_p is not None:
        sig = sorted(k for k, p in holm_p.items() if p is not None and p < 0.05)
        parts.append("No paired difference with any of the six baselines is significant." if not sig else
                     f"Significant paired differences (Holm p < 0.05): {', '.join(sig)}.")
    parts.append("These are development dates; the 2026-Q4 forecast is the first untouched test.")
    return {"point_met": point, "demonstrated": demonstrated, "verdict": " ".join(parts)}


def verdict_from_record(validation: dict) -> dict | None:
    """Compose the verdict from an E36-schema record's validation.model_evaluation (None if it lacks the rows)."""
    me = validation.get("model_evaluation") or {}
    rows = {r.get("key"): r for r in me.get("rows", [])}
    m, ah, b1 = rows.get("E36-LGBM"), rows.get("ALWAYS_HIGH"), rows.get("B1_PERSISTENCE")
    dates = me.get("dates") or []
    if not (m and ah and b1 and dates and m.get("accuracy_ci95")):
        return None
    six = ("B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP")
    pv = me.get("paired_vs_baselines") or {}
    return compose_75pct_verdict(
        correct=m["correct"], n=m["n"], accuracy=m["accuracy_lead1"], ci95=m["accuracy_ci95"], n_dates=len(dates),
        first_quarter=dates[0], last_quarter=dates[-1], balanced_accuracy=m["balanced_accuracy"],
        always_high_accuracy=ah["accuracy_lead1"], persistence_accuracy=b1["accuracy_lead1"],
        holm_p={k: (pv.get(k) or {}).get("holm") for k in six} if pv else None)


def max_reliable_lead(validation: dict) -> dict:
    """Algorithm 3 (THESIS 2, pp. 41-42) applied to the leads the record evaluates for the served model: lead 1
    (model_evaluation, E36-LGBM row) then lead 2 (next_quarter_evaluation, the served lead-2 model's row). A lead passes
    when its accuracy is >= 75%; the search stops at the first failing lead. {"lead": last passing lead or None,
    "basis": one sentence with the numbers}."""
    steps = []
    me = {r.get("key"): r for r in (validation.get("model_evaluation") or {}).get("rows", [])}
    if me.get("E36-LGBM"):
        steps.append((1, me["E36-LGBM"]["accuracy_lead1"]))
    nq = {r.get("key"): r for r in (validation.get("next_quarter_evaluation") or {}).get("rows", [])}
    for key in ("E55", "E38-LGBM"):                         # the served lead-2 model of the E53 / E49 records
        if key in nq:
            steps.append((2, nq[key]["accuracy"]))
            break
    lead, parts = None, []
    for k, acc in steps:
        ok = acc >= TARGET
        parts.append(f"lead {k} {acc:.3f} {'>=' if ok else '<'} 0.75")
        if not ok:
            break
        lead = k
    return {"lead": lead, "basis": "Algorithm 3 (point accuracy): " + "; ".join(parts) if parts else None}
