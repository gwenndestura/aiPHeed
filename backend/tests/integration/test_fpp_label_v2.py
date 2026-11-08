"""
tests/integration/test_fpp_label_v2.py
--------------------------------------
Label v2 (Food Price Pressure, exploratory) is served only behind LABEL_VERSION=v2, carries its note, and matches
its frozen inputs; v1 stays the default. Equal province scores share a rank.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
E39 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E39_Label_V2"


def test_v1_is_the_default_and_v2_is_not_served(monkeypatch):
    monkeypatch.delenv("LABEL_VERSION", raising=False)
    r = client.get("/api/v1/fpp/record")
    assert r.status_code == 404 and "LABEL_VERSION=v2" in r.text
    assert client.get("/api/v1/provinces").status_code == 200             # the v1 dashboard is unchanged


def test_v2_record_carries_the_note_and_matches_the_frozen_specs(monkeypatch):
    monkeypatch.setenv("LABEL_VERSION", "v2")
    rec = client.get("/api/v1/fpp/record").json()
    assert rec["name"] == "Food Price Pressure (exploratory)"
    assert "not food insecurity" in rec["note"] and "not adviser-endorsed" in rec["note"]
    assert "tool-adopted default" in rec["note"]
    freeze = json.loads((E39 / "frozen" / "E39_FREEZE.json").read_text())
    assert rec["specs_sha256"] == freeze["sha256"]
    for f, h in freeze["sha256"].items():
        assert hashlib.sha256((E39 / f).read_bytes()).hexdigest() == h
    assert {f["target_quarter"] for f in rec["forecasts"].values()} == {"2026-Q4", "2027-Q1"}
    assert all(v["verdict"] in ("skill shown", "not demonstrated") or v["verdict"].startswith("not evaluable")
               for v in rec["evaluation"].values())


def test_v2_pdf_is_the_record(monkeypatch):
    monkeypatch.setenv("LABEL_VERSION", "v2")
    rec = client.get("/api/v1/fpp/record").json()
    r = client.get("/api/v1/fpp/report.pdf")
    assert r.status_code == 200 and r.headers["X-Record-SHA256"] == rec["content_sha256"]
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == rec["content_sha256"]
    assert "not food" in r.headers["X-Label-Note"]


def test_equal_scores_share_a_rank():
    rows = client.get("/api/v1/provinces?quarter=2023-Q1&horizon=forecast").json()["data"]
    scores = {}
    for r in rows:
        scores.setdefault(r["riskScore"], set()).add(r["rank"])
    for s, ranks in scores.items():
        assert len(ranks) == 1, (s, ranks)                               # one rank per distinct score
    tied = [r for r in rows if sum(1 for o in rows if o["riskScore"] == r["riskScore"]) > 1]
    assert all(r["rankTied"] for r in tied)
    assert all(r["rank"] == 1 + sum(1 for o in rows if o["riskScore"] > r["riskScore"]) for r in rows)
