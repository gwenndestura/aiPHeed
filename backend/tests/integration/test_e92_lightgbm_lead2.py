"""
tests/integration/test_e92_lightgbm_lead2.py
--------------------------------------------
E92 LightGBM-only Lead-2 model: tied to the frozen protocol, news is an input of every part, every Lead-2 row is issued,
the frozen selection rule picked the reported model, and the reported Lead-2 figures reproduce from the predictions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E92 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E92_LightGBM_Lead2"
RUN = E92 / "runs" / "20261022T055421Z"


@pytest.fixture(scope="module")
def metrics():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def test_tied_to_frozen_protocol(metrics):
    assert metrics["protocol_sha256"] == (E92 / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((E92 / "PROTOCOL.md").read_bytes()).hexdigest() == metrics["protocol_sha256"]


def test_news_is_an_input_of_every_part():
    src = (E92 / "runner" / "run_e92.py").read_text(encoding="utf-8")
    assert 'nf = NEWS if news else []' in src and 'pf, hf, sf = PRICE_F + nf, HUNGER_F + nf, STACK_F + nf' in src
    assert 'NEWS = list(U.NEWS)' in src


def test_selection_and_lead2_figures(metrics):
    sel = metrics["selection_brier_lead2"]
    assert metrics["selected"] == min(sel, key=sel.get) == "M-LGB-DEC-S"
    assert not any(a.endswith("-NONEWS") for a in sel)
    P = pd.read_csv(RUN / "predictions_k2.csv")
    assert len(P) == 65 and P["M-LGB-DEC-S"].notna().all()
    acc = float(((P["M-LGB-DEC-S"] >= 0.5).astype(int) == P["y"]).mean())
    assert acc == pytest.approx(49 / 65)
    assert float(np.mean((P["M-LGB-DEC-S"] - P["y"]) ** 2)) == pytest.approx(
        metrics["leads"]["2"]["per_arm"]["M-LGB-DEC-S"]["metrics"]["brier"])
    assert metrics["leads"]["2"]["per_arm"]["M-LGB-DEC-S"]["pass"]["PASS"] is False
