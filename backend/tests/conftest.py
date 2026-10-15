import pytest
import pytest_asyncio
import numpy as np
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.db.database import Base
from app.dependencies import get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Creates a fresh in-memory SQLite DB for each test.
    All tables created before test and dropped after.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncTestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncTestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """
    Provides a test HTTP client using the test DB.
    Overrides real get_db with test DB session.
    """
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_model():
    """
    Mock LightGBM model fixture.
    Returns a simple object with predict and predict_proba methods.
    """
    class MockModel:
        def predict(self, X):
            return np.zeros(len(X), dtype=int)

        def predict_proba(self, X):
            return np.column_stack([
                np.full(len(X), 0.7),
                np.full(len(X), 0.3),
            ])

    return MockModel()


@pytest.fixture
def mock_shap_values():
    """Mock SHAP values fixture."""
    return np.random.rand(5, 32)

# ---------------------------------------------------------------------------
# E34: tests of the serving path that the E31 promotion replaced
# ---------------------------------------------------------------------------
# On 2026-10-15 (E34, branch e34-main-app-integration) the corrected E31 pipeline was promoted into backend/ as the
# researcher authorized on 2026-10-14. The dashboard now serves the E31 record (PCF21 nowcast/forecast, development
# backtests, the scored 2026-Q3); the E20 forecast quarters, the food-availability LightGBM, its majority-class /
# seasonal-persistence baselines and the plain-language report built on them are no longer served. The tests below
# assert that superseded behaviour, not a property of the served system; each is listed with its reason rather than
# deleted. The served path is tested by the E31 suite run against this backend
# (AIPHEED_TEST_BACKEND=backend, aipheed-backend-aligned/experiments/E31_Chapter1_Completion/tests) and the live E2E.
# Restoring the legacy path needs the data/processed artefacts deleted on 2026-10-15 (E33 git-clean incident).
_E20 = "asserts the E20 forecast-quarter / two-model contract (is_forecast_quarter, originQuarter, E20 horizon edges)"
_LEGACY_MODEL = ("asserts the legacy food-availability LightGBM (its target name, majority-class and seasonal-"
                 "persistence baselines, seasonal/series_history driver groups)")
_PLAIN = "plain-language report built on the E20 path (report_data/plain_report call dashboard.is_forecast_quarter)"
E34_SUPERSEDED = {
    "test_api_dashboard.py::test_quarters_reports_only_scorable_quarters": _E20,
    "test_api_dashboard.py::test_forecast_quarter_is_labelled_and_has_no_qoq": _E20,
    "test_api_dashboard.py::test_every_forecast_carries_what_the_number_means": _LEGACY_MODEL,
    "test_api_dashboard.py::test_accuracy_is_served_with_its_baselines": _LEGACY_MODEL,
    "test_api_dashboard.py::test_seasonal_and_history_groups_are_not_dropped": _LEGACY_MODEL,
    "test_api_dashboard.py::test_config_describes_both_models": _E20,
    "test_api_dashboard.py::test_both_horizons_reach_the_same_edge": _E20,
    "test_api_dashboard.py::test_neither_horizon_scores_past_the_panel_edge": _E20,
    "test_api_report.py::test_forecast_quarter_report_is_refused_not_mislabelled": _E20,
    "test_api_report.py::test_report_states_what_the_number_is_not": _LEGACY_MODEL,
    "test_api_report.py::test_report_quotes_accuracy_with_its_baselines": _LEGACY_MODEL,
    "test_api_report.py::test_report_declares_it_is_a_nowcast": _E20,
    "test_plain_report.py::test_single_quarter_region_has_no_trend_section": _PLAIN,
    "test_plain_report.py::test_two_quarter_province_trend": _PLAIN,
    "test_plain_report.py::test_withheld_results_never_appear": _PLAIN,
    "test_report_data.py::test_trend_payload_is_ascii_and_structured": _PLAIN,
    "test_report_data.py::test_withheld_province_quarter_never_appears": _PLAIN,
    "test_report_data.py::test_shap_payload_for_withheld_province_reports_nothing": _PLAIN,
}


def pytest_collection_modifyitems(config, items):
    import os

    if os.getenv("AIPHEED_RUN_SUPERSEDED"):          # run them anyway, e.g. to see what the promotion changed
        return
    for item in items:
        key = item.nodeid.split("/")[-1]
        if key in E34_SUPERSEDED:
            item.add_marker(pytest.mark.skip(reason=f"E34 superseded by the E31 promotion: {E34_SUPERSEDED[key]}"))
