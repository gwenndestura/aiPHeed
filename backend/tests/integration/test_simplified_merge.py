"""
tests/integration/test_simplified_merge.py
------------------------------------------
The four changes taken from e46-lead2-policy / the merge preview (branch simplified-merge): all five drivers again, tied
ranks with rankTied (E39, A. Melindo), article counts from the evidence quarter (D2), and trigger status / statusNote
(E42, A. Melindo). On tina-e53-port the candidate-only evidenceNote exists and is null for the served model. Final integration: an estimate whose five
shares are all 0 lists no drivers (as 262e81e did), and the note says the bars explain the estimate before
calibration and, for the region, how a factor's bar and colour pool the five provinces.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc

client = TestClient(app)
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")


# ---------------------------------------------------------------- tied ranks
def test_equal_scores_share_a_rank():
    data = client.get("/api/v1/provinces?quarter=2023-Q1").json()["data"]
    assert {p["riskScore"] for p in data} == {0.4}                       # five equal scores in 2023-Q1
    assert all(p["rank"] == 1 and p["rankTied"] is True for p in data)


@pytest.mark.parametrize("q", svc.available_quarters())
def test_rank_is_competition_ranking_on_the_unchanged_scores(q):
    data = client.get(f"/api/v1/provinces?quarter={q}").json()["data"]
    pub = [p for p in data if p["riskScore"] is not None]
    for p in pub:
        assert p["rank"] == 1 + sum(1 for o in pub if o["riskScore"] > p["riskScore"])
        assert p["rankTied"] is (sum(1 for o in pub if o["riskScore"] == p["riskScore"]) > 1)
        assert p["riskScore"] == next(x for x in svc.province_summary(q) if x["id"] == p["id"])["riskScore"]
    ranking = {r["id"]: r["rank"] for r in client.get(f"/api/v1/ranking?quarter={q}").json()["data"]}
    assert ranking == {p["id"]: p["rank"] for p in pub}


# ---------------------------------------------------------------- trigger status
@pytest.mark.parametrize("scope,ident", [("province", "quezon"), ("province", "batangas"), ("region", "calabarzon")])
@pytest.mark.parametrize("q", ["2026-Q2", "2026-Q3", "2026-Q4"])
def test_every_trigger_states_its_status(scope, ident, q):
    tr = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()["triggers"]
    assert {t["key"] for t in tr} == FIVE and sum(t["pct"] for t in tr) == 100
    for t in tr:
        assert t["status"] == ("contributes" if t["pct"] > 0 else "no_effect"), t   # the served model has all five
        assert t["statusNote"] == svc.TRIGGER_STATUS_NOTES[t["status"]]
        assert t.get("evidenceNote") is None                              # candidate-only field: null when served


def test_a_zero_driver_is_marked_no_effect():
    tr = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q3").json()["triggers"]
    zero = [t for t in tr if t["pct"] == 0]
    assert zero and all(t["status"] == "no_effect" for t in zero)


# ---------------------------------------------------------------- article counts (D2)
def test_region_limited_count_follows_the_province_counts():
    for q in ("2026-Q3", "2026-Q4"):
        prov = client.get(f"/api/v1/provinces?quarter={q}").json()["data"]
        region = client.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}").json()
        assert region["provinceCounts"]["limited"] == sum(1 for p in prov if p["articleCount"] < 5)
        assert all(p["limitedSignal"] is (p["articleCount"] < 5) for p in prov)


# ---------------------------------------------------------------- PDFs: a 0% driver
def test_backend_pdf_labels_a_zero_driver_no_measurable_effect():
    from app.services import report as rpt

    explain = {"triggers": [
        {"key": "market", "label": "Market / Prices", "pct": 100, "direction": "increases_risk"},
        {"key": "employment", "label": "Employment", "pct": 0, "direction": "increases_risk"}]}
    flow = rpt._drivers_block(explain, "Quezon", "2026-Q4", 400)

    def texts(obj):                                  # every Paragraph text inside the flowables (tables nested)
        if isinstance(obj, (list, tuple)):
            for x in obj:
                yield from texts(x)
        elif hasattr(obj, "_cellvalues"):
            yield from texts(obj._cellvalues)
        elif hasattr(obj, "text"):
            yield str(obj.text)
        elif isinstance(obj, str):
            yield obj

    labels = [" ".join(t.split()) for t in texts(flow)]           # the Paragraph collapses whitespace
    assert "0% no measurable effect" in labels and "100% raises" in labels, labels
    assert not any(t in ("0% raises", "0% lowers") for t in labels)


def test_visualization_pdf_names_every_driver_and_never_draws_a_zero_bar():
    d = client.get("/api/v1/report/data?type=trend&scope=region&from=2025-Q1&to=2026-Q3").json()
    bars = [b for b in d["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "bars"][0]["chart"]["bars"]
    assert bars and all(b["pct"] > 0 for b in bars)
    table = [b for b in d["blocks"] if b["kind"] == "table" and "Share of Each Factor" in b["title"]][0]
    assert len(table["columns"]) == 6                                     # Province + all five factors
    assert not any(c.startswith("0% ") for r in table["rows"] for c in r)  # 0% reads "No noticeable effect"


# ---------------------------------------------------------------- all five shares 0: no drivers listed
@pytest.mark.parametrize("scope,ident", [("province", "quezon"), ("province", "cavite"), ("region", "calabarzon")])
def test_all_zero_shares_list_no_drivers(scope, ident):
    code = None if scope == "region" else svc.ref.province_code(ident)
    full = (svc.explainability_region("2023-Q1") if code is None else svc.explainability(code, "2023-Q1"))["triggers"]
    assert len(full) == 5 and all(t["pct"] == 0 for t in full)              # the constant 2023-Q1 model
    ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter=2023-Q1").json()
    assert ex["triggers"] == []
    nz = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter=2026-Q3").json()["triggers"]
    assert {t["key"] for t in nz} == FIVE                                  # otherwise all five


# ---------------------------------------------------------------- the note: calibration and the region pooling
CALIBRATION = ("The bars explain the model's estimate before calibration. Calibration pulls every estimate toward the "
               "long-run rate, so it lowers or raises the index but does not change the shares.")
REGION_NET = ("For CALABARZON, a factor can raise the risk in some provinces and lower it in others; its bar shows the "
              "total size of its effect and its colour shows the net direction across the five provinces.")


def _note(scope, ident, q="2026-Q3"):
    return client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()["note"]


@pytest.mark.parametrize("record", ["default_e53", "serve_e49"])
def test_calibrated_records_say_the_bars_are_before_calibration(record, request):
    if record != "default_e53":
        request.getfixturevalue(record)
    for scope, ident in (("province", "quezon"), ("region", "calabarzon")):
        note = _note(scope, ident)
        assert note.count(CALIBRATION) == 1, (record, scope)
        assert note.index("and shrinkage calibration. " + CALIBRATION) > 0  # right after the model sentence
        assert (REGION_NET in note) is (scope == "region"), (record, scope)
        note.encode("ascii")


def test_region_note_order():
    note = _note("region", "calabarzon")
    assert note.index("For CALABARZON, each province's contributions") < note.index(REGION_NET) \
        < note.index("The bars show how much")


def test_uncalibrated_e36_has_no_calibration_sentence(serve_e36):
    assert CALIBRATION not in _note("province", "quezon", "2026-Q4")
    assert REGION_NET in _note("region", "calabarzon", "2026-Q4")
