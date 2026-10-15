"""
tests/integration/test_e41_lead2.py
-----------------------------------
E41 Lead-2 two-layer candidate: off by default (E38 unchanged), served only with AIPHEED_LEAD2_MODEL=e41, equal to its
frozen forecast, explicit about what its score is, never shown for a target it was not issued for, and honest about
the four triggers that have no model input.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as E41

client = TestClient(app)
E41_DIR = Path("..") / "aipheed-backend-aligned" / "experiments" / "E41_Lead2_Audit"
FROZEN = E41_DIR / "frozen" / "E41_PROSPECTIVE_2027Q1.json"


@pytest.fixture
def e41(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e41")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def _rows(quarter="2027-Q1"):
    body = client.get(f"/api/v1/provinces?quarter={quarter}&horizon=forecast").json()
    return {r["provinceCode"]: r for r in body["data"]}


def test_default_is_e38_and_the_candidate_is_not_served(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 404
    rec = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
    e38 = next(q for q in rec["quarters"] if q["quarter"] == "2027-Q1")["provinces"]
    for code, r in _rows().items():
        assert r["riskScore"] == pytest.approx(e38[code]["p_high"], abs=1e-4)
        assert r.get("scoreType") is None


def test_record_equals_the_frozen_forecast(e41):
    frozen = json.loads(FROZEN.read_text())
    want = (E41_DIR / "frozen" / "E41_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == want
    rec = E41.record()
    assert rec["sources"]["frozen_sha256"] == want and rec["targetQuarter"] == frozen["lead2_target"] == "2027-Q1"
    assert rec["origin"] == "2026-10-01" and rec["information"]["cpiMonthsThrough"] == "2026-08"
    for v in frozen["provinces"].values():
        f = rec["provinces"][v["province_code"]]["forecast"]
        assert f["probabilityAbove4pct"] == pytest.approx(v["lead2_fpp_probability"], abs=5e-4)
        p = f["probabilityAbove4pct"]
        assert f["band"] == ("High" if p >= 2 / 3 else "Watch" if p >= 1 / 3 else "Low")
        assert f["components"]["baseEffect"] + f["components"]["recentMomentum"] == pytest.approx(
            f["foodInflationPoint"], abs=0.02)


def test_summary_separates_observed_forecast_and_category(e41):
    s = client.get("/api/v1/lead2/summary").json()
    assert s["targetQuarter"] == "2027-Q1" and s["lead"] == 2
    assert "not the probability that households are hungry" in s["scoreTypes"]["price_pressure_probability"]
    assert "exploratory" in s["scoreTypes"]["exploratory_food_stress_probability"]
    assert s["evaluation"]["lead2"]["gates"]["verdict"].startswith("experimental")
    p = client.get("/api/v1/lead2/provinces/quezon").json()
    assert set(p) >= {"observed", "forecast", "operational", "exploratory", "warnings"}
    assert p["observed"]["hungerRegional"]["level"] == "region"
    assert p["observed"]["ofwRemittance"]["value"] is None and "no official" in p["observed"]["ofwRemittance"]["status"]
    assert any("regional" in w for w in p["warnings"])


def test_dashboard_serves_the_candidate_only_for_its_target(e41):
    frozen = json.loads(FROZEN.read_text())["provinces"]
    rows = _rows("2027-Q1")
    for v in frozen.values():
        r = rows[v["province_code"]]
        assert r["riskScore"] == pytest.approx(v["lead2_fpp_probability"], abs=5e-4)
        assert r["scoreType"] == "price_pressure_probability" and r["riskBand"] == v["lead2_band"]
    other = _rows("2026-Q3")                                    # any other quarter keeps its E36/E38 meaning
    assert all(r.get("scoreType") is None for r in other.values())


def test_no_stale_forecast_when_the_target_moves(e41, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")    # target is now 2027-Q2; E41 issued only 2027-Q1
    r = client.get("/api/v1/lead2/summary")
    assert r.status_code == 409 and "2027-Q2" in r.text
    assert client.get("/api/v1/provinces?quarter=2027-Q2&horizon=forecast").status_code == 404


def test_tampered_record_is_refused(e41, monkeypatch, tmp_path):
    bad = json.loads(E41.RECORD.read_text(encoding="utf-8"))
    bad["provinces"]["PH040300000"]["forecast"]["probabilityAbove4pct"] = 0.99
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(E41, "RECORD", p)
    assert client.get("/api/v1/lead2/summary").status_code == 503


def test_triggers_without_model_input_are_zero_not_invented(e41):
    body = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    by = {t["key"]: t for t in body["triggers"]}
    assert by["market"]["pct"] == 100
    for g in ("climate", "fish_kill", "employment", "ofw_remittance"):
        assert by[g]["pct"] == 0
