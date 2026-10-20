"""
tests/integration/test_alignment_flags.py
-----------------------------------------
Paper-alignment switches, off by default except A3:
  A1 AIPHEED_DSWD_NOTIFY_EMAIL         one email to DSWD 4A when an admin confirms an alert (Rule 7, p.49)
  A2 AIPHEED_REQUIRE_APPROVAL=1        unapproved province forecasts are withheld like rejected ones (p.67)
  A3 AIPHEED_COMPOSED_SELF_DESCRIPTION served engine name / why-served composed from the active record; ON by default
     since E53 became the default (the stored E53 text says "the default system serves E49"); =0 serves the stored text
  A4 AIPHEED_SCHEDULER_DRY_RUN=1, deploy/scheduler.env.example   one cycle in a temporary copy, nothing written
Flag off = the outputs the app gave before the flag existed; flag on = the new behaviour. No served probability
changes either way.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from app.db.models import AlertRecord, AuditRecord
from tests.conftest import _clear_dashboard_caches
from tests.integration.test_api_admin import api, auth_headers, make_user  # noqa: F401  (fixture + helpers)

Q = "2026-Q4"
PROVINCE_IDS = ["cavite", "laguna", "quezon", "rizal", "batangas"]


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    for v in ("AIPHEED_DSWD_NOTIFY_EMAIL", "AIPHEED_REQUIRE_APPROVAL", "AIPHEED_COMPOSED_SELF_DESCRIPTION",
              "AIPHEED_SCHEDULER_DRY_RUN"):
        monkeypatch.delenv(v, raising=False)
    yield
    _clear_dashboard_caches()                       # no flag-on text may stay cached for later tests


def _scores(api_, quarter=Q):
    return {p["id"]: p["riskScore"] for p in api_.get(f"/api/v1/provinces?quarter={quarter}").json()["data"]}


def _admin(api_):
    make_user(api_)
    return auth_headers(api_)


# =====================================================================================================  A1
def _add_alert(api_, code="PH040300000", quarter=Q) -> int:
    async def go():
        async with api_.session_factory() as db:
            row = AlertRecord(quarter=quarter, province_code=code, threshold_exceeded=True,
                              alert_reason="ROLLING_THRESHOLD", prev_risk_probability=0.89, risk_delta=0.02)
            db.add(row)
            await db.commit()
            return row.id

    return asyncio.run(go())


def _audit_actions(api_) -> list[tuple[str, str | None]]:
    from sqlalchemy import select

    async def go():
        async with api_.session_factory() as db:
            return [(r.action, r.notes) for r in (await db.scalars(select(AuditRecord))).all()]

    return asyncio.run(go())


@pytest.fixture
def sent(monkeypatch):
    calls = []
    from app.api.v1 import alerts

    monkeypatch.setattr(alerts.mailer, "send_email", lambda to, subject, body: calls.append((to, subject, body)))
    return calls


def test_a1_off_confirm_sends_nothing(api, sent):
    h = _admin(api)
    a = _add_alert(api)
    assert api.post(f"/api/v1/admin/alerts/{a}/confirm", headers=h).status_code == 200
    assert sent == []
    assert [x for x, _ in _audit_actions(api) if x == "notify_dswd"] == []


def test_a1_on_confirm_sends_once_and_is_audited(api, sent, monkeypatch):
    monkeypatch.setenv("AIPHEED_DSWD_NOTIFY_EMAIL", "dswd4a@example.gov.ph")
    h = _admin(api)
    staged, dismissed = _add_alert(api), _add_alert(api, code="PH040100000")
    assert sent == []                                                          # staging never notifies
    assert api.post(f"/api/v1/admin/alerts/{dismissed}/dismiss", headers=h).status_code == 200
    assert sent == []                                                          # dismissal never notifies
    r = api.post(f"/api/v1/admin/alerts/{staged}/confirm", headers=h)
    assert r.status_code == 200 and r.json()["data"][0]["confirmed"] is True
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == "dswd4a@example.gov.ph" and subject == "aiPHeed early warning confirmed: Quezon, 2026-Q4"
    assert "not an official food insecurity classification" in body and "+0.02" in body
    notes = [n for x, n in _audit_actions(api) if x == "notify_dswd"]
    assert notes == [f"to dswd4a@example.gov.ph: {subject}"]
    api.post(f"/api/v1/admin/alerts/{staged}/confirm", headers=h)              # a repeat does not notify again
    assert len(sent) == 1


# =====================================================================================================  A2
def test_a2_off_nothing_withheld_and_outputs_unchanged(api):
    from app.services import dashboard as svc

    data = api.get(f"/api/v1/provinces?quarter={Q}").json()["data"]
    assert not any(p["withheld"] for p in data)
    assert {p["id"]: p["riskScore"] for p in data} == {p["id"]: p["riskScore"] for p in svc.province_summary(Q)}
    assert api.get(f"/api/v1/rejections?quarter={Q}").json()["data"] == []
    assert api.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={Q}").status_code == 200
    assert api.get(f"/api/v1/report/data?type=trend&scope=region&from=2025-Q1").status_code == 200
    region = api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}").json()
    assert region["riskScore"] == svc.region_forecast(Q)["riskScore"]


def test_a2_on_unapproved_is_withheld_everywhere(api, monkeypatch):
    monkeypatch.setenv("AIPHEED_REQUIRE_APPROVAL", "1")
    data = api.get(f"/api/v1/provinces?quarter={Q}").json()["data"]
    assert all(p["withheld"] and p["riskScore"] is None for p in data)
    rej = api.get(f"/api/v1/rejections?quarter={Q}").json()["data"]
    assert sorted(r["provinceId"] for r in rej) == sorted(PROVINCE_IDS)
    assert {r["reason"] for r in rej} == {"Awaiting DA approval"}
    r = api.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={Q}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "forecast_withheld"
    assert api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}").json()["riskScore"] is None
    assert api.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={Q}").status_code == 404
    assert api.get(f"/api/v1/explainability?scope=region&id=calabarzon&quarter={Q}").status_code == 404
    lgus = api.get(f"/api/v1/provinces/quezon/municipalities?quarter={Q}").json()["data"]
    assert lgus and all(m["riskIndex"] is None for m in lgus)
    assert api.get("/api/v1/report/data?type=shap&scope=province&id=quezon&to=2026-Q4").status_code == 404


def test_a2_on_approved_province_is_public_and_alone_in_the_mean(api, monkeypatch):
    monkeypatch.setenv("AIPHEED_REQUIRE_APPROVAL", "1")
    from app.services import dashboard as svc

    h = _admin(api)
    api.get(f"/api/v1/admin/review?quarter={Q}", headers=h)
    assert api.post("/api/v1/admin/review/rv_2026Q4_quezon/approve", headers=h).status_code == 200
    data = {p["id"]: p for p in api.get(f"/api/v1/provinces?quarter={Q}").json()["data"]}
    served = {p["id"]: p["riskScore"] for p in svc.province_summary(Q)}
    assert data["quezon"]["riskScore"] == served["quezon"] and not data["quezon"]["withheld"]
    assert all(data[s]["withheld"] for s in PROVINCE_IDS if s != "quezon")
    region = api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}").json()
    assert region["riskScore"] == served["quezon"] and region["provincesIncluded"] == 1
    assert api.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={Q}").status_code == 200
    assert api.get(f"/api/v1/explainability?scope=province&id=cavite&quarter={Q}").status_code == 404
    rej = api.get(f"/api/v1/rejections?quarter={Q}").json()["data"]
    assert "quezon" not in {r["provinceId"] for r in rej} and len(rej) == 4


def test_a2_probabilities_identical_flag_on_or_off(api, monkeypatch):
    from app.services import dashboard as svc

    before = {p["id"]: p["riskScore"] for p in svc.province_summary(Q)}
    monkeypatch.setenv("AIPHEED_REQUIRE_APPROVAL", "1")
    assert {p["id"]: p["riskScore"] for p in svc.province_summary(Q)} == before


# =====================================================================================================  A3
def test_a3_off_serves_the_stored_text(api, monkeypatch):
    monkeypatch.setenv("AIPHEED_COMPOSED_SELF_DESCRIPTION", "0")
    _clear_dashboard_caches()
    stored = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))["served_engine"]
    s = api.get("/api/v1/quarterly/e31/summary").json()
    assert s["served_engine"] == stored and "served_engine_as_stored" not in s
    conf = api.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={Q}").json()["confidenceStatement"]
    assert stored["name"] in conf


def test_a3_on_composes_accurate_text_without_changing_numbers(api, monkeypatch):
    rec = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
    monkeypatch.setenv("AIPHEED_COMPOSED_SELF_DESCRIPTION", "0")
    _clear_dashboard_caches()
    before = _scores(api)
    monkeypatch.delenv("AIPHEED_COMPOSED_SELF_DESCRIPTION")              # the default: composed
    _clear_dashboard_caches()                       # set at startup in production; mid-test here
    s = api.get("/api/v1/quarterly/e31/summary").json()
    se = s["served_engine"]
    assert se["name"] == ("aiPHeed-E53-A1 (LightGBM: E48-A1 inputs + measured driver conditions, shrinkage "
                          "calibration)")
    assert se["why_served"].startswith("Served by default.")
    assert "default system serves E49" not in se["why_served"] and "PREVIEW" not in se["evidence_status"]
    assert "0.785 (51/65)" in se["why_served"] and         "is not demonstrated (95% date-bootstrap interval 0.646 to 0.908)" in se["why_served"]
    assert se["config"] == rec["served_engine"]["config"] and s["served_engine_as_stored"] == rec["served_engine"]
    conf = api.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={Q}").json()["confidenceStatement"]
    assert "- PREVIEW" not in conf and se["name"] in conf
    assert _scores(api) == before                                             # no served probability changes
    assert hashlib.md5(Path("data/e53/e53_record.json").read_bytes()).hexdigest() ==         "fa3d0a51939fae66d87bf77c3d15d738"


def test_a3_on_preview_records_keep_preview(api, serve_e49):
    se = api.get("/api/v1/quarterly/e31/summary").json()["served_engine"]
    assert se["name"].endswith("- PREVIEW")
    assert se["why_served"].startswith("Preview, served only when AIPHEED_RECORD=e49; the default serves the E53 record.")
    assert "is demonstrated (95% date-bootstrap interval 0.769 to 0.923)" in se["why_served"]


# =====================================================================================================  A4
WATCH = ["data/e49", "data/e53", "data/e36", "data/e48"]


def _snapshot():
    from app.tasks import scheduler as S

    out = {}
    for rel in list(S.DRY_RUN_COPY) + WATCH:
        p = Path(rel)
        files = [p] if p.is_file() else (sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [])
        out.update({str(f): hashlib.md5(f.read_bytes()).hexdigest() for f in files})
    return out


def test_a4_dry_run_cycle_writes_nothing():
    from app.tasks import scheduler as S

    before = _snapshot()
    rep = S.run_quarterly_cycle(dry_run=True)
    assert rep["dry_run"] is True and rep["update"]["status"] in ("READY", "BLOCKED", "WAITING", "PARTIAL") \
        and "inbox" in rep
    assert not Path(rep["root"]).exists()                                       # the temporary copy is removed
    assert _snapshot() == before                                                # nothing under backend/ changed


def test_a4_env_dry_run_flag_routes_the_scheduled_job(monkeypatch):
    from app.tasks import scheduler as S

    monkeypatch.setattr(S, "run_cycle_dry", lambda *a, **k: {"dry_run": True})
    monkeypatch.setenv("AIPHEED_SCHEDULER_DRY_RUN", "1")
    assert S.run_quarterly_cycle() == {"dry_run": True}


def test_a4_schedule_defaults_unchanged_and_env_example():
    from app.tasks import scheduler as S

    assert (S.CRON_MONTHS, S.CRON_DAY, S.CRON_HOUR, S.ENABLED) == ("1,4,7,10", "15", "3", False)
    text = Path("deploy/scheduler.env.example").read_text(encoding="utf-8")
    for line in ("AIPHEED_ENABLE_SCHEDULER=1", "AIPHEED_QUARTERLY_CRON_MONTHS=1,4,7,10",
                 "AIPHEED_QUARTERLY_CRON_DAY=15", "AIPHEED_QUARTERLY_CRON_HOUR=2"):
        assert line in text.splitlines()
