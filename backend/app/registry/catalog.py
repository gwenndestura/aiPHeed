"""Models known to the registry. `python -m app.registry.catalog` (re)registers them; statuses are kept for an
unchanged artifact (see app.registry.register)."""
from __future__ import annotations

from app import registry as R
from app.paths import BACKEND_DIR

PFI_TESTS = "tests/unit/test_pfi.py"
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
