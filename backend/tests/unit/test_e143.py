"""E143: lock; cross-fitted level; random-effects anchor identification and BLUP algebra; anchors use earlier rounds
only; issued outputs decompose exactly and follow the stricter class rule; registry, register and the admin route."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import registry as R
from app.e143 import OUT
from app.e143 import evaluate as E
from app.e143 import model as M
from app.registry import prospective_provincial as PP


@pytest.fixture(autouse=True)
def _restore_e137_paths():
    from app.e137 import features as F
    saved = F.HRAW
    yield
    F.HRAW = saved
    for fn in (F._cpi, F._psa_rounds, F._quarterly):
        fn.cache_clear()


class _FakeLevel:
    def __init__(self, n):
        self.oof_ = np.zeros(n)

    def predict_y(self, X):
        return np.zeros(len(X))


def _panel(dev_a, dev_b, se=0.1):
    rows = []
    for i, (a, b) in enumerate(zip(dev_a, dev_b)):
        rows += [{"key": f"p{i}", "region": f"r{i % 3}", "survey": "NNS2013", "prev_survey": None, "y": a, "se_y": se},
                 {"key": f"p{i}", "region": f"r{i % 3}", "survey": "FNRI2015", "prev_survey": "NNS2013", "y": b, "se_y": se}]
    return pd.DataFrame(rows)


def test_lock():
    E.verify_lock()


def test_anchor_not_identified_without_different_round_pairs():
    r = json.loads((OUT / "results.json").read_text())
    for p in r["params"]:
        if p["origin"] == "O1":
            assert p["n_own_pairs"] == 0 and p["c"] == 0.0 and p["mean_weight_on_own_surveys"] == 0.0
        assert 0.0 <= p["c"] <= 1.0 and 0.0 <= p["sigma2_G"] <= p["sigma2_A"] + 1e-12


def test_blup_uses_only_earlier_rounds_and_shrinks_with_survey_error():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 0.5, 40)
    tr = _panel(a + rng.normal(0, 0.1, 40), a + rng.normal(0, 0.1, 40))
    m = M.Anchored("re", "lgbm").fit(tr, _FakeLevel(len(tr)))
    assert m.c_ > 0.5
    q15 = M.RQ["FNRI2015"]
    anc_late, _, w_late, n_late = m._one("p0", "r0", q15 + 8)        # both rounds are earlier
    anc_mid, _, w_mid, n_mid = m._one("p0", "r0", q15)               # only 2013 is earlier than a 2015 target
    anc_none, _, _, n_none = m._one("p0", "r0", M.RQ["NNS2013"])     # nothing earlier
    assert (n_late, n_mid, n_none) == (2, 1, 0) and anc_none == 0.0 and w_late > w_mid > 0
    m.tr_["se_y"] = 100.0
    assert abs(m._one("p0", "r0", q15 + 8)[0]) < 1e-3                # survey error swamps the measurement


def test_cross_fitted_level_predicts_each_region_from_a_model_without_it():
    from app.e141 import panel as P
    X = P.data(1)
    tr = X[X["survey"].isin(["NNS2013", "FNRI2015"])].reset_index(drop=True)
    lv = M.Level("ridge").fit(tr)
    assert np.allclose(lv.predict_y(tr), lv.oof_)


def test_issue_decomposes_exactly_and_follows_class_rule():
    f = json.loads((OUT / "issue" / "forecast_next_quarter.json").read_text())
    assert f["display_lead"] == 1 and "NOT validated" in f["claim"] and len(f["provinces"]) == 5
    for q in f["provinces"]:
        ex = q["explanation"]
        assert abs(ex["base_logit"] + sum(ex["groups"].values()) - q["relative_logit"]) < 0.01
        p, (lo, hi) = q["p_elevated"], q["p_refit_range90"]
        cands = [v for k, v in q["model_selection_spread"].items() if k.startswith("C")]
        want = ("HIGH" if p >= 0.8 and lo >= 0.5 and min(cands) >= 0.5 else
                "LOW" if p <= 0.2 and hi < 0.5 and max(cands) < 0.5 else "UNCERTAIN")
        assert q["risk_class"] == want and "NOT a validated forecast" in q["output_type"]
        assert q["last_direct_survey"] in ("FNRI2015", "ENNS2018", "ENNS2019") and q["quarters_since_last_survey"] >= 30
        v = q["variance_decomposition"]
        assert abs(v["transitory_round_shock_sigma2_b"] + v["permanent_component_uncertainty"] - v["total_V"]) < 1e-9
    lg = pd.read_csv(OUT / "issue" / "lgus_next_quarter.csv")
    assert len(lg) == 142 and lg["label"].str.contains("not a municipal food-insecurity measurement").all()


def test_gate_recorded_and_nothing_promoted():
    r = json.loads((OUT / "results.json").read_text())
    assert r["gate"]["adopted"] is None
    a = json.loads((OUT / "audit.json").read_text())
    assert a["C_transition_identification"]["lgbm"]["max_observed_gap_quarters"] == 24
    reg = R.load()
    assert (reg.get("production") or {}).get("model_id") not in ("e143-re-lgbm-1.0", "e143-hre-lgbm-1.0")
    for mid in ("e143-re-lgbm-1.0", "e143-hre-lgbm-1.0"):
        assert reg["models"][mid]["status"] == "rejected"
        assert mid in {x["model_id"] for x in PP.read()}
    assert PP.verify()


def test_admin_route_only():
    from app.main import app
    from app.services.security import require_admin
    c = TestClient(app)
    assert c.get("/api/v1/admin/candidates/e143-re-lgbm-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        o = c.get("/api/v1/admin/candidates/e143-re-lgbm-1.0/outlook").json()
        assert o["CANDIDATE_NOT_APPROVED"] is True and o["target_quarter"] == "2027-Q1"
    finally:
        app.dependency_overrides.pop(require_admin, None)
