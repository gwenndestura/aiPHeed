"""
app/api/v1/insights.py
-----------------------
Why the score is what it is, and the news corpus behind it.

GET /api/v1/explainability?scope=&id=&quarter=
GET /api/v1/news?scope=&id=&quarter=&page=&pageSize=
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.public import ExplainabilityResponse, NewsResponse
from app.services import dashboard as svc
from app.services import reference as ref

router = APIRouter()

# Five research-defined categories (Market/Prices, Climate Stress, Fish Kill,
# Employment, OFW Remittance). Percentages are grouped SHAP values from the
# food-availability shock model, rescaled so these five sum to 100% AMONG
# THEMSELVES. Developer detail, kept here rather than in the public note:
#   * A group can hold a large share while pushing risk down -- read
#     `direction`, not bar size alone. `color` has three values: yellow below
#     the 20% line, red above it while raising the score, green above it while
#     lowering it (the frontend maps these onto its own risk palette).
#   * OFW Remittance holds actual remittance features only; fuel/transport-cost
#     features moved to Market/Prices.
#   * Fish Kill is a real but thin news-derived signal (`newsSignalProportion`),
#     not a structured dataset.
#   * `otherPct` is the share from the commodity series' own recent history and
#     seasonal position plus general (non-fish-kill) news volume -- not folded
#     into the five bars, which would overstate it, nor hidden.
#
# The note itself is shown to the public under the bars: plain, formal, ASCII
# (the PDF exporter renders text verbatim), no field names.
EXPLAINABILITY_NOTE = (
    "The bars show how much each of five factor groups (Market / Prices, "
    "Climate Stress, Fish Kill, Employment and OFW Remittance) contributed to "
    "this forecast. The five shares add up to 100 percent. A long bar does not "
    "by itself mean that a factor raised the risk: the colour of each bar shows "
    "whether that factor raised or lowered the forecast. The OFW Remittance "
    "group uses remittance data only. The Fish Kill group is based on news "
    "reports and is therefore a limited measure. Part of the forecast also "
    "depends on each commodity's recent production history, its usual seasonal "
    "pattern and the overall volume of news; that part is not shown in the five "
    "groups. These figures are model estimates, not official government "
    "statistics."
)


def _resolve_province(scope: str, subject_id: str) -> tuple[str | None, str]:
    """Return (province PSGC code or None for region, display name)."""
    if scope == "region":
        return None, ref.REGION_NAME
    if scope == "province":
        code = ref.province_code(subject_id)
        if code is None:
            raise svc.SubjectNotFound(f"Unknown province id '{subject_id}'.")
        return code, ref.province_name(subject_id)
    row = ref.municipality_row(subject_id)
    if row is None:
        raise svc.SubjectNotFound(f"Unknown municipality id '{subject_id}'.")
    return row["province_code"], row["lgu_name"]


@router.get("/explainability", response_model=ExplainabilityResponse)
async def get_explainability(
    scope: str = Query("province", pattern="^(region|province|municipality)$"),
    id: str = Query(..., description="calabarzon | quezon | quezon-infanta"),
    quarter: str | None = Query(None),
) -> ExplainabilityResponse:
    """
    Grouped SHAP for one subject-quarter.

    Region scope averages the five province breakdowns. Municipality scope
    returns its parent province's breakdown: the disaggregation reweights the
    province score without re-explaining it, so a municipality has no
    explanation of its own.
    """
    q = svc.resolve_quarter(quarter)
    code, name = _resolve_province(scope, id)

    # SHAP is CPU-bound and, on a quarter not yet cached this process, blocks
    # for several seconds per province. Run it off the event loop so it
    # doesn't stall every other request on the server while it computes --
    # confirmed by measurement that a concurrent /config call queued behind
    # an in-flight SHAP call the way it would if this ran inline.
    if code is None:
        result = await run_in_threadpool(svc.explainability_region, q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        risk_score = svc.region_forecast(q)["riskScore"]
    else:
        result = await run_in_threadpool(svc.explainability, code, q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        slug = ref.province_slug(code)
        match = [p for p in svc.province_summary(q) if p["id"] == slug]
        risk_score = match[0]["riskScore"] if match else 0.0

    other_pct = result["otherPct"]
    return ExplainabilityResponse(
        scope=scope,
        id=id.lower(),
        name=name,
        quarter=q,
        riskScore=risk_score,
        triggers=triggers,
        otherPct=other_pct,
        articleCount=article_count,
        triggerMatchedArticles=matched,
        narrative=svc.compose_narrative(name, q, triggers, other_pct),
        formalInterpretation=svc.compose_formal_interpretation(name, q, triggers, other_pct),
        note=EXPLAINABILITY_NOTE,
    )


@router.get("/news", response_model=NewsResponse)
async def get_news(
    scope: str = Query("province", pattern="^(region|province|municipality)$"),
    id: str = Query(..., description="calabarzon | quezon | quezon-infanta"),
    quarter: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
) -> NewsResponse:
    """
    The analysed article corpus for a subject-quarter, with its topic mix.

    Articles are geocoded to province, so municipality scope returns the parent
    province's corpus. A forecast quarter returns its information-cutoff
    quarter's articles (`sourceQuarter`), the news the forecast was built from.
    """
    q = svc.resolve_quarter(quarter)
    code, _ = _resolve_province(scope, id)
    source_q = svc.news_quarter(q)
    body = svc.news(code, source_q, page, pageSize)
    return NewsResponse(
        scope=scope,
        id=id.lower(),
        quarter=q,
        sourceQuarter=source_q,
        page=page,
        pageSize=pageSize,
        **body,
    )
