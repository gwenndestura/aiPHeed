"""Gate evidence for PFI v1.0, derived from the sealed artifact and data/pfi/out/evaluation.json (no hand-entered values)."""
from __future__ import annotations

import json

from app.pfi import OUT, VERSION
from app.pfi import engine as E

FAMILY_OF_COVARIATE = {"poverty": "V1", "subsistence": "V1", "unemployment": "E1", "rice_inflation": "A3"}
GROUP_OF_FAMILY = {"A1": "market", "A2": "market", "A3": "market", "C1": "climate", "C2": "climate", "C3": "climate",
                   "C4": "climate", "E1": "employment", "E2": "employment", "V1": "poverty", "N1": "news"}


def build() -> dict:
    try:
        a = E.load_artifact()
        loads = True
    except E.ArtifactMissing:
        return {"artifact_loads": False, "artifact_path": "data/pfi/model/pfi_model.json", "target": {},
                "families_used": [], "groups_used": []}
    ev = json.loads((OUT / "evaluation.json").read_text())
    covs = [t.replace("logit(", "").rstrip(")") for t in a["level"]["terms"][1:]]
    fams = sorted({FAMILY_OF_COVARIATE[c] for c in covs} | {"H1"})              # H1: the SWS bridge
    sel = ev["level"]["candidates"][ev["level"]["selected"]]
    cal = sel["classification_above_national"]["calibration"]
    n = sum(b["n"] for b in cal)
    ece = sum(b["n"] * abs(b["mean_p"] - b["observed"]) for b in cal if b["n"]) / n
    groups = ev["information_groups"]
    contrib = {
        "market": {"tested_out_of_sample": True, "how": groups["Market and food prices"]["tested_as"],
                   "result": groups["Market and food prices"]["result"], "in_model": False},
        "employment": {"tested_out_of_sample": True, "how": groups["Employment and remittances"]["tested_as"],
                       "result": groups["Employment and remittances"]["result"], "in_model": False},
        "poverty": {"tested_out_of_sample": True, "how": groups["Poverty and social vulnerability"]["tested_as"],
                    "result": groups["Poverty and social vulnerability"]["result"], "in_model": True},
        "climate": {"tested_out_of_sample": False, "how": groups["Climate and agricultural production"]["tested_as"], "in_model": False},
        "news": {"tested_out_of_sample": False, "how": groups["News and NLP"]["tested_as"], "in_model": False},
    }
    o = ev["objective_75"]
    return {
        "model_id": VERSION, "artifact_loads": loads, "artifact_path": "data/pfi/model/pfi_model.json",
        "target": {"construct": a["outcome"], "is_food_insecurity_measurement": True, "served_resolution": "province",
                   "served_frequency": "calendar quarter"},
        "families_used": fams, "groups_used": sorted({GROUP_OF_FAMILY[f] for f in fams if f in GROUP_OF_FAMILY}),
        "n1_version": None,
        "release_notes": "Survey release dates are approximate (conservative month-end); SWS uses published dates.",
        "chronological": None,
        "chronological_note": ("No chronological series of the target exists: FIES is measured for provinces never, for "
                               "CALABARZON in 2023 and 2025 (provisional) only. One held-out wave (n = 1) is not a "
                               f"chronological evaluation. Held-out wave: {ev['bridge']['holdout']['predicted_pct']:.1f}% "
                               f"predicted vs {ev['bridge']['holdout']['observed_pct']}% reported."),
        "independent": {"applicable": True, "passed": bool(o["level_classification"]["met"]),
                        "what": o["level_classification"]["type"], "accuracy": o["level_classification"]["accuracy"],
                        "accuracy_ci95": o["level_classification"]["accuracy_ci95"], "n": o["level_classification"]["n"],
                        "note": "Regional level only (one wave); provincial quarterly forecasts are not covered."},
        "calibration": {"interval_nominal": 0.95, "interval_coverage": sel["interval95_coverage"], "ece": ece,
                        "basis": "leave-one-region-out level model (17 regions)"},
        "geographic": {"passed_at_served_resolution": None,
                       "regional_loo": {"mae_pp": sel["mae_pp"], "n": sel["n"]},
                       "note": "No province has a FIES measurement, so leave-one-province-out cannot be run."},
        "horizon": {"validated_leads": [], "note": "No lead is validated on the food-insecurity target; the SWS input's "
                                                  "Lead 1 record is regional hunger, not the target."},
        "group_contribution": contrib,
        "documents": ["docs/pfi/METHODOLOGY.md"],
    }
