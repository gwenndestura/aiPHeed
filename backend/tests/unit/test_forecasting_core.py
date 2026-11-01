"""
tests/unit/test_forecasting_core.py
-----------------------------------
app.forecasting: point-in-time selection (leak tests that FAIL when a leak is injected: run once with
AIPHEED_LEAK_DEMO=1, which swaps in a leaky selector, docs/aipheed/leak_injection_demo.txt), input validation,
exact equality with the research implementations (E131 target, E132 SEAS-LLM), artifact integrity, inference failure
modes and provenance, reproducibility, geography, and the read-only API.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.forecasting import artifact as A
from app.forecasting import as_of as AO
from app.forecasting import geography as G
from app.forecasting import inference as I
from app.forecasting import models as M
from app.forecasting import sws as T
from app.forecasting.validation import ValidationError, validate_lgus, validate_sws_rounds

REPO = Path(__file__).resolve().parents[3]
EXP = REPO / "aipheed-backend-aligned" / "experiments"
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / "seas_llm_2026-10-01.json"


def _selector():
    """The selector under test; AIPHEED_LEAK_DEMO=1 injects a leak (on-or-before instead of strictly before)."""
    if os.getenv("AIPHEED_LEAK_DEMO") == "1":
        def leaky(df, issue, published_col="published", strict=True):
            pub = pd.to_datetime(df[published_col]).dt.tz_localize(AO.PH)
            return df[pub <= AO.issue_instant(issue) + pd.Timedelta(days=1)].copy()
        return leaky
    return AO.as_of


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- leakage
def test_leak_row_published_on_issue_day_is_excluded():
    df = pd.DataFrame({"v": [1, 2, 3], "published": ["2026-09-30", "2026-10-01", "2026-10-02"]})
    out = _selector()(df, date(2026, 10, 1))
    assert out["v"].tolist() == [1], "a value published on or after the issue date entered the forecast"


def test_leak_real_sws_round_published_after_issue_never_used():
    rr = T.load_rounds()
    issue = date(2026, 10, 14)                        # SWS 2026-Q3 was published on 2026-10-14 itself
    known = _selector()(rr, issue)
    assert (pd.to_datetime(known["published"]) < pd.Timestamp(issue)).all()
    assert "2026-Q3" not in set(known["quarter"])


def test_guard_raises_on_injected_future_row_and_missing_date():
    df = pd.DataFrame({"v": [1, 2], "published": ["2026-09-30", "2026-10-05"]})
    with pytest.raises(AO.LeakageError):
        AO.assert_point_in_time(df, date(2026, 10, 1))
    AO.assert_point_in_time(df.iloc[:1], date(2026, 10, 1))
    with pytest.raises(AO.LeakageError):
        AO.as_of(pd.DataFrame({"v": [1], "published": [None]}), date(2026, 10, 1))
    with pytest.raises(AO.LeakageError):
        AO.as_of(pd.DataFrame({"v": [1]}), date(2026, 10, 1))


# ---------------------------------------------------------------- validation
def test_validation_passes_real_data_and_flags_each_injected_problem():
    raw = pd.read_csv(T.SWS_ROUNDS)
    assert validate_sws_rounds(raw) == []
    cases = {"pre-2021": lambda d: d.assign(quarter=d["quarter"].where(d.index != 0, "2020-Q4")),
             "published before": lambda d: d.assign(published=d["published"].where(d.index != 1, "2021-01-01")),
             "outside 0-100": lambda d: d.assign(visayas=d["visayas"].where(d.index != 2, 120.0)),
             "duplicate": lambda d: pd.concat([d, d.iloc[[3]]], ignore_index=True),
             "missing columns": lambda d: d.drop(columns=["published"]),
             "stale": None}
    for label, f in cases.items():
        if f is None:
            p = validate_sws_rounds(raw, max_age_days=30, today=pd.Timestamp("2027-06-01"))
        else:
            p = validate_sws_rounds(f(raw.copy()))
        assert p and any(label.split()[0] in x for x in p), (label, p)


def test_lgu_reference_valid_and_mismatch_detected():
    d = G.lgus()
    assert validate_lgus(d) == [] and d["lgu_code"].is_unique
    assert (d["name_source"] == "ROSARIO").sum() == 2          # same name in Batangas and Cavite: keyed by code
    bad = d.copy()
    bad.loc[0, "province"] = "Cavite"
    assert validate_lgus(bad)


# ---------------------------------------------------------------- equality with the research implementations
def test_target_equals_e131_implementation():
    X = _load("e131_x1_core", EXP / "E131_Objectives_Resolution" / "runner" / "e131_x1.py")
    a = T.quarter_table(T.load_rounds()).sort_values(["area", "quarter"]).reset_index(drop=True)
    b = X.quarter_table(X.rounds()).sort_values(["area", "quarter"]).reset_index(drop=True)
    for c in ("y", "se", "tol", "k"):
        assert np.allclose(a[c], b[c]), c


def test_seas_llm_equals_e132_seal_and_walk_forward():
    rr = T.load_rounds()
    qt = T.known_at(rr, date(2026, 11, 1))
    p = M.fit_seas(qt)
    seal = pd.read_csv(EXP / "E132_Final_Methodology" / "sealed" / "E132_PROSPECTIVE_SEAL.csv")
    for r in seal.itertuples():
        assert abs(M.forecast_seas(qt, p, T.qi(r.target))[r.area]["f"] - getattr(r, "_11")) < 1e-9
    P = pd.read_csv(EXP / "E136_Methodology_Review" / "out" / "e136_predictions.csv")
    P = P[(P.policy == "P-DASH") & P.issue.isin(["2024-01-01", "2025-07-01", "2026-04-01"])]
    for (issue, k), g in P.groupby(["issue", "lead"]):
        q2 = T.known_at(rr, date.fromisoformat(issue))
        fc = M.forecast_seas(q2, M.fit_seas(q2), T.qi(g["target"].iloc[0]))
        assert np.allclose([fc[a]["f"] for a in g["area"]], g["f_SEAS-LLM"], atol=1e-9)


# ---------------------------------------------------------------- artifact and inference
def test_artifact_tamper_and_config_mismatch_refused(tmp_path):
    body = json.loads(ART.read_text())
    A.load(ART)
    t = copy.deepcopy(body)
    t["params"]["s2"] = 1.0
    (tmp_path / "t.json").write_text(json.dumps(t))
    with pytest.raises(A.ArtifactError, match="hash"):
        A.load(tmp_path / "t.json")
    f = copy.deepcopy(body)
    f["features"] = ["cpi"]
    (tmp_path / "f.json").write_text(json.dumps(f))
    with pytest.raises(A.ArtifactError, match="feature config"):
        A.load(tmp_path / "f.json")


def test_inference_failures_are_loud():
    with pytest.raises(I.InferenceError, match="quarter start"):
        I.forecast(date(2026, 11, 1), ART)
    with pytest.raises(I.InferenceError, match="precedes"):
        I.forecast(date(2026, 7, 1), ART)


def test_inference_records_complete_reproducible_and_never_refit(monkeypatch):
    a = I.forecast(date(2026, 10, 1), ART)
    b = I.forecast(date(2026, 10, 1), ART)
    assert a == b and len(a) == 16
    need = {"issue_date", "target_quarter", "lead", "score", "model_version", "artifact_sha256", "data_vintage_published",
            "feature_cutoff", "preprocessing_version", "evidence_status", "reliability_status", "lo80", "hi80"}
    assert all(need <= set(r) for r in a)
    assert {r["latest_data_quarter"] for r in a} == {"2026-Q2"}     # 2026-Q3 was published after the issue
    monkeypatch.setattr(M, "fit_seas", lambda *_: (_ for _ in ()).throw(AssertionError("inference must not refit")))
    I.forecast(date(2026, 10, 1), ART)


def test_stored_forecast_equals_fresh_inference():
    from app.forecasting import store as S
    b = S.latest(date(2026, 10, 1))
    assert b is not None and b["records"] == json.loads(json.dumps(I.forecast(date(2026, 10, 1), ART)))


# ---------------------------------------------------------------- geography and API
def test_geography_all_142_lgus_with_explicit_status():
    v = G.geography_view(I.forecast(date(2026, 10, 1), ART), lead=2)
    assert len(v["lgus"]) == 142 and len(v["provinces"]) == 5
    assert len({l["lgu_code"] for l in v["lgus"]}) == 142
    assert all(l["lgu_estimate"] is None and l["lgu_estimate_status"] == "AWAITING_GROUND_TRUTH" for l in v["lgus"])
    assert all(p["broader_area_reference"]["status"] == "BROADER_AREA_REFERENCE" for p in v["provinces"])
    served = set(pd.read_csv(REPO / "backend" / "data" / "ch1_engine" / "rows.csv")["province_code"])
    assert {p["province_code"] for p in v["provinces"]} == served


def test_api_routes_read_only_and_errors():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/hunger-forecast")
    assert r.status_code == 200 and len(r.json()["records"]) == 16 and "not the dashboard" in r.json()["status"]
    assert c.get("/api/v1/hunger-forecast", params={"issue_date": "2026-10-02"}).status_code == 422
    assert c.get("/api/v1/hunger-forecast", params={"issue_date": "not-a-date"}).status_code == 422
    assert c.get("/api/v1/hunger-forecast", params={"issue_date": "2021-01-01"}).status_code == 404
    e = c.get("/api/v1/hunger-forecast/explanation", params={"lead": 2, "area": "balance_luzon"}).json()
    comp = e["explanation"]["predictive_contributions"]
    assert abs(sum(x["value"] for x in comp) - e["record"]["score"]) < 1e-3
    assert all(x["role"] == "context only (not a model input)" for x in e["explanation"]["context_indicators"])
    assert c.get("/api/v1/hunger-forecast/explanation", params={"lead": 9}).status_code == 422
    g = c.get("/api/v1/hunger-forecast/geography", params={"lead": 2}).json()
    assert len(g["lgus"]) == 142
    assert c.post("/api/v1/hunger-forecast").status_code == 405
