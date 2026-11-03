"""Models known to the registry. `python -m app.registry.catalog` (re)registers them; statuses are kept for an
unchanged artifact (see app.registry.register)."""
from __future__ import annotations

from app import registry as R
from app.paths import BACKEND_DIR

PFI_TESTS = "tests/unit/test_pfi.py"
HFIAS_TESTS = "tests/unit/test_hfias.py"
CATALOG = [
    {"model_id": "ch1-p0h4", "status": "legacy_incumbent", "version": "ch1 (P0H4 Chapter I composite)",
     "artifact_path": "data/ch1_engine/rows.csv",
     "target": "Price-pressure risk index: probability that the province is HIGH risk (not a food-insecurity measurement)",
     "note": "Served on the map and left panel before this release gate existed; never evaluated by it. Its own metadata "
             "marks it is_food_insecurity_measurement = False."},
    {"model_id": "pfi-1.0", "status": "candidate", "version": "pfi-1.0", "artifact_path": "data/pfi/model/pfi_model.json",
     "target": "FIES moderate-or-severe food insecurity, % of households, province, next calendar quarter",
     "evidence_builder": "app.pfi.evidence:build",
     "tests": {"release": [f"{PFI_TESTS}::test_sws_release_filter", f"{PFI_TESTS}::test_issue_uses_only_released_inputs",
                           f"{PFI_TESTS}::test_build_refuses_unreleased_survey"],
               "leakage": [f"{PFI_TESTS}::test_loo_prediction_ignores_held_out_outcome",
                           f"{PFI_TESTS}::test_issue_uses_only_released_inputs"],
               "all": [PFI_TESTS]}},
    {"model_id": "hfias-1.0", "status": "candidate", "version": "hfias-1.0", "artifact_path": "data/hfias/out/study_insecure.json",
     "target": "HFIAS household food insecurity (any level), province, FNRI ENNS round; locked protocol",
     "evidence_builder": "app.hfias.evidence:build",
     "tests": {"release": [f"{HFIAS_TESTS}::test_features_respect_release_dates",
                           f"{HFIAS_TESTS}::test_quarterly_production_uses_published_quarters_only"],
               "leakage": [f"{HFIAS_TESTS}::test_study_split_is_chronological_and_disjoint",
                           f"{HFIAS_TESTS}::test_protocol_lock_matches_code"],
               "all": [HFIAS_TESTS]}},
    {"model_id": "e137-sarf-1.0", "status": "candidate", "version": "e137-sarf-1.0 (protocol E137-P1)",
     "artifact_path": "data/e137/out/results.json",
     "target": "Food-insecurity RISK: probability that a province's HFIAS moderate-or-severe food insecurity is above the "
               "national level of the same survey (not a prevalence)",
     "note": "Evaluated by its own pre-registered risk gate (app.e137.gate), not by the B-check gate."},
    {"model_id": "e138-where-lrp-1.0", "status": "candidate", "version": "e138 LR-P (protocol E138-P1)",
     "artifact_path": "data/e138/out/results.json",
     "target": "Structural food-insecurity RISK (WHERE only): P(province HFIAS moderate-or-severe above national); "
               "poverty, subsistence and poverty gap; no forecast lead",
     "note": "Selected by E138's frozen one-SE rule; evaluated by its pre-registered gate (app.e138.gate)."},
    {"model_id": "e139-lgbm-1.0", "status": "candidate", "version": "e139 linear-prior LightGBM (protocol E139-P1)",
     "artifact_path": "data/e139/out/model_artifact.json",
     "target": "Food-insecurity RISK: P(province HFIAS moderate-or-severe above the national level of the same survey); "
               "structural estimate, next-survey forecast only if a lead is validated",
     "note": "Final-system candidate; evaluated by its pre-registered gate (app.e139.gate). Candidate outputs on admin "
             "routes /api/v1/admin/candidates/e139-lgbm-1.0/*."},
]


def sync() -> list[dict]:
    out = []
    for e in CATALOG:
        meta = {k: v for k, v in e.items() if k not in ("model_id", "status")}
        meta["artifact_sha256"] = R.file_sha256(BACKEND_DIR / e["artifact_path"])
        out.append(R.register(e["model_id"], meta, e["status"]))
    return out


if __name__ == "__main__":
    for m in sync():
        print(m["model_id"], m["status"])
