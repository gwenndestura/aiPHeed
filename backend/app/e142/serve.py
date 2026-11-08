"""Read-only E142 candidate outputs for /api/v1/admin/candidates/e142-state-lgbm-1.0/<view> (admin only)."""
from __future__ import annotations

import json

import pandas as pd

from app.e139.serve import ArtifactMissing
from app.e140 import serve as S140
from app.e142 import OUT


def _j(path):
    if not path.exists():
        raise ArtifactMissing(f"E142 output {path.name} missing")
    return json.loads(path.read_text())


def outlook() -> dict:
    from app.quarterly.target import forecast_target
    f, ft = _j(OUT / "issue" / "forecast_next_quarter.json"), forecast_target()
    return {**f, "current": f["issue_quarter"] == ft["calendar_quarter"], "viewing_quarter": ft["calendar_quarter"],
            "expected_target_quarter": ft["target_quarter"]}


def evaluation() -> dict:
    r = _j(OUT / "results.json")
    return {"gate": r["gate"], "rolling": r["rolling"], "untouched_2013": r["untouched_2013"],
            "timing_sensitivity": r["timing_sensitivity"], "fssi_v2": _j(OUT / "fssi_v2_validity.json")}


def model_card() -> dict:
    f = outlook()
    return {k: f[k] for k in ("model", "final_model", "validation_status", "claim", "explanation_method", "class_rule",
                              "sealed_prediction_sha256")}


def lgus() -> dict:
    p = OUT / "issue" / "lgus_next_quarter.csv"
    if not p.exists():
        raise ArtifactMissing("E142 LGU file missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


register = S140.register
