"""
tests/integration/test_e61_forecast_context.py
----------------------------------------------
E61 (experiments/E61_E58_Low_Forecast_Investigation): the dashboard's reading of a two-part Lead-2 forecast (E55/E56/E58
records). Checks that
  * the served probabilities, issue date and target quarter are unchanged (the summary only explains them);
  * the summary states both parts, their values equal the record's components, and the product equals the forecast;
  * the caveat's figures are the record's own observations (food inflation, province threshold, headline = food -
    gap, regional hunger and its quarter), so nothing is invented, and it never says food became affordable;
  * the back-test figure quoted for low price-part probabilities equals E61's audit output;
  * the employment note appears only when the model lowered the estimate while unemployment rose;
  * records without the two parts (E52/E53 price-only targets, backtest quarters) keep their previous wording;
  * the cached Lead-2 record is re-read when its file changes (cache freshness).
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.services import dashboard as svc

client = TestClient(app)
E61 = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E61_E58_Low_Forecast_Investigation"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}


@pytest.fixture
def e58(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")


def _summary(scope, ident, quarter="2027-Q1"):
    return client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={quarter}").json()["summary"]


def test_forecast_values_and_timing_unchanged(e58):
    rec = LEAD2.record()
    assert (rec["targetQuarter"], rec["origin"]) == ("2027-Q1", "2026-10-01")
    rows = {r["id"]: r["riskScore"] for r in client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()["data"]}
    for code, v in rec["provinces"].items():
        s = _summary("province", SLUG[code])
        assert s["probability"] == pytest.approx(v["forecast"]["probability"], abs=1e-4)
        assert rows[SLUG[code]] == pytest.approx(v["forecast"]["probability"], abs=1e-4)
        assert s["issued"] == rec["origin"] and s["targetQuarter"] == "2027-Q1" and s["estimateKind"] == "forecast"


def test_summary_states_both_parts_from_the_record(e58):
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        s = _summary("province", SLUG[code])
        c = v["forecast"]["components"]
        assert s["components"]["probabilityHungerElevated"] == pytest.approx(c["probabilityHungerElevated"], abs=1e-4)
        assert s["components"]["probabilityPricePressure"] == pytest.approx(c["probabilityPricePressure"], abs=1e-4)
        assert c["probabilityHungerElevated"] * c["probabilityPricePressure"] == pytest.approx(v["forecast"]["probability"], abs=1e-3)
        assert f"({c['probabilityHungerElevated']:.0%})" in s["sentence"]
        assert f"({c['probabilityPricePressure']:.0%})" in s["sentence"] and "the target needs both" in s["sentence"]
        assert "not independent" in s["components"]["combination"]
        assert f"(model score {v['forecast']['probability']:.0%}:" in s["sentence"] and "not a tested probability" in s["sentence"]
        assert "% probability)" not in s["sentence"] and "HIGH-risk probability" not in s["sentence"]
        assert s["sentence"].isascii() and s["caveat"].isascii()
        # shown through the existing summary text (no new UI element): the sentence ends with the explanation
        assert s["sentence"].endswith(s["caveat"])
        ex = client.get(f"/api/v1/explainability?scope=province&id={SLUG[code]}&quarter=2027-Q1").json()
        assert ex["narrative"].startswith(s["sentence"])


def test_caveat_figures_are_the_records_observations(e58):
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        cav = _summary("province", SLUG[code])["caveat"]
        ob = v["observed"]
        f, g, h = ob["foodInflationLatestMonths"], ob["foodMinusHeadline"], ob["hungerRegional"]
        assert f"{f['value']:.1f}% higher than a year earlier" in cav
        assert f"more than {f['provinceReferenceP60']:.2f}%" in cav
        headline = f["value"] - g["value"]
        if headline > f["value"]:
            assert f"Prices overall rose faster ({headline:.1f}%)" in cav
        assert f"{h['value']:.1f}% in {h['quarter']}" in cav
        assert "does not mean food has become affordable" in cav and "not a measure of household food insecurity" in cav
        partial = LEAD2.partial_inputs("2027-Q1", code)                # e.g. BSP remittances end 2025-Q4
        assert ("how it handles a missing figure, not an observed value" in cav) == bool(partial)
        for g in partial:
            assert svc.LABEL_OF[g] in cav
        assert "affordable again" not in cav and "food is affordable" not in cav


def test_backtest_figure_matches_e61_audit():
    path = E61 / "out" / "a2_calibration_joint.json"
    if not path.exists():
        pytest.skip("E61 audit output not present")
    low = json.loads(path.read_text(encoding="utf-8"))["low_probability_cutoffs"]["E56_p_price<0.2"]
    assert (low["n"], low["observed_HIGH"]) == (svc.E61_LOW_PRICE_BACKTEST["n"], svc.E61_LOW_PRICE_BACKTEST["high"])


def test_employment_note_only_when_direction_conflicts(e58):
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        s = _summary("province", SLUG[code])
        # E62: every Employment bar drawn as lowering the score counts, not only the named reasons (Rizal, Batangas)
        ex = client.get(f"/api/v1/explainability?scope=province&id={SLUG[code]}&quarter=2027-Q1").json()
        lowered = any(t["key"] == "employment" and t["direction"] == "protective" and t["pct"] > 0
                      and t["status"] == "contributes" for t in ex["triggers"])
        rising = (v["observed"]["employment"].get("unemploymentChangeYoY") or 0) > 0
        assert ("not evidence that job losses reduce food stress" in s["caveat"]) == (lowered and rising)


def test_region_and_unaffected_cases(e58, monkeypatch):
    r = _summary("region", "calabarzon")
    assert "across the five provinces" in r["sentence"] and r["components"] and r["caveat"]
    past = _summary("province", "laguna", "2026-Q3")             # backtest quarter: wording unchanged, no parts
    assert past["estimateKind"] == "backtest" and "mainly because" in past["sentence"]
    assert past.get("components") is None and past.get("caveat") is None
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e53")             # price-only target: no hunger part is invented
    s = _summary("province", "quezon")
    assert s["sentence"].startswith("Food-price pressure in Quezon for 2027-Q1 is forecast LOW")
    assert s.get("components") is None and "hunger is" not in s["sentence"]


def test_record_cache_rereads_a_changed_file(monkeypatch, tmp_path):
    src = Path("data/e58/e58_record.json")
    dst = tmp_path / "rec.json"
    shutil.copyfile(src, dst)
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    monkeypatch.setattr(LEAD2, "RECORD_E58", dst)
    first = LEAD2.record()
    assert LEAD2.record() is first                                # cached: same object, no re-read
    body = json.loads(dst.read_text(encoding="utf-8"))
    body["generated_at"] = "changed-for-test"                     # content no longer matches its hash
    dst.write_text(json.dumps(body), encoding="utf-8")
    os.utime(dst, ns=(dst.stat().st_atime_ns, dst.stat().st_mtime_ns + 10_000_000))
    with pytest.raises(LEAD2.RecordError):                        # re-read and re-checked, not served from cache
        LEAD2.record()


@pytest.mark.parametrize("mode", ["e43", "e44", "e46", "e52", "e53"])
def test_older_records_keep_their_wording(monkeypatch, mode):
    """E43-E53 records store other components (or a price-only target): no two-part sentence, no caveat."""
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", mode)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    try:
        LEAD2.record()
    except LEAD2.RecordError:
        pytest.skip(f"no {mode} record")
    s = _summary("province", "quezon")
    if s is None:
        pytest.skip(f"{mode} does not govern 2027-Q1")
    assert s.get("components") is None and s.get("caveat") is None
    assert "the target needs both" not in s["sentence"] and "Within the price part" not in s["sentence"]
