"""E28: the scheduler's jobs exist and import, and the CLI's incremental mode refuses unauthorized quarters."""
import json

import _paths  # noqa: F401
from _paths import EXP


def test_scheduler_registers_the_quarterly_cycle_and_the_daily_news_job(monkeypatch):
    import app.tasks.scheduler as S

    monkeypatch.setattr(S, "ENABLED", True)
    monkeypatch.setattr(S, "_scheduler", None)
    from apscheduler.schedulers.background import BackgroundScheduler

    monkeypatch.setattr(BackgroundScheduler, "start", lambda self, *a, **k: None)
    sch = S.start_scheduler()
    ids = {j.id for j in sch.get_jobs()}
    assert ids == {S.JOB_ID, S.NEWS_JOB_ID}
    S._scheduler = None
    # both job functions import their entry points (the old one imported a module that does not exist)
    import scripts.news_collect  # noqa: F401
    import scripts.quarterly_update  # noqa: F401


def test_incremental_refuses_an_unauthorized_active_quarter(tmp_path, capsys, monkeypatch):
    from scripts import news_collect

    monkeypatch.chdir(EXP / "backend_dev")
    # E31: data are authorized to 2026-10-14 (authorized_until 2026-Q4), so the refusal is tested on 2027-Q1
    code = news_collect.main(["incremental", "--store", str(tmp_path / "s"), "--now", "2027-03-01T10:00:00+08:00"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["requests"] == 0
    runs = [json.loads(l) for l in (tmp_path / "s" / "runs.jsonl").read_text().splitlines()]
    start = [r for r in runs if r["event"] == "start"][0]
    assert start["quarters"] == ["2027-Q1"] and start["refused_quarters"] == ["2027-Q1"]
