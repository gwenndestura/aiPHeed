"""
Integrity-checked loading of pickled model artifacts (joblib). joblib/pickle executes code on load, so an artifact is
loaded only if (1) it resolves inside backend/models/ and (2) its SHA-256 equals the entry recorded in
backend/models/MODEL_MANIFEST.json. Anything else raises ArtifactIntegrityError: no silent fallback.

    python -m app.forecasting.safe_load --record models/<file>   (record an artifact you built and trust)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
MODELS = BACKEND / "models"
MANIFEST = MODELS / "MODEL_MANIFEST.json"


class ArtifactIntegrityError(RuntimeError):
    pass


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    p = (p if p.is_absolute() else BACKEND / p).resolve()
    if MODELS.resolve() not in p.parents:
        raise ArtifactIntegrityError(f"{p} is outside {MODELS}: refusing to unpickle it")
    return p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def verified_joblib_load(path: str | Path):
    import joblib

    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    expected = manifest().get(p.name)
    if expected is None:
        raise ArtifactIntegrityError(f"{p.name} is not recorded in {MANIFEST.name}: refusing to unpickle an unverified file")
    actual = sha256(p)
    if actual != expected:
        raise ArtifactIntegrityError(f"{p.name}: SHA-256 {actual[:12]}… does not match the manifest {expected[:12]}…")
    return joblib.load(p)


def record(path: str | Path) -> str:
    p = _resolve(path)
    m = manifest()
    m[p.name] = sha256(p)
    MANIFEST.write_text(json.dumps(dict(sorted(m.items())), indent=1) + "\n", encoding="utf-8", newline="\n")
    return m[p.name]


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--record":
        print(record(sys.argv[2]))
    else:
        sys.exit("usage: python -m app.forecasting.safe_load --record models/<file>")
