"""E74 regression tests: the employment driver (FIRI v2 indicator E1) and every displayed driver, recomputed from the
raw LFS file and the stored index components, on real served examples from all five provinces. The single synthetic
case (a negative employment push, which never occurs in the real data) is marked."""
from __future__ import annotations

import copy
import csv
import importlib.util
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import dimensions as D
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import thesis_system as T
from app.services import dashboard as DB
from app.services import report as RP

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "e74_trace", ROOT / "aipheed-backend-aligned" / "experiments" / "E74_Employment_Driver_Audit" / "runner" / "e74_trace.py")
TR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TR)
SLUG = TR.SLUG
QUARTERS = ("2027-Q1", "2026-Q3", "2025-Q2", "2024-Q2")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _history_quarters():
    with open(T.FIRI_HISTORY, encoding="utf-8") as f:
        return sorted({r["target"] for r in csv.DictReader(f) if r["FIRI"]})


def test_e1_is_the_lfs_unemployment_change_for_every_served_row(thesis):
    rec, ur = LEAD2.record(), TR.lfs_ur()
    assert all(3.0 <= v <= 20.0 for v in ur.values())                      # unemployment rate, percent
    checked = 0
    for q in _history_quarters() + [rec["targetQuarter"]]:
        xs = set()
        for code in rec["provinces"]:
            f = T.firi_for(rec, q, code)
            x = f["indicators"]["E1"]["x"] if f else None
            if x is None:
                continue
            ind, meta = TR.e1_independent(ur, TR.qs(TR.qi(q) - 2))
            assert ind is not None and math.isclose(float(x), ind, abs_tol=1e-6)
            assert abs(float(x)) < 5.0                                       # percentage points
            assert meta["quarter_t_minus_1"] == TR.qs(TR.qi(q) - 3)          # the quarter before the origin
            xs.add(round(float(x), 9))
            checked += 1
        assert len(xs) <= 1                                                  # national: identical for all provinces
    assert checked > 40


def test_lfs_months_used_end_before_the_issue_date(thesis):
    rec = LEAD2.record()
    for q in _history_quarters() + [rec["targetQuarter"]]:
        origin = TR.qi(q) - 2
        issue_month = (origin + 1) // 4 * 12 + ((origin + 1) % 4) * 3          # first month of the issue quarter
        last_used = (origin - 1) // 4 * 12 + ((origin - 1) % 4) * 3 + 2         # last month of quarter t-1
        assert issue_month - last_used >= 4                                      # >= 3 full months for the LFS release


def test_pushes_reconstruct_the_index_and_api_matches(thesis):
    rec = LEAD2.record()
    for q in QUARTERS:
        for code, slug in SLUG.items():
            f = T.firi_for(rec, q, code)
            pu = T.pushes(f)
            assert math.isclose(sum(pu.values()), f["firi"] - 0.5, abs_tol=1e-6)
            assert math.isclose(sum(T._norm_weights(f).values()), 1.0, abs_tol=1e-12)
            groups = {g: sum(pu.get(k, 0.0) for k in ks) for g, ks in T.FIVE_GROUPS.items()}
            pcts = dict(zip(groups, TR.integer_shares([abs(v) for v in groups.values()])))
            tr = client.get("/api/v1/explainability", params={"scope": "province", "id": slug, "quarter": q}).json()["triggers"]
            assert [t["pct"] for t in tr] == sorted([t["pct"] for t in tr], reverse=True)       # ordered by share
            for t in tr:
                assert t["pct"] == pcts[t["key"]]
                assert math.isclose(t["signedContribution"], round(groups[t["key"]], 6), abs_tol=2e-6)
                if t["signedContribution"] > 0:
                    assert t["direction"] == "increases_risk"
                elif t["signedContribution"] < 0:
                    assert t["direction"] == "protective"


def test_employment_is_never_the_largest_single_push_and_bars_exclude_hunger(thesis):
    rec = LEAD2.record()
    for code in rec["provinces"]:
        f = T.firi_for(rec, rec["targetQuarter"], code)
        pu = T.pushes(f)
        assert max(pu, key=lambda k: abs(pu[k])) == "H1"                     # observed regional hunger, outside the bars
        s = T.largest_push_sentence(f)
        assert "Regional hunger" in s and "not an overall ranking of causes" in s


def test_employment_card_says_national_and_default_weight(thesis):
    rec = LEAD2.record()
    assert T.weight_basis(rec["originQuarter"], "E") == "default"            # E has no evidence weight at 2026-Q3
    assert T.weight_basis(rec["originQuarter"], "C") == "evidence"
    for code in rec["provinces"]:
        txt = T.group_evidence(rec, rec["targetQuarter"], code, "employment")
        assert "same value for all five provinces, not local evidence" in txt and "equal-weight default" in txt


def test_missing_employment_is_insufficient_not_zero_risk(thesis):
    rec = LEAD2.record()
    for q in _history_quarters():
        f = T.firi_for(rec, q, "PH040300000")
        if f and f["indicators"]["E1"]["score"] is None:
            r = client.get("/api/v1/explainability", params={"scope": "province", "id": "quezon", "quarter": q})
            if r.status_code != 200:                                         # quarters before 2024-Q2 are not served
                continue
            tr = {t["key"]: t for t in r.json()["triggers"]}
            assert tr["employment"]["pct"] == 0 and tr["employment"]["status"] == "insufficient_data"
            assert "not counted" in T.group_evidence(rec, q, "PH040300000", "employment")
            return
    pytest.fail("no quarter with missing E1 found")


def test_synthetic_negative_employment_push_is_protective():
    """SYNTHETIC: E1 below its historical middle lowers the index (no real quarter has this)."""
    res = {"domains": {"E": 0.2, "A": 0.5}, "weights": {"E": 1.0, "A": 1.0},
           "indicators": {"E1": {"score": 0.2, "domain": "E"}, "A1": {"score": 0.5, "domain": "A"}}}
    pu = T.pushes(res)
    assert pu["E1"] < 0 and math.isclose(pu["E1"], 0.5 * (0.2 - 0.5))


def test_pdf_texts_are_index_breakdown_not_shap(thesis):
    rec = LEAD2.record()
    ex = DB.explainability("PH040300000", rec["targetQuarter"])               # the dict the PDF builder uses
    assert ex["otherPct"] and ex["otherPct"] > 0
    txt = DB.compose_formal_interpretation("Quezon", rec["targetQuarter"], ex["triggers"], ex["otherPct"])
    assert f"{ex['otherPct']:.0f}% of the index's total push" in txt
    assert "SHAP" not in txt and "not show what causes food insecurity" in txt and "not an overall ranking" in txt
    for t in ex["triggers"]:
        if t["pct"] > 0:
            assert f"{t['label']} ({t['pct']}%)" in txt                        # PDF shares = API shares
    assert "exact share of how far" not in RP._thesis_driver_text(ex) and "not a ranking of causes" in RP._thesis_driver_text(ex)


def test_ranking_reasons_use_the_index_breakdown(thesis):
    r = client.get("/api/v1/ranking", params={"quarter": "2027-Q1"}).json()
    assert "not SHAP" in r["method"]
    for d in r["data"]:
        assert all(w["feature"] in D.ORDER for w in d["whyAboveNextLower"])  # no features of another model


def test_panel_wording_from_config(thesis):
    m = client.get("/api/v1/config").json()["servingModel"]["explanationMethod"]
    assert m["panelTitle"] == "Contributing indicators" and "not causes" in m["orderLabel"]


def test_improving_labour_market_scored_as_risk_is_disclosed(thesis):
    rec = LEAD2.record()
    f = T.firi_for(rec, "2025-Q2", "PH040300000")
    e1 = f["indicators"]["E1"]
    assert float(e1["x"]) < 0 and float(e1["score"]) > 0.5                    # unemployment fell, yet it raised the index
    txt = T.group_evidence(rec, "2025-Q2", "PH040300000", "employment")
    assert "unemployment fell year on year" in txt and "does not mean conditions worsened" in txt
    txt27 = T.group_evidence(rec, rec["targetQuarter"], "PH040300000", "employment")
    assert "unemployment fell" not in txt27                                     # 2027-Q1: a genuine rise (+0.895 points)
