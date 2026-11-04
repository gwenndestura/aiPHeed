"""Read-only E143 candidate outputs for /api/v1/admin/candidates/e143-re-lgbm-1.0/<view> and
/api/v1/admin/candidates/e143-hre-lgbm-1.0/<view> (admin only; both ids read the same issue, which carries the C4
hierarchical values as model-selection spread)."""
from __future__ import annotations

import json

import pandas as pd

from app.e139.serve import ArtifactMissing
from app.e140 import serve as S140
from app.e143 import OUT


def _j(path):
    if not path.exists():
        raise ArtifactMissing(f"E143 output {path.name} missing")
    return json.loads(path.read_text(encoding="utf-8"))


def outlook() -> dict:
    from app.quarterly.target import forecast_target
    f, ft = _j(OUT / "issue" / "forecast_next_quarter.json"), forecast_target()
    return {**f, "CANDIDATE_NOT_APPROVED": True, "current": f["issue_quarter"] == ft["calendar_quarter"],
            "viewing_quarter": ft["calendar_quarter"], "expected_target_quarter": ft["target_quarter"]}


def evaluation() -> dict:
    r = _j(OUT / "results.json")
    return {"gate": r["gate"], "pooled": r["pooled"], "by_origin": r["by_origin"], "untouched_2013": r["untouched_2013"],
            "vs": r["vs"], "holm": r["holm"], "coverage90": r["coverage90"], "change_rho": r["change_rho"],
            "audit": _j(OUT / "audit.json"), "posthoc": _j(OUT / "posthoc.json")}


def model_card() -> dict:
    f = outlook()
    return {k: f[k] for k in ("model", "final_model", "validation_status", "claim", "class_rule", "concepts", "seals")}


def lgus() -> dict:
    p = OUT / "issue" / "lgus_next_quarter.csv"
    if not p.exists():
        raise ArtifactMissing("E143 LGU file missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


register = S140.register
