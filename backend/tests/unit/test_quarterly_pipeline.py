"""
The quarterly self-update (Rule 1): scheduler timing, stage ordering, failure
handling, the single-run lock, and the gate that decides whether a retrained
model replaces the one in service.

Stages are stubbed: these tests check the orchestration, not the fetchers or
the model, and must not touch the network or the served files.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import pytest

from app.config import settings
from app.tasks import quarterly_pipeline as qp
from app.tasks import scheduler

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every path the runner writes at a temp dir."""
    monkeypatch.setattr(qp, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(qp, "LOCK_PATH", tmp_path / "runs" / ".lock")
    calls: list[str] = []

    def stub(name, result="done", exc=None):
        def fn(ctx):
            calls.append(name)
            if exc:
                raise exc
            return result
        return fn

    stubs = {name: stub(name) for name in qp.STAGES}
    monkeypatch.setattr(qp, "STAGE_FUNCS", stubs)
    return tmp_path, calls, stubs, stub


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def test_default_schedule_is_quarterly_two_weeks_into_the_quarter():
    trig = scheduler.build_trigger()
    fires, t = [], datetime(2026, 10, 10, tzinfo=trig.timezone)
    for _ in range(4):
        t = trig.get_next_fire_time(None, t)
        fires.append(t)
        t = t.replace(minute=1)
    assert [(f.year, f.month, f.day, f.hour) for f in fires] == [
        (2026, 10, 15, 2), (2027, 1, 15, 2), (2027, 4, 15, 2), (2027, 7, 15, 2)]
    assert str(fires[0].tzinfo) == "Asia/Manila"


def test_scheduler_registers_the_job_and_reports_next_run(monkeypatch):
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", True)
    try:
        sched = scheduler.start()
        assert sched is not None and sched.get_job(scheduler.JOB_ID) is not None
        st = scheduler.status()
        assert st["enabled"] is True and st["nextRun"] is not None
        assert st["schedule"] == settings.PIPELINE_CRON
    finally:
        scheduler.shutdown()


def test_scheduler_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", False)
    assert scheduler.start() is None
    assert scheduler.status()["enabled"] is False


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def test_stages_run_in_thesis_order_and_record_is_written(sandbox):
    tmp, calls, _, _ = sandbox
    record = qp.run(trigger="test")
    assert calls == list(qp.STAGES)
    assert record.status == "succeeded"
    latest = qp.load_latest_run()
    assert latest["run_id"] == record.run_id
    assert [s["name"] for s in latest["stages"]] == list(qp.STAGES)
    assert not qp.LOCK_PATH.exists()


def test_a_source_outage_warns_and_the_run_continues(sandbox, monkeypatch):
    tmp, calls, stubs, stub = sandbox
    stubs["news"] = stub("news", exc=RuntimeError("feed down"))
    record = qp.run(trigger="test")
    assert calls == list(qp.STAGES)
    assert record.status == "completed_with_warnings"
    assert {s.name: s.status for s in record.stages}["news"] == "warning"


def test_a_failed_panel_never_retrains(sandbox):
    tmp, calls, stubs, stub = sandbox
    stubs["panel"] = stub("panel", exc=RuntimeError("no CPI"))
    record = qp.run(trigger="test")
    assert "retrain" not in calls
    by_name = {s.name: s.status for s in record.stages}
    assert by_name["panel"] == "failed" and by_name["retrain"] == "skipped"
    assert record.status == "failed"


def test_only_one_run_at_a_time(sandbox):
    qp.LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    qp.LOCK_PATH.write_text("123")
    with pytest.raises(qp.PipelineBusy):
        qp.run(trigger="test")


# ---------------------------------------------------------------------------
# Promotion gate
# ---------------------------------------------------------------------------

SERVED = ROOT / "models" / "thesis_food_insecurity_model.joblib"


@pytest.mark.skipif(not SERVED.exists(), reason="served model not present")
def test_the_served_bundle_passes_validation():
    bundle = qp.validate_bundle(SERVED)
    assert 0 < bundle["threshold"] < 1


@pytest.mark.skipif(not SERVED.exists(), reason="served model not present")
def test_a_lightgbm_only_bundle_is_rejected(tmp_path):
    """train_thesis_model.py's output would crash ThesisPredictor; never promote it."""
    full = joblib.load(SERVED)
    broken = {"model": full["lgbm_model"], "threshold": 0.5}
    path = tmp_path / "lgbm_only.joblib"
    joblib.dump(broken, path)
    with pytest.raises(qp.StageFailed, match="missing"):
        qp.validate_bundle(path)


def test_promotion_archives_the_previous_model(tmp_path):
    served = tmp_path / "served.joblib"
    served.write_bytes(b"old")
    candidate = tmp_path / "candidate.joblib"
    candidate.write_bytes(b"new")
    archived = qp.promote(candidate, served=served, archive_dir=tmp_path / "archive")
    assert served.read_bytes() == b"new"
    assert archived is not None and archived.read_bytes() == b"old"


def test_a_refresh_never_erases_stored_values(tmp_path):
    import pandas as pd
    path = tmp_path / "t.parquet"
    pd.DataFrame({"province_code": ["A", "A"], "quarter": ["2026-Q1", "2026-Q2"],
                  "food_cpi": [100.0, 101.0], "poverty": [9.0, 9.5]}).to_parquet(path)
    fresh = pd.DataFrame({"province_code": ["A", "A"], "quarter": ["2026-Q2", "2026-Q3"],
                          "food_cpi": [101.4, 102.0], "poverty": [None, None]})
    qp._upsert_parquet(path, fresh, ["province_code", "quarter"])
    out = pd.read_parquet(path).set_index("quarter")
    assert list(out.index) == ["2026-Q1", "2026-Q2", "2026-Q3"]   # old row kept
    assert out.loc["2026-Q2", "food_cpi"] == 101.4                 # revision applied
    assert out.loc["2026-Q2", "poverty"] == 9.5                    # missing never erases
    assert path.with_suffix(".pre_pipeline.parquet").exists()      # backup written


def test_throttled_news_collection_times_out_softly(monkeypatch):
    """Google News back-offs must not starve the retrain: a timeout is a warning."""
    import subprocess

    def slow(args, timeout):
        raise subprocess.TimeoutExpired(cmd=args, timeout=timeout)

    monkeypatch.setattr(qp, "_run_script", slow)
    with pytest.raises(qp.StageFailed, match="budget"):
        qp.stage_news({})
    assert "news" not in qp.HARD_STAGES
