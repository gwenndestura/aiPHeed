"""
tests/integration/test_e96_target_formulation.py
------------------------------------------------
E96: tied to the frozen protocol; the two-stage frozen selection kept POV and N3; the selected arm reproduces the E94
unified model; news does not add net Brier value; the counterfactual moves Laguna 2024-Q2 (K=1) across 0.5; K = 0.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E96 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E96_Target_Formulation"
RUN = E96 / "runs" / "20261022T073838Z"


@pytest.fixture(scope="module")
def m():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def test_protocol(m):
    assert m["protocol_sha256"] == (E96 / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((E96 / "PROTOCOL.md").read_bytes()).hexdigest() == m["protocol_sha256"]


def test_selection_and_reproduction(m):
    assert m["stage_a"] == min(m["stage_a_selection"], key=m["stage_a_selection"].get) == "M-U96-POV"
    assert m["selected"] == min(m["news_selection"], key=m["news_selection"].get) == "M-U96-NEWS-N3"
    for k in (1, 2, 3, 4):
        P = pd.read_csv(RUN / f"predictions_k{k}.csv")
        assert np.allclose(P["M-U96-NEWS-N3"], P["M-E94-U94"], atol=1e-12)
    assert all(v["K"] == 0 for v in m["K"].values())


def test_news_effect_and_counterfactual(m):
    for k in ("1", "2", "3"):
        assert m["per_k"][k]["_news_effect"]["M-U96-NEWS-N3"]["p_one_sided"] > 0.10
    cf = [c for c in m["news_counterfactual"] if c["target_q"] == "2024-Q2" and c["K"] == 1 and c["province"] == "Laguna"][0]
    assert cf["p_with_news"] >= 0.5 > cf["p_news_at_median"]


def test_measured_hunger_formulation(m):
    h = m["per_k"]["1"]["_hunger_measured"]["M-U96-NEWS-N3"]
    assert h["rmse"]["Hhat"] > h["rmse"]["Hlast"]
    assert h["threshold"]["model"]["accuracy"] == pytest.approx(12 / 13)
