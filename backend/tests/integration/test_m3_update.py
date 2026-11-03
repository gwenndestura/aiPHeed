"""
tests/integration/test_m3_update.py
-----------------------------------
The Lead-2 mid-quarter update (M3, PREREG_LEAD2 addendum 2) served in place of the official Lead-2 rows
(ch1_system.rows overlay; backend/m3_update, written by LEAD2_MIDQUARTER_UPDATE/runner/export_m3.py). The served M3 rows
reproduce the sealed M3 forecast, appear only from their issue date, replace nothing else, switch off with
AIPHEED_LEAD2_UPDATE=official, and leave rows.csv, evaluation.json and the seals untouched.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)
BACKEND = Path(__file__).resolve().parents[2]
SEAL = BACKEND / "seals" / "2026-11-01_2027-Q1_M3.json"
M3_RESULTS = BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "LEAD2_MIDQUARTER_UPDATE" / "out" / "results.json"
FROZEN = {"data/ch1_engine/rows.csv": "86d05bb62b3449d25b4261097a6ad1db1303ed628e3ad8aeea1eb01da1410cb3",
          "data/ch1_engine/evaluation.json": "fbbb51f39721d34c051fec539b71e3d95e6607db38db961e9d2e2868e2e95187",
          "seals/2026-11-01_2027-Q1_M3.json": "84f4bfe61d920aa75d78f5311b7a52acddfafcd93220da0d7b2eca9789235990",
          "seals/2026-10-15_2027-Q1.json": "781f708df5b4d91684c0e88c37b358043211f1e75bb082871df26bcf0d9caffe"}


def _official() -> dict:
    with open(CH1.DATA / "rows.csv", newline="", encoding="utf-8") as f:
        return {(r["province_code"], r["quarter"]): r for r in csv.DictReader(f)}


def _m3() -> list[dict]:
    with open(CH1.M3_DIR / "rows_m3.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def ch1(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-02T09:00:00")
    monkeypatch.delenv("AIPHEED_LEAD2_UPDATE", raising=False)
    return monkeypatch


def _scores(quarter="2027-Q1") -> dict:
    r = client.get("/api/v1/provinces", params={"quarter": quarter})
    assert r.status_code == 200, r.text[:300]
    return {d["provinceCode"]: d["riskScore"] for d in r.json()["data"]}


def test_frozen_files_are_unchanged():
    for f, sha in FROZEN.items():
        assert hashlib.sha256((BACKEND / f).read_bytes()).hexdigest() == sha, f


def test_m3_rows_reproduce_the_sealed_m3_forecast():
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    rows = _m3()
    assert len(rows) == 5 and {r["quarter"] for r in rows} == {"2027-Q1"} and {r["lead"] for r in rows} == {"2"}
    for r in rows:
        s = seal["candidates"]["C3_M3"][r["province_code"]]
        assert float(r["pi_hunger"]) == pytest.approx(s["hunger"], abs=1e-6)
        assert float(r["pi_price"]) == pytest.approx(s["price"], abs=1e-6)
        assert float(r["probability"]) == pytest.approx(s["probability"], abs=1e-6)
        assert float(r["probability"]) == pytest.approx(float(r["pi_hunger"]) * float(r["pi_price"]), abs=1e-6)
        assert r["class"] == s["M3-D0"] == ("HIGH" if float(r["probability"]) >= 0.5 else "LOW")
        assert r["issue_date"] == "2026-11-01" and r["model"] == "P0H4-M3" and r["seal_sha256"] == FROZEN[
            "seals/2026-11-01_2027-Q1_M3.json"]
        assert r["sws_newest_published"] < "2026-11-01" and r["news_latest_published"][:10] < "2026-11-01"
        assert r["psa_newest_month"] == "2026-09"                    # available from 2026-11-01 (month M+2)
    assert list(_m3()[0]) == list(next(iter(_official().values())))  # same columns as rows.csv


def test_m3_replaces_only_the_lead2_rows_and_only_from_its_issue_date(ch1):
    official = _official()
    served = CH1.rows()
    m3_keys = {(r["province_code"], r["quarter"]) for r in _m3()}
    assert set(served) == set(official)
    for k, r in served.items():
        assert (CH1.is_m3(r)) == (k in m3_keys)
        if k not in m3_keys:
            assert r == official[k], k                               # Lead 1, past quarters, Leads 3-4: untouched
    ch1.setenv("AIPHEED_NOW", "2026-10-31T23:00:00")                 # before the M3 issue date: the official Lead 2
    assert not any(CH1.is_m3(r) for r in CH1.rows().values())
    assert all(CH1.rows()[k] == official[k] for k in m3_keys)


def test_the_api_serves_m3_and_the_switch_restores_the_official_lead2(ch1):
    m3 = {r["province_code"]: float(r["probability"]) for r in _m3()}
    got = _scores()
    assert all(got[p] == pytest.approx(v, abs=1e-6) for p, v in m3.items())
    region = client.get("/api/v1/forecast", params={"scope": "region", "id": "calabarzon", "quarter": "2027-Q1"}).json()
    assert region["riskScore"] == pytest.approx(sum(got.values()) / 5, abs=5e-4)
    assert region["provinceCounts"]["high"] == sum(v >= 0.5 for v in got.values())
    lead1 = _scores("2026-Q4")
    ch1.setenv("AIPHEED_LEAD2_UPDATE", "official")
    off = _scores()
    official = _official()
    assert all(off[p] == pytest.approx(float(official[(p, "2027-Q1")]["probability"]), abs=1e-6) for p in off)
    assert _scores("2026-Q4") == lead1                               # Lead 1 is the same either way


def test_m3_drivers_are_its_own_and_close_at_100(ch1):
    for slug in ("cavite", "laguna", "quezon", "rizal", "batangas"):
        d = client.get("/api/v1/explainability", params={"scope": "province", "id": slug, "quarter": "2027-Q1"}).json()
        assert sum(t["pct"] for t in d["triggers"]) + d["otherPct"] == 100
        code = next(c for (c, q), r in CH1.rows().items() if q == "2027-Q1" and r["province"].lower() == slug)
        r = CH1.row(code, "2027-Q1")
        market = float(r["shap_A1"]) + float(r["shap_A2"]) + float(r["shap_A3"])
        t = next(t for t in d["triggers"] if t["key"] == "market")
        assert t["signedContribution"] == pytest.approx(market, abs=1e-5)


def test_m3_is_labelled_experimental_with_its_own_numbers(ch1):
    ev = CH1.evaluation_m3()
    res = json.loads(M3_RESULTS.read_text(encoding="utf-8"))["models"]["M3_midquarter"]
    for k in ("accuracy", "balanced", "precision", "recall", "auc", "brier", "failed"):
        assert ev["development"][k] == res[k]
    f = client.get("/api/v1/forecast", params={"scope": "province", "id": "cavite", "quarter": "2027-Q1"}).json()
    assert "mid-quarter update (M3)" in f["horizonLabel"] and "experimental" in f["horizonLabel"]
    assert "passes 6 of the seven reliability rules" in f["horizonLabel"]
    assert CH1.status(CH1.row(next(iter(_m3()))["province_code"], "2027-Q1")) == "experimental"
    assert any("mid-quarter update (M3" in s for s in CH1.reliability_sentences())
