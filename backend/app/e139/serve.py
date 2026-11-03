"""
Read-only serving of E139 outputs for the candidate routes (/api/v1/admin/candidates/e139-lgbm-1.0/<view>) and, only if
the registry approves the model, for the public outlook. Nothing is refitted on a request.
"""
from __future__ import annotations

import json

import pandas as pd

from app.e139 import OUT


class ArtifactMissing(RuntimeError):
    pass


def _j(name):
    p = OUT / name
    if not p.exists():
        raise ArtifactMissing(f"E139 output {name} is missing; run python -m app.e139.issue")
    return json.loads(p.read_text())


def outlook() -> dict:
    live = _j("provinces_live.json")
    return {"model": live["version"], "issue_date": live["issue_date"], "max_reliable_lead": live["max_reliable_lead"],
            "leads": live["leads"], "what_this_is": live["what_this_is"], "provinces": live["provinces"],
            "forecast": None if live["max_reliable_lead"] is None else "structural estimate only for validated leads"}


def evaluation() -> dict:
    r = _j("results.json")
    keep = {k: r[k] for k in ("n_rows", "n_decisive", "max_reliable_lead", "passed", "global_checks", "accuracy_objective_75")}
    keep["LORO"] = r["schemes"]["LORO"]
    keep["TFWD"] = r["schemes"]["TFWD"]
    keep["lead_checks"] = {k: v["checks"] for k, v in r["leads"].items()}
    keep["ablation"] = r["ablation"]
    return keep


def model_card() -> dict:
    return _j("model_artifact.json")


def lgus() -> dict:
    p = OUT / "lgus_calabarzon.csv"
    if not p.exists():
        raise ArtifactMissing("lgus_calabarzon.csv missing")
    d = pd.read_csv(p)
    return {"n": int(len(d)), "label": d["label"].iloc[0], "lgus": d.drop(columns=["label"]).to_dict(orient="records")}


def register() -> dict:
    a = _j("model_artifact.json")
    return {"sealed_prediction_sha256": a["sealed_prediction_sha256"], "results_sha256": a["results_sha256"]}
