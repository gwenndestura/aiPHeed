"""
tests/integration/test_foodinsecurity_autopublish.py
----------------------------------------------------
Auto-publish (team decision 2026-11-04): with the C-B6 main export served, an issued forecast is public without
administrator approval; an administrator's rejection still withholds it; AIPHEED_AUTO_PUBLISH=0 restores Rule 1 (STAGED
until approved); other exports (C-b) keep Rule 1 by default. HIGH alerts are unaffected (still staged for confirmation).
"""
from __future__ import annotations

import pytest

from app.ml.inference import foodinsecurity_system as FI
from app.services import review as rv


@pytest.fixture
def fi(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    monkeypatch.delenv("AIPHEED_AUTO_PUBLISH", raising=False)
    monkeypatch.setattr(FI, "DATA", FI.MAIN_DATA)
    monkeypatch.setattr(FI, "LGU_VULNERABILITY", FI.MAIN_DATA / "lgu_vulnerability.csv")
    return monkeypatch


def test_default_on_for_cb6_off_for_cb_and_overridable(fi):
    assert FI.auto_publish() is True                         # C-B6 main export
    fi.setattr(FI, "DATA", FI.CB_DATA)
    assert FI.auto_publish() is False                        # C-b: Rule 1 unchanged
    fi.setenv("AIPHEED_AUTO_PUBLISH", "1")
    assert FI.auto_publish() is True
    fi.setattr(FI, "DATA", FI.MAIN_DATA)
    fi.setenv("AIPHEED_AUTO_PUBLISH", "0")
    assert FI.auto_publish() is False


async def test_cb6_forecasts_public_without_approval_rejection_still_withholds(fi, client, test_db):
    from sqlalchemy import select

    from app.db.models import AdminUser, ReviewRecord

    await rv.ensure_rows(test_db, "2027-Q1")
    rows = (await test_db.execute(select(ReviewRecord).where(ReviewRecord.quarter == "2027-Q1"))).scalars().all()
    assert rows and {r.status for r in rows} == {rv.STAGED}   # nobody approved
    assert await rv.rejected_pairs(test_db, "2027-Q1") == set()
    d = (await client.get("/api/v1/provinces", params={"quarter": "2027-Q1"})).json()
    assert all(not x["withheld"] and x["riskScore"] is not None for x in d["data"])
    u = AdminUser(email="t@local.invalid", full_name="Test admin", password_hash="x", role="admin", is_active=True)
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    await rv.reject(test_db, rows[0].id, u, sorted(rv.REJECTION_REASONS)[0])
    assert (rows[0].province_id, "2027-Q1") in await rv.rejected_pairs(test_db, "2027-Q1")


async def test_switch_off_restores_rule_1(fi, test_db):
    fi.setenv("AIPHEED_AUTO_PUBLISH", "0")
    await rv.ensure_rows(test_db, "2027-Q1")
    assert len(await rv.rejected_pairs(test_db, "2027-Q1")) == 5


def test_config_reports_auto_publish(fi):
    from app.services import dashboard as svc
    assert svc.serving_model()["autoPublish"] is True
