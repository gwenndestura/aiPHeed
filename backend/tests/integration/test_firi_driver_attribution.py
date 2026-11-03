"""
Five-driver attribution of the served FIRI v2 index and the reproducibility of its provincial classification.

  * mapping: Market / Prices = A1-A3, Climate Stress = C1-C3, Fish Kill = C4, Employment = E1, OFW Remittance = E2;
    V1, H1 and N1 are in the index but in none of the five drivers;
  * a driver's size is the sum of its indicators' absolute Shapley values, its direction the sign of the net push,
    |net| below THESIS.NET_ZERO is no direction (on /explainability and /index alike);
  * shares are among the five drivers only; a driver with no observed input has no share on /index (never a 0%)
    and is not listed as contributing on /explainability;
  * /explainability and /index give the same shares for every province and the region;
  * the provincial confusion matrix is recomputed from the stored records (firi2_history.csv x rows.csv labels).
"""
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import e41_lead2 as E41L2
from app.ml.inference import thesis_system as THESIS
from app.services import dashboard as D

client = TestClient(app)
DATA = Path(__file__).resolve().parents[2] / "data"
APPROVED = {"market": ("A1", "A2", "A3"), "climate": ("C1", "C2", "C3"), "fish_kill": ("C4",), "employment": ("E1",),
            "ofw_remittance": ("E2",)}
LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
          "employment": "Employment", "ofw_remittance": "OFW Remittance"}
SLUGS = {"cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000", "rizal": "PH040400000",
         "batangas": "PH040500000"}


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _res(scores: dict[str, float | None]) -> dict:
    return {"indicators": {k: {"score": s, "domain": k[0]} for k, s in scores.items()}}


# ------------------------------------------------------------------------------------------------- mapping
def test_driver_mapping_is_the_approved_one():
    assert THESIS.FIVE_GROUPS == APPROVED and CH1.FIVE_GROUPS == APPROVED
    assert THESIS.GROUP_LABELS == LABELS
    in_driver = {k for ks in APPROVED.values() for k in ks}
    assert not in_driver & set(THESIS.OTHER_INDICATORS)
    assert set(THESIS.OTHER_INDICATORS) == {"V1", "H1", "N1"}


# ------------------------------------------------------------------------------------------- composition math
def test_magnitude_is_gross_and_direction_is_net():
    sv = {"A1": 0.04, "A2": -0.03, "C1": 0.01, "C4": -0.02, "E1": 0.05, "E2": 0.0, "V1": 0.5}
    res = _res({"A1": .9, "A2": .1, "A3": None, "C1": 1, "C2": None, "C3": None, "C4": .3, "E1": .9, "E2": .5, "V1": 1})
    drivers, other = D.firi_composition([(res, sv)], APPROVED, LABELS)
    by = {d["key"]: d for d in drivers}
    # gross magnitudes 0.07, 0.01, 0.02, 0.05, 0 -> shares of 0.15
    assert [by[k]["pct"] for k in ("market", "climate", "fish_kill", "employment", "ofw_remittance")] == [47, 7, 13, 33, 0]
    assert sum(d["pct"] for d in drivers) == 100
    assert by["market"]["direction"] == "raises_index" and by["market"]["signedContribution"] == pytest.approx(0.01)
    assert by["fish_kill"]["direction"] == "lowers_index"
    assert by["ofw_remittance"]["status"] == "no_effect"                 # observed at its middle: a measured 0%
    assert other == round(100 * 0.5 / 0.65)                              # separate, not in the five shares


def test_near_zero_net_has_no_direction_but_keeps_its_size():
    sv = {"A1": 0.02, "A2": -0.02 + 1e-17, "E1": 0.02}
    res = _res({"A1": .8, "A2": .2, "E1": .8})
    by = {d["key"]: d for d in D.firi_composition([(res, sv)], APPROVED, LABELS)[0]}
    assert by["market"]["direction"] == "none" and by["market"]["signedContribution"] == 0.0
    assert by["market"]["pct"] == 67 and by["market"]["status"] == "contributes"


def test_unavailable_driver_has_no_share_and_the_rest_add_to_100():
    sv = {"A1": 0.03, "C1": 0.01, "C4": 0.02, "E1": 0.04}
    res = _res({"A1": .9, "C1": 1, "C4": .7, "E1": .9, "E2": None})
    by = {d["key"]: d for d in D.firi_composition([(res, sv)], APPROVED, LABELS)[0]}
    assert by["ofw_remittance"]["pct"] is None and by["ofw_remittance"]["status"] == "insufficient_data"
    assert sum(d["pct"] for d in by.values() if d["pct"] is not None) == 100


def test_all_zero_pushes_give_no_shares():
    sv = {"A1": 0.0, "C1": 0.0, "C4": 0.0, "E1": 0.0, "E2": 0.0}
    res = _res({"A1": .5, "C1": .5, "C4": .5, "E1": .5, "E2": .5})
    drivers, _ = D.firi_composition([(res, sv)], APPROVED, LABELS)
    assert all(d["pct"] is None and d["status"] == "no_effect" and d["direction"] == "none" for d in drivers)


def test_non_finite_attribution_is_refused():
    assert D.firi_composition([(_res({"A1": .9}), {"A1": float("nan")})], APPROVED, LABELS) is None


def test_firi_drivers_near_zero_net_is_no_effect(monkeypatch):
    res = {"firi": 0.6, "indicators": {}, "domains": {}}
    monkeypatch.setattr(THESIS, "firi_for", lambda rec, q, code: res)
    monkeypatch.setattr(THESIS, "shap_values", lambda r: {"A1": 0.02, "A2": -0.02 + 1e-17, "E1": 0.05})
    out = THESIS.firi_drivers({}, "2027-Q1", "PH040100000", {"drivers": []})
    by = {d["driver_group"]: d for d in out["drivers"]}
    assert by["market"]["direction"] == "no_effect" and by["market"]["group_shap"] == 0.0
    assert by["employment"]["direction"] == "increases_risk"


# ------------------------------------------------------------------------------------------ served endpoints
@pytest.mark.parametrize("quarter", ("2026-Q2", "2026-Q4", "2027-Q1"))
def test_explainability_equals_index_for_every_scope(thesis, quarter):
    for scope, id_ in [("region", "calabarzon")] + [("province", s) for s in SLUGS]:
        ex = {t["key"]: t for t in _get("/api/v1/explainability", scope=scope, id=id_, quarter=quarter)["triggers"]}
        idx = {d["key"]: d for d in _get("/api/v1/index", scope=scope, id=id_, quarter=quarter)["drivers"]}
        assert set(ex) == set(idx) == set(APPROVED)
        assert {k: t["label"] for k, t in ex.items()} == LABELS
        assert sum(t["pct"] for t in ex.values()) == 100
        for k, d in idx.items():
            if d["pct"] is None:                     # unavailable on /index: zero size and not contributing on the panel
                assert ex[k]["pct"] == 0 and ex[k]["status"] != "contributes"
            else:
                assert ex[k]["pct"] == d["pct"], (scope, id_, k)
            if d["pct"] and d["direction"] != "none" and ex[k]["status"] == "contributes":
                assert ex[k]["direction"] == ("increases_risk" if d["direction"] == "raises_index" else "protective")


# ------------------------------------------------------------------------------- provincial classification
def _province_rows() -> pd.DataFrame:
    h = pd.read_csv(DATA / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    r = pd.read_csv(DATA / "ch1_engine" / "rows.csv", dtype={"province_code": str})
    r = r[r["observed"].isin(["HIGH", "LOW"])]
    lab = r.groupby(["province_code", "quarter"])["observed"].agg(["first", "nunique"]).reset_index()
    assert (lab["nunique"] == 1).all()                                    # one label per province-quarter
    b = h[(h["kind"] == "backtest") & h["FIRI"].notna()]
    return b.merge(lab.rename(columns={"quarter": "target"}), on=["province_code", "target"])


def test_history_is_lead2_unique_and_thresholded_at_half():
    h = pd.read_csv(DATA / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    qi = lambda q: int(q[:4]) * 4 + int(q[-1])  # noqa: E731
    assert set(h["target"].map(qi) - h["origin_quarter"].map(qi)) == {2}
    assert not h.duplicated(["target", "province_code"]).any()
    v = h[h["FIRI"].notna()]
    assert ((v["FIRI"] >= 0.5).map({True: "HIGH", False: "LOW"}) == v["class"]).all()


def test_provincial_confusion_matrix_is_reproducible_from_records():
    p = _province_rows()
    y, yh = (p["first"] == "HIGH").astype(int), (p["FIRI"] >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    assert tp + fp + fn + tn == len(p) and len(p) == 5 * p["target"].nunique()
    out = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "FIRI_PROVINCIAL_RELIABILITY" \
        / "out" / "firi_provincial_reliability.json"
    if out.exists():                                                      # the report's numbers come from these rows
        rep = json.loads(out.read_text(encoding="utf-8"))["provincialLead2"]
        assert (rep["TP"], rep["FP"], rep["FN"], rep["TN"]) == (tp, fp, fn, tn)


def test_served_province_values_equal_the_history(thesis):
    h = pd.read_csv(DATA / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    for q in ("2024-Q2", "2025-Q3", "2026-Q3", "2026-Q4"):
        for slug, code in SLUGS.items():
            f = _get("/api/v1/forecast", scope="province", id=slug, quarter=q, horizon="forecast")
            assert f["riskScore"] == pytest.approx(float(h[(h.target == q) & (h.province_code == code)]["FIRI"].iloc[0]),
                                                   abs=1e-6)
        reg = _get("/api/v1/forecast", scope="region", id="calabarzon", quarter=q, horizon="forecast")
        assert reg["riskScore"] == pytest.approx(h[h.target == q]["FIRI"].mean(), abs=1e-4)


# ------------------------------------------------------------------------------- served wording (master audit)
def test_bar_note_describes_the_bar_actually_drawn(thesis):
    ex = _get("/api/v1/explainability", scope="province", id="cavite", quarter="2027-Q1")
    for t in ex["triggers"]:
        assert "The bar is this group's SHAP value (its push on the index)" not in (t["evidenceNote"] or "")
    note = next(t for t in ex["triggers"] if t["key"] == "market")["evidenceNote"]
    assert "share of the five drivers' total absolute SHAP" in note and "net push" in note


def test_audited_data_outside_the_index_is_not_called_unpublished(thesis):
    """OFW 2027-Q1: FIRI had no E2 value, but the audited BSP figure was published before the 2026-10-01 issue date
    (FIRI_V2_DATA_AUDIT). The panel says data exist but are not in the index (as /index's not_in_index), shows the
    audited figure as evidence, and never says "no published value"."""
    ex = {t["key"]: t for t in _get("/api/v1/explainability", scope="province", id="cavite", quarter="2027-Q1")["triggers"]}
    idx = {d["key"]: d for d in _get("/api/v1/index", scope="province", id="cavite", quarter="2027-Q1")["drivers"]}
    ofw = ex["ofw_remittance"]
    assert idx["ofw_remittance"]["status"] == "not_in_index" and idx["ofw_remittance"]["pct"] is None
    assert ofw["status"] == "data_not_in_model" and ofw["pct"] == 0 and ofw["statusNote"] == D.TRIGGER_STATUS_NOTES["data_not_in_model"]
    assert "no published value" not in ofw["evidenceNote"]
    r = CH1.row("PH040100000", "2027-Q1")
    assert f"remittances {-float(r['val_E2']):+.1f}% year on year" in ofw["evidenceNote"]
    reg = {t["key"]: t for t in _get("/api/v1/explainability", scope="region", id="calabarzon", quarter="2027-Q1")["triggers"]}
    assert reg["ofw_remittance"]["status"] == "data_not_in_model"


def test_unaudited_missing_driver_stays_insufficient_data(thesis, monkeypatch):
    monkeypatch.setattr(D, "audited_published", lambda code, issue: set())
    ex = {t["key"]: t for t in _get("/api/v1/explainability", scope="province", id="cavite", quarter="2027-Q1")["triggers"]}
    assert ex["ofw_remittance"]["status"] == "insufficient_data"


def test_shared_indicators_are_identical_across_provinces():
    from app.ml.inference import firi as FI
    h = pd.read_csv(DATA / "thesis" / "firi2_history.csv", dtype={"province_code": str})
    for k in FI.NATIONAL:
        per = h.groupby("target")["indicators_json"].apply(lambda s: len({json.loads(x).get(k, {}).get("x") for x in s}))
        assert (per == 1).all(), k
    assert "national" in FI.LABELS["C1"] and "national" in FI.LABELS["E1"] and "national" in FI.LABELS["E2"]
