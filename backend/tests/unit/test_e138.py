"""E138: lock, frozen selection rule, baseline behaviour (REG shrinkage, HIER = LR for an unseen region), the WHEN
Holm adjustment, the seal and the registry status."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from app import registry as R
from app.e138 import OUT
from app.e138 import evaluate as E
from app.e138 import models as M
from app.e138 import when as W
from app.e138 import where as WH


def _toy(n=60, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    q = 1 / (1 + np.exp(-2 * x))
    return pd.DataFrame({"p_poverty": x, "p_subsistence": x + rng.normal(0, .3, n), "p_poverty_gap": x,
                         "q": q, "region": np.repeat(list("ABCDEF"), n // 6), "y": x, "se_y": 0.1})


def test_protocol_lock_matches_code():
    E.verify_lock()


def test_reg_shrinks_to_national_and_unseen_region_gets_national():
    t = _toy()
    m = M.REG().fit(t)
    a = t[t["region"] == "A"]["q"]
    assert np.isclose(m.r_["A"], (a.mean() * len(a) + m.nat_ * M.KAPPA) / (len(a) + M.KAPPA))
    assert m.predict_proba(pd.DataFrame({"region": ["Z"]}))[0] == m.nat_


def test_hier_equals_lr_for_an_unseen_region():
    t = _toy()
    h, lr = M.HIER(M.P, C=1.0).fit(t), M.LR(M.P, C=1.0).fit(t)
    z = t.head(3).assign(region="Z")
    assert np.allclose(h.predict_proba(z), lr.predict_proba(z))


def test_one_se_rule_prefers_simpler_model():
    rng = np.random.default_rng(1)
    t = _toy(120).assign(NAT=0.5)
    t["LR-P"] = np.clip(t["q"] + rng.normal(0, .05, len(t)), 0, 1)
    t["RR-P"] = np.clip(t["q"] + rng.normal(0, .049, len(t)), 0, 1)
    assert WH.select(t, np.random.default_rng(2))["selected"] == "LR-P"


def test_holm_is_monotone_and_capped():
    assert np.allclose(W.holm([0.01, 0.04, 0.03, 0.5]), [0.04, 0.09, 0.09, 0.5])
    assert max(W.holm([0.6, 0.7])) == 1.0


def test_results_and_seal_integrity():
    res = json.loads((OUT / "results.json").read_text())
    assert res["protocol_version"] == "E138-P1" and res["selection"]["selected"] in M.CANDIDATES
    cal = json.loads((OUT / "calabarzon.json").read_text())
    body = (OUT / "sealed_prediction.json").read_text()
    assert hashlib.sha256(body.encode()).hexdigest() == cal["sealed_prediction_sha256"]


def test_e138_rejected_not_production():
    reg = R.load()
    m = reg["models"]["e138-where-lrp-1.0"]
    assert m["status"] == "rejected" and (reg.get("production") or {}).get("model_id") != "e138-where-lrp-1.0"
