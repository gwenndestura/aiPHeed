"""
The plain-language PDF payload (app/services/plain_report.py) against the
real model: no technical vocabulary, APA-shaped tables and figures, the
single-quarter case, and withheld results never surfacing.
"""

import json

import pytest

from app.services import dashboard as svc
from app.services import plain_report as pr
from tests.unit.test_plain_text import BANNED, TYPOGRAPHIC


def visible_text(body: dict) -> str:
    """Everything the PDF prints (the payload's `type` field is not printed)."""
    parts = [body["title"], body["subtitle"]] + [v for row in body["metadata"] for v in row]
    for b in body["blocks"]:
        for key in ("text", "label", "title", "note"):
            if b.get(key):
                parts.append(b[key])
        parts += b.get("items", [])
        parts += [c["label"] for c in b.get("columns", [])]
        parts += [cell for r in b.get("rows", []) for cell in r]
        chart = b.get("chart") or {}
        parts += [s["name"] for s in chart.get("series", [])]
        parts += [bar["label"] for bar in chart.get("bars", [])]
        parts += [ln["label"] for ln in chart.get("lines", [])]
    return "\n".join(parts)


def assert_plain(body: dict) -> None:
    text = visible_text(body)
    assert text.isascii()
    for ch in TYPOGRAPHIC:
        assert ch not in text
    for word in BANNED:
        assert word.lower() not in text.lower(), word


def assert_apa(body: dict) -> None:
    tables = [b for b in body["blocks"] if b["kind"] == "table"]
    figures = [b for b in body["blocks"] if b["kind"] == "figure"]
    assert [t["label"] for t in tables] == [f"Table {i}" for i in range(1, len(tables) + 1)]
    assert [f["label"] for f in figures] == [f"Figure {i}" for i in range(1, len(figures) + 1)]
    body_text = " ".join(b["text"] for b in body["blocks"] if b["kind"] == "paragraph")
    for b in tables + figures:
        assert not b["title"].endswith(".")
        assert b["label"] in body_text, f"{b['label']} is never referred to in the text"
        # Referred to before it appears.
        idx = body["blocks"].index(b)
        before = " ".join(x.get("text", "") for x in body["blocks"][:idx])
        assert b["label"] in before


@pytest.fixture(scope="module")
def last():
    return svc.available_quarters()[-1]


def test_single_quarter_region_has_no_trend_section(last):
    body = pr.build_plain_report("trend", "region", None, last, last, set())
    headings = [b["text"] for b in body["blocks"] if b["kind"] == "heading"]
    assert "How Risk Changed" not in headings
    assert headings == ["Key Points", "Risk at a Glance", "What Is Driving the Risk",
                        "Province Profile", "News Reports", "Important Notes"]
    text = visible_text(body)
    q = last.replace("-", " ")
    assert f"{q} to {q}" not in text
    assert "+0.000" not in text and "+0.00" not in text
    assert not any(b["kind"] == "figure" and b["chart"]["type"] == "line" for b in body["blocks"])
    assert_plain(body)
    assert_apa(body)


def test_two_quarter_province_trend(last):
    prev = svc._previous_quarter(last)
    body = pr.build_plain_report("trend", "province", "cavite", prev, last, set())
    assert any(b["kind"] == "figure" and b["chart"]["type"] == "line" for b in body["blocks"])
    assert_plain(body)
    assert_apa(body)


def test_factors_report_for_one_province(last):
    body = pr.build_plain_report("shap", "province", "quezon", last, last, set())
    assert body["subtitle"] == "Factors Behind the Risk"
    assert_plain(body)
    assert_apa(body)


def test_withheld_results_never_appear(last):
    held = next(p["riskScore"] for p in svc.province_summary(last) if p["id"] == "batangas")
    body = pr.build_plain_report("trend", "region", None, last, last, {("batangas", last)})
    text = json.dumps(body)
    assert str(held) not in text
    glance = next(b for b in body["blocks"] if b["kind"] == "table")
    batangas = next(r for r in glance["rows"] if r[0] == "Batangas")
    assert batangas[1:3] == ["Withheld", "Withheld"]
    assert "withheld by the reviewing team" in visible_text(body)
    assert_plain(body)
