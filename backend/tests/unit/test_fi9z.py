"""FI9-Z tests: class-specific metrics, lock, recomputation, decision consistency, served-model protection, API fields."""
from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi9 import MODEL
from app.fi9z import OUT
from app.fi9z.classmetrics import class_metrics
from app.paths import BACKEND_DIR

E = json.loads((OUT / "evaluation.json").read_text())


def test_class_metrics_hand_computed():
    y = [1, 1, 1, 0, 0, 0, 0, 0]
    c = [1, 1, 0, 1, 0, 0, 0, 0]
    m = class_metrics(y, c)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 4)
    assert m["high_precision"] == pytest.approx(2 / 3) and m["high_recall"] == pytest.approx(2 / 3)
    assert m["low_precision"] == pytest.approx(0.8) and m["low_recall"] == pytest.approx(0.8)
    assert m["balanced_accuracy"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert m["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert m["false_high_rate"] == pytest.approx(0.2) and m["missed_high_rate"] == pytest.approx(1 / 3)
    always_low = class_metrics(y, [0] * 8)
    assert always_low["balanced_accuracy"] == 0.5 and always_low["high_f1"] == 0.0


def test_lock_matches():
    from app.fi9z.study import _code, _digest
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    assert lock["sha256"] == _digest() == E["protocol_sha256"] and lock["code_sha256"] == _code()


def test_reported_class_metrics_recompute_from_predictions():
    W = pd.read_csv(OUT / "predictions.csv")
    for (o, c), g in W.groupby(["origin", "config"]):
        rep = E["evaluation"][o][c]["full"]
        mine = class_metrics(g["y"], g["cls"], g["p"])
        for k in ["tp", "fp", "fn", "tn", "balanced_accuracy", "macro_f1", "brier"]:
            assert (mine[k] is None and rep[k] is None) or abs(mine[k] - rep[k]) < 1e-9, (o, c, k)


def test_decisions_consistent_and_production_unchanged():
    for o, models in E["evaluation"].items():
        for c, v in models.items():
            assert v["passes_all"] == all(v["checks"].values()), (o, c)
    assert E["passing"]["OP1"] == [] and E["max_reliable_lead"] is None
    pin = json.loads((BACKEND_DIR / "data" / "fi9" / "PRODUCTION_PIN.json").read_text())
    art = json.loads((MODEL / "lead1_model.json").read_text())
    assert art["sha256"] == pin["artifact_sha256_at_pin"] and art["kind"] == pin["kind"]


def test_production_fails_high_recall_and_dashboard_says_so(monkeypatch):
    c0 = E["evaluation"]["OP1"]["C0 damped persistence (production)"]
    assert not c0["checks"]["high_recall_ok"]
    from app.main import app
    f = json.loads((BACKEND_DIR / "data" / "fi9" / "out" / "forecast.json").read_text())
    monkeypatch.setenv("AIPHEED_NOW", f["issue_date"])
    b = TestClient(app).get("/api/v1/fi9/outlook").json()
    cp = b["class_performance"]
    assert cp["high_caught"] == c0["full"]["tp"] and cp["false_high"] == c0["full"]["fp"] and "high_recall_ok" in cp["requirements_failed"]
    assert b["p_low"] == pytest.approx(1 - b["forecast"]["p_high"], abs=0.005)
    assert "not used to set the outlook" in b["news_context"]["status"]
