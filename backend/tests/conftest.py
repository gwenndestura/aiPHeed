import pytest
import pytest_asyncio
import numpy as np
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.db.database import Base
from app.dependencies import get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _memory_db():
    """A fresh, empty in-memory database per request. E36: tests must never open the production backend/aipheed.db
    (the app's default DATABASE_URL); module-level TestClient(app) calls used to reach it through get_db."""
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


app.dependency_overrides[get_db] = _memory_db          # covers module-scope calls made before any fixture runs


@pytest.fixture(autouse=True)
def _never_open_production_db():
    """Re-install the in-memory default after a test's own override was cleared; a test may still install its own."""
    app.dependency_overrides.setdefault(get_db, _memory_db)
    yield
    app.dependency_overrides.setdefault(get_db, _memory_db)


# Release gate (2026-11-03): research engines' routes need an admin login. These modules test those engines' own
# outputs, so they run as an admin; every other module keeps real authentication (see tests/unit/test_public_api_gate.py).
RESEARCH_ROUTE_TESTS = {
    "test_dynamic_target", "test_e36_served_model", "test_e41_lead2", "test_e42_lead2", "test_e43_five_trigger",
    "test_e44_final_candidate", "test_e46_corrected_candidate", "test_e56_final_model", "test_fpp_label_v2",
    "test_sws_reissue_dashboard", "test_e107", "test_e108", "test_e109", "test_e110", "test_e111", "test_e112",
    "test_e113", "test_fi10", "test_fi5", "test_fi6", "test_fi6_news", "test_fi7", "test_fi9", "test_fi9r", "test_fi9x",
    "test_fi9z", "test_forecasting_core", "test_simple_method", "test_v2_core", "test_v2_defects", "test_v2_paths",
    "test_v4_core", "test_v6_core", "test_api_final_system",
}


@pytest.fixture(autouse=True)
def _research_routes_as_admin(request):
    from app.services.security import require_admin
    if request.module.__name__.rsplit(".", 1)[-1] not in RESEARCH_ROUTE_TESTS:
        yield
        return
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_admin, None)


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


# ------------------------------------------------------------------------------------- tests of a model no longer served
# Since 2026-11-14 FINAL (final-rate-mind-1.0) is production. Tests that check the E168/E196/CH1 serving path itself (their
# probabilities, group names, record formulas, legacy news feed) are marked `legacy_served`: they run when one of those models
# is production and are skipped, with this reason, otherwise. FINAL's own serving path is tested in tests/unit/test_final_realtime.py
# and by the generic API tests, which run against whatever model is production.
LEGACY_SERVED = {"e168-lgbm-1.0", "e184-lgbm-syn50-1.0", "e196-lgbm-avg5-laf-1.0", "ch1-p0h4"}


def _production_model_id():
    import json
    from app.paths import BACKEND_DIR
    try:
        reg = json.loads((BACKEND_DIR / "data" / "registry" / "registry.json").read_text(encoding="utf-8"))
        return (reg.get("production") or {}).get("model_id")
    except Exception:
        return None


def pytest_configure(config):
    config.addinivalue_line("markers", "legacy_served: checks the E168/E196/CH1 serving path; skipped while another model is production")


def pytest_runtest_setup(item):
    if item.get_closest_marker("legacy_served"):
        prod = _production_model_id()
        if prod not in LEGACY_SERVED:
            pytest.skip(f"checks the E168/E196/CH1 serving path; production is {prod}")
