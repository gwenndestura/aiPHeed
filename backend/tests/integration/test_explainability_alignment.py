"""Explainability alignment (E57 alignment audit, Phase B): B1 all five drivers are listed (a 0% one had no measurable
effect; B1's earlier omission was undone in the merge preview), B2 the note states
this forecast's own split between the regional hunger survey inputs, news, and the five drivers, B3 the regional
driver panel is on the regional index's (probability) scale. Expected values are recomputed here from the record."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e31_engine as E31
from app.services import dashboard as svc

client = TestClient(app)
REC = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
GROUPS = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
QUARTERS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"]
sig = lambda z: 1 / (1 + math.exp(-z))


@pytest.fixture
def lead2_e53(serve_e53, lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    yield


def _row(q):
    return next(x for x in REC["quarters"] if x["quarter"] == q and x["lead"] == (2 if q == "2027-Q1" else 1))


def _expected(code, q):
    """Independent recomputation: the five drivers' magnitudes (news inputs split by title topic) and signs, the
    hunger-survey part and the news part, all |SHAP| in log-odds; plus the probability-scale factor."""
    row = _row(q)
    v = row["provinces"][code]
    shap = {d["key"]: d["contribution"] for d in v["drivers"]}
    ev_q = row["provenance"]["news_evidence_window"]["evidence_quarter"]
    groups = E31.trigger_group_features()
    signed = {g: sum(shap.get(f, 0.0) for f in fs) for g, fs in groups.items()}
    mag = {g: abs(s) for g, s in signed.items()}
    news_left = 0.0
    for level, feats in E31.NEWS_FEATURES.items():
        sh, _ = E31.news_topic_shares(code if level == "province" else None, ev_q)
        a = sum(abs(shap.get(f, 0.0)) for f in feats)
        s = sum(shap.get(f, 0.0) for f in feats)
        for g, w in sh.items():
            mag[g] += w * a
            signed[g] += w * s
        news_left += a * (1 - sum(sh.values()))
    survey = sum(abs(shap.get(f, 0.0)) for f in ("H_last", "H_gap", "H_trend", "H_margin", "y_last"))
    news = news_left + abs(shap.get("fssi_v2", 0.0)) + abs(shap.get("fssi_missing", 0.0))
    base = v["shap_expected_value_logodds"]
    z = base + sum(shap.values())
    scale = (sig(z) - sig(base)) / (z - base)
    return mag, signed, survey, news, scale


@pytest.mark.parametrize("q", QUARTERS)
def test_b1_all_five_drivers_are_listed(lead2_e53, q):
    for scope, ident in [("province", s) for s in SLUG.values()] + [("region", "calabarzon")]:
        ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()
        tr = ex["triggers"]
        assert {t["key"] for t in tr} == {"market", "climate", "fish_kill", "employment", "ofw_remittance"}, (q, ident)
        assert sum(t["pct"] for t in tr) == 100, (q, ident)
        full = (svc.explainability_region(q) if scope == "region"
                else svc.explainability(next(c for c, s in SLUG.items() if s == ident), q))["triggers"]
        # the response is exactly the service's five drivers, shares unchanged
        assert len(full) == 5
        assert {t["key"]: t["pct"] for t in tr} == {t["key"]: t["pct"] for t in full}, (q, ident)


def test_b1_the_audits_zero_drivers_are_listed_at_0(lead2_e53):
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    assert {t["key"]: t["pct"] for t in ex["triggers"]}["climate"] == 0        # the audit's 0% driver, listed at 0
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q2").json()
    assert {t["key"]: t["pct"] for t in ex["triggers"]}["ofw_remittance"] == 0


@pytest.mark.parametrize("q", QUARTERS)
def test_b2_note_states_this_forecasts_split(lead2_e53, q):
    for code, slug in SLUG.items():
        mag, _, survey, news, _ = _expected(code, q)
        want = svc._integer_shares([survey, news, sum(mag.values())])
        note = client.get(f"/api/v1/explainability?scope=province&id={slug}&quarter={q}").json()["note"]
        head = (f"Regional hunger survey (SWS) inputs and the latest published label: {want[0]}% of this forecast; "
                + (f"news tone and news that matches no driver: {want[1]}%; " if want[1] else "")
                + f"the five drivers below explain the remaining {want[2]}%.")
        assert note.startswith(head), (q, slug, note[:240])
        assert "not shown in the five groups" not in note                       # replaced by the split
        assert "A driver shown at 0 percent had no measurable effect on this forecast." in note
        note.encode("ascii")
        for term in ("`", "direction", "color", "otherPct", "SHAP", "--"):
            assert term not in note, term


def test_b2_quezon_q3_2026_numbers(lead2_e53):
    note = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q3").json()["note"]
    assert note.startswith("Regional hunger survey (SWS) inputs and the latest published label: 26% of this "
                           "forecast; news tone and news that matches no driver: 25%; the five drivers below explain "
                           "the remaining 49%.")


@pytest.mark.parametrize("q", QUARTERS)
def test_b3_region_panel_is_on_the_index_scale(lead2_e53, q):
    exp = {code: _expected(code, q) for code in SLUG}
    pooled = {g: sum(abs(math.copysign(e[0][g], e[1][g])) * e[4] for e in exp.values()) for g in GROUPS}
    signed = {g: sum(math.copysign(e[0][g], e[1][g]) * e[4] for e in exp.values()) for g in GROUPS}
    pct = dict(zip(GROUPS, svc._integer_shares([pooled[g] for g in GROUPS])))
    ex = client.get(f"/api/v1/explainability?scope=region&id=calabarzon&quarter={q}").json()
    for t in ex["triggers"]:
        g = t["key"]
        assert t["pct"] == pct[g], (q, g)
        assert t["direction"] == ("increases_risk" if signed[g] >= 0 else "protective"), (q, g)
        assert t["signedContribution"] == pytest.approx(signed[g] / 5, abs=1e-4), (q, g)
    survey = sum(e[2] * e[4] for e in exp.values())
    news = sum(e[3] * e[4] for e in exp.values())
    want = svc._integer_shares([survey, news, sum(pooled.values())])
    assert ex["note"].startswith(f"Regional hunger survey (SWS) inputs and the latest published label: {want[0]}%")
    assert "regional index averages the five probabilities" in ex["note"]


@pytest.mark.parametrize("q", QUARTERS)
def test_b3_scaled_contributions_add_up_to_each_probability(lead2_e53, q):
    """On the probability scale each province's contributions add up to its raw probability minus the base, so the
    region's add up to the mean raw probability minus the mean base (the index, before the linear calibration)."""
    row = _row(q)
    for code, v in row["provinces"].items():
        base = v["shap_expected_value_logodds"]
        total = sum(d["contribution"] for d in v["drivers"])
        scale = svc._prob_scale(code, q)
        assert total * scale == pytest.approx(sig(base + total) - sig(base), abs=1e-9)


def test_b3_market_direction_follows_the_index_in_q4_2026(lead2_e53):
    """Four provinces near p = 1 carry large positive Market log-odds that barely move their probabilities, while
    Market pulls Batangas (raw p 0.09) down: on the index's scale Market lowers the region (audit item 3)."""
    ex = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4").json()
    by = {t["key"]: t for t in ex["triggers"]}
    assert by["market"]["direction"] == "protective" and by["employment"]["direction"] == "increases_risk"
    prov = {s: client.get(f"/api/v1/explainability?scope=province&id={s}&quarter=2026-Q4").json() for s in SLUG.values()}
    ups = [s for s, e in prov.items() if {t["key"]: t for t in e["triggers"]}["market"]["direction"] == "increases_risk"]
    assert sorted(ups) == ["cavite", "laguna", "quezon", "rizal"]               # province panels are unchanged
