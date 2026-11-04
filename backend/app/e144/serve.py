"""Read-only E144 candidate outputs for /api/v1/admin/candidates/e144-lbf-1.0/<view> (admin only)."""
from __future__ import annotations

import json

import pandas as pd

from app.e139.serve import ArtifactMissing
from app.e140 import serve as S140
from app.e144 import OUT


def _j(path):
    if not path.exists():
        raise ArtifactMissing(f"E144 output {path.name} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def outlook() -> dict:
    from app.quarterly.target import forecast_target
    f, ft = _j(OUT / "issue" / "forecast.json"), forecast_target()
    return {**f, "CANDIDATE_NOT_APPROVED": True, "current": f["viewing_quarter"] == ft["calendar_quarter"],
            "expected_target_quarter": ft["target_quarter"]}


def evaluation() -> dict:
    return _j(OUT / "results.json")


def model_card() -> dict:
    f = outlook()
    return {k: f[k] for k in ("model", "validation_status", "threshold", "link", "class_rule", "meaning",
                              "sealed_prediction_sha256")}


def lgus() -> dict:
    p = OUT / "issue" / "lgus_next_quarter.csv"
    if not p.exists():
        raise ArtifactMissing("E144 LGU file missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


register = S140.register
