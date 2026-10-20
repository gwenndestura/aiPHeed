"""
tests/integration/test_e49_served_model.py
------------------------------------------
E48-A1 (E36's inputs + the five trigger proportions, Chapter 3 Eq. 5) with E49-C2 shrinkage calibration
(data/e49/e49_record.json), served with AIPHEED_RECORD=e49 (serve_e49 fixture; the default was E49 until the final
integration, and is now E53-A1, see test_e53_served_model.py). The record is intact, every served probability is the
E48-A1 probability shrunk toward the training base rate with that date's weight, and the API, drivers and PDF carry
the record's numbers. AIPHEED_RECORD=e36 still serves the E36 record (serve_e36 fixture; see also
test_e36_served_model.py).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e31_engine as E31

client = TestClient(app)
REC = json.loads(Path("data/e49/e49_record.json").read_text(encoding="utf-8"))
NOTE = ("Probabilities are calibrated by shrinkage toward the training base rate (E49-C2); driver shares come from "
        "the LightGBM before calibration.")


def test_e49_is_selectable_and_intact(serve_e49):
    assert E31.DEFAULT_RECORD == "e53"                                       # E49 is no longer the default
    assert Path(E31.RECORD_PATH) == Path("data/e49/e49_record.json")
    body = {k: v for k, v in REC.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == REC["content_sha256"]
    assert "E49-C2" in REC["served_engine"]["name"] and NOTE in REC["served_engine"]["why_served"]
    assert all(NOTE in v["driver_method"] for q in REC["quarters"] if q["lead"] == 1 for v in q["provinces"].values())


def test_served_probabilities_are_the_c2_shrinkage_of_e48_a1():
    bundle = json.loads(Path("data/e49/model/E48_SERVING_BUNDLE.json").read_text(encoding="utf-8"))
    cal = json.loads(Path("data/e49/model/E49_C2_calibration.json").read_text(encoding="utf-8"))
    raw = {q["quarter"]: q["provinces"] for q in bundle["backtests"] + [bundle["forecast"]]}
    for q in REC["quarters"]:
        if q["lead"] != 1:
            continue
        par = cal["params_by_target_quarter"].get(q["quarter"])
        for code, v in q["provinces"].items():
            p0 = raw[q["quarter"]][code]["p_high"]
            want = p0 if par is None else par["a"] * p0 + (1 - par["a"]) * par["base_rate"]
            assert v["p_high"] == pytest.approx(want, abs=1e-4), (q["quarter"], code)
    assert max(v["p_high"] for q in REC["quarters"] if q["lead"] == 1 for v in q["provinces"].values()) < 0.99


def test_q4_2026_index_levels_and_drivers(serve_e49, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    region = client.get("/api/v1/forecast?scope=region&id=calabarzon").json()
    assert region["quarter"] == "2026-Q4" and region["riskScore"] == pytest.approx(0.7784, abs=1e-4)
    prov = {r["name"]: r for r in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]}
    assert prov["Batangas"]["riskScore"] == pytest.approx(0.3353, abs=1e-4) and prov["Batangas"]["riskLevel"] == "low"
    assert all(prov[n]["riskLevel"] == "high" for n in ("Cavite", "Laguna", "Quezon", "Rizal"))
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4").json()
    pct = {t["key"]: t["pct"] for t in ex["triggers"]}
    # region shares on the probability scale (the index averages probabilities); all five groups listed
    assert pct == {"market": 72, "climate": 26, "fish_kill": 2, "employment": 0, "ofw_remittance": 0}
    assert all(t["direction"] == "protective" for t in ex["triggers"] if t["pct"] > 0)   # the drivers with an effect
    # status / statusNote (E42, A. Melindo): what each group is in this forecast
    assert list(ex["triggers"][0]) == ["key", "label", "share", "pct", "signedContribution", "direction", "status",
                                      "statusNote", "evidenceNote", "color", "newsSignalProportion",
                                      "measuredCondition"]           # evidenceNote: Angel's E44 field (null here)
    assert all(t["measuredCondition"] is None for t in ex["triggers"])     # E49 has no condition inputs
    assert "trigger proportions" in ex["note"] and "shrinkage calibration" in ex["note"]


def test_pdf_is_the_e49_record(serve_e49):
    r = client.get("/api/v1/quarterly/e31/report.pdf")
    assert r.status_code == 200 and r.headers["X-Record-SHA256"] == REC["content_sha256"]
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == REC["content_sha256"]


def test_e36_is_still_selectable(serve_e36, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    region = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert region["riskScore"] == pytest.approx(0.8215, abs=1e-4)
    prov = {r["name"]: r["riskScore"] for r in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]}
    assert prov["Batangas"] == pytest.approx(0.169, abs=1e-4)
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert {t["key"]: t["pct"] for t in ex["triggers"]}["market"] == 95
