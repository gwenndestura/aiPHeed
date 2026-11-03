"""PFI tests: outcome data and constructs, leave-one-out integrity, release-aware inputs, the next-quarter clock,
reproducibility, benchmarking, artifact protection, the prospective register, geography and the API."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.pfi import MODEL, OUT, PROVINCES
from app.pfi import engine as E
from app.pfi import model as M
from app.pfi import serve as PS
from app.pfi import sources as S
from app.pfi.sources import expit


@pytest.fixture()
def tmp_out(tmp_path, monkeypatch):
    """Redirect forecast/register output to a temporary folder (the sealed artifact is read from data/pfi/model)."""
    for f in ("evaluation.json",):
        if (OUT / f).exists():
            shutil.copy(OUT / f, tmp_path / f)
    monkeypatch.setattr(E, "OUT", tmp_path)
    monkeypatch.setattr(PS, "OUT", tmp_path)
    return tmp_path


# ------------------------------------------------------------------------------------------------------------- data
def test_fies_outcomes_and_constructs():
    f = S.fies()
    reg = f[(f["level"] == "region") & (f["year"] == 2023) & (f["status"] == "verified_primary")]
    assert len(reg) == 17 and reg["key"].notna().all() and reg["key"].is_unique
    iva = reg.set_index("key").loc["IV-A"]
    assert (iva["pct"], iva["ci_low"], iva["ci_high"]) == (19.1, 17.0, 21.1)
    assert set(f["instrument"]) == {"FIES"}                      # HFIAS and subsistence are kept in separate loaders
    nat = f[f["key"] == "PH"].set_index("year")["pct"]
    assert nat[2021] == 33.4 and nat[2023] == 31.4
    assert not f.loc[f["year"] == 2019, "in_study_window"].any()
    p25 = f[(f["key"] == "IV-A") & (f["year"] == 2025)]
    assert len(p25) == 1 and p25["status"].iloc[0] != "verified_primary"


def test_region_and_province_tables_complete():
    R = S.region_table(2023)
    assert len(R) == 17 and R[["fies", "poverty", "subsistence", "unemployment", "rice_inflation"]].notna().all().all()
    P = S.province_table(2023)
    assert list(P["province"]) == PROVINCES and P.drop(columns="province").notna().all().all()
    assert P.set_index("province").loc["Quezon", "poverty"] == 10.2


def test_hfias_is_separate_and_verified():
    h = S.hfias_2015().set_index("geography")
    assert set(PROVINCES) <= set(h.index) and h.loc["Quezon", "mod_sev_pct"] == pytest.approx(48.8)
    assert (h["se_pp"] > 0).all()


# ------------------------------------------------------------------------------------------------------------ model
def test_loo_prediction_ignores_held_out_outcome():
    R = S.region_table(2023)
    a = M.loo_level(R, ["subsistence"], 31.4)
    R2 = R.copy()
    R2.loc[R2["key"] == "IX", "fies"] = 5.0                     # change only the held-out region's outcome
    b = M.loo_level(R2, ["subsistence"], 31.4)
    ra = next(r for r in a["rows"] if r["region"] == "IX")
    rb = next(r for r in b["rows"] if r["region"] == "IX")
    assert ra["predicted_pct"] == pytest.approx(rb["predicted_pct"])


def test_selection_rule():
    s = {"A": {"mae_pp": 5.0, "covariates": ["x", "y"]}, "B": {"mae_pp": 5.2, "covariates": ["x"]},
         "C": {"mae_pp": 5.4, "covariates": []}}
    assert M.select_level(s) == "B"
    s["B"]["mae_pp"] = 5.3
    assert M.select_level(s) == "A"


def test_metrics_hand_computed():
    m = M._class_metrics([1, 1, 0, 0, 0], [1, 0, 0, 0, 1], [0.9, 0.4, 0.1, 0.2, 0.6])
    assert (m["tp"], m["fn"], m["tn"], m["fp"]) == (1, 1, 2, 1)
    assert m["accuracy"] == pytest.approx(0.6) and m["balanced_accuracy"] == pytest.approx((0.5 + 2 / 3) / 2)
    assert m["roc_auc"] == pytest.approx(5 / 6)


def test_benchmark_shift_hits_target():
    eta = np.array([-1.5, -1.2, -1.4])
    w = np.array([1.0, 2.0, 3.0])
    c = M.benchmark_shift(eta, w, 0.25)
    assert float(np.sum(w / w.sum() * expit(eta + c))) == pytest.approx(0.25, abs=1e-9)


def test_provincial_estimates_benchmark_to_region():
    a = E.load_artifact()
    rng = np.random.default_rng(1)
    prov, reg = E._draw_offsets(a, rng, 2000)
    w = E._weights(a)
    assert np.allclose((expit(prov) * w).sum(axis=1), expit(reg), atol=1e-6)


# ---------------------------------------------------------------------------------------------- release awareness
def test_sws_release_filter():
    q = S.sws_quarterly("balance_luzon", "2026-10-13")
    assert q["published"].max() <= pd.Timestamp("2026-10-13") and "2026-Q3" not in set(q["quarter"])
    assert "2026-Q3" in set(S.sws_quarterly("balance_luzon", "2026-10-14")["quarter"])


def test_issue_uses_only_released_inputs(tmp_out):
    f = E.issue("2025-03-01", register=False)
    assert f["inputs"]["state_reference_year"] == 2023            # the 2025 wave was not yet published
    assert pd.Timestamp(f["data_cutoff"]) <= pd.Timestamp("2025-03-01")
    for w in f["inputs"]["sws_balance_luzon_window"]:
        if w["kind"] == "observed":
            assert pd.Timestamp(w["published"]) <= pd.Timestamp("2025-03-01")


def test_build_refuses_unreleased_survey():
    with pytest.raises(RuntimeError):
        E.build("2024-01-01")


# ------------------------------------------------------------------------------------------------------ clock
@pytest.mark.parametrize("d,cur,tgt", [("2026-11-03", "2026-Q4", "2027-Q1"), ("2026-12-31", "2026-Q4", "2027-Q1"),
                                       ("2027-01-01", "2027-Q1", "2027-Q2"), ("2027-06-30", "2027-Q2", "2027-Q3")])
def test_next_calendar_quarter(tmp_out, d, cur, tgt):
    f = E.issue(d, register=False)
    assert (f["current_quarter"], f["target_quarter"]) == (cur, tgt)
    assert all(r["forecast"]["target_quarter"] == tgt for r in f["provinces"])


def test_serving_clock_rolls_over(tmp_out, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-03")
    a = PS.outlook()
    assert a["target_quarter"] == "2027-Q1"
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-02")
    b = PS.outlook()
    assert b["target_quarter"] == "2027-Q2" and b["reissued_on_request"]
    c = PS.outlook()
    assert not c["reissued_on_request"] and c["sha256"] == b["sha256"]


# -------------------------------------------------------------------------------------------- outputs and safety
def test_reproducible_and_valid(tmp_out):
    f1 = E.issue("2026-11-03", register=False)
    f2 = E.issue("2026-11-03", register=False)
    assert f1["sha256"] == f2["sha256"]
    assert [r["province"] for r in f1["provinces"]] == PROVINCES
    assert sorted(r["priority_rank"] for r in f1["provinces"]) == [1, 2, 3, 4, 5]
    for r in f1["provinces"]:
        fc = r["forecast"]
        assert 0 <= fc["p_high"] <= 1 and 0 <= fc["p_rise_vs_current"] <= 1
        assert 0 < fc["p05"] <= fc["p10"] <= fc["p50"] <= fc["p90"] <= fc["p95"] < 100
        assert fc["class"] == ("HIGH" if fc["p_high"] >= 0.5 else "LOW")
        c = r["contributions_pp"]
        assert c["regional_2023_level"] + c["province_structure"] + c["change_since_2023"] == pytest.approx(fc["pct"], abs=0.6)


def test_tampered_artifact_is_refused(tmp_path, monkeypatch):
    bad = tmp_path / "pfi_model.json"
    a = json.loads((MODEL / "pfi_model.json").read_text())
    a["bridge"]["lambda"] = 0.9
    bad.write_text(json.dumps(a))
    monkeypatch.setattr(E, "ARTIFACT", bad)
    with pytest.raises(E.ArtifactMissing):
        E.load_artifact()


def test_register_once_per_quarter(tmp_out):
    E.issue("2026-11-03")
    E.issue("2026-12-15")
    E.issue("2027-01-05")
    recs = E.register()
    assert [r["issue_quarter"] for r in recs] == ["2026-Q4", "2027-Q1"]
    assert set(recs[0]["provinces"]) == set(PROVINCES)


# ------------------------------------------------------------------------------------------------------ geography
def test_geography_142_lgus(tmp_out, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-03")
    g = PS.lgus()
    assert g["count"] == 142 and set(g["by_province"]) == set(PROVINCES)
    assert len({r["lgu_psgc"] for r in g["rows"]}) == 142
    f = PS.outlook()
    byp = {r["province"]: r["forecast"]["pct"] for r in f["provinces"]}
    assert all(r["food_insecurity_forecast_pct"] == byp[r["province"]] for r in g["rows"])


def test_evaluation_statuses():
    ev = PS.evaluation()
    o = ev["objective_75"]
    assert o["provincial_quarterly"]["met"] is None and "NOT EVALUABLE" in o["provincial_quarterly"]["status"]
    lv = ev["level"]["candidates"][ev["level"]["selected"]]
    assert lv["n"] == 17
    assert o["level_classification"]["met"] == (o["level_classification"]["accuracy"] >= 0.75
                                                and o["level_classification"]["balanced_accuracy"] >= 0.75)


# ------------------------------------------------------------------------------------------------------------- API
def test_candidate_is_not_public(tmp_out, monkeypatch):
    """PFI is a candidate: the public food-insecurity route must not serve it; candidate routes need admin auth."""
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-03")
    from app import registry as R
    from app.main import app
    from app.services.security import require_admin
    monkeypatch.setattr(R, "REGISTRY", tmp_out / "registry.json")
    c = TestClient(app)
    r = c.get("/api/v1/final/food-insecurity/outlook")
    assert r.status_code == 503 and r.json()["detail"]["status"] == "validation_pending"
    assert c.get("/api/v1/admin/candidates/pfi-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        j = c.get("/api/v1/admin/candidates/pfi-1.0/outlook").json()
        assert j["CANDIDATE_NOT_APPROVED"] is True and j["target_quarter"] == "2027-Q1" and len(j["provinces"]) == 5
        m = c.get("/api/v1/admin/candidates/pfi-1.0/model").json()
        assert m["artifact_sha256"] == j["artifact_sha256"]
    finally:
        app.dependency_overrides.pop(require_admin, None)
    assert c.get("/api/v1/final/overview").status_code in (200, 503)          # existing contract untouched
