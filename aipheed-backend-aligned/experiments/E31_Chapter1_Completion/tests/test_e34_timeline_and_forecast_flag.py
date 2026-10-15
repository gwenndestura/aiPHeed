"""E34 regression tests (D1, D2): the served timeline lists every quarter in range and explains each gap; isForecast follows
the E31 row's mode. Runs against backend_dev, or against the promoted backend/ with AIPHEED_TEST_BACKEND."""
import pytest

import _paths  # noqa: F401

fastapi_tc = pytest.importorskip("fastapi.testclient")


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    """In-memory database (as backend/tests/conftest.py): the app's default database is never opened."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.db.database import Base
    from app.dependencies import get_db
    from app.main import app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
                                 connect_args={"check_same_thread": False})
    session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    yield fastapi_tc.TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    mp.chdir(_paths.BD)
    mp.delenv("AIPHEED_DATA_LAYER", raising=False)
    yield mp
    mp.undo()


def _idx(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


@pytest.mark.parametrize("horizon", ["forecast", "nowcast"])
def test_timeline_has_no_silent_gaps(client, horizon):
    qs = client.get("/api/v1/quarters", params={"horizon": horizon}).json()["quarters"]
    idx = [_idx(x["id"]) for x in qs]
    assert idx == list(range(idx[0], idx[0] + len(idx)))
    for x in qs:
        if x["state"] == "unavailable":
            assert x["reason"] and "not a low score" in x["reason"] or "nowcast view" in x["reason"], x
        else:
            assert x.get("reason") is None


def test_supplementary_sws_quarters_are_explained(client):
    qs = {x["id"]: x for x in client.get("/api/v1/quarters", params={"horizon": "forecast"}).json()["quarters"]}
    for q in ("2025-Q2", "2025-Q3"):
        assert qs[q]["state"] == "unavailable" and "supplementary" in qs[q]["reason"]
        r = client.get("/api/v1/provinces", params={"quarter": q, "horizon": "forecast"})
        assert r.status_code == 404                     # no score is invented for an unavailable quarter


def test_forecast_view_never_shows_the_nowcast_value(client):
    qs = {x["id"]: x for x in client.get("/api/v1/quarters", params={"horizon": "forecast"}).json()["quarters"]}
    assert qs["2026-Q4"]["state"] == "unavailable" and qs["2027-Q1"]["state"] == "forecast"


def test_is_forecast_matches_config_forecast_quarters(client):
    fq = set(client.get("/api/v1/config").json()["quarterRange"]["forecastQuarters"])
    assert fq == {"2026-Q4", "2027-Q1"}
    for horizon in ("forecast", "nowcast"):
        series = client.get("/api/v1/forecast/timeseries",
                            params={"scope": "province", "id": "quezon", "horizon": horizon}).json()["series"]
        flagged = {p["quarter"] for p in series if p["isForecast"]}
        assert flagged == fq & {p["quarter"] for p in series}
        assert flagged, horizon
    one = client.get("/api/v1/forecast", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"}).json()
    assert one["isForecast"] is True
    old = client.get("/api/v1/forecast", params={"scope": "province", "id": "quezon", "quarter": "2026-Q3"}).json()
    assert old["isForecast"] is False


def test_alert_flag_needs_an_administrator_confirmation(client):
    """E34 D3: a high score alone never makes an alert; only a CONFIRMED alert for the area and quarter does."""
    import asyncio

    from app.db.models import AlertRecord
    from app.dependencies import get_db
    from app.main import app

    def fc(scope, id_):
        return client.get("/api/v1/forecast", params={"scope": scope, "id": id_, "quarter": "2027-Q1"}).json()

    assert fc("region", "calabarzon")["riskScore"] >= 0.60 and fc("region", "calabarzon")["alert"] is False
    assert fc("province", "quezon")["riskScore"] >= 0.60 and fc("province", "quezon")["alert"] is False

    async def add(code, confirmed, dismissed=False):
        agen = app.dependency_overrides[get_db]()
        db = await agen.__anext__()
        db.add(AlertRecord(quarter="2027-Q1", province_code=code, threshold_exceeded=True, confirmed=confirmed,
                           dismissed=dismissed, alert_reason="REGIONAL_HUNGER_HIGH"))
        await db.commit()
        await agen.aclose()

    asyncio.run(add("PH040000000", confirmed=False))          # staged: still not public
    assert fc("region", "calabarzon")["alert"] is False
    asyncio.run(add("PH040000000", confirmed=True))           # confirmed regional alert
    assert fc("region", "calabarzon")["alert"] is True
    assert fc("province", "quezon")["alert"] is False          # never copied onto the five provinces
    asyncio.run(add("PH040300000", confirmed=True))           # confirmed Quezon alert
    assert fc("province", "quezon")["alert"] is True
    assert fc("municipality", "quezon-sariaya")["alert"] is True
    assert fc("province", "batangas")["alert"] is False
