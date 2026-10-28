"""
tests/integration/test_sws_reissue_dashboard.py
-----------------------------------------------
End-to-end SWS re-issue: manual entry through the CLI, the scheduler job, the persisted history, the audit API, and
the dashboard routes, which show the forecast in force (issue date, SWS reading, data cut-off) and never a superseded,
not-yet-issued or mismatched one. Every test uses a temporary store (AIPHEED_SWS_REISSUE_DIR) and a pinned clock
(AIPHEED_NOW). Rounds marked SYNTHETIC exist only inside these temporary stores, to exercise supersession.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import sws_reissue as RI

client = TestClient(app)
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
QUEZON = "PH040300000"
Q3_2026 = [("NCR", "27.0", "6"), ("BL", "23.6", "4"), ("VIS", "16.0", "6"), ("MIN", "23.7", "6")]


@pytest.fixture
def env(tmp_path, monkeypatch):
    r = RI.load_sws(RI.SWS_STORE)
    r[r["published"] < "2026-10-14"].to_csv(tmp_path / RI.SWS_STORE.name, index=False)
    monkeypatch.setenv("AIPHEED_SWS_REISSUE_DIR", str(tmp_path))
    monkeypatch.setenv("AIPHEED_SWS_REISSUE", "1")
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)

    def at(day: str):
        monkeypatch.setenv("AIPHEED_NOW", f"{day}T09:00:00")
    at("2026-10-10")
    return tmp_path, at


def _cli(*args) -> int:
    from scripts.sws_reissue import main
    return main(list(args))


def _enter_q3():
    for a, h, m in Q3_2026:
        assert _cli("enter", "--area", a, "--quarter", "2026-Q3", "--H", h, "--published", "2026-10-14",
                    "--fw-end", "2026-09-27", "--moe", m) == 0


def _base():
    p = CH1.data_dir() / "rows.csv"
    return CH1._rows(str(p), p.stat().st_mtime_ns)


def _summary(quarter="2027-Q1"):
    r = client.get("/api/v1/explainability", params={"scope": "province", "id": "quezon", "quarter": quarter})
    assert r.status_code == 200, r.text[:300]
    return r.json()["summary"]


def test_full_path_entry_scheduler_history_api_dashboard(env):
    tmp, at = env
    from app.tasks import scheduler as SCH
    out = SCH.run_sws_reissue()                                   # before the release: records the served issue only
    assert out["quarter_start_rows_recorded"] == len(_base()) and out["rows_added"] == 0
    assert CH1.rows() == _base() and _summary()["issued"] == "2026-10-01"
    at("2026-10-14")
    _enter_q3()                                                   # manual entry on the publication day
    assert SCH.run_sws_reissue()["rows_added"] == 0              # published "today": not before the issue date yet
    at("2026-10-15")
    out = SCH.run_sws_reissue()
    assert out["rows_added"] == 15 and out["reissued_origins"][0]["issue_date"] == "2026-10-15"
    assert SCH.run_sws_reissue()["rows_added"] == 0              # repeated scheduler run: idempotent
    # persistence: quarter-start and re-issue both kept
    h = RI.load_history()
    assert set(h.loc[(h["province_code"] == QUEZON) & (h["target_quarter"] == "2027-Q1"), "issue_date"]) == {"2026-10-01", "2026-10-15"}
    # audit API
    a = client.get("/api/v1/forecast-history", params={"province": QUEZON, "quarter": "2027-Q1"}).json()
    assert a["reissueEnabled"] and [x["issue_date"] for x in a["issues"]] == ["2026-10-01", "2026-10-15"]
    shown = a["shownOnDashboard"][0]
    assert shown["issue_date"] == "2026-10-15" and shown["sws_reading_used"] == "2026-Q3" and shown["data_cutoff"] == "2026-10-15"
    # the dashboard number equals the evaluated P0H4-U re-issue (ch1_engine_fr), not the quarter-start one
    fr = pd.read_csv(Path(CH1.DATA_FR) / "rows.csv", dtype={"province_code": str})
    want = float(fr[(fr["province_code"] == QUEZON) & (fr["quarter"] == "2027-Q1")]["probability"].iloc[0])
    assert shown["probability"] == pytest.approx(want, abs=1e-5)
    s = _summary()
    assert s["issued"] == "2026-10-15" and s["probability"] == pytest.approx(want, abs=1e-4)
    assert "Re-issued 2026-10-15" in s["sentence"] and "published before 2026-10-15" in s["sentence"]
    st = client.get("/api/v1/forecast-history/status").json()
    assert st["historyRows"] == len(_base()) + 15 and st["overlayRefused"] == [] and st["lastRun"]["rows_added"] == 15


def test_clock_never_shows_a_forecast_before_its_issue_date(env):
    _, at = env
    at("2026-10-14")
    _enter_q3()
    at("2026-10-15")
    RI.run_daily()
    assert _summary()["issued"] == "2026-10-15"
    at("2026-10-12")                                              # earlier clock: the re-issue did not exist yet
    assert _summary()["issued"] == "2026-10-01" and CH1.rows() == _base()


def test_newer_release_supersedes_and_history_is_immutable(env):
    tmp, at = env
    at("2026-10-14")
    _enter_q3()
    at("2026-10-15")
    RI.run_daily()
    first = (tmp / RI.HISTORY.name).read_bytes()
    at("2026-11-05")                                              # SYNTHETIC second 2026-Q3 round, temp store only
    assert RI.enter_sws_reading("BL", "2026-Q3", 30.0, "2026-11-05", "2026-10-30", 4.0) == "added"
    at("2026-11-06")
    out = RI.run_daily()
    assert out["rows_added"] == 15 and out["reissued_origins"][0]["issue_date"] == "2026-11-06"
    assert (tmp / RI.HISTORY.name).read_bytes().startswith(first)  # earlier rows byte-identical
    h = RI.history_for(QUEZON, "2027-Q1")
    assert list(h["issue_date"]) == ["2026-10-01", "2026-10-15", "2026-11-06"]
    assert h["supersedes"].iloc[2] == h["forecast_id"].iloc[1] and h["supersedes"].iloc[1] == h["forecast_id"].iloc[0]
    assert _summary()["issued"] == "2026-11-06"
    assert RI.run_daily()["rows_added"] == 0


def test_mismatched_or_future_informed_history_is_refused(env):
    tmp, at = env
    at("2026-10-14")
    _enter_q3()
    at("2026-10-15")
    RI.run_daily()
    hp = tmp / RI.HISTORY.name
    h = RI.load_history(hp)
    b = h["issue_schedule"] == "B"
    bad = h.copy()
    bad.loc[b & (bad["province_code"] == QUEZON), "pi_price"] += 0.1            # not the served model's price part
    bad.loc[b & (bad["province_code"] == "PH040100000"), "sws_published_used"] = "2026-10-15"   # not before issue
    RI._atomic_write(bad, hp)
    refused = CH1.overlay_report()
    assert sum("price part" in x for x in refused) == 3 and sum("not published before" in x for x in refused) == 3
    rows = CH1.rows()
    assert rows[(QUEZON, "2027-Q1")]["issue_date"] == "2026-10-01"             # export kept, never the bad row
    assert rows[("PH040100000", "2027-Q1")]["issue_date"] == "2026-10-01"
    assert rows[("PH040200000", "2027-Q1")]["issue_date"] == "2026-10-15"


def test_a_newer_export_wins_over_an_older_reissue(env):
    tmp, at = env
    at("2026-10-14")
    _enter_q3()
    at("2026-10-15")
    RI.run_daily()
    hp = tmp / RI.HISTORY.name
    h = RI.load_history(hp)
    late = h[(h["issue_schedule"] == "B") & (h["target_quarter"] == "2027-Q1")].copy()
    late["issue_date"] = "2026-09-30"                                         # older than the served 2026-10-01 row
    late["forecast_id"] = late["forecast_id"].str[:-1] + "x"
    RI._atomic_write(pd.concat([h[h["issue_schedule"] == "A"], late]), hp)
    assert all(r["issue_date"] == "2026-10-01" for (c, q), r in CH1.rows().items() if q == "2027-Q1")


def test_disabled_by_default_serves_the_export_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("AIPHEED_SWS_REISSUE", raising=False)
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    monkeypatch.setenv("AIPHEED_SWS_REISSUE_DIR", str(tmp_path))
    assert CH1.rows() == _base() and CH1.state_token() == "" and CH1.overlay_report() == []
    assert client.get("/api/v1/forecast-history/status").json()["reissueEnabled"] is False
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.data_dir().name == "ch1_engine"
