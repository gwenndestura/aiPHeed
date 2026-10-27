"""
tests/integration/test_forecast_research_ii.py
----------------------------------------------
FORECAST_RESEARCH_II candidate Z0-U (served only with AIPHEED_CH1_ENGINE=fr2): the P0H4-U rows and issue schedule with
the price part replaced by the structural CPI projection that the frozen DEV rule selected. The default (P0H4) and the
fr candidate (P0H4-U) are unchanged.
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
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
II_OUT = EXP / "FORECAST_RESEARCH_II" / "out"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not (CH1.DATA_FR2 / "rows.csv").exists(), reason="FORECAST_RESEARCH_II export missing")


def _clear_caches():
    from app.services import dashboard
    for mod in (dashboard, CH1):
        for v in vars(mod).values():
            if callable(getattr(v, "cache_clear", None)):
                v.cache_clear()


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")

    def use(name: str | None):
        if name is None:
            monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
        else:
            monkeypatch.setenv("AIPHEED_CH1_ENGINE", name)
        _clear_caches()
    yield use
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    _clear_caches()


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_default_and_fr_engines_are_unchanged(engine):
    engine(None)
    assert CH1.data_dir() == CH1.DATA and CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    assert not CH1.structural() and {r["model"] for r in CH1.rows().values()} == {"P0H4"}
    assert CH1.indicator() is CH1.INDICATOR and CH1.text("REPORT_COVER") == CH1.REPORT_COVER
    engine("fr")
    assert CH1.data_dir() == CH1.DATA_FR and not CH1.structural()
    assert CH1.model_line().startswith("P0H4-U")


def test_fr2_changes_only_the_price_part(engine):
    engine("fr")
    fr = dict(CH1.rows())
    engine("fr2")
    assert CH1.data_dir() == CH1.DATA_FR2 and CH1.structural()
    z = {}
    with open(EXP / "FORECAST_RESEARCH" / "out" / "price_arms_all_origins.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["arm"] == "Z0":
                z[(int(r["t"]), int(r["lead"]), r["province_code"])] = float(r["pi_P"])
    cand = CH1.rows()
    assert cand.keys() == fr.keys()
    for k, c in cand.items():
        s = fr[k]
        for f in ("pi_hunger", "issue_date", "lead", "sws_newest_q", "h_last", "observed", "val_A3", "val_E1", "A1_food"):
            assert s[f] == c[f], (k, f)
        q = c["quarter"]
        t = int(q[:4]) * 4 + int(q[-1]) - 1 - int(c["lead"])
        assert abs(float(c["pi_price"]) - z[(t, int(c["lead"]), c["province_code"])]) < 1e-5, k
        p = float(c["pi_hunger"]) * float(c["pi_price"])
        assert abs(p - float(c["probability"])) < 1e-5 and c["class"] == ("HIGH" if p >= 0.5 else "LOW")
        assert c["model"] == "Z0-U"
        assert all(float(c[f"shap_{f}"]) == 0 for f in ("A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"))


def test_fr2_seal_matches_its_file_and_other_seals_are_untouched(engine):
    engine("fr2")
    ev = CH1.evaluation()
    doc = json.loads((II_OUT / "PROSPECTIVE_SEAL.json").read_text())
    seal = doc["FINAL"]["sha256"]
    assert hashlib.sha256((II_OUT / doc["FINAL"]["file"]).read_bytes()).hexdigest() == seal
    assert hashlib.sha256((II_OUT / doc["exploratory"]["file"]).read_bytes()).hexdigest() == doc["exploratory"]["sha256"]
    assert ev["seal_sha256"] == seal and doc["served_seal_unchanged"] == SERVED_SEAL
    assert {r["seal_sha256"] for r in CH1.rows().values() if r["issue_date"] >= "2026-10-01"} == {seal}
    assert doc["p0h4u_seal_unchanged"].startswith("bd6572e1")


def test_fr2_verdict_matches_the_study(engine):
    engine("fr2")
    ev = CH1.evaluation()
    res = json.loads((II_OUT / "results_ii.json").read_text())
    assert res["selection"]["chosen_FINAL"] == "Z0" and ev["price_part"]["kind"] == "structural"
    assert ev["max_reliable_lead"] == res["arms"]["Z0"]["max_reliable_lead"] == 1
    assert ev["sws_update"]["lead2"]["reliable"] is False and ev["leads"]["2"]["failed"] == ["R5"]
    assert ev["leads"]["1"]["reliable"] is True
    assert abs(ev["leads"]["1"]["metrics"]["accuracy"] - res["arms"]["Z0"]["leads"]["1"]["metrics"]["accuracy"]) < 1e-12


def test_fr2_api_serves_the_rows(engine):
    engine("fr2")
    cand = CH1.rows()
    for q in ("2026-Q4", "2027-Q1"):
        data = {p["id"]: p for p in _get("/api/v1/provinces", quarter=q)["data"]}
        rows = {r["province"].lower(): r for (_, qq), r in cand.items() if qq == q}
        assert set(rows) <= set(data)
        for slug, r in rows.items():
            assert data[slug]["riskLevel"] == r["class"].lower(), (q, slug)
            assert abs(data[slug]["riskScore"] - float(r["probability"])) < 1e-5, (q, slug)


def test_fr2_text_names_the_structural_price_part(engine):
    engine("fr2")
    assert CH1.model_line().startswith("Z0-U") and "no learned model" in CH1.model_line()
    assert "LightGBM" not in CH1.indicator()["definition"] and "no learned model" in CH1.indicator()["definition"]
    assert "LightGBM" not in CH1.text("REPORT_COVER")
    assert "Market / Prices" in CH1.evidence_note("PH040300000", "2026-Q4")
    assert any("FORECAST_RESEARCH_II protocol" in s for s in CH1.reliability_sentences())
    d = CH1.drivers("PH040300000", "2026-Q4", {"drivers": []})
    pushes = {x["driver_group"]: x["group_shap"] for x in d["drivers"]}
    assert pushes["market"] != 0 and all(v == 0 for g, v in pushes.items() if g != "market") and d["other_pct"] == 0
