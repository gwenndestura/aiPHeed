"""
tests/integration/test_lead2_preview_flag.py
--------------------------------------------
AIPHEED_LEAD2_PREVIEW (on by default since the final integration; =0 turns it off): the lead-2 row (2027-Q1) is
served as a labelled experimental preview and the dashboard opens on it (defaultQuarter in /quarters and /config, by
the researchers' decision), while the other defaults (current quarter, forecast target, quarter resolution, PDF) stay
on the lead-1 quarter (2026-Q4), which stays on the timeline, and lead 2 never raises an alert. Flag off: responses
carry none of the new fields, and the defaults are the earlier ones. No served probability changes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _clear_dashboard_caches

client = TestClient(app)
PREVIEW_KEYS = {"isPreview", "belowAccuracyTarget", "previewNote", "defaultQuarter"}
LEAD1, LEAD2 = "2026-Q4", "2027-Q1"


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    monkeypatch.delenv("AIPHEED_LEAD2_PREVIEW", raising=False)
    monkeypatch.delenv("AIPHEED_MAX_LEAD", raising=False)
    _clear_dashboard_caches()
    yield
    _clear_dashboard_caches()


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "1")
    _clear_dashboard_caches()


@pytest.fixture
def preview_off(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "0")
    _clear_dashboard_caches()


def _keys(o) -> set:
    if isinstance(o, dict):
        return set(o) | set().union(*(_keys(v) for v in o.values())) if o else set()
    if isinstance(o, list):
        return set().union(*(_keys(v) for v in o)) if o else set()
    return set()


URLS = ["/api/v1/quarters", "/api/v1/config", "/api/v1/provinces", "/api/v1/ranking",
        "/api/v1/forecast?scope=region&id=calabarzon", "/api/v1/forecast?scope=province&id=quezon",
        "/api/v1/explainability?scope=province&id=quezon", "/api/v1/provinces/quezon/municipalities",
        "/api/v1/report/data?type=trend&scope=region&from=2025-Q1"]


@pytest.mark.parametrize("lead", ["1", "2"])
def test_flag_off_has_no_preview_fields_and_todays_defaults(preview_off, monkeypatch, lead):
    monkeypatch.setenv("AIPHEED_MAX_LEAD", lead)
    _clear_dashboard_caches()
    for u in URLS:
        body = client.get(u).json()
        assert not (_keys(body) & PREVIEW_KEYS), u
    q = client.get("/api/v1/quarters").json()
    assert q["current"] == LEAD1
    assert q["forecastTarget"]["target_quarter"] == (LEAD2 if lead == "2" else LEAD1)    # today's behaviour
    ids = [x["id"] for x in q["quarters"]]
    assert (LEAD2 in ids) == (lead == "2")


def test_the_flag_is_on_by_default_and_0_turns_it_off(monkeypatch):
    from app.quarterly.target import lead2_preview

    assert lead2_preview() is True                                    # unset (the _now fixture removes it)
    for v, on in (("1", True), ("0", False), (" 0 ", False), ("yes", True)):
        monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", v)
        assert lead2_preview() is on, v


@pytest.mark.parametrize("flag", ["unset", "1"])
def test_flag_on_opens_on_lead2_and_every_other_default_is_lead1(monkeypatch, flag):
    if flag == "1":
        monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "1")
        _clear_dashboard_caches()
    q = client.get("/api/v1/quarters").json()
    assert q["current"] == LEAD1 and q["defaultQuarter"] == LEAD2 and q["forecastTarget"]["target_quarter"] == LEAD1
    ids = [x["id"] for x in q["quarters"]]
    assert LEAD1 in ids and ids[-1] == LEAD2                                    # 2026-Q4 stays on the timeline
    marks = {x["id"]: x.get("isPreview") for x in q["quarters"]}
    assert marks[LEAD2] is True and marks[LEAD1] is False and all(v is False for k, v in marks.items() if k != LEAD2)
    cfg = client.get("/api/v1/config").json()["quarterRange"]
    assert cfg["defaultQuarter"] == LEAD2 and cfg["forecastTarget"]["target_quarter"] == LEAD1
    for u in URLS[2:8]:
        body = client.get(u).json()
        assert body["quarter"] == LEAD1 and body.get("isPreview") is False, u
    rep = client.get("/api/v1/report/data?type=trend&scope=region&from=2025-Q1").json()
    assert dict(rep["metadata"])["Data"].startswith("2026 Q4") and rep["isPreview"] is False      # the PDF default


def test_flag_on_lead2_reachable_and_labelled(serve_e49, preview):          # the E49 record's E38 lead-2 row
    rec = json.loads(Path("data/e49/e49_record.json").read_text(encoding="utf-8"))
    rows = {r["key"]: r for r in rec["validation"]["next_quarter_evaluation"]["rows"]}
    acc, pers = rows["E38-LGBM"]["accuracy"], rows["B1_PERSISTENCE"]["accuracy"]
    note = (f"Experimental two-quarter-ahead preview. Development accuracy {acc:.3f}, below the 75% target and below "
            f"persistence ({pers:.3f}); not a validated forecast.")
    assert note == ("Experimental two-quarter-ahead preview. Development accuracy 0.709, below the 75% target and "
                    "below persistence (0.800); not a validated forecast.")
    q = next(x for x in client.get("/api/v1/quarters").json()["quarters"] if x["id"] == LEAD2)
    assert q["previewNote"] == note and q["belowAccuracyTarget"] is True
    f = client.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={LEAD2}").json()
    assert f["quarter"] == LEAD2 and f["isPreview"] is True and f["belowAccuracyTarget"] is True and f["previewNote"] == note
    assert "experimental preview" in f["horizonLabel"] and "below the 75% accuracy target" in f["horizonLabel"]
    assert f["confidenceStatement"].endswith(note) and "aiPHeed-E38-LGBM-NQ" in f["confidenceStatement"]
    for u in (f"/api/v1/provinces?quarter={LEAD2}", f"/api/v1/ranking?quarter={LEAD2}",
              f"/api/v1/forecast?scope=region&id=calabarzon&quarter={LEAD2}",
              f"/api/v1/explainability?scope=province&id=quezon&quarter={LEAD2}",
              f"/api/v1/provinces/quezon/municipalities?quarter={LEAD2}"):
        body = client.get(u).json()
        assert body["isPreview"] is True and body["previewNote"] == note, u
    rep = client.get(f"/api/v1/report/data?type=trend&scope=region&from=2025-Q1&to={LEAD2}").json()
    assert rep["isPreview"] is True and dict(rep["metadata"])["Data"].startswith("2027 Q1 lead-2 preview")


def test_flag_on_e53_note_uses_its_own_numbers(preview, serve_e53):
    f = client.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={LEAD2}").json()
    assert f["previewNote"] == ("Experimental two-quarter-ahead preview. Development accuracy 0.673, below the 75% "
                                "target and below persistence (0.800); not a validated forecast.")


@pytest.mark.parametrize("flag", ["unset", "1"])
def test_flag_on_lead2_raises_no_alert(monkeypatch, flag):
    if flag == "1":
        monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "1")
        _clear_dashboard_caches()
    from app.ml.inference import e31_engine as E31
    from app.quarterly import alerts_e31 as A

    assert {c["quarter"] for c in A.candidates(E31.record(), "all")} <= {LEAD1}
    assert {c["quarter"] for c in A.candidates(E31.record())} <= {LEAD1}


def test_probabilities_identical_flag_on_or_off(monkeypatch):
    def scores(q):
        return {p["id"]: p["riskScore"] for p in client.get(f"/api/v1/provinces?quarter={q}").json()["data"]}

    monkeypatch.setenv("AIPHEED_MAX_LEAD", "2")
    _clear_dashboard_caches()
    before = {q: scores(q) for q in (LEAD1, LEAD2, "2026-Q3")}
    monkeypatch.delenv("AIPHEED_MAX_LEAD")
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "1")
    _clear_dashboard_caches()
    assert {q: scores(q) for q in (LEAD1, LEAD2, "2026-Q3")} == before
