"""
v2 artifact: the pre-registered procedure applied once at a training cutoff (a quarter-start issue date), frozen as
canonical JSON with its own SHA-256 (never pickle). It records the inner-fold selection, the selected model's
parameters, the split-conformal half-widths per lead, the mechanical reliability labels from the validation run,
the data hash and the pre-registration hash. load() verifies all of it and raises on any mismatch.

    python -m app.forecasting.v2.artifact build 2026-10-01   -> data/forecasting/artifacts/v2_<cutoff>.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from app.forecasting import sws as T
from app.forecasting.evidence import ReliabilityStatus
from app.forecasting.v2 import models as V
from app.forecasting.v2 import select as S

ART_DIR = Path(__file__).resolve().parents[3] / "data" / "forecasting" / "artifacts"
VERDICT = Path(__file__).resolve().parents[4] / "docs" / "aipheed" / "v2" / "results" / "v2_verdict.json"
PREREG = Path(__file__).resolve().parents[4] / "docs" / "aipheed" / "v2" / "PREREGISTRATION.md"
SCHEMA = 2
METHOD = "AIPHEED-V2"
PREPROCESSING_VERSION = "sws-quarter-mean+binomial-se/1"
FEATURES = ["sws_hunger_history"]
LABELS = {s.value for s in ReliabilityStatus} | {"DEVELOPMENT_PASS"}


class ArtifactError(RuntimeError):
    pass


def _canonical(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(p: Path, normalise: bool = False) -> str:
    b = Path(p).read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if normalise else b).hexdigest()


def build(cutoff: date, rounds_path: Path = T.SWS_ROUNDS, verdict_path: Path = VERDICT) -> dict:
    if cutoff.day != 1 or cutoff.month not in (1, 4, 7, 10):
        raise ArtifactError("the training cutoff must be a quarter-start issue date")
    rr = T.load_rounds(rounds_path)
    known = T.known_at(rr, cutoff)
    if known.empty:
        raise ArtifactError(f"no SWS round published before {cutoff}")
    wf = S.walk_forward(rr, cutoff)
    model, log = S.select(wf, rr, cutoff)
    p = V.fit(model, known)
    conformal = {}
    for k in S.LEADS:
        half, n = S.conformal_halfwidth(wf, rr, cutoff, model, k)
        conformal[str(k)] = {"halfwidth80": half, "n_residuals": n}
    verdict = json.loads(Path(verdict_path).read_text(encoding="utf-8"))
    status = {str(k): v for k, v in verdict["served_reliability_status_by_lead"].items()}
    body = {"schema": SCHEMA, "method": METHOD, "model": model, "candidates": list(V.CANDIDATES),
            "training_cutoff": cutoff.isoformat(), "latest_quarter_used": T.qs(p.upto),
            "params": {"q": p.q, "kappa": p.kappa, "upto": p.upto, "loglik": p.loglik},
            "selection_log": log, "conformal": conformal,
            "reliability_status_by_lead": status, "verdict_file_sha256": _sha(verdict_path),
            "features": FEATURES, "preprocessing_version": PREPROCESSING_VERSION,
            "data_file": Path(rounds_path).name, "data_sha256": _sha(rounds_path),
            "preregistration_sha256_lf": _sha(PREREG, normalise=True),
            "evidence_scope": "SWS area level (4 areas); CALABARZON lies in Balance Luzon"}
    body["artifact_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def write(body: dict, art_dir: Path = ART_DIR) -> Path:
    art_dir.mkdir(parents=True, exist_ok=True)
    out = art_dir / f"v2_{body['training_cutoff']}.json"
    if out.exists():
        raise ArtifactError(f"{out.name} exists: artifacts are write-once")
    out.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return out


def load(path: Path) -> tuple[dict, V.Params]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if body.get("schema") != SCHEMA or body.get("method") != METHOD or body.get("model") not in V.CANDIDATES:
        raise ArtifactError("unsupported v2 artifact schema, method or model")
    if body.get("features") != FEATURES or body.get("preprocessing_version") != PREPROCESSING_VERSION:
        raise ArtifactError("artifact feature config or preprocessing version does not match this code")
    claimed = body.get("artifact_sha256")
    if hashlib.sha256(_canonical({k: v for k, v in body.items() if k != "artifact_sha256"})).hexdigest() != claimed:
        raise ArtifactError("artifact hash mismatch: the file was edited")
    pr = body["params"]
    if not (0 < float(pr["q"]) < 1e3) or float(pr["kappa"]) not in V.KAPPA_GRID:
        raise ArtifactError("parameter out of range")
    for k in map(str, S.LEADS):
        c = body["conformal"].get(k)
        if c is None or (c["halfwidth80"] is not None and not (0 < c["halfwidth80"] < 50)):
            raise ArtifactError(f"conformal half-width for lead {k} missing or out of range")
        if body["reliability_status_by_lead"].get(k) not in LABELS:
            raise ArtifactError(f"reliability status for lead {k} missing or not a locked label")
    return body, V.Params(body["model"], float(pr["q"]), float(pr["kappa"]), int(pr["upto"]), float(pr["loglik"]))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "build":
        print(write(build(date.fromisoformat(sys.argv[2]))))
    else:
        sys.exit("usage: python -m app.forecasting.v2.artifact build YYYY-MM-DD")
