"""
tests/integration/test_e97_validation.py
----------------------------------------
E97: tied to the frozen protocol; the served FIRI v2 evaluation is reproduced and leakage-free (H domain, evidence
weights, timeline); the calibrated regional probability is not served (decision rule 2); the Objective 4 table is on
the same origins; the LGU audit; ISO 25010 reports no invented responses; the thesis dashboard keeps serving its
issued record, under its own quarter, after the calendar advances, and every LGU joins a map shape.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

E97 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E97_Validation_Completion"
RUNS = E97 / "runs"


def _run(suffix: str) -> Path:
    c = sorted(p for p in RUNS.iterdir() if p.is_dir() and p.name.endswith(suffix) and any(p.iterdir()))
    assert c, suffix
    return c[-1]


@pytest.fixture(scope="module")
def firi():
    p = sorted(p for p in RUNS.iterdir() if p.is_dir() and p.name.endswith("Z"))[-1]
    return json.loads((p / "firi_validation.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def obj4():
    return json.loads((_run("_objective4") / "objective4_t43.json").read_text(encoding="utf-8"))


def test_protocol_hash(firi, obj4):
    sha = hashlib.sha256((E97 / "PROTOCOL.md").read_bytes()).hexdigest()
    assert (E97 / "PROTOCOL.sha256").read_text().split()[0] == sha == firi["protocol_sha256"] == obj4["protocol_sha256"]
    for s in ("_lgu", "_fnri"):
        j = next(_run(s).glob("*.json"))
        assert json.loads(j.read_text(encoding="utf-8"))["protocol_sha256"] == sha


def test_firi_reproduced_and_leakage_free(firi):
    q = firi["Q1"]
    a = q["Q1a"]
    assert a["recomputed"]["confusion"] == a["stored"]["confusion"]
    assert abs(a["recomputed"]["brier"] - a["stored"]["brier"]) < 1e-6        # history stores 6 decimals
    assert q["Q1b"]["mismatches"] == 0 and q["Q1b"]["rows"] == 90
    assert q["Q1c"]["mismatched_targets"] == 0 and q["Q1c"]["max_abs_weight_diff"] < 1e-9
    assert q["Q1d"]["violations"] == []


def test_firi_regional_results(firi):
    m = firi["Q2"]["metrics"]
    assert firi["quarters"] == 15
    assert m["firi"]["accuracy"] == pytest.approx(14 / 15) and m["firi"]["confusion"] == {"TP": 9, "FP": 0, "FN": 1, "TN": 5}
    assert m["h1"]["accuracy"] == pytest.approx(10 / 15)
    assert firi["Q2"]["serve_calibrated_probability"] is False                # decision rule 2
    assert firi["Q2"]["paired_balacc_firi_minus_h1"]["ci95"][0] > 0
    assert firi["Q4"]["onsets"]["firi_hits"] == 2 and firi["Q4"]["onsets"]["h1_hits"] == 1


def test_objective4_same_origins(obj4):
    for k in ("1", "2"):
        r = obj4["per_k"][k]
        assert r["rows"] == 65 and r["target_quarters"] == 13
        assert all(a["n"] == 65 for a in r["arms"].values())
        assert r["arms"]["LR-ALL"]["issued"] == 65
    assert obj4["per_k"]["1"]["arms"]["M-U96-POV"]["accuracy"] == pytest.approx(55 / 65)


def test_lgu_audit():
    j = json.loads(next(_run("_lgu").glob("lgu_sensitivity.json")).read_text(encoding="utf-8"))
    a = j["audit"]
    assert a["rows"] == a["unique_codes"] == a["map_features"] == 142
    assert a["lgu_specific_poverty"] == 141 and [s["lgu_name"] for s in a["substituted"]] == ["Lucena"]
    assert a["psgc_province_prefix_consistent"] and a["missing_population_or_area"] == 0


def test_iso25010_never_invents_responses():
    out = subprocess.run([sys.executable, str(E97 / "iso25010" / "score_iso25010.py"), str(E97 / "iso25010" / "response_template.csv")],
                         capture_output=True, text=True, check=True)
    r = json.loads(out.stdout)
    assert r["status"] == "NO_RESPONSES" and r["respondents"] == 0 and r["required"] == 50


@pytest.fixture()
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app), monkeypatch


@pytest.mark.parametrize("now, target, available, rows", [
    ("2026-10-22T10:00:00", "2027-Q1", True, 5),
    ("2027-01-15T10:00:00", "2027-Q2", False, 5),     # E97: was 0 (blank dashboard) before the governs() fix
    ("2027-04-15T10:00:00", "2027-Q3", False, 0),     # a record whose target has passed is not served as a forecast
])
def test_target_advances_and_record_keeps_its_quarter(thesis, now, target, available, rows):
    c, mp = thesis
    mp.setenv("AIPHEED_NOW", now)
    ft = c.get("/api/v1/config").json()["quarterRange"]["forecastTarget"]
    assert ft["target_quarter"] == target
    st = ft["issuedForecast"]
    assert st["available"] is available and st["issuedForecastTarget"] == "2027-Q1"
    j = c.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json()
    assert j["quarter"] == "2027-Q1" and len(j["data"]) == rows
    for p in j["data"]:
        assert 0 <= p["riskScore"] <= 1 and p["riskLevel"] == ("high" if p["riskScore"] >= 0.5 else "low")
    if not available:
        assert target in st["statement"] and "not been issued" in st["statement"]


def muni_key(pid: str, name: str) -> tuple[str, str]:
    """frontend/src/components/PhilippineMap.tsx muniKey: lower-case, trimmed, without 'city of ' / ' city'."""
    n = re.sub(r"\s+city$", "", re.sub(r"^city of\s+", "", name.lower().strip()))
    return pid, n


def test_every_lgu_joins_a_map_shape(thesis):
    c, mp = thesis
    mp.setenv("AIPHEED_NOW", "2026-10-22T10:00:00")
    geo = json.loads((Path("..") / "frontend" / "public" / "calabarzon-municities.json").read_text(encoding="utf-8"))
    shapes = {muni_key(f["properties"]["province_id"], f["properties"]["name"]) for f in geo["features"]}
    served = set()
    for pid in ("batangas", "cavite", "laguna", "quezon", "rizal"):
        j = c.get(f"/api/v1/provinces/{pid}/municipalities", params={"quarter": "2027-Q1"}).json()
        for m in j["data"]:
            assert m["riskIndex"] is not None and 0 <= m["riskIndex"] <= 1
            served.add(muni_key(pid, m["name"]))
    assert len(served) == 142 and served == shapes
