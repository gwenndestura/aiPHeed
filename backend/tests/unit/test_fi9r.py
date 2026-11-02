"""FI9-R tests: production protection, register immutability, conformal interval, local level, reproduction, API."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi9 import MODEL
from app.fi9 import OUT as FI9OUT
from app.fi9r import OUT
from app.paths import BACKEND_DIR

PIN = BACKEND_DIR / "data" / "fi9" / "PRODUCTION_PIN.json"


def test_production_model_is_pinned_and_unchanged():
    pin, art = json.loads(PIN.read_text()), json.loads((MODEL / "lead1_model.json").read_text())
    adoption = json.loads((OUT / "adoption.json").read_text())
    assert (art["model"], art["kind"]) == (pin["model"], pin["kind"])
    assert not any(v.get("adopt") for v in adoption.values() if isinstance(v, dict))
    assert art["sha256"] == pin["artifact_sha256_at_pin"]


def test_reassessment_code_never_writes_production_files():
    import re
    for f in (BACKEND_DIR / "app" / "fi9r").glob("*.py"):
        src = f.read_text(encoding="utf-8")
        pattern = r'(MODEL|FI9OUT|"fi9" / "model"|"fi9" / "out")[^\n]*\.(write_text|write_bytes|to_csv|to_json|open\()'
        assert not re.search(pattern, src), f.name


def test_register_is_append_only_and_tamper_evident(tmp_path: Path):
    from app.fi9 import prospective as PR
    reg = tmp_path / "r.jsonl"
    rec = {"issue_date": "2027-02-28", "target_quarter": "2027-Q2", "forecast": {"class": "LOW", "p_high": 0.1,
           "interval95_pct": [5, 20]}, "baselines": {}}
    a = PR.append(rec, reg)
    b = PR.append({**rec, "issue_date": "2027-03-10"}, reg)
    assert PR.verify(reg) and a["scored"] and not b["scored"] and b["revision"] == 1
    lines = reg.read_text().splitlines()
    lines[0] = lines[0].replace('"p_high": 0.1', '"p_high": 0.9')
    reg.write_text("\n".join(lines) + "\n")
    assert not PR.verify(reg)
    with pytest.raises(RuntimeError):
        PR.append(rec, reg)


def test_live_register_intact_and_records_baselines():
    from app.fi9 import prospective as PR
    recs = PR.read()
    assert PR.verify() and recs
    r = recs[0]
    for k in ["issue_date", "target_quarter", "model_version", "artifact_sha256", "training_data_cutoff", "generated_utc"]:
        assert r[k]
    assert {"naive_persistence", "climatology_always_low", "local_level_challenger"} <= set(r["baselines"])
    assert r["forecast"]["interval95_pct"][0] < r["forecast"]["level_pp"] < r["forecast"]["interval95_pct"][1]


def test_conformal_interval_in_serving_equals_reassessment():
    """The production half-width at a historical origin equals the one the reassessment evaluated."""
    from app.fi7.design import Designer
    from app.fi9.serve import conformal_halfwidth
    W = pd.read_csv(OUT / "wf_predictions.csv")
    w = W[(W["tag"] == "C0 damped persistence (FI9)") & (W["target_quarter"] == "2019-Q1")].iloc[0]
    X = Designer("operational").frame(1)
    tr = X[X["y"].notna() & (X["target_published"] <= pd.Timestamp(w["issue_date"]))]
    assert conformal_halfwidth(tr) == pytest.approx(w["cpi95_hi"] - w["level_hat"], abs=1e-9)


def test_local_level_filter_limits():
    from app.fi9r.evaluate import _kalman
    y = np.array([10.0, 20.0, np.nan, 30.0])
    m_small_r, _, _ = _kalman(y, np.full(4, 1e-6), 1.0)
    assert m_small_r[-1] == pytest.approx(30.0, abs=1e-3)              # precise readings: follow the data
    m_big_r, _, _ = _kalman(y, np.full(4, 1e6), 1e-6)
    assert m_big_r[-1] == pytest.approx(20.0, abs=0.01)                # constant level, equal noise: the average


def test_reassessment_reproduces_fi9_and_rejects_no_evidence_changes():
    S = json.loads((OUT / "reassessment.json").read_text())
    assert S["reproduces_fi9"]["c0_vs_fi9_max_abs_p_diff"] < 1e-9 and S["reproduces_fi9"]["c0_vs_fi9_class_mismatches"] == 0
    A = json.loads((OUT / "adoption.json").read_text())
    g = S["periods"]["full"]["models"]["C0 damped persistence (FI9)"]
    assert A["interval"]["gaussian_coverage"] == g["interval_gaussian"]["coverage"]
    assert A["interval"]["replace_with_conformal"] == (not 0.90 <= A["interval"]["gaussian_coverage"] <= 0.99)
    assert json.loads((OUT / "audit.json").read_text())["all_passed"]


def test_label_stability_recorded():
    S = json.loads((OUT / "reassessment.json").read_text())
    ls = S["label_stability"]
    assert ls["20q"]["n_high"] == 11 and all(ls[k]["flips_vs_20q"] <= 5 for k in ["12q", "16q", "24q", "28q"])


def test_api_outlook_communicates_scope_baseline_and_interval(monkeypatch):
    from app.main import app
    c = TestClient(app)
    f = json.loads((FI9OUT / "forecast.json").read_text())
    monkeypatch.setenv("AIPHEED_NOW", f["issue_date"])
    b = c.get("/api/v1/fi9/outlook").json()
    art = json.loads((MODEL / "lead1_model.json").read_text())
    lvl = b["forecast"]["projected_hunger_pct"]
    hw = art["params"]["conformal_halfwidth_95"]
    assert abs(b["forecast"]["projected_hunger_interval95_pct"][1] - (lvl + hw)) <= 1
    assert "no better than simply carrying the latest reading forward" in b["baseline_comparison"]["statement"]
    assert any("Regional only" in x for x in b["limitations"])
    m = c.get("/api/v1/fi9/provincial-measurements").json()
    assert {r["geography"] for r in m["fnri_2015_hfias"]} == {"CALABARZON", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
    assert "not forecasts" in m["note"]
    assert all(r["verification_status_aipheed"] == "verified_primary" for r in m["food_poverty_records"])
    r = c.get("/api/v1/fi9/register").json()
    assert r["intact"] and r["n_records"] >= 1
