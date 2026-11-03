"""Read-only E140 candidate outputs for /api/v1/admin/candidates/e140-lgbm-native-1.0/<view> (admin only)."""
from __future__ import annotations

import json

import pandas as pd

from app.e139.serve import ArtifactMissing
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e140" / "out"


def _j(name):
    p = OUT / name
    if not p.exists():
        raise ArtifactMissing(f"E140 output {name} is missing; run python -m app.e140.issue")
    return json.loads(p.read_text())


def outlook() -> dict:
    return _j("forecast_next_quarter.json")


def evaluation() -> dict:
    r = _j("results.json")
    return {"decision": r["gate"]["decision"], "checks": r["gate"]["checks"], "final_model": r["final_model"],
            "LORO": r["schemes"]["LORO"], "TFWD": r["schemes"]["TFWD"], "quarterly_test": r["quarterly_test"]}


def model_card() -> dict:
    f = _j("forecast_next_quarter.json")
    return {"model": f["model"], "final_model": f["final_model"], "validation_status": f["validation_status"],
            "sealed_prediction_sha256": f.get("sealed_prediction_sha256")}


def lgus() -> dict:
    p = OUT / "lgus_next_quarter.csv"
    if not p.exists():
        raise ArtifactMissing("lgus_next_quarter.csv missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


def register() -> dict:
    from app.registry import prospective_provincial as PP
    return {"verified": PP.verify(), "records": PP.read()}
