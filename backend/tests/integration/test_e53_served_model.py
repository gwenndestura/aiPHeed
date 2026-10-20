"""
tests/integration/test_e53_served_model.py
------------------------------------------
The E53-A1 record (data/e53/e53_record.json): E48-A1's inputs plus five measured driver-condition inputs (cond_*),
shrinkage-calibrated. It is the default served model since the final integration (AIPHEED_RECORD unset); E49 stays
selectable with AIPHEED_RECORD=e49 (serve_e49 fixture). The served scores are the record's p_high, the API's Q4 2026
index and driver shares must equal the E53 experiment's (backend/experiments/e53/E53_results.json), every driver must
have a non-zero share, the served engine is named from the record, and the E49 driver mapping must be unchanged.
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
REC = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
RES = json.loads(Path("experiments/e53/E53_results.json").read_text(encoding="utf-8"))["arms"]["A1"]["q4_2026"]
COND = ["cond_market", "cond_climate", "cond_fish", "cond_employment", "cond_ofw"]
DRIVERS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
SLUG = {"Cavite": "cavite", "Laguna": "laguna", "Quezon": "quezon", "Rizal": "rizal", "Batangas": "batangas"}


def test_e53_record_loads_and_is_the_default():
    assert E31.DEFAULT_RECORD == "e53" and Path(E31.RECORD_PATH) == Path("data/e53/e53_record.json")
    body = {k: v for k, v in REC.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == REC["content_sha256"]
    assert "E53-A1" in REC["served_engine"]["name"]
    assert set(COND) <= set(REC["served_engine"]["config"]["features"])
    for f in ("E53-A1-LGBM_O2026-10-01.txt", "E53_C2_calibration.json", "E53_COND_2026Q2.json"):
        assert (Path("data/e53/model") / f).exists(), f
    q4 = next(q for q in REC["quarters"] if q["quarter"] == "2026-Q4")
    cond = json.loads(Path("data/e53/model/E53_COND_2026Q2.json").read_text(encoding="utf-8"))["values"]
    for v in q4["provinces"].values():                                     # served cond_* = the frozen values
        vals = {d["key"]: d["value"] for d in v["drivers"]}
        for c in COND:
            want = cond[v["province"]][c]
            assert (vals[c] is None and want is None) or vals[c] == pytest.approx(want, abs=1e-3), (v["province"], c)


def test_q4_2026_index_and_drivers_match_e53_results(serve_e53, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    region = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert region["riskScore"] == pytest.approx(RES["index"]["CALABARZON"], abs=1e-4)
    prov = {r["name"]: r["riskScore"] for r in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]}
    for name, slug in SLUG.items():
        assert prov[name] == pytest.approx(RES["index"][name], abs=1e-4), name
        ex = client.get(f"/api/v1/explainability?scope=province&id={slug}&quarter=2026-Q4").json()
        assert {t["key"]: t["pct"] for t in ex["triggers"]} == RES["drivers"][name]["a"], name
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4").json()
    pct = {t["key"]: t["pct"] for t in ex["triggers"]}
    # E53_results pooled raw log-odds; the API puts each province on its probability scale first (B3), so only the
    # ranking of the two largest drivers is shared with the experiment
    assert pct == {"market": 64, "employment": 18, "fish_kill": 12, "climate": 5, "ofw_remittance": 1}
    assert [k for k, _ in sorted(pct.items(), key=lambda kv: -kv[1])][:2] == ["market", "employment"]
    assert all(pct[k] > 0 for k in DRIVERS), pct                          # all five drivers non-zero
    assert "national-level indicators" in ex["note"] and "SHAP" not in ex["note"]


def test_e53_pdf_is_the_e53_record(serve_e53):
    r = client.get("/api/v1/quarterly/e31/report.pdf")
    assert r.status_code == 200 and r.headers["X-Record-SHA256"] == REC["content_sha256"]
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == REC["content_sha256"]


def test_e49_mapping_and_note_unchanged(serve_e49, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    assert not E31.uses_condition_inputs()
    assert E31.trigger_group_features() is E31.TRIGGER_GROUP_FEATURES
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert {t["key"]: t["pct"] for t in ex["triggers"]} == {"market": 72, "climate": 26, "fish_kill": 2,
                                                            "employment": 0, "ofw_remittance": 0}   # all five
    assert "national-level indicators" not in ex["note"]


# ---------------------------------------------------------------- the default served model (no AIPHEED_RECORD)
def _region_from_record(q):
    row = next(r for r in REC["quarters"] if r["quarter"] == q and r.get("lead", 1) == 1)
    return round(sum(v["p_high"] for v in row["provinces"].values()) / 5, 4)


def test_default_serves_the_e53_scores(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    want = {"2026-Q2": 0.7539, "2026-Q3": 0.896, "2026-Q4": 0.7894}           # the mean of the record's p_high
    for q, v in want.items():
        assert _region_from_record(q) == v, q
        assert client.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}").json()["riskScore"] == v, q
    for row in (r for r in REC["quarters"] if r.get("lead", 1) == 1):         # every province score is the record's
        prov = {p["name"]: p["riskScore"] for p in
                client.get(f"/api/v1/provinces?quarter={row['quarter']}").json()["data"]}
        assert prov == {v["province"]: v["p_high"] for v in row["provinces"].values()}, row["quarter"]


def test_default_names_the_e53_engine(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    se = client.get("/api/v1/quarterly/e31/summary").json()["served_engine"]
    stored = REC["served_engine"]["name"]                                   # "... - PREVIEW" in the protected record
    assert se["name"] == stored.removesuffix(" - PREVIEW") and "E53-A1" in se["name"]
    assert se["why_served"].startswith("Served by default.") and "serves E49" not in se["why_served"]
    assert "0.785 (51/65)" in se["why_served"] and "not demonstrated (95% date-bootstrap interval 0.646 to 0.908)"         in se["why_served"]
    conf = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q4").json()["confidenceStatement"]
    assert se["name"] in conf and "PREVIEW" not in conf
