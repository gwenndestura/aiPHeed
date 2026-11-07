"""Safeguards of the quarterly E168 regeneration (app.e168.regenerate) and the single feature path for validation and
serving. The heavy forecast itself is exercised by `python -m app.e168.regenerate stage`, not here."""
import inspect
import json

import pandas as pd
import pytest

from app.e168 import lgbm_only, regenerate as RG, serve


def _rows(issue="2026-Q4"):
    from app.fi5.target import qindex, qlabel
    i = qindex(issue)
    return [{"province": p, "lead": l, "target_quarter": qlabel(i + l), "score_pct": 30.0, "range90_pct": [20.0, 40.0],
             "p_high": 0.1, "risk_class": "LOW", "config": "RSS|FULL|prune=False|leaves=3|cal=raw"}
            for l in RG.LEADS for p in sorted(RG.PROVINCES)]


def _dash(rows):
    return pd.DataFrame([{"probability": r["p_high"], "score_pct": r["score_pct"], "model": RG.MODEL_ID} for r in rows])


def test_valid_issue_passes():
    r = _rows()
    RG.validate("2026-Q4", r, _dash(r))


@pytest.mark.parametrize("break_it, msg", [
    (lambda r: r.pop(), "provinces"),
    (lambda r: r[0].update(target_quarter="2026-Q4"), "target"),
    (lambda r: r[0].update(p_high=0.7), "probability/class"),
    (lambda r: r[0].update(p_high=1.5, risk_class="HIGH"), "probability/class"),
    (lambda r: r[0].update(config="logistic"), "LightGBM"),
])
def test_invalid_issue_is_refused(break_it, msg):
    r = _rows()
    break_it(r)
    with pytest.raises(RG.RegenerationError, match=msg):
        RG.validate("2026-Q4", r, _dash(_rows()) if msg == "provinces" else _dash(r))


def test_model_version_mismatch_is_refused():
    r = _rows()
    d = _dash(r)
    d.loc[0, "model"] = "ch1"
    with pytest.raises(RG.RegenerationError, match="model version"):
        RG.validate("2026-Q4", r, d)


def test_existing_issue_is_never_regenerated(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "ISSUES", tmp_path)
    (tmp_path / "2027-Q1").mkdir()
    (tmp_path / "2027-Q1" / "live.json").write_text("{}")
    assert RG.stage("2027-Q1")["status"] == "exists"


def test_concurrent_run_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "ISSUES", tmp_path)
    (tmp_path / ".lock").write_text("2027-Q1")
    assert RG.stage("2027-Q1")["status"] == "already running"


def test_serving_and_validation_build_features_the_same_way():
    """Audit finding: serving used to add E154.add_income before N.add_sources; both now use N.add_sources only (which
    adds the income columns itself), exactly as lgbm_only.task does."""
    src_serve, src_task = inspect.getsource(serve._forecast), inspect.getsource(lgbm_only.task)
    assert "add_income" not in src_serve
    for s in (src_serve, src_task):
        assert "N.add_sources(Pv.add_inputs(S, M.rows_for(S," in s and "N.add_sources(Pv.add_inputs(S, P" in s


def test_outlook_reports_origin_and_threshold():
    o = serve.outlook()
    assert o["origin_date"] == "2026-10-01" and o["classification_threshold"] == 0.5
    assert {r["target_quarter"] for r in o["provinces"]} == {"2027-Q1", "2027-Q2", "2027-Q3"}
