"""
The Visualization PDF payload (app/services/report_data.py) against the real
model: every string is ASCII, and a withheld province-quarter never surfaces.
"""

import json

from app.services import dashboard as svc
from app.services import report_data as rd


def _nowcast_quarters() -> list[str]:
    # Reports cover nowcast quarters only; the appended E20 quarter is excluded.
    return [q for q in svc.available_quarters() if not svc.is_forecast_quarter(q)]


def _score(slug: str, quarter: str) -> float:
    return next(p["riskScore"] for p in svc.province_summary(quarter) if p["id"] == slug)


def test_trend_payload_is_ascii_and_structured():
    quarters = _nowcast_quarters()
    body = rd.build_report("trend", "region", None, quarters[-3], quarters[-1], set())
    text = json.dumps(body)
    assert text.isascii()
    kinds = {b["kind"] for b in body["blocks"]}
    assert {"heading", "bullets", "figure", "table", "paragraph"} <= kinds
    figure = next(b for b in body["blocks"] if b["kind"] == "figure")
    assert figure["chart"]["type"] == "line"
    assert len(figure["chart"]["series"]) == 5


def test_withheld_province_quarter_never_appears():
    quarters = _nowcast_quarters()
    last = quarters[-1]
    held = _score("batangas", last)
    body = rd.build_report("trend", "region", None, quarters[-3], last, {("batangas", last)})
    text = json.dumps(body)
    assert str(held) not in text
    assert f"{held:.3f}" not in text
    assert "Batangas is withheld from publication" in text
    region = next(b for b in body["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "bars")
    assert "pooled across 4 published provinces" in region["caption"]


def test_shap_payload_for_withheld_province_reports_nothing():
    last = _nowcast_quarters()[-1]
    body = rd.build_report("shap", "province", "rizal", last, last, {("rizal", last)})
    text = json.dumps(body)
    assert "withheld from publication" in text
    assert not any(b["kind"] == "figure" for b in body["blocks"])
