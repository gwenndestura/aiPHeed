"""
tests/integration/test_sws_reissue.py
-------------------------------------
Deployable SWS-release re-issue of Lead-2+ forecasts (app.ml.inference.sws_reissue): manual SWS entry, the
release-triggered update, the window cap, repeated scheduler runs, append-only history, the data cut-off, the
day-by-day replay reproducing P0H4-U, the scheduler switch, and the unchanged served default.
"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.ml.inference import ch1_system as CH1
from app.ml.inference import sws_reissue as RI

ROOT = Path(__file__).resolve().parents[3]
REPLAY = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER" / "out" / "deploy_replay.json"
SERVED = Path(CH1.DATA) / "rows.csv"
FR = Path(CH1.DATA_FR) / "rows.csv"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
Q3_2026 = [("NCR", 27.0, 6.0), ("BL", 23.6, 4.0), ("VIS", 16.0, 6.0), ("MIN", 23.7, 6.0)]


@pytest.fixture
def store(tmp_path):
    """SWS store without the 2026-Q3 release (published 2026-10-14) and a history holding the served 2026-10-01 issue."""
    r = RI.load_sws(RI.SWS_STORE)
    sws = tmp_path / "sws.csv"
    r[r["published"] < "2026-10-14"].to_csv(sws, index=False)
    rows = pd.read_csv(SERVED, dtype={"province_code": str})
    rows = rows[rows["issue_date"] == "2026-10-01"]
    hist = tmp_path / "history.csv"
    assert RI.record_quarter_start(rows, path=hist, recorded_at="2026-10-01") == 20
    return sws, hist


def _enter_q3(sws):
    return [RI.enter_sws_reading(a, "2026-Q3", h, "2026-10-14", "2026-09-27", m, now=date(2026, 10, 14), path=sws)
            for a, h, m in Q3_2026]


def test_manual_entry_validation(store):
    sws, _ = store
    assert _enter_q3(sws) == ["added"] * 4
    assert RI.enter_sws_reading("BL", "2026-Q3", 23.6, "2026-10-14", "2026-09-27", 4.0, now=date(2026, 10, 14), path=sws) == "duplicate"
    bad = [dict(area="XX"), dict(H=120.0), dict(published="2026-11-01"), dict(fw_end="2026-10-20"),
           dict(fw_end="2026-06-01"), dict(H=19.0)]                   # last one: conflicting value for the same round
    for b in bad:
        a = {"area": "BL", "quarter": "2026-Q3", "H": 23.6, "published": "2026-10-14", "fw_end": "2026-09-27", "moe": 4.0, **b}
        with pytest.raises(ValueError):
            RI.enter_sws_reading(a["area"], a["quarter"], a["H"], a["published"], a["fw_end"], a["moe"],
                                 now=date(2026, 10, 14), path=sws)
    assert len(RI.load_sws(sws)) == len(RI.load_sws(RI.SWS_STORE))


def test_release_triggers_reissue_matching_p0h4u(store):
    sws, hist = store
    assert RI.reissue(date(2026, 10, 10), sws_path=sws, path=hist, log_path=None)["rows_added"] == 0
    _enter_q3(sws)
    assert RI.reissue(date(2026, 10, 14), sws_path=sws, path=hist, log_path=None)["rows_added"] == 0   # same day: not yet
    s = RI.reissue(date(2026, 10, 15), sws_path=sws, path=hist, log_path=None)
    assert s["rows_added"] == 15 and s["reissued_origins"] == [{"origin": "2026-Q3", "issue_date": "2026-10-15", "trigger": "sws_release"}]
    h = RI.load_history(hist)
    b = h[h["issue_schedule"] == "B"]
    assert set(b["lead"]) == {2, 3, 4} and (b["sws_q_used"] == "2026-Q3").all() and (b["h_last"] == 23.6).all()
    fr = pd.read_csv(FR, dtype={"province_code": str})
    fr = fr[fr["issue_date"] == "2026-10-15"]
    m = b.merge(fr, left_on=["province_code", "target_quarter"], right_on=["province_code", "quarter"])
    assert len(m) == 15 and (m["probability_x"] - m["probability_y"]).abs().max() < 1e-5


def test_window_cap_without_release(store):
    sws, hist = store
    assert RI.reissue(date(2026, 11, 30), sws_path=sws, path=hist, log_path=None)["rows_added"] == 0
    s = RI.reissue(date(2026, 12, 3), sws_path=sws, path=hist, log_path=None)
    assert s["reissued_origins"] == [{"origin": "2026-Q3", "issue_date": "2026-12-01", "trigger": "window_cap"}]
    b = RI.load_history(hist).query("issue_schedule == 'B'")
    assert (b["sws_q_used"] == "2026-Q2").all()


def test_repeated_runs_add_nothing_and_history_is_append_only(store):
    sws, hist = store
    _enter_q3(sws)
    before = hist.read_bytes()
    RI.reissue(date(2026, 10, 15), sws_path=sws, path=hist, log_path=None)
    after = hist.read_bytes()
    assert after.startswith(before)                                     # earlier rows untouched
    for d in (date(2026, 10, 15), date(2026, 10, 16), date(2026, 12, 2), date(2027, 3, 1)):
        assert RI.reissue(d, sws_path=sws, path=hist, log_path=None)["rows_added"] == 0
    assert hist.read_bytes() == after
    h = RI.load_history(hist)
    assert not h["forecast_id"].duplicated().any() and (h["issue_schedule"] == "A").sum() == 20
    cur = RI.current(date(2026, 10, 20), path=hist)
    assert len(cur) == 20 and set(cur.loc[cur["lead"] >= 2, "issue_date"]) == {"2026-10-15"}
    assert set(RI.current(date(2026, 10, 10), path=hist)["issue_date"]) == {"2026-10-01"}
    b = h[h["issue_schedule"] == "B"]
    assert set(b["supersedes"]) <= set(h.loc[h["issue_schedule"] == "A", "forecast_id"])


def test_no_future_data_enters(store, tmp_path):
    sws, hist = store
    _enter_q3(sws)
    RI.reissue(date(2026, 10, 15), sws_path=sws, path=hist, log_path=None)
    ref = RI.load_history(hist).query("issue_schedule == 'B'")["pi_hunger"].to_numpy()
    # a later, extreme round sitting in the store must not change a forecast issued before it was published
    r = RI.load_sws(sws)
    fut = pd.concat([r, pd.DataFrame([{"area": a, "q": 8107, "H": 90.0, "published": "2027-01-20", "fw_end": "2026-12-15",
                                       "moe": 4.0} for a in RI.AREAS])])
    sws2, hist2 = tmp_path / "sws2.csv", tmp_path / "h2.csv"
    fut.to_csv(sws2, index=False)
    shutil.copy(hist, hist2)
    h2 = RI.load_history(hist2)
    RI._atomic_write(h2[h2["issue_schedule"] == "A"], hist2)
    RI.reissue(date(2026, 10, 15), sws_path=sws2, path=hist2, log_path=None)
    assert (RI.load_history(hist2).query("issue_schedule == 'B'")["pi_hunger"].to_numpy() == ref).all()
    h = RI.load_history(hist)
    assert (h["sws_published_used"].astype(str) < h["issue_date"]).all() and (h["issue_date"] <= "2026-10-15").all()


def test_replay_reproduces_p0h4u_and_is_idempotent():
    if not REPLAY.exists():
        pytest.skip("replay not run")
    r = json.loads(REPLAY.read_text())
    assert r["max_abs_vs_P0H4U_probability"] < 1e-5 and r["issue_dates_equal_S_AB"] and r["reissued_rows"] == 180
    assert r["second_same_day_runs_adding_rows"] == 0 and r["extra_runs_added"] == 0 and r["duplicate_ids"] == 0
    assert r["sws_used_published_before_issue"] and r["quarter_start_rows_intact"]
    assert r["lead2"]["P0H4 + SWS re-issue (deployable)"]["failed"] == ["R6"]   # timing alone does not pass R6


@pytest.mark.legacy_served
def test_scheduler_registers_job_only_when_enabled(monkeypatch):
    pytest.importorskip("apscheduler")
    from app.tasks import scheduler as SCH
    monkeypatch.setattr(SCH, "ENABLED", True)
    for flag, want in (("0", False), ("1", True)):
        monkeypatch.setenv("AIPHEED_SWS_REISSUE", flag)
        monkeypatch.setattr(SCH, "_scheduler", None)
        s = SCH.start_scheduler()
        try:
            assert (SCH.SWS_REISSUE_JOB_ID in {j.id for j in s.get_jobs()}) is want
        finally:
            SCH.shutdown_scheduler()


def test_served_default_unchanged(monkeypatch):
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    monkeypatch.delenv("AIPHEED_SWS_REISSUE", raising=False)
    assert not RI.enabled()
    assert CH1.data_dir().name == "ch1_engine" and CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    assert not RI.HISTORY.exists()                                       # nothing written to the deployed store by tests
