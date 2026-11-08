"""Release-gate tests: no approved model -> nothing served; promotion refused unless every check passed for the exact
artifact; tampering and artifact changes clear production; the gate logic on synthetic evidence; frozen thresholds."""
from __future__ import annotations

import json

import pytest

from app import registry as R
from app.registry import gate as G


@pytest.fixture()
def reg(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "REGISTRY", tmp_path / "registry.json")
    monkeypatch.setattr(R, "APPROVALS", tmp_path / "approvals")
    monkeypatch.setattr(R, "BACKEND_DIR", tmp_path)
    (tmp_path / "art.json").write_text('{"m": 1}')
    R.register("m1", {"version": "1", "artifact_path": "art.json", "artifact_sha256": R.file_sha256(tmp_path / "art.json")})
    return tmp_path


def _gate(passed: bool, sha: str) -> dict:
    return {"passed": passed, "artifact_file_sha256": sha, "evaluated_utc": "x",
            "checks": [{"id": "B6", "status": "pass" if passed else "not_evaluable"}]}


def test_nothing_served_without_approval(reg):
    with pytest.raises(R.NoApprovedModel):
        R.production()


def test_promotion_refused_when_gate_failed(reg):
    R.record_gate("m1", _gate(False, R.file_sha256(reg / "art.json")))
    assert R.load()["models"]["m1"]["status"] == "rejected"
    with pytest.raises(PermissionError):
        R.promote("m1", "tester")
    with pytest.raises(R.NoApprovedModel):
        R.production()


def test_promotion_and_tamper_detection(reg):
    R.record_gate("m1", _gate(True, R.file_sha256(reg / "art.json")))
    rec = R.promote("m1", "tester")
    assert R.production()["model_id"] == "m1" and (reg / "approvals" / "m1.json").exists()
    assert rec["approver"] == "tester"
    (reg / "art.json").write_text('{"m": 2}')                    # artifact edited after approval
    with pytest.raises(R.NoApprovedModel):
        R.production()


def test_artifact_must_match_gate(reg):
    R.record_gate("m1", _gate(True, "0" * 64))
    with pytest.raises(PermissionError):
        R.promote("m1", "tester")


def test_new_artifact_clears_production(reg):
    R.record_gate("m1", _gate(True, R.file_sha256(reg / "art.json")))
    R.promote("m1", "tester")
    (reg / "art.json").write_text('{"m": 3}')
    R.register("m1", {"version": "2", "artifact_path": "art.json", "artifact_sha256": R.file_sha256(reg / "art.json")})
    assert R.load()["production"] is None and R.load()["models"]["m1"]["status"] == "candidate"


def _evidence(**over) -> dict:
    ev = {"artifact_loads": True, "artifact_path": "a", "target": {"is_food_insecurity_measurement": True},
          "families_used": G.THRESHOLDS["required_families"], "groups_used": G.THRESHOLDS["required_groups"],
          "n1_version": "improved",
          "chronological": {"n_targets": 30, "n_high": 12,
                            "metrics": {"accuracy": 0.8, "balanced_accuracy": 0.78, "high_recall": 0.7, "high_precision": 0.6},
                            "baselines": {"model_brier": 0.10, "baseline_brier": {"persistence": 0.12}}},
          "independent": {"applicable": True, "passed": True},
          "calibration": {"interval_nominal": 0.9, "interval_coverage": 0.88, "ece": 0.05},
          "geographic": {"passed_at_served_resolution": True}, "horizon": {"validated_leads": [1]},
          "group_contribution": {g: {"tested_out_of_sample": True} for g in G.THRESHOLDS["required_groups"]},
          "documents": ["docs/pfi/METHODOLOGY.md"]}
    ev.update(over)
    return ev


OK = {"returncode": 0}


def test_gate_passes_only_complete_evidence():
    t = {"release": OK, "leakage": OK, "all": OK}
    assert all(c["status"] == "pass" for c in G.checks(_evidence(), t))
    bad = {"n1_version": None, "chronological": None,
           "target": {"is_food_insecurity_measurement": False}}
    for k, v in bad.items():
        cs = G.checks(_evidence(**{k: v}), t)
        assert any(c["status"] != "pass" for c in cs), k


def test_majority_class_and_low_recall_rejected():
    t = {"release": OK, "leakage": OK, "all": OK}
    ch = _evidence()["chronological"]
    ch = {**ch, "metrics": {"accuracy": 0.82, "balanced_accuracy": 0.5, "high_recall": 0.0, "high_precision": 0.0}}
    cs = {c["id"]: c["status"] for c in G.checks(_evidence(chronological=ch), t)}
    assert cs["B9"] == "fail"


def test_failed_tests_reject():
    cs = {c["id"]: c["status"] for c in G.checks(_evidence(), {"release": OK, "leakage": {"returncode": 1}, "all": OK})}
    assert cs["B5"] == "fail"


def test_thresholds_frozen():
    assert G.THRESHOLDS["accuracy_min"] == 0.75 and G.THRESHOLDS["high_recall_min"] == 0.60
    assert G.THRESHOLDS_SHA256 == G.hashlib.sha256(json.dumps(G.THRESHOLDS, sort_keys=True).encode()).hexdigest()
