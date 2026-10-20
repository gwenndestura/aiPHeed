"""
tests/quality/test_security.py
------------------------------
ISO/IEC 25010 Security (confidentiality, authenticity, accountability). Every admin route rejects a missing token
(401), an expired token (401 token_expired) and a non-admin role (403); the public routes expose no personal data
(feedback respondents' names and e-mails, admin names and e-mails), even after an admin has acted and a respondent
has submitted the survey. Throwaway database (tests/integration/test_api_admin.py `api` fixture), never aipheed.db.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.main import app
from app.services import security
from tests.integration.test_api_admin import FULL_ANSWERS, api, auth_headers, make_user  # noqa: F401

ADMIN_EMAIL, ADMIN_NAME = "analyst@calabarzon.da.gov.ph", "J. Dela Cruz"     # make_user defaults
RESPONDENT = {"fullName": "Maria Respondent Santos", "email": "maria.respondent@example.org",
              "agency": "DA RFO IV-A Survey Unit", "designation": "Agricultural Technologist"}
DUMMY = {"item_id": "rv_2026Q4_quezon", "province_id": "quezon", "quarter": "2026-Q4", "account_id": "1",
         "alert_id": "1"}


def _admin_routes():
    out = []
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith("/api/v1/admin"):
            for m in sorted(getattr(r, "methods", []) or []):
                out.append((m, path.format(**DUMMY)))
    return out


ADMIN_ROUTES = _admin_routes()


def test_there_are_admin_routes():
    assert len(ADMIN_ROUTES) >= 16


def _call(api_, method, path, headers=None):
    return api_.request(method, path, headers=headers or {}, json={} if method in ("POST", "PUT", "PATCH") else None)


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_route_rejects_a_missing_token(api, method, path):
    r = _call(api, method, path)
    assert r.status_code == 401, (method, path, r.status_code)
    assert r.json()["error"]["code"] == "missing_token"


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_route_rejects_an_expired_token(api, method, path):
    make_user(api)
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = jwt.encode({"sub": "1", "email": ADMIN_EMAIL, "name": ADMIN_NAME, "role": "admin", "iss": security.ISSUER,
                        "jti": "expired-test", "ver": 0, "iat": int((past - timedelta(hours=1)).timestamp()),
                        "exp": int(past.timestamp())}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    r = _call(api, method, path, {"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, (method, path, r.status_code)
    assert r.json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_route_rejects_a_non_admin_role(api, method, path):
    make_user(api, role="viewer")
    r = _call(api, method, path, auth_headers(api))
    assert r.status_code == 403, (method, path, r.status_code)
    assert r.json()["error"]["code"] == "forbidden"


PUBLIC_GETS = [
    "/api/v1/health", "/api/v1/config", "/api/v1/quarters", "/api/v1/provinces?quarter=2026-Q4",
    "/api/v1/ranking?quarter=2026-Q4", "/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4",
    "/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q4", "/api/v1/forecast/timeseries?scope=region&id=calabarzon",
    "/api/v1/provinces/quezon/municipalities?quarter=2026-Q4",
    "/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q4",
    "/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q4",
    "/api/v1/news?scope=province&id=quezon&quarter=2026-Q3", "/api/v1/rejections", "/api/v1/rejections?quarter=2026-Q4",
    "/api/v1/alerts", "/api/v1/search?q=que", "/api/v1/report/data?type=trend&scope=region&from=2023-Q1",
    "/api/v1/report/data?type=shap&scope=province&id=quezon&to=2026-Q4", "/api/v1/quarterly/e31/summary",
    "/api/v1/insights/topics",
]


def test_public_routes_expose_no_personal_data(api, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    make_user(api)
    h = auth_headers(api)
    # a respondent submits the survey with personal details, and the admin acts (reject + undo leaves an audit trail;
    # a second rejection stays in place so /rejections has a row)
    assert api.post("/api/v1/feedback", json={"answers": FULL_ANSWERS, "demographics": RESPONDENT,
                                              "liked": "the map"}).status_code == 201
    api.get("/api/v1/admin/review?quarter=2026-Q4", headers=h)
    r = api.post("/api/v1/admin/review/rv_2026Q4_batangas/reject", headers=h,
                 json={"reason": "Data quality issue", "notes": "checked by the analyst"})
    assert r.status_code == 200
    secrets = [ADMIN_EMAIL, ADMIN_NAME, RESPONDENT["fullName"], RESPONDENT["email"], RESPONDENT["agency"],
               RESPONDENT["designation"]]
    checked = 0
    for url in PUBLIC_GETS:
        resp = api.get(url)
        if resp.status_code != 200:
            continue
        body = resp.text.lower()
        leaked = [s for s in secrets if s.lower() in body]
        assert not leaked, (url, leaked)
        checked += 1
    assert checked >= len(PUBLIC_GETS) - 2                    # nearly every public route answered and was checked
    rej = api.get("/api/v1/rejections?quarter=2026-Q4").json()["data"]
    assert [r["provinceId"] for r in rej] == ["batangas"] and set(rej[0]) == {
        "provinceId", "province", "quarter", "reason", "notes", "timestamp"}


def test_public_routes_need_no_token_and_ignore_a_bad_one(api):
    bad = {"Authorization": "Bearer not-a-token"}
    for url in ("/api/v1/provinces?quarter=2026-Q4", "/api/v1/rejections", "/api/v1/alerts"):
        assert api.get(url).status_code == 200 and api.get(url, headers=bad).status_code == 200



def test_rejection_notes_are_public_by_design(api):
    """Observation for the report: the reviewer's free-text rejection note is published on /rejections (schema
    RejectionRow.notes). It names no reviewer, but an admin who types personal details into it would publish them."""
    make_user(api)
    h = auth_headers(api)
    api.get("/api/v1/admin/review?quarter=2026-Q4", headers=h)
    api.post("/api/v1/admin/review/rv_2026Q4_batangas/reject", headers=h,
             json={"reason": "Data quality issue", "notes": "free text written by the reviewer"})
    rows = api.get("/api/v1/rejections?quarter=2026-Q4").json()["data"]
    assert rows[0]["notes"] == "free text written by the reviewer"
