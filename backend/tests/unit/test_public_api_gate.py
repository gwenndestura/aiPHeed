"""No unapproved forecast is reachable through the public API: research engines need an admin login, /final/overview
carries no forecast, the food-insecurity route is validation_pending, and CH1 is labelled a price-pressure index."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)

RESTRICTED = ["/api/v1/fi9/outlook", "/api/v1/fi10/provinces", "/api/v1/fi7/forecast", "/api/v1/fi6/forecast",
              "/api/v1/fi5/forecast", "/api/v1/e113/forecast", "/api/v1/hunger-forecast/v2", "/api/v1/simple/forecast",
              "/api/v1/forecast-history", "/api/v1/lead2/summary", "/api/v1/final/evaluation", "/api/v1/final/archive",
              "/api/v1/final/contributions", "/api/v1/admin/candidates/pfi-1.0/outlook", "/api/v1/assessments",
              "/api/v1/quarterly/timeline"]


@pytest.mark.parametrize("path", RESTRICTED)
def test_unapproved_forecasts_need_admin(path):
    assert c.get(path).status_code == 401


def test_food_insecurity_outlook_is_validation_pending():
    j = c.get("/api/v1/final/food-insecurity/outlook").json()
    assert j["status"] == "validation_pending" and j["forecast"] is None
    assert not any(k in j for k in ("provinces", "region", "target_quarter"))


def test_overview_has_no_forecast():
    r = c.get("/api/v1/final/overview")
    if r.status_code == 200:
        j = r.json()
        assert "outlook" not in j and "validation pending" in j["forecastStatus"]


def test_ch1_is_labelled_price_pressure_not_food_insecurity():
    from app.ml.inference import ch1_system as CH1
    if not CH1.rows():
        pytest.skip("CH1 export not present")
    code, quarter = next(iter(CH1.rows()))
    for s in (CH1.sentence(code, "Province", quarter), CH1.sentence(None, "CALABARZON", quarter, mean_p=0.3)):
        assert s.startswith("PRICE-PRESSURE RISK INDEX for") and "(not a food-insecurity forecast)" in s
    assert CH1.INDICATOR["is_food_insecurity_measurement"] is False
    assert "not a food-insecurity forecast" in CH1.INDICATOR["caveat"] and "hunger_forecast" not in CH1.INDICATOR
