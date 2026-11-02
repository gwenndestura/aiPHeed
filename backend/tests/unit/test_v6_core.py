"""
tests/unit/test_v6_core.py
--------------------------
app.forecasting.v6 (docs/aipheed/v6): seal and tier integrity, point-in-time history and training rows (an injected round
never changes a forecast, with a positive control), the pre-registered LightGBM configuration (determinism, fallback, exact
TreeSHAP sum), the selection rule, the DM-HLN statistic, artifact integrity, inference that never refits (served path and a
forced LightGBM path), geography and the read-only v6 API.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.forecasting import geography as G
from app.forecasting import sws as T
from app.forecasting.v2 import models as V
from app.forecasting.v2 import select as S2
from app.forecasting.v4 import features as F
from app.forecasting.v6 import lgbm as LG
from app.forecasting.v6 import select as S6
from app.forecasting.v6 import serving as SV

REPO = Path(__file__).resolve().parents[3]
V6 = REPO / "docs" / "aipheed" / "v6"
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / "v6_2026-10-01.json"
ISSUE = date(2026, 10, 1)
SEAL_SHA256 = "1309a55697d1c0c8351a9e817a0255ecbcbdbb361b19f3f21bebcaa4c334f4e4"
BASELINE_SEAL_SHA256 = "495e6a93263200ce9ecbc2dbcd9283335274593b78b11134e63fecc9dbad80dd"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _script(name: str):
    sys.path.insert(0, str(REPO / "backend" / "scripts"))
    spec = importlib.util.spec_from_file_location(f"{name}_t", REPO / "backend" / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def rr():
    return T.load_rounds()


@pytest.fixture(scope="module")
def wf2(rr):
    return S2.walk_forward(rr, ISSUE)


def _train(n_issues=10, per=4, seed=0):
    r = np.random.default_rng(seed)
    rows = []
    areas = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
    for i in range(n_issues):
        for j in range(per):
            x = r.normal()
            rows.append({"issue": f"20{20 + i // 12}-{i % 12 + 1:02d}-01", "area": areas[j % 4], "h": 3.0, "last_change": x,
                         "dev_mean": r.normal(), "change": 3 * x + 0.2 * r.normal(), **{f: np.nan for f in F.FEATURES}})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- integrity
def test_seals_unchanged_and_only_unpublished_targets(rr):
    assert _sha(V6 / "sealed" / "V6_PROSPECTIVE_SEAL.csv") == SEAL_SHA256
    assert _sha(V6 / "sealed" / "V6_BASELINE_SEAL.csv") == BASELINE_SEAL_SHA256
    for f in ("V6_PROSPECTIVE_SEAL.csv", "V6_BASELINE_SEAL.csv"):
        assert not pd.read_csv(V6 / "sealed" / f).target.isin(set(rr.quarter)).any()


def test_seal_reproducible(rr):
    m = _script("v6_seal")
    sealed = pd.read_csv(V6 / "sealed" / "V6_PROSPECTIVE_SEAL.csv")
    fresh = pd.concat([m.seal_rows(rr, F.table(), date(2026, 7, 1)), m.seal_rows(rr, F.table(), ISSUE)], ignore_index=True)
    assert len(sealed) == len(fresh) and np.allclose(sealed.f, fresh.f)


def test_devtest_rows_are_the_hashed_tier_and_verdict_is_development_only():
    su = pd.read_csv(V6 / "results" / "v6_devtest_predictions.csv")
    assert su.groupby("lead").size().to_dict() == {1: 44, 2: 40, 3: 36, 4: 32}
    v = json.loads((V6 / "results" / "v6_verdict.json").read_text())
    assert v["claim_75_frozen_development"]["verdict"] == "DEVELOPMENT_ONLY"
    assert v["claim_75_sealed"]["frozen"]["verdict"] == "NOT_YET_TESTABLE" and v["beats_all_sealed"]["verdict"] == "NOT_YET_TESTABLE"
    assert v["served_model"] == json.loads(ART.read_text())["model"]


def test_sealed_scorer_covers_all_eight_baselines():
    m = _script("v6_score_sealed")
    assert set(m.BASELINES) <= set(m.load_seals().model.unique())


# ---------------------------------------------------------------- leakage
def _inject(rr, published, value=95.0):
    extra = rr[rr.quarter == "2026-Q3"].assign(published=published, value=value)
    return pd.concat([rr, extra], ignore_index=True)


def test_injected_round_on_or_after_issue_never_changes_lgbm(rr, wf2):
    feats = F.table()
    base = S6.lgbm_at(rr, feats, wf2, ISSUE, {})
    leaky = _inject(rr, ISSUE + timedelta(days=3))
    again = S6.lgbm_at(leaky, feats, S2.walk_forward(leaky, ISSUE), ISSUE, {})
    assert np.allclose(base.f, again.f)


def test_injected_round_before_issue_is_used_positive_control(rr, wf2):
    feats = F.table()
    early = _inject(rr, ISSUE - timedelta(days=1))
    again = S6.lgbm_at(early, feats, S2.walk_forward(early, ISSUE), ISSUE, {})
    assert not np.allclose(S6.lgbm_at(rr, feats, wf2, ISSUE, {}).f, again.f)


def test_training_truth_known_at_the_issue_and_history_point_in_time(rr, wf2):
    I = date(2025, 7, 1)
    tr = S6.training(rr, F.table(), wf2, I, 2, {})
    assert len(tr) and (tr.issue < I.isoformat()).all()
    pub = T.quarter_table(T.as_of(rr, I)).set_index(["area", "qi"])["published"]
    assert all(pub[(a, q)] < I for a, q in zip(tr.area, tr.tqi))
    h = S6.history(rr, "2024-01-01").set_index("area")
    k = T.known_at(rr, date(2024, 1, 1))
    bl = k[k.area == "balance_luzon"].sort_values("qi").y.to_numpy()
    assert h.loc["balance_luzon", "last_change"] == pytest.approx(bl[-1] - bl[-2])
    assert h.loc["balance_luzon", "dev_mean"] == pytest.approx(bl[-1] - bl.mean())


# ---------------------------------------------------------------- LightGBM configuration
def test_lgbm_config_matches_preregistration():
    p = LG.PARAMS
    assert (p["num_leaves"], p["max_depth"], p["min_data_in_leaf"], p["learning_rate"]) == (4, 2, 10, 0.05)
    assert (p["lambda_l1"], p["lambda_l2"], p["feature_fraction"], p["bagging_fraction"], p["bagging_freq"]) == (1.0, 5.0, 0.8, 0.8, 1)
    assert p["max_bin"] == 63 and p["deterministic"] and p["force_row_wise"] and p["seed"] == 2026
    assert (LG.MAX_ROUNDS, LG.STOP, LG.MIN_ROWS) == (200, 20, 30) and LG.W_GRID == (0.0, 0.25, 0.5, 0.75, 1.0)


def test_lgbm_deterministic_fallback_and_treeshap_sum():
    t = _train()
    a, b = LG.fit(t), LG.fit(t)
    assert a.model is not None and a.model == b.model and a.w == b.w
    pred, ex = LG.predict(a, t.head(8))
    assert np.allclose(pred, [sum(e.values()) for e in ex], atol=1e-9)         # TreeSHAP + expected value = prediction
    few = LG.fit(_train(n_issues=5))                                           # 20 rows < 30
    assert few.model is None and few.w == 0.0
    assert np.all(LG.predict(few, t.head(4))[0] == 0)


def test_lgbm_learns_a_planted_signal():
    """The configuration can find a strong signal, so 'no gain' on hunger is not a broken learner."""
    t, new = _train(n_issues=20), _train(n_issues=4, seed=9)
    f = LG.fit(t)
    p, _ = LG.predict(f, new)
    assert np.corrcoef(p, new.change)[0, 1] > 0.7


# ---------------------------------------------------------------- selection rule and DM-HLN
def _inner(n_q, better):
    rows = []
    for q in range(n_q):
        for a in range(4):
            for m in S6.CANDIDATES:
                hit = (m == "LGBM-D" and better) or a < 2
                rows.append({"model": m, "tqi": 8000 + q, "area": f"a{a}", "issue": "2020-01-01", "f": 10.0 if hit else 30.0, "y": 10.0, "se": 2.0})
    return pd.DataFrame(rows)


def test_selection_rule(monkeypatch, rr):
    monkeypatch.setattr(S2, "inner_rows", lambda wf, r, I, lead: _inner(8, True))
    assert S6.select(None, rr, ISSUE)[0] == "LGBM-D"
    monkeypatch.setattr(S2, "inner_rows", lambda wf, r, I, lead: _inner(5, True))
    assert S6.select(None, rr, ISSUE)[0] == "PERSIST"
    monkeypatch.setattr(S2, "inner_rows", lambda wf, r, I, lead: _inner(8, False))
    assert S6.select(None, rr, ISSUE)[0] == "PERSIST"


def test_dm_hln_statistic():
    m = _script("v6_validate")
    r = np.random.default_rng(1)
    n = 12
    su = pd.DataFrame({"lead": 2, "tqi": np.arange(n), "h": 1, "y": 0.0, "f_V6": r.normal(0, 1, n), "f_PERSIST": r.normal(0, 3, n)})
    for b in m.BASELINES:
        su[f"f_{b}"] = su.f_PERSIST
    su.loc[:, "f_V4"] = su.f_V6                                                # identical forecasts have no statistic
    su = pd.concat([su, su.assign(lead=1), su.assign(lead=3), su.assign(lead=4)], ignore_index=True)
    d = m.dm_hln(su, "V6")
    x = d[(d.lead == 2) & (d.baseline == "PERSIST")].iloc[0]
    g = su[su.lead == 2]
    dd = (g.f_V6 ** 2 - g.f_PERSIST ** 2).to_numpy()
    t = np.sqrt((n - 1) / n) * dd.mean() / np.sqrt(((dd - dd.mean()) ** 2).sum() / n / n)
    assert x.hln_t == pytest.approx(t) and x["T"] == n
    assert pd.isna(d[(d.lead == 2) & (d.baseline == "V4")].iloc[0].hln_t)


# ---------------------------------------------------------------- artifact, inference, explanation
def test_artifact_tamper_refused_and_rebuild_reproduces(tmp_path):
    body = json.loads(ART.read_text())
    for edit in (lambda b: b["params"].update(q=1.0), lambda b: b.update(model="XGB"),
                 lambda b: b["claims"].update(beats_all_sealed="YES"), lambda b: b.update(model="LGBM-D")):
        b = copy.deepcopy(body)
        edit(b)
        p = tmp_path / "a.json"
        p.write_text(json.dumps(b))
        with pytest.raises(SV.ArtifactError):
            SV.load(p)
    assert SV.build(ISSUE)["artifact_sha256"] == body["artifact_sha256"]
    with pytest.raises(SV.ArtifactError):
        SV.write(body, ART.parent)


def test_inference_never_refits_matches_store_and_status_is_mechanical(monkeypatch):
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("refit"))  # noqa: E731
    monkeypatch.setattr(V, "fit", boom)
    monkeypatch.setattr(LG, "fit", boom)
    recs = SV.forecast(ISSUE, ART)
    assert len(recs) == 16 and SV.latest(ISSUE)["records"] == recs
    v = json.loads((V6 / "results" / "v6_verdict.json").read_text())
    for r in recs:
        assert r["reliability_status"] == v["served_reliability_status_by_lead"][str(r["lead"])]
        e = SV.explain(r)
        assert abs(e["contributions_sum"] - r["score"]) <= SV.SUM_TOLERANCE and e["explanation_model_sha256"] == r["artifact_sha256"]
        assert e["summary"] == "last observed value carried forward" and r["claims"]["75pct_proposed_status"].startswith("PROPOSED_NOT_ADOPTED")
    for bad in (date(2026, 10, 2), date(2026, 7, 1)):
        with pytest.raises(SV.InferenceError):
            SV.forecast(bad, ART)


def test_forced_lgbm_path_end_to_end(monkeypatch, tmp_path):
    """If the rule had selected LightGBM: same numbers as the walk-forward, and the explanation sums exactly."""
    monkeypatch.setattr(S6, "select", lambda wf, rr, I: ("LGBM-D", []))
    p = SV.write(SV.build(ISSUE), tmp_path)
    recs = SV.forecast(ISSUE, p)
    sealed = pd.read_csv(V6 / "sealed" / "V6_PROSPECTIVE_SEAL.csv")
    sealed = sealed[(sealed.issue == ISSUE.isoformat()) & (sealed.model == "LGBM-D")]
    for r in recs:
        s = sealed[(sealed.lead == r["lead"]) & (sealed.area == r["area"])].f.iloc[0]
        assert r["score"] == pytest.approx(s, abs=1e-3)
        e = SV.explain(r, F.snapshot(F.table(), ISSUE.isoformat()).loc[r["area"]].to_dict())
        assert abs(e["contributions_sum"] - r["score"]) <= SV.SUM_TOLERANCE and len(e["five_group_summary"]) == 5
    assert any(r["components"]["predicted_change"] for r in recs)


def test_v6_geography():
    v = G.geography_view(SV.forecast(ISSUE, ART), lead=2)
    assert len(v["lgus"]) == 142 and len(v["provinces"]) == 5
    assert all(l["lgu_estimate"] is None and l["lgu_estimate_status"] == "AWAITING_GROUND_TRUTH" for l in v["lgus"])


def test_v6_api():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/hunger-forecast/v6")
    assert r.status_code == 200 and len(r.json()["records"]) == 16 and "never provincial" in r.json()["status"]
    e = c.get("/api/v1/hunger-forecast/v6/explanation", params={"lead": 2}).json()["explanation"]
    assert {g["data_state"] for g in e["five_group_summary"]} == {"OBSERVED"}
    assert c.get("/api/v1/hunger-forecast/v6", params={"issue_date": "2026-10-05"}).status_code == 422
    assert c.get("/api/v1/hunger-forecast/v6", params={"issue_date": "2021-01-01"}).status_code == 404
    assert len(c.get("/api/v1/hunger-forecast/v6/geography").json()["lgus"]) == 142
    assert c.post("/api/v1/hunger-forecast/v6").status_code == 405
