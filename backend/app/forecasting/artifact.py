"""
Frozen, hashed model artifacts (JSON, never pickle). An artifact records the model name, its estimated parameters, the
training cutoff (issue date whose published data were used), the data file hash, the code version and a feature
config; its own SHA-256 is computed over the canonical JSON. load() verifies schema, hash and data vintage and raises
on any mismatch.

    python -m app.forecasting.artifact build 2026-11-01      -> backend/data/forecasting/artifacts/seas_llm_<cutoff>.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from app.forecasting import models as M
from app.forecasting import sws as T

ART_DIR = Path(__file__).resolve().parents[2] / "data" / "forecasting" / "artifacts"
SCHEMA = 1
PREPROCESSING_VERSION = "sws-quarter-mean+binomial-se/1"
FEATURES = ["sws_hunger_history"]          # SEAS-LLM uses only the target history and documented survey facts


class ArtifactError(RuntimeError):
    pass


def _file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _canonical(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build(cutoff: date, rounds_path: Path = T.SWS_ROUNDS) -> dict:
    qt = T.known_at(T.load_rounds(rounds_path), cutoff)
    if qt.empty:
        raise ArtifactError(f"no SWS round published before {cutoff}")
    p = M.fit_seas(qt)
    body = {"schema": SCHEMA, "model": "SEAS-LLM", "model_family": "measurement-aware seasonal local level",
            "training_cutoff": cutoff.isoformat(), "latest_quarter_used": T.qs(p.upto),
            "params": {"s2": p.s2, "b": p.b, "seas": {str(k): v for k, v in p.seas.items()}, "upto": p.upto},
            "break_quarter": T.qs(M.BREAK), "features": FEATURES, "preprocessing_version": PREPROCESSING_VERSION,
            "data_file": rounds_path.name, "data_sha256": _file_sha(rounds_path),
            "evidence_scope": "SWS area level (4 areas); CALABARZON lies in Balance Luzon"}
    body["artifact_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def write(body: dict) -> Path:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    out = ART_DIR / f"seas_llm_{body['training_cutoff']}.json"
    if out.exists():
        raise ArtifactError(f"{out.name} exists: artifacts are write-once")
    out.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return out


def load(path: Path, rounds_path: Path = T.SWS_ROUNDS, allow_newer_data: bool = True) -> tuple[dict, M.SeasParams]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if body.get("schema") != SCHEMA or body.get("model") != "SEAS-LLM":
        raise ArtifactError("unsupported artifact schema or model")
    if body.get("features") != FEATURES or body.get("preprocessing_version") != PREPROCESSING_VERSION:
        raise ArtifactError("artifact feature config or preprocessing version does not match this code")
    claimed = body.get("artifact_sha256")
    check = {k: v for k, v in body.items() if k != "artifact_sha256"}
    if hashlib.sha256(_canonical(check)).hexdigest() != claimed:
        raise ArtifactError("artifact hash mismatch: the file was edited")
    if not allow_newer_data and _file_sha(rounds_path) != body["data_sha256"]:
        raise ArtifactError("data file differs from the artifact's training data vintage")
    pr = body["params"]
    for k in ("s2", "b"):
        if not (0 <= float(pr[k]) < 1e4):
            raise ArtifactError(f"parameter {k} out of range")
    return body, M.SeasParams(float(pr["s2"]), float(pr["b"]), {int(k): float(v) for k, v in pr["seas"].items()}, int(pr["upto"]))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "build":
        print(write(build(date.fromisoformat(sys.argv[2]))))
    else:
        sys.exit("usage: python -m app.forecasting.artifact build YYYY-MM-DD")
