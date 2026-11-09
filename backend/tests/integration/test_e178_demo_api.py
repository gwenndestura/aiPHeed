"""E178 Part A: the scenario / demo endpoints are admin-only and labelled, and the real endpoints never serve synthetic rows
(docs/e178/PROTOCOL.md, Rules 1-3)."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from app.e178 import common as K
from app.main import app
from app.paths import BACKEND_DIR
from app.services.security import require_admin

c = TestClient(app)
SUMMARY = K.SYN / "scenarios_summary.json"
needs_data = pytest.mark.skipif(not SUMMARY.exists(), reason="python -m app.e178.scenarios run not run")
MARKERS = ("is_synthetic", "scenario_id", "SYNTHETIC", "generator_seed", "e178")
REAL = ["/api/v1/final/food-insecurity/outlook", "/api/v1/provinces?quarter=2027-Q1", "/api/v1/ranking?quarter=2027-Q1",
        "/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1", "/api/v1/provinces/quezon/municipalities?quarter=2027-Q1",
        "/api/v1/forecast?scope=province&id=quezon&quarter=2027-Q1", "/api/v1/alerts", "/api/v1/config"]


@pytest.fixture
def as_admin():
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.parametrize("path", ["/api/v1/demo/scenarios", "/api/v1/demo/scenarios/S0", "/api/v1/demo/scenarios/S4"])
def test_demo_routes_need_an_admin_login(path):
    assert c.get(path).status_code == 401


@needs_data
def test_demo_index_is_labelled(as_admin):
    j = c.get("/api/v1/demo/scenarios").json()
    assert j["synthetic"] is True and j["label"] == "SYNTHETIC – FOR DEMONSTRATION"
    assert [s["id"] for s in j["scenarios"]] == ["S0", "S1", "S2", "S3", "S4", "S5"]
    assert j["production"]["model_id"] == "e168-lgbm-1.0"


@needs_data
@pytest.mark.parametrize("sid", ["S0", "S1", "S2", "S3", "S4", "S5", "s3"])
def test_every_scenario_is_labelled(as_admin, sid):
    j = c.get(f"/api/v1/demo/scenarios/{sid}").json()
    assert j["synthetic"] is True and j["label"] == K.LABEL and j["id"] == sid.upper()


@needs_data
def test_unknown_scenario_is_404(as_admin):
    assert c.get("/api/v1/demo/scenarios/S9").status_code == 404


@pytest.mark.parametrize("path", REAL)
def test_real_endpoints_never_return_synthetic_rows(path):
    r = c.get(path)
    text = r.text
    for m in MARKERS:
        assert m not in text, f"{path} contains {m!r}"


def test_outlook_still_equals_the_production_artifact():
    from app import registry as R
    j = c.get("/api/v1/final/food-insecurity/outlook").json()
    p = R.production()
    live = json.loads((BACKEND_DIR / p["artifact_path"]).read_text())
    served = set(live["served_leads"])
    want = [r for r in live["provinces"] if r["lead"] in served]
    got = j.get("forecast", j).get("provinces") if isinstance(j.get("forecast", j), dict) else None
    got = got if got is not None else j.get("provinces")
    assert got == want


def test_only_the_demo_route_imports_e178():
    """No real API, service or inference module reads E178 code or its synthetic files."""
    bad = []
    for sub in ("api", "services", "ml", "e168", "quarterly", "registry"):
        for p in (BACKEND_DIR / "app" / sub).rglob("*.py"):
            s = p.read_text(encoding="utf-8", errors="replace")
            # code references only (imports, quoted paths); comments that mention E178 do not count
            if re.search(r"app\.e178|from app import e178|[\"']data/e178|/ ?[\"']e178[\"']", s) and p.name != "demo.py":
                bad.append(str(p.relative_to(BACKEND_DIR)))
    assert bad == []


def test_strict_model_check_still_passes(monkeypatch):
    from app.main import strict_model_check
    monkeypatch.setenv("AIPHEED_STRICT_MODEL", "1")
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    strict_model_check()                      # raises if E168 is not served in strict mode
