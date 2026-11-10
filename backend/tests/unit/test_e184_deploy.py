"""E184 deployment (docs/e184/PROTOCOL.md): with E168 in production the dashboard adapter is unchanged; once the owner
promotes E184 (simulated here with a temporary registry), the dashboard, outlook and strict check serve E184 with its own
name and accuracy, and the monthly E168 refresh no longer promotes over it."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from app import registry as R
from app.e168 import live_refresh as LR
from app.e168 import serve as SV
from app.ml.inference import e168_system as E
from app.ml.inference import map_engine as M

E184 = "e184-lgbm-syn50-1.0"


def _clear():
    for f in (E._rows_path, E._evaluation, E._relabels, E._production):
        f.cache_clear()


def test_with_e168_in_production_nothing_changes():
    _clear()
    assert E.served_id() == "e168-lgbm-1.0" and E.active()
    s = "Serving e168-lgbm-1.0 (E168 LightGBM food-insecurity risk) on the dashboard (strict)"
    assert E.relabel(s) is s
    assert M.indicator() is E.INDICATOR and M.RISK_LEVEL_BASIS == E.RISK_LEVEL_BASIS
    assert M.evaluation()["model"] == "e168-lgbm-1.0" and M.evaluation()["seal_sha256"] == "f8228fae"
    assert LR._other_production() is None


@pytest.fixture
def e184_in_production(tmp_path, monkeypatch):
    _clear()
    issue = tmp_path / "issue"
    issue.mkdir()
    rows = pd.read_csv(E.rows_path())
    rows["model"] = E184
    rows.to_csv(issue / "dashboard_rows.csv", index=False)
    live = json.loads(SV.artifact().read_text())
    live["model"] = E184
    (issue / "live.json").write_text(json.dumps(live))
    H = json.loads((E.DATA / "lead_horizon.json").read_text())
    H["leads"] = {k: v for k, v in H["leads"].items() if k in ("1", "2", "3")}
    H["leads"]["1"] |= {"accuracy": 0.792, "correct": 57}
    out = tmp_path / "out"
    out.mkdir()
    (out / "lead_horizon.json").write_text(json.dumps(H))
    (out / "sealed_enns2022.json").write_text("{}")
    regdir = tmp_path / "registry"
    regdir.mkdir()
    sha = R.file_sha256(issue / "live.json")
    reg = {"production": {"model_id": E184, "version": "test", "artifact_path": str(issue / "live.json"), "artifact_file_sha256": sha,
                          "approved_utc": "2026-11-10T00:00:00+00:00"}, "models": {}, "history": []}
    (regdir / "registry.json").write_text(json.dumps(reg))
    monkeypatch.setattr(R, "DIR", regdir)
    monkeypatch.setattr(R, "REGISTRY", regdir / "registry.json")
    monkeypatch.setattr(R, "APPROVALS", regdir / "approvals")
    monkeypatch.setattr(E, "E184_DATA", out)
    _clear()
    yield
    _clear()


def test_after_promotion_the_dashboard_serves_e184(e184_in_production):
    assert E.served_id() == E184 and E.active() and E.not_served_reasons() == []
    ev = M.evaluation()
    assert ev["model"] == E184 and ev["leads"]["1"]["metrics"]["accuracy"] == 0.792 and ev["seal_sha256"] != "f8228fae"
    ind = M.indicator()
    assert "E184" in ind["name"] and "E168" not in ind["name"] and "79.2%" in ind["caveat"] and "75.0% at one quarter" not in ind["caveat"]
    assert "E168" not in M.RISK_LEVEL_BASIS and "E184" in M.RISK_LEVEL_BASIS
    assert E.relabel("E168 (e168-lgbm-1.0)") == "E184 (e184-lgbm-syn50-1.0)"
    assert all(r["model"] == E184 for r in E.rows().values())
    assert SV.artifact().name == "live.json" and SV.outlook()["model"] == E184
    assert LR._other_production() == E184            # the monthly E168 refresh stages but does not promote over E184


def test_outlook_route_has_a_server_for_e184():
    from app.api.v1 import registry as API
    assert API.PRODUCTION_SERVERS[E184] == ("app.e168.serve", "outlook")
