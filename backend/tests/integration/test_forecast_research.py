"""
tests/integration/test_forecast_research.py
-------------------------------------------
FORECAST_RESEARCH candidate P0H4-U (served only with AIPHEED_CH1_ENGINE=fr): the served P0H4 rows, with the Lead-2+
forecasts re-issued the day after the SWS release (hunger part only). The default stays P0H4 with its seal.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
FR_OUT = ROOT / "aipheed-backend-aligned" / "experiments" / "FORECAST_RESEARCH" / "out"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not (CH1.DATA_FR / "rows.csv").exists(), reason="FORECAST_RESEARCH export missing")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _clear_caches():
    """The engine is chosen at process start in serving; here it switches mid-process, so drop memoised views."""
    from app.services import dashboard
    for mod in (dashboard, CH1):
        for v in vars(mod).values():
            if callable(getattr(v, "cache_clear", None)):
                v.cache_clear()


@pytest.fixture
def fr(thesis):
    thesis.setenv("AIPHEED_CH1_ENGINE", "fr")
    _clear_caches()
    yield thesis
    thesis.delenv("AIPHEED_CH1_ENGINE", raising=False)
    _clear_caches()


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_default_is_the_served_p0h4(thesis):
    thesis.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.data_dir() == CH1.DATA
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and "sws_update" not in CH1.evaluation()
    assert {r["model"] for r in CH1.rows().values()} == {"P0H4"}


def test_candidate_changes_only_the_lead2_hunger_part(fr):
    assert CH1.data_dir() == CH1.DATA_FR
    fr.delenv("AIPHEED_CH1_ENGINE")
    served = dict(CH1.rows())
    fr.setenv("AIPHEED_CH1_ENGINE", "fr")
    cand = CH1.rows()
    assert served.keys() == cand.keys()
    same = ("pi_price", "observed", "A1_food", "A1_gap", "shap_A1", "shap_A3", "val_A3", "val_C1", "val_E1")
    for k, s in served.items():
        c = cand[k]
        assert all(s[f] == c[f] for f in same), k
        if c["issue_schedule"] == "A":
            assert all(s[f] == c[f] for f in s if f not in ("model",)), k
        else:
            assert int(c["lead"]) >= 2 and c["issue_date"] == "2026-10-15" and c["sws_newest_q"] == "2026-Q3"
            p = float(c["pi_hunger"]) * float(c["pi_price"])
            assert abs(p - float(c["probability"])) < 1e-5
            assert c["class"] == ("HIGH" if p >= 0.5 else "LOW") and c["model"] == "P0H4-U"


def test_candidate_seal_matches_its_file_and_served_seal_is_untouched(fr):
    ev = CH1.evaluation()
    seal = ev["sws_update"]["seal_sha256"]
    assert hashlib.sha256((FR_OUT / "sealed_prospective_P0H4U.csv").read_bytes()).hexdigest() == seal
    assert ev["seal_sha256"] == SERVED_SEAL
    assert {r["seal_sha256"] for r in CH1.rows().values() if r["issue_schedule"] == "B"} == {seal}
    doc = json.loads((FR_OUT / "PROSPECTIVE_SEAL.json").read_text())
    assert doc["p0h4u_sha256"] == seal and doc["served_seal_unchanged"] == SERVED_SEAL


def test_candidate_keeps_the_reliability_verdict(fr):
    ev = CH1.evaluation()
    assert ev["max_reliable_lead"] == 1 and ev["sws_update"]["lead2"]["reliable"] is False
    assert ev["sws_update"]["lead2"]["failed"]


def test_api_serves_the_candidate_rows(fr):
    cand = CH1.rows()
    for q in ("2026-Q4", "2027-Q1"):
        data = {p["id"]: p for p in _get("/api/v1/provinces", quarter=q)["data"]}
        rows = {r["province"].lower(): r for (_, qq), r in cand.items() if qq == q}
        assert set(rows) <= set(data)
        for slug, r in rows.items():
            assert data[slug]["riskLevel"] == r["class"].lower(), (q, slug)
            assert abs(data[slug]["riskScore"] - float(r["probability"])) < 1e-5, (q, slug)
    ts = {p["quarter"]: p["riskScore"] for p in _get("/api/v1/forecast/timeseries", scope="province",
                                                     id="quezon")["series"]}
    r = next(r for (c, q), r in cand.items() if q == "2027-Q1" and r["province"] == "Quezon")
    assert abs(ts["2027-Q1"] - float(r["probability"])) < 1e-6


def test_lead2_text_states_the_update_and_that_it_is_experimental(fr):
    r = next(r for (_, q), r in CH1.rows().items() if q == "2027-Q1")
    t = CH1.reliability_text(r)
    assert "experimental" in t and "Re-issued 2026-10-15" in t and "SWS" in t
    assert any(s.startswith("SWS-update issue") for s in CH1.reliability_sentences())
    assert CH1.model_line().startswith("P0H4-U")
