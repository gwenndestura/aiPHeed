"""E83: the monthly refresh records every step, survives a failing step, and never touches served records."""
import json

from app.tasks import scheduler as S


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "news_e31").mkdir(parents=True)
    (tmp_path / "data" / "news_e31" / "articles.jsonl").write_text(json.dumps(
        {"article_key": "k1", "title": "Rice prices rise in Laguna", "source_domain": "example.org",
         "ph_date": "2026-09-01"}) + "\n", encoding="utf-8")


def test_monthly_refresh_logs_success(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    from app.news import lead_extractor as LX
    monkeypatch.setattr(LX, "extract", lambda arts, out: {"no_method": len(arts)})
    monkeypatch.setattr(S, "run_quarterly_cycle", lambda: {"exit_code": 0})
    out = S.run_monthly_refresh()
    assert out["ok"] and out["steps"]["lead_text"]["counts"] == {"no_method": 1}
    log = [json.loads(l) for l in (tmp_path / S.REFRESH_LOG).read_text(encoding="utf-8").splitlines()]
    assert len(log) == 1 and log[0]["ok"]


def test_monthly_refresh_failure_is_recorded_not_raised(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    from app.news import lead_extractor as LX

    def boom(*a, **k):
        raise TimeoutError("publisher unreachable")
    monkeypatch.setattr(LX, "extract", boom)
    monkeypatch.setattr(S, "run_quarterly_cycle", lambda: {"exit_code": 0})
    out = S.run_monthly_refresh()
    assert not out["ok"]
    assert out["steps"]["lead_text"]["ok"] is False and "publisher unreachable" in out["steps"]["lead_text"]["error"]
    assert out["steps"]["cycle"]["ok"] is True          # the other step still ran


def test_monthly_job_is_registered_monthly():
    assert S.MONTHLY_DAY == "10" and S.MONTHLY_JOB_ID
