"""E70 (2026-10-20): the thesis backend discloses the E70 outcome in its existing text fields only; nothing served
(scores, classes, ranks, model) changes, and the summary file is a required artifact (no silent fallback)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import thesis_system as T

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
SCORE = ROOT / "aipheed-backend-aligned" / "experiments" / "E70_Objectives_Completion" / "out" / "score.json"


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _summary(q, slug, scope="province"):
    r = client.get("/api/v1/explainability", params={"scope": scope, "id": slug, "quarter": q})
    assert r.status_code == 200, r.text[:300]
    return r.json()["summary"]


def test_summary_file_matches_score_and_is_required():
    s, e = json.loads(SCORE.read_text(encoding="utf-8")), T.e70_summary()
    g = s["decision"]["goal_80"]
    assert e["goal_80"] == {k: g[k] for k in e["goal_80"]} and e["goal_80"]["met"] is False
    assert e["candidates_passing_rule"] == [] and T.E70_SUMMARY in T.REQUIRED


def test_performance_sentences_disclose_e70():
    s = T.performance_tables()["sentences"][-1]
    assert s.startswith("E70 (2026-10-20)") and "36/50 = 0.72" in s and "80% Lead-2 goal is NOT met" in s
    assert "not food-insecurity accuracy" in s


def test_region_summary_flags_all_high_and_goal(thesis):
    reg = _summary("2027-Q1", "calabarzon", "region")
    text = reg["sentence"]
    assert "All 5 provinces are HIGH" in text and "compare the index values and ranks" in text
    assert "neither the 75% nor the 80% Lead-2 accuracy goal is demonstrated" in text


def test_mixed_quarter_has_no_all_high_note(thesis):
    reg = _summary("2025-Q2", "calabarzon", "region")             # Laguna LOW in FIRI v2 history
    assert "provinces are HIGH;" not in reg["sentence"]
