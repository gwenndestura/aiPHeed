"""
Exact explanation of a v2 forecast. The model is additive, so no approximation (such as SHAP) is needed:

    score = latest SWS reading + noise-filter adjustment + predicted change beyond the anchor (0 by design)

The explanation is computed from the stored record of the same artifact (explanation hash = forecast hash). The five
trigger groups are not model inputs (the diagnosis found no repeatable leading signal); they are listed as context
indicators with their data state, never as contributions and never weighted.
"""
from __future__ import annotations

from app.forecasting.evidence import DataState
from app.forecasting.explain import TRIGGER_GROUPS

SUM_TOLERANCE = 1e-3          # components are rounded to 4 decimals each


def explain(record: dict, context: dict | None = None) -> dict:
    c = record["components"]
    parts = [("latest_reading", c["latest_reading"],
              f"latest published SWS reading ({record['latest_data_quarter']})"),
             ("noise_filter_adjustment", c["noise_filter_adjustment"],
              "estimated survey sampling noise removed from the latest reading (0 for persistence)"),
             ("predicted_change_beyond_anchor", c["predicted_change_beyond_anchor"],
              "change predicted after the latest reading: 0, because no repeatable leading signal was found "
              "(docs/aipheed/v2/DIAGNOSIS.md Q3)")]
    total = sum(v for _, v, _ in parts)
    if abs(total - record["score"]) > SUM_TOLERANCE:
        raise ValueError(f"contributions sum to {total:.4f}, not the score {record['score']:.4f}")
    persistence = record["model"] == "PERSIST"
    ctx, missing = [], []
    for g, lab in TRIGGER_GROUPS.items():
        v = (context or {}).get(g)
        state = DataState.UNAVAILABLE if v is None else DataState(v.get("state", "OBSERVED"))
        ctx.append({"group": g, "label": lab, "role": "contextual indicator (not a model input; no weight)",
                    "indicator": None if v is None else v.get("label"), "value": None if v is None else v.get("value"),
                    "period": None if v is None else v.get("period"), "available": None if v is None else v.get("available"),
                    "source": None if v is None else v.get("source"), "data_state": state.value})
        if state is not DataState.OBSERVED:
            missing.append(f"{lab}: {state.value}")
    warnings = []
    if record["horizon_quarters_from_latest_data"] >= 3:
        warnings.append(f"target is {record['horizon_quarters_from_latest_data']} quarters past the newest SWS reading")
    if record["reliability_status"] != "RELIABLE":
        warnings.append(f"Lead {record['lead']} status {record['reliability_status']}: not validated by the frozen rules N1-N7")
    return {"score": record["score"],
            "summary": ("last observed value carried forward" if persistence else
                        "latest reading, denoised; no change predicted beyond it"),
            "predictive_contributions": [{"component": n, "value": v, "meaning": m} for n, v, m in parts],
            "contributions_sum": round(total, 4), "sum_tolerance": SUM_TOLERANCE,
            "contextual_indicators": ctx, "data_quality_warnings": warnings, "missing_information": missing,
            "explanation_model_sha256": record["artifact_sha256"],
            "uncertainty": {"lo80": record["lo80"], "hi80": record["hi80"], "method": record["interval_method"],
                            "n_residuals": record["interval_residuals"]}}
