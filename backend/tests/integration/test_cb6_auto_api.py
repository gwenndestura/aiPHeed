"""A forecast added by the automatic update reaches the real API: the served model's indicator, and withheld until approved."""
from __future__ import annotations

import shutil

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.cb6_auto import job as J
from app.main import app
from app.ml.inference import foodinsecurity_system as FI
from app.services import dashboard as svc

client = TestClient(app)


def _clear_caches():
    for name in dir(svc):
        fn = getattr(svc, name)
        if callable(fn) and hasattr(fn, "cache_clear"):
            fn.cache_clear()


@pytest.fixture
def added(tmp_path, monkeypatch):
    """The export plus a 2027-Q2 forecast written by the job's own row writer, on a clock inside 2027-Q1."""
    for f in ("rows.csv", "evaluation.json", "lgu_vulnerability.csv"):
        shutil.copyfile(FI.MAIN_DATA / f, tmp_path / f)
    rows = pd.read_csv(tmp_path / "rows.csv", dtype=str).fillna("")
    new = rows[rows["quarter"] == "2027-Q1"].to_dict("records")
    for r in new:
        r.update(quarter="2027-Q2", issue_date="2027-01-01", origin="2026-Q4", cfg="frozen:f718ea6d")
    J.append_served(tmp_path / "rows.csv", new)
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-09T05:00:00+08:00")
    monkeypatch.setattr(FI, "DATA", tmp_path)
    _clear_caches()
    yield tmp_path
    _clear_caches()


def test_new_quarter_is_described_as_the_served_model(added):
    assert FI.covers("2027-Q2")
    assert svc.indicator_for("2027-Q2")["id"] == FI.indicator()["id"] == "regional_food_insecurity_forecast"


def test_new_quarter_is_released_automatically(added):
    r = client.get("/api/v1/provinces", params={"quarter": "2027-Q2"})
    assert r.status_code == 200
    body = r.json()
    assert body["indicator"]["id"] == "regional_food_insecurity_forecast"
    assert len(body["data"]) == 5 and all(p["riskScore"] is not None and not p["withheld"] for p in body["data"])


def test_frozen_forecast_says_so_in_its_text(added):
    row = FI.row("PH040300000", "2027-Q2")
    assert "frozen at origin 2026-Q3" in FI.reliability_text(row)
    assert "frozen at origin" not in FI.reliability_text(FI.row("PH040300000", "2027-Q1"))
