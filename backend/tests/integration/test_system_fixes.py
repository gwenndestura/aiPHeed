"""
tests/integration/test_system_fixes.py
--------------------------------------
SYSTEM_FIXES (FINAL_SYSTEM_SELECTION plan items 1-6, approved 2026-10-27): with the Chapter I forecast (P0H4) served in
thesis mode, every surface describes THAT forecast, never FIRI v2 or another model.

  1. the downloadable reports (/report/data and the /report PDF) name the probability, the model and its evidence;
  2. an LGU's risk level is its province's class (the index only orders LGUs inside the province);
  3. the news beside a forecast follows P0H4's timing and is labelled as classifier-v2 output;
  4. the quarter list, timeseries and verification date follow P0H4's own rows;
  5. the Employment and News bars state what they are, from the forecast's own input values;
  6. served rows carry the model name, the seal of sealed rows and the input values at the issue date.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)
PROVINCES = ("batangas", "cavite", "laguna", "quezon", "rizal")
SEAL = (Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "LEAD2_OPTIMIZATION" / "out"
        / "sealed_prospective_P0H4.csv")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _ch1_quarters():
    return sorted({q for _, q in CH1.rows() if q <= "2027-Q1"})


def _issue(quarter):
    return next(r["issue_date"] for (_, q), r in CH1.rows().items() if q == quarter)


# ---------------------------------------------------------------------------------------------- item 1: reports
def test_report_series_equals_the_served_forecast_and_never_describes_firi(thesis):
    pl = _get("/api/v1/report/data", type="trend", scope="province", id="quezon", **{"from": "2023-Q1", "to": "2026-Q4"})
    fig = next(b for b in pl["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "line")
    served = {p["quarter"]: p["riskScore"] for p in _get("/api/v1/forecast/timeseries", scope="province",
                                                         id="quezon")["series"]}
    quarters = [q.replace(" ", "-") for q in fig["chart"]["quarters"]]
    values = fig["chart"]["series"][0]["values"]
    assert None not in values                               # 2025-Q2/Q3 were blank with the FIRI quarter list
    assert all(abs(v - served[q]) < 1e-6 for q, v in zip(quarters, values))
    text = json.dumps(pl)
    assert "FIRI" not in text and "not a probability" not in text and "exact share" not in text
    meta = dict(pl["metadata"])
    assert meta["Model"] == CH1.model_line() and "Lead-1 forecast issued 2026-10-01" in meta["Data"]
    assert any("Reliability rule" in i for b in pl["blocks"] if b["kind"] == "bullets" for i in b["items"])


def test_report_marks_lead2_as_experimental(thesis):
    pl = _get("/api/v1/report/data", type="trend", scope="region", **{"from": "2026-Q3", "to": "2027-Q1"})
    kp = next(b for b in pl["blocks"] if b["kind"] == "bullets")["items"]
    assert any("Lead-2 forecast issued 2026-10-01 (experimental" in i for i in kp)


def test_server_pdf_describes_the_served_forecast(thesis):
    from pdfminer.high_level import extract_text

    for path, params in (("/api/v1/report", {"scope": "province", "id": "quezon", "quarter": "2026-Q4"}),
                         ("/api/v1/report", {"scope": "region", "id": "calabarzon", "quarter": "2027-Q1"})):
        r = client.get(path, params=params)
        if r.status_code in (401, 403):
            pytest.skip("report PDF is guarded in this configuration")
        assert r.status_code == 200, r.text[:300]
        text = " ".join(extract_text(io.BytesIO(r.content)).split())
        assert "FIRI" not in text and "not a probability" not in text and "exact shares" not in text
        assert "FORECAST PROBABILITY OF HIGH FOOD-INSECURITY RISK" in text and "Reliability rule" in text


def test_summary_is_the_served_forecast(thesis):
    for scope, slug, code in (("province", "quezon", "PH040300000"), ("region", "calabarzon", None)):
        s = _get("/api/v1/explainability", scope=scope, id=slug, quarter="2026-Q4")["summary"]
        rs = [r for (c, q), r in CH1.rows().items() if q == "2026-Q4" and (code is None or c == code)]
        p = sum(float(r["probability"]) for r in rs) / len(rs)
        assert abs(s["probability"] - p) < 1e-3 and s["result"] == ("HIGH" if p >= 0.5 else "LOW")
        assert "FIRI" not in json.dumps(s)
        assert s["modelIdentity"]["servedModel"] == "P0H4" and s["modelIdentity"]["issued"] == "2026-10-01"
        assert s.get("earlyWarning") is None and s.get("climateWatch") is None


# ---------------------------------------------------------------------------------------------- item 2: LGU band
@pytest.mark.parametrize("quarter", ["2024-Q2", "2025-Q2", "2026-Q4", "2027-Q1"])
def test_lgu_level_is_the_province_class(thesis, quarter):
    level = {p["id"]: p["riskLevel"] for p in _get("/api/v1/provinces", quarter=quarter)["data"]}
    n = 0
    for slug in PROVINCES:
        ms = _get(f"/api/v1/provinces/{slug}/municipalities", quarter=quarter)["data"]
        n += len(ms)
        assert {m["riskLevel"] for m in ms} == {level[slug]}
        assert sorted(m["rankInProvince"] for m in ms) == list(range(1, len(ms) + 1))
        idx = [m["riskIndex"] for m in sorted(ms, key=lambda m: m["rankInProvince"])]
        assert idx == sorted(idx, reverse=True)              # the index still orders the LGUs
        assert all(m["riskLevelBasis"] == CH1.LGU_LEVEL_BASIS for m in ms)
        assert all(m["provinceEstimateSource"]["mode"].startswith("P0H4_LEAD") for m in ms)
    assert n == 142


# ---------------------------------------------------------------------------------------------- item 3: news timing
@pytest.mark.parametrize("quarter", ["2024-Q3", "2025-Q2", "2026-Q4", "2027-Q1"])
def test_news_follows_the_forecast_timing(thesis, quarter):
    issue = _issue(quarter)
    for slug in ("quezon", "laguna"):
        n = _get("/api/v1/news", scope="province", id=slug, quarter=quarter, pageSize=100)
        assert "R1.1" not in n["feedNote"] and "classifier v2" in n["feedNote"]
        assert "two-quarter-ahead" not in n["evidenceNote"]
        if n["evidenceMode"] == "FORECAST":
            assert issue in n["evidenceNote"]
            assert all(a["date"] < issue for a in n["data"])
        else:
            assert f"was made as of {issue}" in n["evidenceNote"]


# ---------------------------------------------------------------------------------------------- item 4: quarters
def test_quarter_list_and_timeseries_follow_the_served_rows(thesis):
    qs = _get("/api/v1/quarters")["quarters"]
    assert [q["id"] for q in qs] == _ch1_quarters()
    kind = {q: CH1.kind(r) for (_, q), r in CH1.rows().items()}
    assert all(q["state"] == ("forecast" if kind[q["id"]] == "forecast" else "actual") for q in qs)
    cfg = _get("/api/v1/config")["quarterRange"]
    assert cfg["earliest"] == "2023-Q1" and cfg["count"] == len(qs)
    assert cfg["forecastQuarters"] == [q for q in _ch1_quarters() if kind[q] == "forecast"]
    ts = _get("/api/v1/forecast/timeseries", scope="province", id="cavite")["series"]
    assert [p["quarter"] for p in ts] == _ch1_quarters()
    assert all(p["isForecast"] == (kind[p["quarter"]] == "forecast") for p in ts)
    assert client.get("/api/v1/provinces", params={"quarter": "2023-Q1"}).status_code == 200
    assert client.get("/api/v1/provinces", params={"quarter": "2027-Q2"}).status_code == 404   # Lead 3 stays off


@pytest.mark.parametrize("quarter", ["2023-Q2", "2026-Q4", "2027-Q1"])
def test_verification_date_is_the_issue_date(thesis, quarter):
    f = _get("/api/v1/forecast", scope="province", id="quezon", quarter=quarter, horizon="forecast")
    assert f["verificationDate"] == _issue(quarter)


# ---------------------------------------------------------------------------------------------- item 5: bar notes
def test_employment_and_news_bars_state_what_they_are(thesis):
    r = CH1.row("PH040300000", "2026-Q4")
    e = {t["key"]: t for t in _get("/api/v1/explainability", scope="province", id="quezon", quarter="2026-Q4")["triggers"]}
    emp = e["employment"]["plainEvidence"]
    assert "calendar trend" in emp and "Apr-Jun 2026" in emp and f"{abs(float(r['val_E1'])):.1f} points" in emp
    assert "Jan-Mar 2026" not in emp                         # FIRI's 2026-07-01 data window, not this forecast's
    assert "GDELT" in e["news"]["plainEvidence"] and "does not change the forecast" in e["news"]["plainEvidence"]
    assert e["market"]["plainEvidence"] == CH1.market_evidence("PH040300000", "2026-Q4")
    region = {t["key"]: t for t in _get("/api/v1/explainability", scope="region", id="calabarzon",
                                         quarter="2026-Q4")["triggers"]}
    assert region["employment"]["plainEvidence"] == CH1.EMPLOYMENT_CAUTION
    assert region["news"]["plainEvidence"] == CH1.NEWS_BASIS


def test_bar_periods_follow_the_issue_date():
    assert CH1._period("2026-10-01", 1) == "Jul-Sep 2026" and CH1._period("2026-10-01", 2) == "Apr-Jun 2026"
    assert CH1._period("2025-04-01", 2) == "Oct-Dec 2024" and CH1._period("2023-01-01", 1) == "Oct-Dec 2022"


# ---------------------------------------------------------------------------------------------- item 6: archive
def test_rows_carry_model_seal_and_input_values(thesis):
    ev = CH1.evaluation()
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == ev["seal_sha256"]      # the frozen seal is unchanged
    rows = _get("/api/v1/final/risk/rows")["rows"]
    assert len(rows) == 95 and all(r["model"] == "P0H4" for r in rows)
    for r in rows:
        assert r["seal_sha256"] == (ev["seal_sha256"] if r["issue_date"] >= "2026-10-01" else "")
        assert all(f"val_{c}" in r for c in ("A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "G_pri_yoy",
                                             "NG_gap_price", "H1"))
    status, note = CH1.data_status("PH040300000", "2026-Q4")
    assert status == "limited" and "FSSI-v3" in note       # FSSI missing at that issue date is now visible
