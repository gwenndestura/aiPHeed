"""
tests/integration/test_lead2_arch.py
------------------------------------
LEAD2_ARCH: the P0H4-U equation P = pi_H x pi_P is reproduced; the hunger cap on the three 2023-Q4 cases is real
(controlled test with the actual pi_H and a LightGBM fitted by the production recipe); P0H4 and P0H4-U share the price
part and differ only in the hunger reading's timing; the served model and seal are unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "arch_audit.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_ARCH results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def T():
    sys.path.insert(0, str(LT / "runner"))
    import lt_lib
    return lt_lib


def test_equation_reproduced(res):
    a = res["A_equation"]
    assert a["pi_H_recomputed_max_abs"] < 1e-6 and a["P_equals_piH_x_piP_max_abs"] < 1e-6 and a["rows"] == 250


def test_hunger_cap_controlled(T):
    F = T.F
    t = 2023 * 4 + 1                                           # origin 2023-Q2, Lead 2 -> target 2023-Q4
    h = F.pi_h(F.issue(t, "B"), t + 2)
    assert h["h_last_iss"] == pytest.approx(11.3) and h["pi_H"] == pytest.approx(0.5, abs=1e-12)
    # the strongest possible price evidence from a LightGBM fitted with the production recipe still stays below 1
    S = T.stack()
    tr = T.train_rows(S, t)
    m = T.Uni(T.GRID[7], T.U2).fit(tr)
    x = S[S["t"] == t].head(1).copy()
    for c in ("A1_food", "A1_gap", "A_mom"):
        x[c] = 1e6
    p = float(m.predict(x)[0])
    assert p < 1.0 and h["pi_H"] * p < 0.5 and h["pi_H"] * (1 - 1e-12) < 0.5


def test_cap_and_ceiling_reported_correctly(res):
    b = res["B_cap"]
    assert b["capped"] == 3 and b["capped_h_last"] == [11.3] and b["recall_ceiling_at_0.50"] == "14/17"
    assert b["controlled_max_P_if_pi_P_1"] < 0.5


def test_p0h4_and_p0h4u_differ_only_in_hunger_timing(res):
    d = res["D_p0h4_vs_u"]
    assert d["same_price_part"] and d["rows_differing"] == 8 and d["gained_hits"] == 4 and d["new_false_alarms"] == 3


def test_direct_target_lacks_development_labels(res):
    c = res["C_target_learning"]
    assert c["price_label_identical_across_leads_and_origins"]
    assert c["dev_origins_direct_ineligible"] == 5 and c["dev_origins"] == 7


def test_served_model_and_seal_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    ev = CH1.evaluation()
    assert ev["seal_sha256"] == SERVED_SEAL and CH1.data_dir().name == "ch1_engine"
