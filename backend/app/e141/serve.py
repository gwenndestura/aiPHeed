"""Read-only E141 candidate outputs for /api/v1/admin/candidates/e141-lgbm-3round-1.0/<view> (admin only)."""
from __future__ import annotations

import json

from app.e139.serve import ArtifactMissing
from app.e140 import serve as S140
from app.e141 import OUT


def outlook() -> dict:
    from app.quarterly.target import forecast_target
    p = OUT / "issue" / "forecast_next_quarter.json"
    if not p.exists():
        raise ArtifactMissing("E141 issue missing; run python -m app.e141.issue")
    f, ft = json.loads(p.read_text()), forecast_target()
    return {**f, "current": f["issue_quarter"] == ft["calendar_quarter"], "viewing_quarter": ft["calendar_quarter"],
            "expected_target_quarter": ft["target_quarter"]}


def evaluation() -> dict:
    p = OUT / "results.json"
    if not p.exists():
        raise ArtifactMissing("E141 results missing")
    r = json.loads(p.read_text())
    return {"gate": r["gate"], "untouched_2013": r["untouched_2013"], "rolling": r["rolling"], "ablation": r["ablation"]}


def model_card() -> dict:
    f = outlook()
    return {k: f[k] for k in ("model", "final_model", "validation_status", "claim", "explanation_method", "sealed_prediction_sha256")}


def lgus() -> dict:
    import pandas as pd
    p = OUT / "issue" / "lgus_next_quarter.csv"
    if not p.exists():
        raise ArtifactMissing("E141 LGU file missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


register = S140.register
