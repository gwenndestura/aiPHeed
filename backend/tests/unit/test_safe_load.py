"""
tests/unit/test_safe_load.py
----------------------------
Hash-checked unpickling (AUDIT D2): recorded artifacts load; a file outside backend/models, an unrecorded file and a
tampered file are refused.
"""
from __future__ import annotations

import shutil

import pytest

from app.forecasting import safe_load as S


def test_recorded_artifacts_match_manifest():
    m = S.manifest()
    assert m, "MODEL_MANIFEST.json missing"
    present = [n for n in m if (S.MODELS / n).exists()]     # backend/models is gitignored: a fresh clone may lack them
    for name in present:
        assert S.sha256(S.MODELS / name) == m[name]


def test_outside_models_dir_refused(tmp_path):
    f = tmp_path / "x.joblib"
    f.write_bytes(b"\x80\x04K\x01.")
    with pytest.raises(S.ArtifactIntegrityError, match="outside"):
        S.verified_joblib_load(f)


def test_unrecorded_and_tampered_refused(monkeypatch, tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    present = [n for n in S.manifest() if (S.MODELS / n).exists()]
    if not present:
        pytest.skip("no model artifact present locally (backend/models is gitignored)")
    src = S.MODELS / present[0]
    dst = models / src.name
    shutil.copy(src, dst)
    monkeypatch.setattr(S, "MODELS", models)
    monkeypatch.setattr(S, "BACKEND", tmp_path)
    monkeypatch.setattr(S, "MANIFEST", models / "MODEL_MANIFEST.json")
    with pytest.raises(S.ArtifactIntegrityError, match="not recorded"):
        S.verified_joblib_load(dst)
    S.record(dst)
    with open(dst, "ab") as f:
        f.write(b"tamper")
    with pytest.raises(S.ArtifactIntegrityError, match="does not match"):
        S.verified_joblib_load(dst)
