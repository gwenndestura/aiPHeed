"""
tests/unit/test_v2_core.py
--------------------------
app.forecasting.v2 (docs/aipheed/v2): leakage (injected rounds and feature rows must never change a forecast or must
raise), lead/target alignment, model and selection-rule mechanics, conformal intervals, equality with the independent
E131 local-level implementation, artifact integrity, inference that never refits, exact explanations, geography with
injected defects, the read-only v2 API, the prospective seal and the mechanical reliability status.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.forecasting import as_of as AO
from app.forecasting import geography as G
from app.forecasting import sws as T
from app.forecasting.validation import validate_lgus
from app.forecasting.v2 import artifact as A
from app.forecasting.v2 import explain as X
from app.forecasting.v2 import inference as I
from app.forecasting.v2 import models as V
from app.forecasting.v2 import select as S
from app.forecasting.v2 import store as ST
from app.forecasting.v2 import verdict as VD
from app.quarterly.target import forecast_target

REPO = Path(__file__).resolve().parents[3]
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / "v2_2026-10-01.json"
RESULTS = REPO / "docs" / "aipheed" / "v2" / "results"
SEAL = REPO / "docs" / "aipheed" / "v2" / "sealed" / "V2_PROSPECTIVE_SEAL.csv"
SEAL_SHA256 = "e88f7bb265140d43dea75f6e82748a8777e5bf7b56ed2bd111f6187f3ed325d7"
ISSUE = date(2026, 10, 1)


@pytest.fixture(scope="module")
def rr():
    return T.load_rounds()


def _fake_round(rr: pd.DataFrame, published: date, quarter: str, value: float) -> pd.DataFrame:
    extra = rr[rr.quarter == rr.quarter.max()].copy()
    return pd.concat([rr, extra.assign(quarter=quarter, published=published, value=value)], ignore_index=True)


# ---------------------------------------------------------------- leakage
def test_round_published_on_or_after_issue_never_changes_v2_forecast(rr):
    base = S.forecasts_at(rr, ISSUE)
    for pub in (ISSUE, ISSUE + timedelta(days=30)):
        leaky = _fake_round(rr, pub, "2026-Q3", 95.0)
        assert S.forecasts_at(leaky, ISSUE).equals(base), f"a round published {pub} entered the forecast"


def test_round_published_the_day_before_issue_is_used(rr):
    """Positive control: the same injection one day earlier MUST change the forecast (the test above is not vacuous)."""
    leaky = _fake_round(rr, ISSUE - timedelta(days=1), "2026-Q3", 95.0)
    assert not S.forecasts_at(leaky, ISSUE).equals(S.forecasts_at(rr, ISSUE))


def test_feature_table_with_future_row_raises():
    t = pd.DataFrame({"published": [date(2026, 9, 30), ISSUE]})
    with pytest.raises(AO.LeakageError):
        AO.assert_point_in_time(t, ISSUE)


def test_inner_truth_uses_only_values_known_at_the_outer_issue(rr):
    wf = S.walk_forward(rr, date(2025, 1, 1))
    g = S.inner_rows(wf, rr, date(2025, 1, 1), 2)
    pub = T.quarter_table(T.as_of(rr, date(2025, 1, 1))).set_index(["area", "qi"])["published"]
    assert len(g) and all(pub[(a, q)] < date(2025, 1, 1) for a, q in zip(g.area, g.tqi))
    assert (g.issue < "2025-01-01").all()


def test_context_indicators_are_point_in_time():
    ctx = json.loads((REPO / "backend" / "data" / "forecasting" / "context" / "context_2026-10-01.json").read_text())
    for groups in ctx["areas"].values():
        assert set(groups) == {"market", "climate", "employment_ofw", "news_nlp", "poverty_vulnerability"}
        m = groups["market"]
        assert date.fromisoformat(m["available"]) < ISSUE
        assert date.fromisoformat(groups["poverty_vulnerability"]["available"]) < ISSUE


# ---------------------------------------------------------------- lead / target alignment
@pytest.mark.parametrize("issue", [date(2024, 1, 1), date(2025, 7, 1), ISSUE])
def test_lead_target_alignment_matches_dashboard_clock(rr, issue):
    f = S.forecasts_at(rr, issue, models=("PERSIST",))
    D = S.dashboard_quarter(issue)
    assert S.issue_of(D) == issue
    for k in S.LEADS:
        assert set(f[f.lead == k].tqi) == {D - 1 + k}
    ft = forecast_target(f"{issue.isoformat()}T09:00")
    assert set(f[f.lead == 2].tqi) == {T.qi(ft["target_quarter"])}            # Lead 2 = the dashboard target
    assert (f.h == f.tqi - f.latest_qi).all() and (f.h >= 1).all()


# ---------------------------------------------------------------- models and selection rule
def test_ll_equals_independent_e131_local_level():
    P = pd.read_csv(REPO / "aipheed-backend-aligned" / "experiments" / "E136_Methodology_Review" / "out" / "e136_predictions.csv")
    P = P[P.policy == "P-DASH"]
    W = pd.read_csv(RESULTS / "v2_walk_forward.csv")
    W = W[W.model == "LL"].assign(target=lambda d: d.tqi.map(T.qs))
    m = P.merge(W, on=["area", "issue", "lead", "target"])
    assert len(m) == 272 and np.abs(m["f_LLM"] - m["f"]).max() < 1e-9


def test_persist_is_latest_and_fit_stays_in_grid(rr):
    known = T.known_at(rr, ISSUE)
    p = V.fit("LL-K", known)
    assert p.kappa in V.KAPPA_GRID and 0 < p.q < 100
    f = V.forecast(known, V.fit("PERSIST", known), T.qi("2027-Q1"))
    latest = known.sort_values("qi").groupby("area").y.last()
    assert all(f[a]["f"] == latest[a] and f[a]["noise_adjustment"] == 0 for a in f)


def _inner(n_q: int, better: bool):
    rows = []
    for q in range(n_q):
        for a in range(4):
            for m in V.CANDIDATES:
                hit = m == "LL" and better or (a < 2)
                rows.append({"model": m, "tqi": 8000 + q, "area": f"a{a}", "issue": f"2020-0{q % 9 + 1}-01",
                             "f": 10.0 if hit else 30.0, "y": 10.0, "se": 2.0})
    return pd.DataFrame(rows)


def test_selection_rule_replaces_only_with_ci_above_zero_and_enough_quarters(monkeypatch, rr):
    monkeypatch.setattr(S, "inner_rows", lambda wf, rr_, I_, lead: _inner(8, better=True))
    assert S.select(None, rr, ISSUE)[0] == "LL"
    monkeypatch.setattr(S, "inner_rows", lambda wf, rr_, I_, lead: _inner(5, better=True))
    assert S.select(None, rr, ISSUE)[0] == "PERSIST"            # < 6 inner quarters: never replaced
    monkeypatch.setattr(S, "inner_rows", lambda wf, rr_, I_, lead: _inner(8, better=False))
    assert S.select(None, rr, ISSUE)[0] == "PERSIST"            # equal performance: the simpler model stays


def test_conformal_rank_and_minimum(monkeypatch, rr):
    res = np.arange(1, 10, dtype=float)                         # 9 residuals -> ceil(0.8 * 10) = 8th smallest
    monkeypatch.setattr(S, "inner_rows", lambda *a: pd.DataFrame({"model": "PERSIST", "f": res, "y": 0.0}))
    assert S.conformal_halfwidth(None, rr, ISSUE, "PERSIST", 2) == (8.0, 9)
    monkeypatch.setattr(S, "inner_rows", lambda *a: pd.DataFrame({"model": "PERSIST", "f": res[:7], "y": 0.0}))
    assert S.conformal_halfwidth(None, rr, ISSUE, "PERSIST", 2) == (None, 7)


def test_decision_table_labels():
    assert VD.label(True, 10, 40, future=False) == "DEVELOPMENT_PASS"
    assert VD.label(False, 10, 40, future=False) == "NOT_RELIABLE"
    assert VD.label(True, 9, 40, future=True) == "NOT_YET_TESTABLE"
    assert VD.label(True, 10, 40, future=True) == "RELIABLE"
    assert VD.maximum_reliable_lead({1: "RELIABLE", 2: "NOT_RELIABLE", 3: "RELIABLE"}) == 1
    assert VD.maximum_reliable_lead({1: "NOT_YET_TESTABLE"}) is None
    assert VD.served_status("NOT_RELIABLE", "NOT_YET_TESTABLE") == "NOT_RELIABLE"


# ---------------------------------------------------------------- artifact, inference, explanation
def test_artifact_tamper_config_and_write_once_refused(tmp_path):
    body = json.loads(ART.read_text())
    for edit in (lambda b: b["params"].update(q=b["params"]["q"] + 1), lambda b: b.update(features=["x"]),
                 lambda b: b.update(model="LGBM"), lambda b: b["reliability_status_by_lead"].update({"2": "RELIABLE"})):
        b = copy.deepcopy(body)
        edit(b)
        p = tmp_path / "a.json"
        p.write_text(json.dumps(b))
        with pytest.raises(A.ArtifactError):
            A.load(p)
    with pytest.raises(A.ArtifactError):
        A.write(body, ART.parent)


def test_artifact_rebuild_reproduces_hash():
    assert A.build(ISSUE)["artifact_sha256"] == json.loads(ART.read_text())["artifact_sha256"]


def test_inference_never_refits_and_fails_loudly(monkeypatch):
    monkeypatch.setattr(V, "fit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("inference refitted")))
    recs = I.forecast(ISSUE, ART)
    assert len(recs) == 16 and {r["artifact_sha256"] for r in recs} == {json.loads(ART.read_text())["artifact_sha256"]}
    for bad in (date(2026, 10, 2), date(2026, 7, 1)):
        with pytest.raises(I.InferenceError):
            I.forecast(bad, ART)


def test_stored_forecast_equals_fresh_inference():
    assert ST.latest(ISSUE)["records"] == I.forecast(ISSUE, ART)


def test_explanation_exact_and_hash_bound():
    for r in I.forecast(ISSUE, ART):
        e = X.explain(r)
        assert abs(sum(c["value"] for c in e["predictive_contributions"]) - r["score"]) <= X.SUM_TOLERANCE
        assert e["explanation_model_sha256"] == r["artifact_sha256"]
        assert e["summary"] == "last observed value carried forward"
        assert len(e["contextual_indicators"]) == 5 and all("no weight" in c["role"] for c in e["contextual_indicators"])
    bad = dict(r, score=r["score"] + 1)
    with pytest.raises(ValueError):
        X.explain(bad)


def test_served_status_is_the_mechanical_verdict():
    v = json.loads((RESULTS / "v2_verdict.json").read_text())
    rel = pd.read_csv(RESULTS / "v2_reliability.csv")
    for r in I.forecast(ISSUE, ART):
        k = r["lead"]
        dev = rel[(rel.model == "V2") & (rel.lead == k)]["label"].iloc[0]
        assert r["reliability_status"] == v["served_reliability_status_by_lead"][str(k)] == dev
    assert v["served_model"] == json.loads(ART.read_text())["model"]


# ---------------------------------------------------------------- geography with injected defects
def test_v2_geography_and_injected_defects_detected():
    v = G.geography_view(I.forecast(ISSUE, ART), lead=2)
    assert len(v["lgus"]) == 142 and len({l["lgu_code"] for l in v["lgus"]}) == 142 and len(v["provinces"]) == 5
    assert all(l["lgu_estimate"] is None and l["lgu_estimate_status"] == "AWAITING_GROUND_TRUTH" for l in v["lgus"])
    d = G.lgus()
    dup = pd.concat([d.iloc[:-1], d.iloc[[0]]], ignore_index=True)      # 142 rows, one code twice, one LGU dropped
    assert len(dup) == 142
    assert any("duplicate" in p for p in validate_lgus(dup))
    assert any("expected 142" in p for p in validate_lgus(d.iloc[1:]))
    wrong = d.copy()
    wrong.loc[5, "province"] = "Quezon" if wrong.loc[5, "province"] != "Quezon" else "Rizal"
    assert any("mismatch" in p for p in validate_lgus(wrong))


# ---------------------------------------------------------------- API
def test_v2_api_read_only_and_errors():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/hunger-forecast/v2")
    assert r.status_code == 200 and len(r.json()["records"]) == 16 and "approved v2" in r.json()["status"]
    assert c.get("/api/v1/hunger-forecast/v2", params={"issue_date": "2026-10-02"}).status_code == 422
    assert c.get("/api/v1/hunger-forecast/v2", params={"issue_date": "2021-01-01"}).status_code == 404
    e = c.get("/api/v1/hunger-forecast/v2/explanation", params={"lead": 2, "area": "balance_luzon"}).json()["explanation"]
    assert {x["data_state"] for x in e["contextual_indicators"]} == {"OBSERVED"} and e["missing_information"] == []
    assert c.get("/api/v1/hunger-forecast/v2/explanation", params={"area": "cavite"}).status_code == 422
    assert len(c.get("/api/v1/hunger-forecast/v2/geography").json()["lgus"]) == 142
    assert c.post("/api/v1/hunger-forecast/v2").status_code == 405
    assert "superseded" in c.get("/api/v1/hunger-forecast").json()["status"]


# ---------------------------------------------------------------- prospective seal
def test_seal_unchanged_and_reproducible(rr):
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == SEAL_SHA256
    import importlib.util
    spec = importlib.util.spec_from_file_location("v2_seal_t", REPO / "backend" / "scripts" / "v2_seal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sealed = pd.read_csv(SEAL)
    fresh = pd.concat([m.seal_rows(rr, date(2026, 7, 1)), m.seal_rows(rr, ISSUE)], ignore_index=True)
    assert np.allclose(sealed.f, fresh.f) and (sealed.target == fresh.target).all()
    assert not sealed.target.isin(set(rr.quarter)).any()                  # only unpublished targets were sealed


def test_frozen_n1_n7_reapplied_reproduces_committed_labels():
    """The served labels come from the frozen e130_lib rules applied to the stored outer predictions, not by hand."""
    SU = pd.read_csv(RESULTS / "v2_outer_predictions.csv")
    rel = pd.read_csv(RESULTS / "v2_reliability.csv")
    for k in S.LEADS:
        g = SU[SU.lead == k].reset_index(drop=True).assign(f_persistence=lambda d: d.f_PERSIST, f_climatology=lambda d: d.f_CLIM)
        for m in ("V2", "LL", "LL-K"):
            r = VD.reliability(g, m)
            row = rel[(rel.lead == k) & (rel.model == m)].iloc[0]
            assert VD.label(bool(r["passed"]), r["n_target_quarters"], r["n_rows"], future=False) == row["label"]
            assert bool(r["rules"]["N2_within_tolerance_75"]) == bool(row["N2_within_tolerance_75"])
            assert r["n_rows"] == row["n_rows"]
