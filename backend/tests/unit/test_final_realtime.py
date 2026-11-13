"""Real-time quarterly forecasting of the served model (app.final): quarter transitions, horizon, history, outcomes, cycle,
sources, API. A controllable clock (the `now` argument) simulates future quarters; nothing waits for the calendar."""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.final import cycle as CY
from app.final import history as HI
from app.final import period as PD
from app.final import sources as SR

CFG = {**PD.serving(), "max_lead": 2, "validated_max_lead": 2, "issue_rule": {"month_of_quarter": 2, "day": 1}}
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


# ------------------------------------------------------------------ quarter detection and transitions
@pytest.mark.parametrize("now,cal,issue,targets", [
    ("2026-12-15T09:00", "2026-Q4", "2026-Q4", ["2027-Q1", "2027-Q2"]),
    ("2027-01-15T09:00", "2027-Q1", "2026-Q4", ["2027-Q1", "2027-Q2"]),     # Q4 -> Q1 across the year: before the issue day
    ("2027-02-01T00:00", "2027-Q1", "2027-Q1", ["2027-Q2", "2027-Q3"]),     # issue day of Q1
    ("2027-04-30T23:59", "2027-Q2", "2027-Q1", ["2027-Q2", "2027-Q3"]),     # Q1 -> Q2
    ("2027-05-01T00:00", "2027-Q2", "2027-Q2", ["2027-Q3", "2027-Q4"]),
    ("2027-08-01T08:00", "2027-Q3", "2027-Q3", ["2027-Q4", "2028-Q1"]),     # Q2 -> Q3; targets cross the year
    ("2027-11-01T08:00", "2027-Q4", "2027-Q4", ["2028-Q1", "2028-Q2"]),     # Q3 -> Q4
    ("2028-02-02T08:00", "2028-Q1", "2028-Q1", ["2028-Q2", "2028-Q3"]),
])
def test_quarter_transitions(now, cal, issue, targets):
    p = PD.period(now, CFG)
    assert (p["current_quarter"], p["issue_quarter"], p["forecast_quarters"]) == (cal, issue, targets)


def test_philippine_timezone_decides_the_issue():
    assert PD.period("2027-01-31T15:59:00+00:00", CFG)["issue_quarter"] == "2026-Q4"      # 23:59 in Manila
    assert PD.period("2027-01-31T16:00:00+00:00", CFG)["issue_quarter"] == "2027-Q1"      # 00:00 1 Feb in Manila
    assert PD.period("2027-01-01T00:00", CFG)["current_quarter"] == "2027-Q1"            # naive = Philippine time


def test_target_status_past_current_future():
    p = PD.period("2027-01-15T09:00", CFG)
    assert [t["status"] for t in p["targets"]] == ["current", "future"]
    assert PD.status_of("2026-Q4", "2027-Q1") == "past"


def test_horizon_follows_the_validated_lead_time():
    assert PD.period("2027-02-01", {**CFG, "max_lead": 1})["forecast_quarters"] == ["2027-Q2"]
    with pytest.raises(ValueError):
        PD.period("2027-02-01", {**CFG, "max_lead": 3})                                 # beyond the validated lead time
    with pytest.raises(ValueError):
        PD.period("2027-02-01", {**CFG, "max_lead": 0})


def test_next_issue_date_moves_with_the_clock():
    assert PD.period("2027-01-15", CFG)["next_issue_date"].startswith("2027-02-01")
    assert PD.period("2027-02-15", CFG)["next_issue_date"].startswith("2027-05-01")
    assert PD.period("2027-12-15", CFG)["next_issue_date"].startswith("2028-02-01")


# ------------------------------------------------------------------ helpers: a stand-in issue (no model run)
def fake_issue(root: Path, issue: str, version="m1", share=20.0) -> Path:
    d = root / issue
    d.mkdir(parents=True)
    i = PD.quarter_index(issue)
    rows = [{"province_code": f"PH0{n}", "province": p, "quarter": PD.label(i + L), "lead": L, "probability": 0.01 * (n + 1),
             "class": "LOW", "score_pct": share + n, "range90_low": share - 5, "range90_high": share + 15}
            for L in (1, 2) for n, p in enumerate(PROV)]
    pd.DataFrame(rows).to_csv(d / "dashboard_rows.csv", index=False)
    (d / "manifest.json").write_text(json.dumps({"issue_quarter": issue, "information_cutoff": PD.issue_datetime(issue, CFG).date().isoformat(),
                                                 "generated_utc": "2027-01-01T00:00:00+00:00", "model_id": CFG["model_id"],
                                                 "model_sha256": version * 32, "data_version": {"tag": "d" + issue}}))
    (d / "live.json").write_text("{}")
    return d


@pytest.fixture
def env(tmp_path, monkeypatch):
    led, runs, lock, issues = tmp_path / "ledger.jsonl", tmp_path / "runs.jsonl", tmp_path / ".lock", tmp_path / "issues"
    monkeypatch.setattr(HI, "LEDGER", led)
    monkeypatch.setattr(PD, "serving", lambda: CFG)
    monkeypatch.setattr(SR, "STATUS", tmp_path / "src_status.json")
    monkeypatch.setattr(SR, "LOG", tmp_path / "src_log.jsonl")
    monkeypatch.setattr(SR, "DIR", tmp_path)
    built = []

    def build(issue):
        built.append(issue)
        return fake_issue(issues, issue)

    def run(now, **kw):
        return CY.run(now, skip_data=True, update_sources=lambda n: {}, build_issue=kw.pop("build", build), ledger=led, runs=runs, lock=lock, **kw)
    return {"led": led, "runs": runs, "lock": lock, "issues": issues, "built": built, "run": run, "tmp": tmp_path}


# ------------------------------------------------------------------ cycle: issue, archive, duplicates, repeated runs
def test_cycle_issues_once_per_quarter_and_archives_the_previous(env):
    r1 = env["run"]("2026-12-01T07:00")
    assert r1["status"] == "issued" and r1["issue_quarter"] == "2026-Q4"
    for _ in range(3):                                                    # the scheduler fires again: nothing new
        assert env["run"]("2026-12-20T07:00")["status"] == "up to date"
    assert env["run"]("2027-01-20T07:00")["status"] == "up to date"        # new calendar quarter, before its issue day
    r2 = env["run"]("2027-02-01T06:30")
    assert r2["status"] == "issued" and r2["issue_quarter"] == "2027-Q1"
    assert env["built"] == ["2026-Q4", "2027-Q1"]
    f = HI.forecasts(env["led"])
    assert len(f) == 20                                                   # 2 issues x 5 provinces x 2 leads, no duplicates
    assert {r["issue_quarter"] for r in f} == {"2026-Q4", "2027-Q1"}       # the Q4 2026 issue is kept, not overwritten
    q1 = [r for r in f if r["target_quarter"] == "2027-Q2"]
    assert sorted(r["issue_quarter"] for r in q1) == ["2026-Q4"] * 5 + ["2027-Q1"] * 5   # both forecasts of 2027-Q2 stay identifiable
    assert HI.verify(env["led"])["ok"]


def test_cycle_status_reports_staleness_and_generation(env):
    env["run"]("2026-12-01T07:00")
    st = CY.status("2027-02-03T10:00", ledger=env["led"], runs=env["runs"])
    assert st["issue_quarter"] == "2027-Q1" and st["served_issue_quarter"] == "2026-Q4" and st["stale"]
    assert "2026-Q4" in st["stale_reason"] and st["served_generated_utc"]


def test_failed_run_keeps_the_last_valid_issue(env):
    env["run"]("2026-12-01T07:00")

    def boom(issue):
        raise RuntimeError("PSA download timed out")
    r = env["run"]("2027-02-02T07:00", build=boom)
    assert r["status"] == "failed" and "timed out" in r["error"]
    assert HI.latest_issue(CFG["model_id"], env["led"]) == "2026-Q4"
    st = CY.status("2027-02-02T08:00", ledger=env["led"], runs=env["runs"])
    assert st["stale"] and st["last_run"]["status"] == "failed"
    assert env["run"]("2027-02-03T07:00")["status"] == "issued"            # retried on the next scheduled run


def test_new_survey_round_stops_the_issue(env):
    from app.final.issue import RetrainingRequired

    def stale(issue):
        raise RetrainingRequired("training rows changed")
    assert env["run"]("2026-12-01T07:00", build=stale)["status"] == "retraining required"
    assert HI.forecasts(env["led"]) == []


def test_concurrent_run_is_skipped(env):
    env["lock"].write_text("busy")
    assert env["run"]("2026-12-01T07:00")["status"] == "skipped"
    assert HI.forecasts(env["led"]) == []


def test_issue_built_but_not_recorded_is_recorded_not_rebuilt(env, monkeypatch):
    d = fake_issue(env["issues"], "2026-Q4")
    r = CY.run("2026-12-01T07:00", skip_data=True, update_sources=lambda n: {}, build_issue=lambda q: d, ledger=env["led"], runs=env["runs"], lock=env["lock"])
    assert r["status"] == "issued" and len(HI.forecasts(env["led"])) == 10


# ------------------------------------------------------------------ history integrity and model versions
def test_history_refuses_to_overwrite_and_keeps_model_versions(env):
    from app.final import issue as IS
    rows = IS.ledger_rows(fake_issue(env["issues"], "2026-Q4", version="a"))
    assert HI.record_issue(rows, env["led"]) == {"appended": 10, "already_recorded": 0}
    assert HI.record_issue(rows, env["led"]) == {"appended": 0, "already_recorded": 10}
    changed = [{**r, "p_high": 0.9} for r in rows]
    with pytest.raises(HI.HistoryError):
        HI.record_issue(changed, env["led"])
    rows2 = IS.ledger_rows(fake_issue(env["issues"], "2027-Q1", version="b"))
    HI.record_issue(rows2, env["led"])
    v = {(r["issue_quarter"], r["model_version"]) for r in HI.forecasts(env["led"])}
    assert v == {("2026-Q4", "a" * 16), ("2027-Q1", "b" * 16)}


def test_tampering_is_detected(env):
    from app.final import issue as IS
    HI.record_issue(IS.ledger_rows(fake_issue(env["issues"], "2026-Q4")), env["led"])
    lines = env["led"].read_text().splitlines()
    rec = json.loads(lines[3]); rec["p_high"] = 0.99
    lines[3] = json.dumps(rec)
    env["led"].write_text("\n".join(lines) + "\n")
    assert not HI.verify(env["led"])["ok"]


# ------------------------------------------------------------------ outcomes: association, no automatic correctness
def test_outcome_association_and_evaluation(env):
    from app.final import issue as IS
    HI.record_issue(IS.ledger_rows(fake_issue(env["issues"], "2026-Q4")), env["led"])
    w = HI.with_outcomes(path=env["led"])
    assert all(r["validation_status"] == "awaiting outcome" and r["correct"] is None for r in w)
    with pytest.raises(HI.HistoryError):
        HI.record_outcome("Quezon", "2027-Q1", 55.0, "FNRI", "abc", "someone", path=env["led"])     # no full hash
    HI.record_outcome("Quezon", "2027-Q1", 55.0, "FNRI ENNS provincial HFIAS", "f" * 64, "DA reviewer", path=env["led"])
    HI.record_outcome("Batangas", "2027-Q1", 20.0, "FNRI ENNS provincial HFIAS", "f" * 64, "DA reviewer", path=env["led"])
    w = {(r["province"], r["target_quarter"]): r for r in HI.with_outcomes(path=env["led"])}
    q = w[("Quezon", "2027-Q1")]
    assert q["validation_status"] == "validated" and q["observed_class"] == "HIGH" and q["correct"] is False
    assert q["error_pp"] == pytest.approx((20.0 + 3) - 55.0)
    assert w[("Batangas", "2027-Q1")]["correct"] is True
    assert w[("Cavite", "2027-Q1")]["validation_status"] == "awaiting outcome"
    ev = HI.evaluation(path=env["led"])
    assert ev["overall"]["n"] == 2 and ev["overall"]["FN"] == 1 and ev["overall"]["TN"] == 1 and ev["awaiting_outcome"] == 8
    assert set(ev["by_lead"]) == {"1"}


# ------------------------------------------------------------------ data sources: missing data, failures, retries
def test_source_failure_keeps_previous_data_and_is_retried(env):
    calls = {"n": 0}

    def flaky(today):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("PSA OpenSTAT unreachable")
        return {"status": "ok", "newest": "2027-01"}
    f = {"psa_cpi": flaky, "noaa_oni": lambda t: {"status": "ok", "newest": "NDJ 2026"}}
    r = SR.update("2027-01-10T06:30", fetchers=f)
    assert r["psa_cpi"]["status"] == "failed" and r["noaa_oni"]["status"] == "ok"
    st = {s["id"]: s for s in SR.status("2027-01-10T07:00")}
    assert st["psa_cpi"]["consecutive_failures"] == 1 and st["psa_cpi"]["due_now"] and not st["noaa_oni"]["due_now"]
    r = SR.update("2027-01-11T06:30", fetchers=f)                          # retried next run; ONI not due again yet
    assert r["psa_cpi"]["status"] == "ok" and "noaa_oni" not in r
    assert {s["id"]: s for s in SR.status("2027-01-11T07:00")}["psa_cpi"]["consecutive_failures"] == 0


def test_annual_sources_are_not_fetched_every_quarter(env):
    n = {"k": 0}
    f = {"psa_grdp_aff": lambda t: (n.__setitem__("k", n["k"] + 1) or {"status": "ok"})}
    SR.update("2027-01-10", fetchers=f); SR.update("2027-01-20", fetchers=f); SR.update("2027-02-15", fetchers=f)
    assert n["k"] == 2                                                    # every 30 days, not on every run


# ------------------------------------------------------------------ API: dashboard retrieval of history and periods
def test_api_returns_current_and_historical_forecasts(env, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import final_realtime as API
    from app.final import issue as IS
    HI.record_issue(IS.ledger_rows(fake_issue(env["issues"], "2026-Q4")), env["led"])
    HI.record_issue(IS.ledger_rows(fake_issue(env["issues"], "2027-Q1")), env["led"])
    monkeypatch.setenv("AIPHEED_NOW", "2027-03-01T09:00")
    monkeypatch.setattr(CY, "RUNS", env["runs"])
    app = FastAPI(); app.include_router(API.router, prefix="/api/v1")
    c = TestClient(app)
    p = c.get("/api/v1/forecast-period").json()
    assert p["current_quarter"] == "2027-Q1" and p["served_issue_quarter"] == "2027-Q1" and not p["stale"]
    assert [t["quarter"] for t in p["served_targets"]] == ["2027-Q2", "2027-Q3"]
    h = c.get("/api/v1/final/forecast-history").json()
    assert h["issues"] == ["2026-Q4", "2027-Q1"] and h["count"] == 20 and h["ledger"]["ok"]
    st = {r["issue_quarter"]: r["issue_status"] for r in h["forecasts"]}
    assert st == {"2026-Q4": "historical", "2027-Q1": "current issue"}
    assert {r["target_status"] for r in h["forecasts"] if r["target_quarter"] == "2027-Q1"} == {"current"}
    one = c.get("/api/v1/final/forecast-history", params={"province": "Laguna", "target": "2027-Q2"}).json()
    assert one["count"] == 2 and {r["issue_quarter"] for r in one["forecasts"]} == {"2026-Q4", "2027-Q1"}
    assert c.get("/api/v1/forecast-evaluation").json()["overall"] == {"n": 0}
    assert c.post("/api/v1/internal/forecast-cycle").status_code == 401
    monkeypatch.setenv("AIPHEED_CRON_TOKEN", "x" * 32)
    assert c.post("/api/v1/internal/forecast-cycle", headers={"Authorization": "Bearer wrong"}).status_code == 401


# ------------------------------------------------------------------ database mirror (migration f6a7b8c9d0e1)
def test_database_mirror_inserts_once_and_never_overwrites(env, tmp_path):
    import subprocess, sys, os
    from sqlalchemy import create_engine, text
    from app.final import dbsync as DB, issue as IS
    db = tmp_path / "m.db"
    url = f"sqlite+aiosqlite:///{db.as_posix()}"
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env={**os.environ, "DATABASE_URL": url},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    env["run"]("2026-12-01T07:00")
    first = DB.sync(url, env["led"], env["runs"], tmp_path / "none.jsonl")
    assert first["forecasts"] == 10 and first["runs"] == 1
    again = DB.sync(url, env["led"], env["runs"], tmp_path / "none.jsonl")
    assert again == {"forecasts": 0, "outcomes": 0, "runs": 0, "sources": 0}
    env["run"]("2027-02-01T07:00")
    DB.sync(url, env["led"], env["runs"], tmp_path / "none.jsonl")
    with create_engine(f"sqlite:///{db.as_posix()}").connect() as c:
        assert c.execute(text("SELECT COUNT(*), COUNT(DISTINCT issue_quarter) FROM final_forecast_history")).one() == (20, 2)


# ------------------------------------------------------------------ Poverty and Vulnerability on the explanation cards
@pytest.mark.parametrize("pid", ["calabarzon", "quezon", "rizal"])
def test_poverty_and_vulnerability_is_shown_only_when_the_forecast_used_it(pid):
    from app.final import shap_api as SA
    d = SA.province(pid, "2027-Q1")
    shown = any(x["key"] == "poverty" for x in d["groups"])
    used = any(SA.group_of(c["feature"]) == "poverty" for c in d["contributors"])
    assert shown == used                                                  # never a 0% placeholder for an unused group
    assert sum(x["pct"] for x in d["groups"]) + d["otherPct"] in range(99, 102)


def test_outlook_of_the_served_issue_has_the_model_fields():
    """Regression: the 2026-Q4 issue file has no acceptance_basis / accuracy_by_lead; the outlook must still answer (they come
    from the model's files), so the dashboard does not fall back to the old labels."""
    from app.final import serving as SVG
    from app.hcw import serve as SV
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    o = SV.outlook()
    assert o["issue_quarter"] == "2026-Q4" and o["acceptance_basis"].startswith("Leads 1-2")
    assert o["accuracy_by_lead"]["1"]["accuracy"] == pytest.approx(0.861)
    assert {(p["province"], p["lead"]) for p in o["provinces"]} == {(p, L) for p in PROV for L in (1, 2)}


def test_visualization_explanation_and_pdf_match_the_dashboard():
    """The Visualization page's chart (/explainability) and its PDF (/report/data) show FINAL's own groups, numbers and words:
    the same as the dashboard cards (/final/shap) and the outlook, never another model's grouping or a probability."""
    import json
    from app.final import report_data as FRD
    from app.final import serving as SVG
    from app.final import shap_api as SA
    from app.hcw import serve as SV
    from app.services import dashboard as D
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    from app.services import reference as ref
    for pid in ("quezon", "rizal"):
        code = ref.PROVINCES[pid]["code"]
        e, s = D.explainability(code, "2027-Q1"), SA.province(pid, "2027-Q1")
        assert e["model"] == "final-rate-mind-1.0" and e["otherPct"] == s["otherPct"]
        assert [(t["key"], t["label"], t["pct"]) for t in e["triggers"]] == [(g["key"], g["label"], g["pct"]) for g in s["groups"]]
    assert D.explainability_region("2027-Q1")["model"] == "final-rate-mind-1.0"

    share = {(p["province"], p["target_quarter"]): p["score_pct"] for p in SV.outlook()["provinces"]}
    r = FRD.drivers("quezon", "2027-Q1")
    text = json.dumps(r)
    assert "Setup H" not in text and "probability" not in text.lower()
    head = next(b for b in r["blocks"] if b["kind"] == "table")
    assert head["rows"][0][1].startswith(f"{share[('Quezon', '2027-Q1')]}%")
    bars = next(b for b in r["blocks"] if b["kind"] == "figure")["chart"]["bars"]
    assert [b["label"] for b in bars[:-1]] == [g["label"] for g in SA.province("quezon", "2027-Q1")["groups"][:5]]
    assert "Poverty (PSA" not in text
    assert sum(b["pct"] for b in bars) in range(99, 102)

    t = FRD.trend("region", None, "2027-Q1", "2027-Q2")
    tab = next(b for b in t["blocks"] if b["kind"] == "table")
    row = next(x for x in tab["rows"] if x[0] == "Quezon")
    assert row[1:3] == [f"{share[('Quezon', '2027-Q1')]}%", f"{share[('Quezon', '2027-Q2')]}%"]
    fig = next(b for b in t["blocks"] if b["kind"] == "figure")["chart"]
    assert fig["yFormat"] == "percent" and fig["lines"][0]["value"] == 0.5
    with pytest.raises(KeyError):
        FRD.trend("region", None, "2026-Q1", "2026-Q2")                   # outside the served quarters: no invented values


def test_news_panel_lists_every_story_the_served_issue_read():
    """The news count is the stories FINAL read (3 months before the cut-off: provinces, region, Luzon, national), not a
    province-tagged subset; regression for 307 -> 49."""
    import json
    from app.final import serving as SVG
    from app.services import dashboard as D
    issue = SVG.ROOT / "issues" / "2026-Q4"
    assert SVG.activate(issue)["active"]
    doc = json.loads((issue / "news_used.json").read_text(encoding="utf-8"))
    n = D.news(None, "2027-Q1", 1, 5)
    assert n["articleCount"] == len(doc["stories"]) == 307
    assert n["provinceAttributed"] == doc["counts"]["province"]                  # 64 stories about a specific province
    assert (doc["from"], doc["to"]) == ("2026-08-01", "2026-10-31")


# ------------------------------------------------------------------------------------------- full-system audit 2026-11-14
def test_an_issue_cannot_use_figures_published_after_its_cut_off(monkeypatch):
    """C1: the 2026-Q4 issue used October CPI / September LFS released after 1 November (E168 refresh rule). An issue now
    refuses to build unless only figures online before its cut-off count."""
    from app.final import issue as IS
    from app.e168 import live_data as LD
    monkeypatch.setenv("AIPHEED_LIVE_ASOF", "2027-02-01")
    monkeypatch.setenv("AIPHEED_LIVE_PUBLISHED", "2027-02-08")
    with pytest.raises(IS.IssueError, match="published up to 2027-02-08"):
        IS.check_information_rule("2027-Q1")
    monkeypatch.delenv("AIPHEED_LIVE_PUBLISHED")
    IS.check_information_rule("2027-Q1")                                  # strict: published-by = cut-off
    assert LD._live_dates()[1] == LD._live_dates()[0]
    monkeypatch.setenv("AIPHEED_LIVE_ASOF", "2026-11-01")
    with pytest.raises(IS.IssueError, match="not the issue cut-off"):
        IS.check_information_rule("2027-Q1")


def test_the_cycle_never_carries_a_later_published_by_date(env, monkeypatch):
    import os
    seen = {}
    monkeypatch.setenv("AIPHEED_LIVE_PUBLISHED", "2099-01-01")

    def stage(as_of, published):
        seen["pub"] = os.environ.get("AIPHEED_LIVE_PUBLISHED")
        return {}
    CY.run("2027-02-01T07:00", update_sources=lambda n: {}, refresh_data=stage, build_issue=lambda q: fake_issue(env["issues"], q),
           ledger=env["led"], runs=env["runs"], lock=env["lock"])
    assert seen["pub"] is None                                            # a stray later published-by date is dropped


def test_issue_disclosure_reaches_every_surface():
    """C1 disclosure for the served 2026-Q4 issue: outlook, forecast period, history and both PDFs state it."""
    import json
    from app.final import period as PD
    from app.final import report_data as FRD
    from app.final import serving as SVG
    from app.hcw import serve as SV
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    assert PD.published_by("2026-Q4") == "2026-11-08" and "October 2026 consumer prices" in PD.issue_note("2026-Q4")
    assert PD.published_by("2027-Q1") == "2027-02-01" and PD.issue_note("2027-Q1") is None
    o = SV.outlook()
    assert o["data_published_by"] == "2026-11-08" and o["issue_note"] and "as published by 2026-11-08" in o["information_cutoff"]
    t = json.dumps(FRD.trend("region", None, "2027-Q1", "2027-Q2"))
    assert "as published by 8 November 2026" in t and "About the data" in t


def test_town_panel_shows_the_poverty_value_the_rank_used():
    """L1: Lucena showed a 16.8% 'province substitute' while its rank used PSA's own 2021 City of Lucena figure (10%)."""
    import pandas as pd
    from app.e145 import lgu as L
    from app.final import serving as SVG
    from app.services import dashboard as D
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    V = pd.read_csv(L.BASE, dtype={"lgu_psgc": str})
    used = dict(zip(V["lgu_psgc"].str.zfill(9), V["poverty_incidence_2021"]))
    M = D.municipality_summary("2027-Q1")
    assert len(M) == 142
    assert all(abs(m["povertyValueUsed"] - used[m["lguCode"]]) < 1e-9 for m in M)
    luc = next(m for m in M if m["name"] == "Lucena")
    assert luc["povertyRate"] == 10.0 and "substitute" not in (luc["povertyEstimateKind"] or "")
    assert all("probability" not in m["riskLevelBasis"] and "probability" not in m["disaggregationLabel"] for m in M)


def test_rows_endpoint_horizon_note_is_finals_own():
    from app.final import serving as SVG
    from app.ml.inference import hcw_system as HS
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    assert "Lead 18" not in HS.horizon()["why_not_longer"] and "Lead 3" in HS.horizon()["why_not_longer"]


def test_pdf_population_matches_the_dashboard():
    """Quezon's PDF headline read 1,980,338 (PSA province row, without Lucena); the dashboard and the 41 towns sum to 2,260,669."""
    from app.final import report_data as FRD
    from app.final import serving as SVG
    from app.services import dashboard as D
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    towns = sum(m["population"] for m in D.municipality_summary("2027-Q1", province_id="quezon"))
    head = next(b for b in FRD.drivers("quezon", "2027-Q1")["blocks"] if b["kind"] == "table")
    row = next(r for r in head["rows"] if r[0].startswith("Population"))
    assert row[1] == f"{towns:,}" == "2,260,669"


def test_harvest_period_shown_is_the_one_the_inputs_used():
    """The panel said Oct 2025-Sep 2026; the 45-day rule (app.e137.features._published_quarters) gives Q3 2025-Q2 2026."""
    from app.final import serving as SVG
    from app.ml.inference import hcw_system as HS
    assert SVG.activate(SVG.ROOT / "issues" / "2026-Q4")["active"]
    it = next(i for i in HS.data_used()["items"] if i["name"] == "Rice and corn harvest")
    assert it["when"] == "Jul 2025–Jun 2026" and it["period"].startswith("Q3 2025 to Q2 2026")
