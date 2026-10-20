"""The Visualization PDF (frontend/src/lib/chartReport.ts renderReportPdf, fed by GET /api/v1/report/data) and the
backend PDFs: every field the frontend reads is present and filled, every served quarter is covered, the notes follow
the served rows, and no section is empty."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc
from app.services import reference as ref

client = TestClient(app)


@pytest.fixture
def lead2_e53(serve_e53, lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    yield


@pytest.fixture
def now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    yield


def _blocks(d, kind):
    return [b for b in d["blocks"] if b["kind"] == kind]


def _check_contract(d):
    """The keys and non-null values chartReport.ts reads (ReportPayload, ReportBlock, LineChart, BarChart)."""
    for k in ("type", "title", "subtitle", "generatedDate", "metadata", "blocks"):
        assert d.get(k) not in (None, ""), k
    assert all(len(m) == 2 and m[0] and m[1] for m in d["metadata"])
    for b in d["blocks"]:
        assert b["kind"] in ("heading", "paragraph", "bullets", "table", "figure")
        if b["kind"] in ("heading", "paragraph"):
            assert b["text"]
        if b["kind"] == "table":
            assert b["label"] and b["title"] and b["rows"]
            assert all(set(c) == {"label", "align", "width"} and c["align"] in ("left", "right", "center")
                       for c in b["columns"])
            # widths are FRACTIONS of the text width (chartReport multiplies by contentW)
            assert all(0 < c["width"] < 1 for c in b["columns"]) and sum(c["width"] for c in b["columns"]) <= 1.0001
            assert all(len(r) == len(b["columns"]) and all(isinstance(x, str) and x for x in r) for r in b["rows"])
        if b["kind"] == "figure":
            assert b["label"] and b["title"] and b["note"]
            ch = b["chart"]
            if ch["type"] == "line":
                for k in ("quarters", "series", "yMin", "yMax", "yStep", "lines"):
                    assert ch[k] is not None, k
                assert all(len(s["values"]) == len(ch["quarters"]) and s["name"] for s in ch["series"])
            else:
                assert ch["bars"] and all(b2["label"] and b2["pct"] > 0 for b2 in ch["bars"])
                assert all(b2["direction"] in ("increases_risk", "protective") for b2 in ch["bars"])


TREND_SECTIONS = ["Key Points", "Risk at a Glance", "How Risk Changed", "What Is Driving the Risk",
                  "Province Profile", "News Reports", "Important Notes"]
DRIVER_SECTIONS = [h for h in TREND_SECTIONS if h != "How Risk Changed"]
GLANCE_COLUMNS = ["Province", "Risk score", "Risk level", "Main factor"]


def _get(**params):
    r = client.get("/api/v1/report/data", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _trend(**params):
    return _get(**{"type": "trend", "scope": "region", **params})


def _check_layout(d, sections):
    """The mock report: title, metadata, the sections in order, each non-empty, plain ASCII, every width a fraction."""
    _check_contract(d)
    assert d["title"] == "aiPHeed Food Insecurity Forecast Report"
    keys = [m[0] for m in d["metadata"]]
    # E53 port: the served model and its accuracy follow (and, for a period ending on the lead-2 preview, its model)
    assert keys[:6] == ["Area", "Period", "Date prepared", "Prepared for", "Data", "Model"] and len(keys) <= 7
    model = dict(d["metadata"])["Model"]
    assert "0.785 (51/65, 95% interval 0.646 to 0.908)" in model and "not demonstrated" in model or "E53" not in model
    assert dict(d["metadata"])["Prepared for"] == "DA Region IV-A"
    heads = [i for i, b in enumerate(d["blocks"]) if b["kind"] == "heading"]
    assert [d["blocks"][i]["text"] for i in heads] == sections
    assert all(b - a > 1 for a, b in zip(heads, heads[1:] + [len(d["blocks"])]))          # no empty section
    assert d["blocks"][0]["kind"] == "paragraph" and "not a measure of how many families lack food" in d["blocks"][0]["text"]
    for b in _blocks(d, "table"):
        assert abs(sum(c["width"] for c in b["columns"]) - 1) < 1e-3
    text = repr(d)
    assert text.isascii() and "global median" not in text
    assert "riskScore" not in text and "trig_" not in text                                 # no field names


def _glance(d):
    t = _blocks(d, "table")[0]
    labels = [c["label"] for c in t["columns"]]
    assert labels[:3] == GLANCE_COLUMNS[:3] and labels[3].startswith("Change from ") and labels[4] == "Main factor"
    return t


def _numbers_match_api(d, quarter):
    """Table 1 and the profile table carry the same numbers as the dashboard's provinces and explainability."""
    prov = {p["name"]: p for p in svc.province_summary(quarter)}
    for r in _glance(d)["rows"]:
        if r[0] in prov:
            p = prov[r[0]]
            assert r[1] == f"{p['riskScore']:.2f}"
            top = svc.nonzero_triggers(svc.explainability(ref.province_code(p["id"]), quarter)["triggers"])[0]
            assert r[4].endswith(f"({top['pct']}%)")
    prof = next(b for b in _blocks(d, "table") if "Population" in b["title"])
    assert [c["label"] for c in prof["columns"]] == ["Province", "Population", "Poverty incidence"]
    for r in prof["rows"]:
        assert r[1] == f"{prov[r[0]]['population']:,}" and r[2] == f"{prov[r[0]]['povertyRate']:.1f}%"
    for f in _blocks(d, "figure"):
        if f["chart"]["type"] == "bars":                         # 0% drivers are never drawn
            assert all(b["pct"] > 0 for b in f["chart"]["bars"])


def test_trend_region_layout_and_every_served_quarter_e49(now):
    d = _trend(**{"from": "2021-Q1"})
    _check_layout(d, TREND_SECTIONS)
    assert dict(d["metadata"])["Data"] == "2026 Q4 forecast, lead 1, issued 2026-10-01"
    fig = _blocks(d, "figure")[0]
    qs = fig["chart"]["quarters"]
    assert qs[0] == "2023 Q1" and qs[-1] == "2026 Q4" and len(qs) == 16          # 2025 Q2/Q3 stay on the axis
    assert all(s["values"][qs.index("2025 Q2")] is None for s in fig["chart"]["series"])
    assert "No estimate for 2025 Q2 and 2025 Q3" in fig["note"] and "2026 Q4 is a forecast, lead 1" in fig["note"]
    ch = fig["chart"]
    assert 0 <= ch["yMin"] < ch["yMax"] <= 1 and round(ch["yMin"] * 20, 6) % 1 == 0 and round(ch["yMax"] * 20, 6) % 1 == 0
    g = _glance(d)
    assert [r[0] for r in g["rows"]][-1] == "CALABARZON (mean)" and len(g["rows"]) == 6
    _numbers_match_api(d, "2026-Q4")
    notes = _blocks(d, "bullets")[-1]["items"]
    assert any("one quarter ahead are the reliable horizon" in n for n in notes)
    assert any("not an official food insecurity classification" in n for n in notes)


def test_trend_e53_lead2_includes_the_preview(lead2_e53):
    d = _trend(**{"from": "2021-Q1"})
    _check_layout(d, TREND_SECTIONS)
    fig = _blocks(d, "figure")[0]
    assert fig["chart"]["quarters"][-2:] == ["2026 Q4", "2027 Q1"]
    assert "2027 Q1 is a lead-2 preview, issued 2026-10-01" in fig["note"]
    notes = " ".join(_blocks(d, "bullets")[-1]["items"])
    assert "correct 67% of the time" in notes and "experimental preview" in notes
    news = " ".join(b["text"] for b in d["blocks"] if b["kind"] == "paragraph")
    assert "the quarter has not started yet" in news and "built from the news of 2026 Q3" in news
    _numbers_match_api(d, "2027-Q1")


def test_province_trend_and_driver_layouts(lead2_e53):
    d = _trend(scope="province", id="quezon", **{"from": "2023-Q1"})
    _check_layout(d, TREND_SECTIONS)
    assert d["subtitle"] == "Province Risk Level Trend" and dict(d["metadata"])["Area"] == "Quezon"
    assert [r[0] for r in _glance(d)["rows"]] == ["Quezon"]
    s = _get(type="shap", scope="province", id="quezon", to="2026-Q4")
    _check_layout(s, DRIVER_SECTIONS)
    assert s["subtitle"] == "What Is Driving the Risk" and dict(s["metadata"])["Period"] == "2026 Q4"
    _numbers_match_api(s, "2026-Q4")
    bars = [f for f in _blocks(s, "figure") if f["chart"]["type"] == "bars"][0]["chart"]["bars"]
    shown = svc.nonzero_triggers(svc.explainability(ref.province_code("quezon"), "2026-Q4")["triggers"])
    assert [(b["pct"], b["direction"]) for b in bars] == [(t["pct"], t["direction"]) for t in shown]
    drive = next(b["text"] for b in s["blocks"] if b["kind"] == "paragraph" and b["text"].startswith("As shown in Figure"))
    assert f"about {bars[0]['pct']}%" in drive and "regional hunger survey" in drive


def test_a_range_ending_before_the_forecasts(lead2_e53):
    d = _trend(**{"from": "2021-Q1", "to": "2026-Q3"})
    _check_layout(d, TREND_SECTIONS)
    assert _blocks(d, "figure")[0]["chart"]["quarters"][-1] == "2026 Q3"
    assert dict(d["metadata"])["Data"] == "2026 Q3 backtest, lead 1"


def test_one_main_factor_with_two_directions_is_not_called_different():
    from app.services import plain_text as pt

    rows = [{"name": n, "value": 0.8, "withheld": False, "start": None, "mainKey": "market", "mainPct": 70,
             "mainDirection": d} for n, d in (("A", "increases_risk"), ("B", "protective"))]
    kp = " ".join(pt.compose_key_points(rows, "2026-Q4", None, 0.5, 0.6))
    assert "differs" not in kp and "raise it in A and lower it in B" in kp


def test_explainability_region_accepts_withheld(now):
    q = "2026-Q3"
    full = svc.explainability_region(q)
    held = svc.explainability_region(q, frozenset({"batangas"}))
    assert full["triggers"] and held["triggers"] and full["articleCount"] >= 0
    assert held["triggers"] != full["triggers"]                      # Batangas left out of the pooling


def test_legacy_report_builders_call_the_new_signature():
    """report_data.py and plain_report.py passed a second argument that did not exist (TypeError if reached)."""
    import inspect

    sig = inspect.signature(svc.explainability_region)
    assert list(sig.parameters) == ["quarter", "withheld"] and sig.parameters["withheld"].default == frozenset()


def _render(url):
    r = client.get(url)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    return r.content


@pytest.mark.parametrize("record", ["e49", "e53"])
def test_backend_pdfs_have_no_empty_sections(record, request, now):
    from app.services import report as rpt

    if record == "e53":
        request.getfixturevalue("serve_e53")
    perf = svc.model_performance()
    assert perf["maxReliableLeadTime"] == 1 and "lead 2" in perf["maxReliableLeadTimeBasis"]
    text = rpt._method_text(perf)
    assert "global median" not in text and "PAGASA" not in text and "inputs are" in text
    assert _render("/api/v1/report?scope=region&id=calabarzon")
    assert _render("/api/v1/report?scope=province&id=quezon")
    # the region table drops the Class column (no record row carries a class label) and the news block has no
    # empty Score column
    src = rpt._news_block({"articleCount": 2, "provinceAttributed": 2, "topics": [], "data": [
        {"date": "2026-09-01", "title": "A", "source": "s", "topicLabel": "t", "relevanceScore": None}]}, 400)
    assert any(getattr(f, "text", "") == "Recent headlines" for f in src)
