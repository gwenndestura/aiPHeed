"""
The map serves the FIRI v2 index by default, as origin/main does; the Chapter I probability (P0H4) is opt-in
(AIPHEED_MAP_MODEL=ch1). On the FIRI path the five driver bars use the corrected attribution: a driver's size is the
sum of the absolute Shapley values of its indicators, shares are among the five drivers only, and the direction is
the sign of the net push.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import e41_lead2 as E41L2
from app.ml.inference import thesis_system as THESIS
from app.services import dashboard as D

client = TestClient(app)
FIVE = ("market", "climate", "fish_kill", "employment", "ofw_remittance")
SLUGS = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
         "batangas": "PH040500000"}


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_default_map_model_is_firi(thesis):
    assert not CH1.active()
    thesis.setenv("AIPHEED_MAP_MODEL", "ch1")
    assert CH1.active() == CH1.exported()


@pytest.mark.parametrize("scope,id_,quarter,score", [
    ("province", "cavite", "2027-Q1", 0.757098),        # origin/main's served values
    ("region", "calabarzon", "2027-Q1", 0.744),
])
def test_served_score_matches_origin_main(thesis, scope, id_, quarter, score):
    f = _get("/api/v1/forecast", scope=scope, id=id_, quarter=quarter, horizon="forecast")
    assert f["riskScore"] == pytest.approx(score, abs=1e-4)
    assert f["riskLevel"] == "high"


@pytest.mark.parametrize("quarter", ("2026-Q4", "2027-Q1"))
def test_province_score_is_the_firi_index(thesis, quarter):
    rec = E41L2.record()
    for slug, code in SLUGS.items():
        res = THESIS.firi_for(rec, quarter, code)
        f = _get("/api/v1/forecast", scope="province", id=slug, quarter=quarter, horizon="forecast")
        assert f["riskScore"] == pytest.approx(res["firi"], abs=1e-6)


@pytest.mark.parametrize("quarter", ("2026-Q4", "2027-Q1"))
def test_driver_shares_are_gross_and_five_only(thesis, quarter):
    rec = E41L2.record()
    for slug, code in SLUGS.items():
        sv = THESIS.shap_values(THESIS.firi_for(rec, quarter, code))
        mags = {g: sum(abs(sv.get(k, 0.0)) for k in THESIS.FIVE_GROUPS[g]) for g in FIVE}
        nets = {g: sum(sv.get(k, 0.0) for k in THESIS.FIVE_GROUPS[g]) for g in FIVE}
        e = _get("/api/v1/explainability", scope="province", id=slug, quarter=quarter)
        got = {t["key"]: t for t in e["triggers"]}
        assert set(got) == set(FIVE)
        assert sum(t["pct"] for t in got.values()) == 100
        assert {g: got[g]["pct"] for g in FIVE} == dict(zip(FIVE, D._integer_shares([mags[g] for g in FIVE])))
        for g in FIVE:
            if got[g]["pct"] > 0 and abs(nets[g]) > 1e-12:
                assert got[g]["direction"] == ("increases_risk" if nets[g] > 0 else "protective")


def test_cavite_and_region_shares_2027_q1(thesis):
    cav = {t["key"]: t["pct"] for t in _get("/api/v1/explainability", scope="province", id="cavite",
                                            quarter="2027-Q1")["triggers"]}
    assert cav == {"employment": 39, "climate": 33, "fish_kill": 17, "market": 11, "ofw_remittance": 0}
    reg = {t["key"]: t["pct"] for t in _get("/api/v1/explainability", scope="region", id="calabarzon",
                                            quarter="2027-Q1")["triggers"]}
    assert reg == {"climate": 44, "employment": 36, "market": 11, "fish_kill": 9, "ofw_remittance": 0}


def test_region_bars_match_the_index_endpoint(thesis):
    e = {t["key"]: t["pct"] for t in _get("/api/v1/explainability", scope="region", id="calabarzon",
                                          quarter="2027-Q1")["triggers"]}
    idx = _get("/api/v1/index", scope="region", id="calabarzon", quarter="2027-Q1")
    for d in idx["drivers"]:
        if d["pct"] is not None:
            assert e[d["key"]] == d["pct"]


def test_chapter1_probability_still_served_when_opted_in(thesis):
    thesis.setenv("AIPHEED_MAP_MODEL", "ch1")
    r = CH1.row("PH040100000", "2027-Q1")
    f = _get("/api/v1/forecast", scope="province", id="cavite", quarter="2027-Q1", horizon="forecast")
    assert f["riskScore"] == pytest.approx(float(r["probability"]), abs=1e-6)


def test_chapter1_evaluation_readable_in_firi_mode(thesis):
    assert _get("/api/v1/final/risk/evaluation")["max_reliable_lead"] == 1
