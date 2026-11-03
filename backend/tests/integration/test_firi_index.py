"""
tests/integration/test_firi_index.py
------------------------------------
Option B: the overall food-insecurity index (FIRI v2, GET /api/v1/index) is served beside the Chapter I HIGH-risk
probability (GET /api/v1/forecast, P0H4), never in its place. The index comes only from the authoritative FIRI
functions, is never called a probability, carries its own five-driver composition (exact Shapley values whose
shares plus otherPct close at 100), keeps direction apart from size and missing data apart from a measured zero,
and leaves the P0H4 forecast, its fields and its seal untouched.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import e41_lead2 as E41L2
from app.ml.inference import thesis_system as THESIS

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
SEAL = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_OPTIMIZATION" / "out" / "sealed_prospective_P0H4.csv"
HISTORY = ROOT / "backend" / "data" / "thesis" / "firi2_history.csv"
SLUGS = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
         "batangas": "PH040500000"}
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
QUARTERS = ("2024-Q2", "2025-Q2", "2026-Q2", "2026-Q4", "2027-Q1")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")           # these tests cover the Chapter I map mode (opt-in)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _scopes():
    return [("region", "calabarzon")] + [("province", s) for s in SLUGS]


# 1. the index equals the authoritative calculation and, for earlier quarters, the frozen history
@pytest.mark.parametrize("quarter", QUARTERS)
def test_index_equals_the_authoritative_firi(thesis, quarter):
    rec = E41L2.record()
    vals = {}
    for slug, code in SLUGS.items():
        d = _get("/api/v1/index", scope="province", id=slug, quarter=quarter)
        res = THESIS.firi_for(rec, quarter, code)
        assert d["index"] == pytest.approx(res["firi"], abs=1e-6)
        vals[slug] = res["firi"]
    reg = _get("/api/v1/index", scope="region", id="calabarzon", quarter=quarter)
    assert reg["index"] == pytest.approx(sum(vals.values()) / 5, abs=1e-6)
    assert reg["provincesIncluded"] == 5


def test_history_quarters_match_the_frozen_history_file(thesis):
    with open(HISTORY, newline="", encoding="utf-8") as f:
        hist = {(r["target"], r["province_code"]): float(r["FIRI"]) for r in csv.DictReader(f) if r["FIRI"]}
    n = 0
    for q in ("2024-Q2", "2025-Q2", "2026-Q2", "2026-Q4"):
        for slug, code in SLUGS.items():
            if (q, code) in hist:
                d = _get("/api/v1/index", scope="province", id=slug, quarter=q)
                assert d["index"] == pytest.approx(hist[(q, code)], abs=1e-5)
                n += 1
    assert n >= 15


def test_unavailable_index_is_404_not_a_low_value(thesis):
    # one province without an index: the region is a 404 with its own message, never a partial mean or a filled value
    real = THESIS.firi_for
    thesis.setattr(THESIS, "firi_for", lambda rec, q, code: None if code == "PH040300000" else real(rec, q, code))
    for scope, ident in (("region", "calabarzon"), ("province", "quezon")):
        r = client.get("/api/v1/index", params=dict(scope=scope, id=ident, quarter="2026-Q4"))
        assert r.status_code == 404 and "missing data, not a low index" in r.json()["error"]["message"]
    assert _get("/api/v1/index", scope="province", id="cavite", quarter="2026-Q4")["index"] > 0
    r = client.get("/api/v1/index", params=dict(scope="region", id="calabarzon", quarter="2021-Q1"))
    assert r.status_code == 404                                      # outside every served quarter


# 2, 3. the P0H4 forecast, its fields and its seal are unchanged
@pytest.mark.parametrize("quarter", ("2026-Q2", "2026-Q4", "2027-Q1"))
def test_p0h4_forecast_is_unchanged_and_backward_compatible(thesis, quarter):
    for slug, code in SLUGS.items():
        f = _get("/api/v1/forecast", scope="province", id=slug, quarter=quarter, horizon="forecast")
        r = CH1.row(code, quarter)
        assert f["riskScore"] == pytest.approx(float(r["probability"]), abs=1e-6)
        assert f["riskLevel"] in (("high", "severe") if float(r["probability"]) >= 0.5 else ("low",))
        assert {"riskScore", "riskLevel", "indicator", "quarter"} <= set(f)
        assert "index" not in f                                      # the forecast response gains no index field
    e = _get("/api/v1/explainability", scope="region", id="calabarzon", quarter=quarter)
    assert {"riskScore", "triggers", "otherPct", "narrative", "note"} <= set(e)


def test_p0h4_seal_is_unchanged(thesis):
    want = (SEAL.parent / "sealed_prospective_P0H4.csv.sha256").read_text().strip()
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == want == CH1.evaluation()["seal_sha256"]


# 4, 5. names: the index is never a probability, the probability is never the composite index
def test_the_two_scores_are_named_for_what_they_are(thesis):
    d = _get("/api/v1/index", scope="region", id="calabarzon", quarter="2027-Q1")
    assert "not a probability" in d["definition"] and "index" in d["definition"].lower()
    assert not any("probability" in k.lower() for k in d)
    f = _get("/api/v1/forecast", scope="region", id="calabarzon", quarter="2027-Q1", horizon="forecast")
    name = f["indicator"]["name"].lower()
    assert "probability" in name and "index" not in name


# 6. each card's bars come from its own scoring system
@pytest.mark.parametrize("quarter", ("2026-Q4", "2027-Q1"))
def test_index_bars_are_the_index_shapley_values_not_the_forecast_shap(thesis, quarter):
    rec = E41L2.record()
    for slug, code in SLUGS.items():
        d = {x["key"]: x for x in _get("/api/v1/index", scope="province", id=slug, quarter=quarter)["drivers"]}
        sv = THESIS.shap_values(THESIS.firi_for(rec, quarter, code))
        for g, ks in THESIS.FIVE_GROUPS.items():
            assert d[g]["signedContribution"] == pytest.approx(sum(sv.get(k, 0.0) for k in ks), abs=1e-6)
        r = CH1.row(code, quarter)                                    # not the forecast's tree SHAP
        assert d["market"]["signedContribution"] != pytest.approx(sum(float(r[f"shap_{f}"]) for f in ("A1", "A2", "A3")))


def test_index_shapley_values_sum_to_the_index_minus_its_neutral_point(thesis):
    rec = E41L2.record()
    for q in QUARTERS:
        for code in SLUGS.values():
            res = THESIS.firi_for(rec, q, code)
            assert sum(THESIS.shap_values(res).values()) == pytest.approx(res["firi"] - 0.5, abs=1e-5)


# 7, 8, 9, 11. shares among the five drivers only, sum of absolute indicator values, direction apart, exact labels
@pytest.mark.parametrize("quarter", QUARTERS)
def test_shares_direction_and_labels(thesis, quarter):
    rec = E41L2.record()
    for scope, ident in _scopes():
        d = _get("/api/v1/index", scope=scope, id=ident, quarter=quarter)
        assert len(d["drivers"]) == 5 and {x["key"]: x["label"] for x in d["drivers"]} == LABELS
        # the observed drivers close at 100 (largest remainder); an unavailable one has no share, never 0%
        assert sum(x["pct"] for x in d["drivers"] if x["pct"] is not None) == 100
        for x in d["drivers"]:
            assert (x["pct"] is None) == (x["status"] in ("insufficient_data", "not_in_index"))
            assert x["pct"] is None or 0 <= x["pct"] <= 100
            s = x["signedContribution"]
            assert x["direction"] == ("raises_index" if s > 0 else "lowers_index" if s < 0 else "none")
        sv_all = [THESIS.shap_values(THESIS.firi_for(rec, quarter, c))
                  for c in ([SLUGS[ident]] if scope == "province" else SLUGS.values())]
        mags = {g: sum(abs(sv.get(k, 0.0)) for sv in sv_all for k in ks) for g, ks in THESIS.FIVE_GROUPS.items()}
        by = {x["key"]: x for x in d["drivers"]}
        for g, m in mags.items():                                    # pooled over provinces at region scope
            if by[g]["pct"] is None:                                  # unavailable: no input, so no size either
                assert m == 0
            else:
                assert by[g]["pct"] == pytest.approx(100 * m / sum(mags.values()), abs=1)
        other = sum(abs(v) for sv in sv_all for k, v in sv.items() if k in THESIS.OTHER_INDICATORS)
        assert d["otherPct"] == round(100 * other / (sum(mags.values()) + other))      # separate, not in the 100


# synthetic Shapley values with known answers (independent of the historical data)
def _res(observed):
    return {"indicators": {k: {"score": (0.5 if k in observed else None)}
                           for k in ("A1", "A2", "A3", "C1", "C2", "C3", "C4", "E1", "E2", "V1", "H1", "N1")}}


def _comp(per):
    from app.services import dashboard as D
    return D.firi_composition(per, THESIS.FIVE_GROUPS, THESIS.GROUP_LABELS)


def test_synthetic_cancellation_keeps_size_and_takes_direction_from_the_net():
    # Market: -0.03, +0.02, +0.01 (net 0.00, size 0.06); Climate: +0.04, -0.01 (net +0.03, size 0.05);
    # Fish Kill -0.02; Employment +0.07; OFW missing; other inputs 0.50 (must not enter the five shares)
    sv = {"A1": -0.03, "A2": 0.02, "A3": 0.01, "C1": 0.04, "C3": -0.01, "C4": -0.02, "E1": 0.07,
          "V1": 0.2, "H1": 0.3}
    drivers, other = _comp([(_res(set(sv)), sv)])
    by = {d["key"]: d for d in drivers}
    # magnitudes 0.06, 0.05, 0.02, 0.07, 0 -> total 0.20 -> 30, 25, 10, 35, 0
    assert {g: by[g]["pct"] for g in by} == {"market": 30, "climate": 25, "fish_kill": 10, "employment": 35,
                                            "ofw_remittance": None}
    assert sum(d["pct"] for d in drivers if d["pct"] is not None) == 100
    assert by["market"]["direction"] == "none" and by["market"]["status"] == "contributes"   # cancels, still sized
    assert by["climate"]["direction"] == "raises_index" and by["fish_kill"]["direction"] == "lowers_index"
    assert by["ofw_remittance"]["status"] == "insufficient_data" and by["ofw_remittance"]["direction"] == "none"
    assert other == round(100 * 0.5 / 0.7)                          # 71: separate transparency figure


def test_synthetic_observed_zero_is_no_effect_and_all_zero_has_no_shares():
    sv = {"A1": 0.0, "C1": 0.05, "C4": 0.0, "E1": 0.05, "E2": 0.0}
    by = {d["key"]: d for d in _comp([(_res(set(sv)), sv)])[0]}
    assert by["fish_kill"]["status"] == "no_effect" and by["fish_kill"]["pct"] == 0          # measured zero
    zero = {"A1": 0.0, "C1": 0.0, "C4": 0.0, "E1": 0.0, "E2": 0.0, "V1": 0.1}
    drivers, other = _comp([(_res(set(zero)), zero)])
    assert all(d["pct"] is None and d["share"] is None for d in drivers)     # no share defined, never a false 0%
    assert all(d["status"] == "no_effect" for d in drivers) and other == 100


def test_synthetic_invalid_values_give_no_composition():
    sv = {"A1": float("nan"), "C1": 0.05}
    assert _comp([(_res(set(sv)), sv)]) is None
    sv = {"A1": float("inf"), "C1": 0.05}
    assert _comp([(_res(set(sv)), sv)]) is None


def test_synthetic_region_pools_magnitudes_and_averages_the_net():
    p1 = {"A1": 0.04, "E1": 0.01}                                    # market +0.04
    p2 = {"A1": -0.02, "E1": 0.03}                                   # market -0.02
    by = {d["key"]: d for d in _comp([(_res(set(p1)), p1), (_res(set(p2)), p2)])[0]}
    # pooled sizes: market 0.06, employment 0.04 -> 60 / 40; market net mean +0.01 raises
    assert by["market"]["pct"] == 60 and by["employment"]["pct"] == 40
    assert by["market"]["signedContribution"] == pytest.approx(0.01) and by["market"]["direction"] == "raises_index"


# 10. missing data is not a measured zero
def test_missing_inputs_are_never_zero_and_published_data_are_not_called_missing(thesis):
    """An input absent from the index is insufficient_data when no audited value was published at the issue date,
    and not_in_index when the audited series (used by the provincial forecast) has one: the index predates the
    FIRI_V2_DATA_AUDIT corrections. Neither is a 0% contribution."""
    from app.services import dashboard as D
    rec = E41L2.record()
    seen = set()
    for q in QUARTERS:
        for slug, code in SLUGS.items():
            res = THESIS.firi_for(rec, q, code)
            published = D.audited_published(code, res["issueDate"])
            d = {x["key"]: x for x in _get("/api/v1/index", scope="province", id=slug, quarter=q)["drivers"]}
            for g, ks in THESIS.FIVE_GROUPS.items():
                if any(res["indicators"][k]["score"] is not None for k in ks):
                    assert d[g]["status"] in ("contributes", "no_effect")
                    continue
                want = "not_in_index" if g in published else "insufficient_data"
                assert d[g]["status"] == want and d[g]["direction"] == "none"
                seen.add(want)
    assert "not_in_index" in seen                                    # remittances: BSP published, index not rebuilt


def test_cavite_2027_q1_remittances_are_published_but_not_in_the_index(thesis):
    rows = [r for (c, _), r in CH1.rows().items() if c == "PH040100000" and r["issue_date"] == "2026-10-01"]
    assert rows and rows[0]["val_E2"] not in ("", None)               # the audited BSP value the forecast uses
    d = {x["key"]: x for x in _get("/api/v1/index", scope="province", id="cavite", quarter="2027-Q1")["drivers"]}
    assert d["ofw_remittance"]["status"] == "not_in_index" and "not been recomputed" in d["ofw_remittance"]["statusNote"]
    v = _get("/api/v1/index", scope="province", id="cavite", quarter="2027-Q1")["validation"]
    assert "not been recomputed with the audited" in v


def test_synthetic_published_but_absent_is_not_in_index():
    sv = {"A1": 0.01, "C1": 0.02, "C4": -0.01, "E1": 0.03}
    res = _res(set(sv))
    from app.services import dashboard as D
    by = {d["key"]: d for d in D.firi_composition([(res, sv)], THESIS.FIVE_GROUPS, THESIS.GROUP_LABELS,
                                                   [{"ofw_remittance"}])[0]}
    assert by["ofw_remittance"]["status"] == "not_in_index" and by["ofw_remittance"]["pct"] is None
    by = {d["key"]: d for d in D.firi_composition([(res, sv)], THESIS.FIVE_GROUPS, THESIS.GROUP_LABELS, [set()])[0]}
    assert by["ofw_remittance"]["status"] == "insufficient_data"
