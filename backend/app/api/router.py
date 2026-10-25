from fastapi import APIRouter

from app.api.v1 import (
    admin, alerts, assessments, auth, dashboard, e107, e108, e109, e110, e111, e112, forecast, fpp, health, insights,
    lead2, quarterly, report, simple,
)

router = APIRouter()

# The dashboard contract lives under /api/v1, the base path the frontend spec
# fixes. Health keeps its original /v1 mount so existing probes keep working.
router.include_router(health.router, prefix="/v1", tags=["Health"])

API_V1 = "/api/v1"
router.include_router(health.router, prefix=API_V1, tags=["Health"])
router.include_router(dashboard.router, prefix=API_V1, tags=["Dashboard"])
router.include_router(forecast.router, prefix=API_V1, tags=["Forecast"])
router.include_router(insights.router, prefix=API_V1, tags=["Insights"])
router.include_router(report.router, prefix=API_V1, tags=["Report"])
# Revised, time-valid province assessments (fixed 0.50 rule, INSUFFICIENT_DATA, regional/provincial evidence).
router.include_router(assessments.router, prefix=API_V1, tags=["Assessments"])
# Current forecast period + status from the single quarterly forecast record (E23).
router.include_router(quarterly.router, prefix=API_V1, tags=["Quarterly"])
# Label v2: Food Price Pressure (exploratory), served only when LABEL_VERSION=v2 (E39); v1 stays the default.
router.include_router(fpp.router, prefix=API_V1, tags=["Food Price Pressure (exploratory)"])
# E41 Lead-2 two-layer candidate, served only when AIPHEED_LEAD2_MODEL=e41; E38 stays the default.
router.include_router(lead2.router, prefix=API_V1, tags=["Lead-2 candidate (E41)"])
# Simple methodology (E106, branch aipheed/simple-methodology): read-only record and evaluation files.
router.include_router(simple.router, prefix=API_V1, tags=["Simple methodology (E106)"])
# E107 twelve-indicator LightGBM (branch aipheed/e107-twelve-indicator-lightgbm): read-only exported files.
router.include_router(e107.router, prefix=API_V1, tags=["Twelve-indicator LightGBM (E107)"])
# E108 factored LightGBM (branch aiPHeed/e108-best-defensible-forecasting): read-only exported files.
router.include_router(e108.router, prefix=API_V1, tags=["Factored twelve-indicator LightGBM (E108)"])
# E109 SWS Balance Luzon hunger forecasting (branch aiPHeed/e109-hunger-forecasting): read-only exported files.
router.include_router(e109.router, prefix=API_V1, tags=["Regional hunger forecasting (E109)"])
# E110 SWS hunger generalization (branch aiPHeed/e110-hunger-generalization): read-only exported files.
router.include_router(e110.router, prefix=API_V1, tags=["Hunger forecast generalization (E110)"])
# E111 audited SWS hunger forecasting (branch aiPHeed/e111-hunger-forecast-audit): read-only exported files.
router.include_router(e111.router, prefix=API_V1, tags=["Audited hunger forecasting (E111)"])
# E112 food-insecurity forecasting with issue-date news indicators (branch aiPHeed/e112-food-insecurity-forecasting).
router.include_router(e112.router, prefix=API_V1, tags=["Food-insecurity forecasting with news (E112)"])

# Auth, and the public face of the review pipeline (rejections, feedback
# submission) -- both unauthenticated by design.
router.include_router(auth.router, prefix=f"{API_V1}/auth", tags=["Auth"])
router.include_router(admin.public_router, prefix=API_V1, tags=["Publication"])
# Confirmed early warning alerts. Staged and dismissed alerts are never served
# here -- Rule 7 requires human confirmation before an alert is shown.
router.include_router(alerts.public_router, prefix=API_V1, tags=["Alerts"])

# Everything that changes publication state. The router carries the admin
# dependency, so a new route added here is gated by default rather than by
# remembering to add it.
router.include_router(admin.admin_router, prefix=f"{API_V1}/admin", tags=["Admin"])
router.include_router(alerts.admin_router, prefix=f"{API_V1}/admin", tags=["Admin"])
