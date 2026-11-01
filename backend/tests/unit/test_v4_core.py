"""
tests/unit/test_v4_core.py
--------------------------
app.forecasting.v4 (docs/aipheed/v4): tier and seal integrity, point-in-time feature snapshots (a snapshot used at
another issue raises; injected rounds never change a forecast), the stability rule and ridge mechanics, the
mechanical verdicts (moving-block bootstrap, 75 % claim, Holm "beats all"), artifact integrity, inference that never
refits (both the served PERSIST path and a DELTA-X path), exact explanations, geography and the read-only v4 API.
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

from app.forecasting import geography as G
from app.forecasting import sws as T
from app.forecasting.as_of import LeakageError
from app.forecasting.v2 import models as V
from app.forecasting.v4 import features as F
from app.forecasting.v4 import models as DX
from app.forecasting.v4 import select as S4
from app.forecasting.v4 import serving as SV
from app.forecasting.v4 import verdict as VD

REPO = Path(__file__).resolve().parents[3]
V4 = REPO / "docs" / "aipheed" / "v4"
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / "v4_2026-10-01.json"
ISSUE = date(2026, 10, 1)
SEAL_SHA256 = "7ac72fec4c6d85c73006fdcc2c857acdb77ec2c4a864a4bdf00f2d933a8fad0e"
TIER_SHA256 = {"DEVTEST_rows.csv": "93a7bef67544dd1f14b91f9625eafaa20de3cd7134cfb2db47108cfe02fe0fa4",
               "TRAIN_rows.csv": "820c88d235261054b427ffe8cad75dd8c0e8dc5496d57547092049ef96275657"}
FEATURES_SHA256 = "b3957bb82c37bb0000e3894a48cdb4a070290f1c69344e4dc511e666b5d98b6a"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- integrity of tiers, snapshots, seal
def test_tiers_snapshots_and_seal_unchanged():
    for name, h in TIER_SHA256.items():
        assert _sha(V4 / "tiers" / name) == h
    assert _sha(F.SNAPSHOTS) == FEATURES_SHA256
    assert _sha(V4 / "sealed" / "V4_PROSPECTIVE_SEAL.csv") == SEAL_SHA256


def test_tiers_are_disjoint_and_devtest_is_the_frozen_su_set():
    tr, dv = pd.read_csv(V4 / "tiers" / "TRAIN_rows.csv"), pd.read_csv(V4 / "tiers" / "DEVTEST_rows.csv")
    k = ["issue", "area", "lead"]
    assert tr.merge(dv, on=k).empty
    assert dv.groupby("lead").size().to_dict() == {1: 44, 2: 40, 3: 36, 4: 32}
    sealed = pd.read_csv(V4 / "sealed" / "V4_PROSPECTIVE_SEAL.csv")
    assert not sealed.target.isin(set(T.load_rounds().quarter)).any()        # only unpublished targets


# ---------------------------------------------------------------- leakage
def test_snapshot_used_at_another_issue_raises():
    t = F.table()
    with pytest.raises(LeakageError):
        F.snapshot(t, "2026-07-01", used_at="2026-10-01")
    assert set(F.snapshot(t, "2026-10-01", used_at="2026-10-01").index) == {"metro_manila", "balance_luzon", "visayas", "mindanao"}


def test_injected_round_on_or_after_issue_does_not_change_v4_forecast():
    rr = T.load_rounds()
    base = S4.delta_at(__import__("app.forecasting.v2.select", fromlist=["walk_forward"]).walk_forward(rr, ISSUE), rr, F.table(), ISSUE)
    extra = rr[rr.quarter == "2026-Q3"].assign(published=ISSUE + timedelta(days=3), value=95.0)
    leaky = pd.concat([rr, extra], ignore_index=True)
    from app.forecasting.v2 import select as S2
    again = S4.delta_at(S2.walk_forward(leaky, ISSUE), leaky, F.table(), ISSUE)
    assert np.allclose(base.f, again.f)


# ---------------------------------------------------------------- stability rule and ridge
def _train(rho_sign_flip: bool, n_issues: int = 8):
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n_issues):
        for a in range(4):
            x = rng.normal()
            s = -1 if (rho_sign_flip and i >= n_issues // 2) else 1
            rows.append({"issue": f"2024-{i + 1:02d}-01", "change": s * 2 * x + 0.1 * rng.normal(), "rice_yoy": x})
    d = pd.DataFrame(rows)
    for f in F.FEATURES:
        if f not in d:
            d[f] = np.nan
    return d


def test_stability_rule_admits_stable_and_rejects_flipping_or_short():
    assert DX.fit_delta(_train(False)).features == ["rice_yoy"]
    assert DX.fit_delta(_train(True)).features == []                  # sign flips between halves
    assert DX.fit_delta(_train(False, n_issues=5)).features == []     # < 6 issues
    p = DX.fit_delta(_train(False))
    chg, contrib = DX.predict_delta(p, pd.Series({"rice_yoy": p.mean["rice_yoy"] + p.sd["rice_yoy"]}))
    assert chg > 0 and abs(chg - sum(contrib.values())) < 1e-12
    assert DX.predict_delta(p, pd.Series({"rice_yoy": np.nan}))[0] == 0.0     # missing -> z = 0


# ---------------------------------------------------------------- verdicts
def test_claim_75_and_beats_all_mechanics():
    cl = np.repeat(np.arange(12), 4)
    assert VD.claim_75(np.ones(48, bool), cl, sealed=True)["verdict"] == "CONFIRMED"
    assert VD.claim_75(np.zeros(48, bool), cl, sealed=True)["verdict"] == "REJECTED"
    assert VD.claim_75(np.ones(36, bool), cl[:36], sealed=True)["verdict"] == "NOT_YET_TESTABLE"   # 9 quarters
    assert VD.claim_75(np.ones(48, bool), cl, sealed=False)["verdict"] == "DEVELOPMENT_ONLY"
    assert VD.holm({"a": 0.01, "b": 0.02, "c": 0.04}) == {"a": 0.03, "b": 0.04, "c": 0.04}
    assert VD.beats_all({"a": 0.01, "b": 0.02})["verdict"] == "YES"
    assert VD.beats_all({"a": 0.01, "b": 0.2})["verdict"] == "NO"
    assert VD.paired_p(np.ones(48, bool), np.ones(48, bool), cl) == 1.0      # identical forecasts never "beat"
    idx = VD.block_indices(cl, draws=5)
    assert all(len(np.unique(cl[i])) <= 12 and len(i) == 48 for i in idx)


def test_development_verdict_file_is_development_only_and_sealed_not_testable():
    v = json.loads((V4 / "results" / "v4_verdict.json").read_text())
    assert v["claim_75_frozen_development"]["verdict"] == "DEVELOPMENT_ONLY"
    assert v["claim_75_sealed"]["frozen"]["verdict"] == "NOT_YET_TESTABLE"
    assert v["beats_all_sealed"]["verdict"] == "NOT_YET_TESTABLE"
    assert v["served_model"] == json.loads(ART.read_text())["model"]


# ---------------------------------------------------------------- artifact, inference, explanation
def test_artifact_tamper_refused_and_rebuild_reproduces(tmp_path):
    body = json.loads(ART.read_text())
    for edit in (lambda b: b["params"].update(q=1.0), lambda b: b.update(model="LGBM"),
                 lambda b: b["claims"].update(beats_all_sealed="YES")):
        b = copy.deepcopy(body)
        edit(b)
        p = tmp_path / "a.json"
        p.write_text(json.dumps(b))
        with pytest.raises(SV.ArtifactError):
            SV.load(p)
    assert SV.build(ISSUE)["artifact_sha256"] == body["artifact_sha256"]


def test_inference_never_refits_and_matches_store(monkeypatch):
    monkeypatch.setattr(V, "fit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("refit")))
    recs = SV.forecast(ISSUE, ART)
    assert len(recs) == 16 and SV.latest(ISSUE)["records"] == recs
    for r in recs:
        e = SV.explain(r)
        assert abs(e["contributions_sum"] - r["score"]) <= SV.SUM_TOLERANCE
        assert e["explanation_model_sha256"] == r["artifact_sha256"] and e["summary"] == "last observed value carried forward"
        assert r["claims"]["75pct_amended_status"].startswith("PROPOSED_NOT_ADOPTED")


def test_delta_x_path_end_to_end(monkeypatch, tmp_path):
    """If the rule had selected DELTA-X, inference and explanation still work and decompose exactly."""
    monkeypatch.setattr(S4, "select", lambda wf, rr, I: ("DELTA-X", []))
    p = SV.write(SV.build(ISSUE), tmp_path)
    recs = SV.forecast(ISSUE, p)
    snap = F.snapshot(F.table(), ISSUE.isoformat())
    for r in recs:
        e = SV.explain(r, snap.loc[r["area"]].to_dict())
        assert abs(e["contributions_sum"] - r["score"]) <= SV.SUM_TOLERANCE
        assert len(e["five_group_summary"]) == 5
    assert any(r["components"]["predicted_change"] for r in recs)


def test_v4_geography_142_lgus():
    v = G.geography_view(SV.forecast(ISSUE, ART), lead=2)
    assert len(v["lgus"]) == 142 and len(v["provinces"]) == 5
    assert all(l["lgu_estimate"] is None and l["lgu_estimate_status"] == "AWAITING_GROUND_TRUTH" for l in v["lgus"])


def test_v4_api():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/hunger-forecast/v4")
    assert r.status_code == 200 and len(r.json()["records"]) == 16 and "NOT YET TESTABLE" in r.json()["status"]
    e = c.get("/api/v1/hunger-forecast/v4/explanation", params={"lead": 2}).json()["explanation"]
    assert {g["data_state"] for g in e["five_group_summary"]} == {"OBSERVED"}
    assert c.get("/api/v1/hunger-forecast/v4", params={"issue_date": "2026-10-05"}).status_code == 422
    assert c.get("/api/v1/hunger-forecast/v4", params={"issue_date": "2021-01-01"}).status_code == 404
    assert len(c.get("/api/v1/hunger-forecast/v4/geography").json()["lgus"]) == 142
    assert c.post("/api/v1/hunger-forecast/v4").status_code == 405
