"""
Explanations from the actual model. SEAS-LLM is additive, so the explanation is exact (not an approximation such as
SHAP): forecast = estimated current true level (hunger history with sampling noise filtered out) + quarter-of-year
design effect (learned after the documented 2025 respondent-base break). The five trigger groups are NOT inputs of
this model; they are listed separately as context with their data state, never as contributions.
"""
from __future__ import annotations

from app.forecasting.evidence import DataState

TRIGGER_GROUPS = {
    "market": "Market and food prices (A1-A3)",
    "climate": "Climate stress (C1-C4)",
    "employment_ofw": "Employment and OFW remittances (E1-E2)",
    "news_nlp": "News / NLP (N1)",
    "poverty_vulnerability": "Poverty and social vulnerability (V1)",
}


def explain(record: dict, context: dict | None = None) -> dict:
    c = record["components"]
    total = c["level"] + c["design_effect"]
    if abs(total - record["score"]) > 1e-3:
        raise ValueError("components do not add up to the score")
    ctx = []
    for g, label in TRIGGER_GROUPS.items():
        v = (context or {}).get(g)
        ctx.append({"group": g, "label": label, "role": "context only (not a model input)",
                    "value": None if v is None else v.get("value"),
                    "data_state": (DataState.UNAVAILABLE if v is None else DataState(v.get("state", "OBSERVED"))).value})
    warnings = []
    if record["horizon_quarters_from_latest_data"] >= 3:
        warnings.append(f"target is {record['horizon_quarters_from_latest_data']} quarters past the newest SWS reading")
    if record["reliability_status"] != "RELIABLE":
        warnings.append(f"Lead {record['lead']} has not passed the frozen reliability rules (N1-N7)")
    return {"score": record["score"],
            "predictive_contributions": [
                {"component": "hunger_history_level", "value": c["level"],
                 "meaning": "estimated current true hunger level after removing survey sampling noise"},
                {"component": "survey_design_effect", "value": c["design_effect"],
                 "meaning": "quarter-of-year effect of the post-2025 SWS design (0 before the break)"}],
            "context_indicators": ctx, "data_quality_warnings": warnings,
            "uncertainty": {"lo80": record["lo80"], "hi80": record["hi80"],
                            "method": "Kalman predictive variance (state + horizon + median sampling variance); "
                                      "development coverage at Lead 2 is reported in docs/aipheed/MODEL_REPORT.md"}}
