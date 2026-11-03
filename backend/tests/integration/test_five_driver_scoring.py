"""
tests/integration/test_five_driver_scoring.py
---------------------------------------------
The five-driver presentation of the served Chapter I forecast (FIXES_EVAL): the bars are the five risk drivers'
SHAP shares of the price LightGBM, the other model inputs are reported as otherPct (never reassigned to a driver),
bars plus other close at exactly 100%, 0% is kept apart from missing data, magnitude is kept apart from direction,
and the index, the province scores, the ranking and the drivers all come from the same forecast record.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.services import dashboard as D

client = TestClient(app)
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SLUGS = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
         "batangas": "PH040500000"}
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


# ---------------------------------------------------------------------------------------------- arithmetic
def test_integer_shares_close_at_100_and_keep_zeros():
    assert sum(D._integer_shares([0.3, 0.3, 0.3])) == 100
    assert D._integer_shares([1.0, 0.0, 0.0, 0.0]) == [100, 0, 0, 0]
    assert D._integer_shares([0.0, 0.0]) == [0, 0]                      # nothing to explain: no invented share
    s = D._integer_shares([0.004, 0.996, 0.0])
    assert sum(s) == 100 and s[2] == 0


def test_driver_groups_sum_signed_shap_and_report_other_separately(monkeypatch):
    """Mixed signs within a group net out; a group with no push is no_effect; poverty, news and the hunger indicator
    go to other_abs as absolute values and are never added to a driver."""
    row = {f"shap_{f}": 0.0 for f in ("A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1")}
    row.update(shap_A1=-0.8, shap_A2=0.3, shap_E1=0.4, shap_V1=-0.2, shap_N1=0.1, shap_H1=0.0)
    monkeypatch.setattr(CH1, "row", lambda code, q: row)
    out = CH1.drivers("PH040100000", "2026-Q4", {"drivers": []})
    by = {d["driver_group"]: d for d in out["drivers"]}
    assert set(by) == FIVE
    assert by["market"]["group_shap"] == pytest.approx(-0.5) and by["market"]["direction"] == "protective"
    assert by["employment"]["direction"] == "increases_risk"
    assert by["climate"]["group_shap"] == 0 and by["climate"]["direction"] == "no_effect"
    assert out["other_abs"] == pytest.approx(0.3)
    assert out["other_pct"] == pytest.approx(100 * 0.3 / (0.5 + 0.4 + 0.3), abs=0.1)


# ---------------------------------------------------------------------------------------------- served API
@pytest.mark.parametrize("quarter", QUARTERS)
def test_five_bars_plus_other_close_at_100_everywhere(thesis, quarter):
    for scope, ident in [("region", "calabarzon")] + [("province", s) for s in SLUGS]:
        d = _get("/api/v1/explainability", scope=scope, id=ident, quarter=quarter)
        assert {t["key"] for t in d["triggers"]} == FIVE
        assert {t["key"]: t["label"] for t in d["triggers"]} == LABELS
        assert all(0 <= t["pct"] <= 100 for t in d["triggers"])
        assert sum(t["pct"] for t in d["triggers"]) + d["otherPct"] == 100
        for t in d["triggers"]:                                     # magnitude and direction are separate fields
            assert t["direction"] in ("increases_risk", "protective", "no_effect")
            if scope == "province" and t["signedContribution"] != 0:
                assert (t["direction"] == "increases_risk") is (t["signedContribution"] > 0)


@pytest.mark.parametrize("quarter", QUARTERS)
def test_zero_is_kept_apart_from_missing_data(thesis, quarter):
    for slug, code in SLUGS.items():
        r = CH1.row(code, quarter)
        for t in _get("/api/v1/explainability", scope="province", id=slug, quarter=quarter)["triggers"]:
            if str(r[f"avail_{t['key']}"]) != "1":
                assert t["status"] == "insufficient_data"            # no published input: never shown as "no effect"
            else:
                assert t["status"] == ("contributes" if t["pct"] > 0 else "no_effect")


@pytest.mark.parametrize("quarter", QUARTERS)
def test_index_scores_ranking_and_drivers_come_from_one_record(thesis, quarter):
    probs = {}
    for slug, code in SLUGS.items():
        r = CH1.row(code, quarter)
        f = _get("/api/v1/forecast", scope="province", id=slug, quarter=quarter, horizon="forecast")
        assert f["riskScore"] == pytest.approx(float(r["probability"]), abs=1e-6)
        probs[slug] = float(r["probability"])
        e = {t["key"]: t for t in _get("/api/v1/explainability", scope="province", id=slug, quarter=quarter)["triggers"]}
        for g, fams in CH1.FIVE_GROUPS.items():                      # the bars explain this same row
            assert e[g]["signedContribution"] == pytest.approx(sum(float(r[f"shap_{x}"]) for x in fams), abs=1e-6)
    reg = _get("/api/v1/forecast", scope="region", id="calabarzon", quarter=quarter, horizon="forecast")
    assert reg["riskScore"] == pytest.approx(sum(probs.values()) / 5, abs=1e-4)   # index = mean of the 5 provinces
    ranked = [p["id"] for p in _get("/api/v1/ranking", quarter=quarter)["data"]] if quarter else []
    if ranked:
        assert ranked == sorted(probs, key=probs.get, reverse=True)[:len(ranked)]
    levels = {p["id"]: p["riskLevel"] for p in _get("/api/v1/provinces", quarter=quarter)["data"]}
    for slug, p in probs.items():                                   # map colour = HIGH at 0.50 on the same number
        assert (levels[slug] in ("high", "severe")) is (p >= 0.5)
