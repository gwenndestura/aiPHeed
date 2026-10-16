"""
app/api/v1/insights.py
-----------------------
Why the score is what it is, and the news corpus behind it.

GET /api/v1/explainability?scope=&id=&quarter=
GET /api/v1/news?scope=&id=&quarter=&page=&pageSize=
"""

from __future__ import annotations

from fastapi import APIRouter, Query

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


E36_EXPLAINABILITY_NOTE = (
    "The bars show how much each of five factor groups (Market / Prices, Climate Stress, Fish Kill, Employment and "
    "OFW Remittance) contributed to this forecast. The five shares add up to 100 percent. A long bar does not by "
    "itself mean that a factor raised the risk: the colour of each bar shows whether that factor raised or lowered "
    "the forecast. In the current model only Market / Prices (provincial food and rice price movements) is an "
    "input; Climate Stress, Fish Kill, Employment and OFW Remittance have no input in it, so they show 0 percent, "
    "and the news reports linked to them are listed separately. Part of the forecast also depends on the regional "
    "hunger survey, the latest published risk level and the overall volume of news; that part is not shown in the "
    "five groups. These figures are model estimates, not official government statistics."
)


CANDIDATE_EXPLAINABILITY_NOTE = (
    "The bars show how much each of five factor groups (Market / Prices, Climate Stress, Fish Kill, Employment and "
    "OFW Remittance) moved this experimental forecast; the five shares add up to 100 percent. Each card states "
    "whether the group raised or lowered the forecast and the official observation behind it. Every group has inputs "
    "in this model; a 0 percent bar means no measurable effect this quarter, not missing data. Employment and OFW "
    "figures are national, so they shift every province equally. Contributions are model attributions, not proof "
    "that an event causes food insecurity. These figures are model estimates, not official government statistics."
)


def _served_note(quarter: str | None = None) -> str:
    from app.ml.inference import e31_engine as E31
    from app.ml.inference import e41_lead2 as LEAD2

    if quarter and LEAD2.serves(quarter) and LEAD2.mode() == "e44":
        return CANDIDATE_EXPLAINABILITY_NOTE
    return E36_EXPLAINABILITY_NOTE if E31.record().get("schema") == "e36/1" else E31_EXPLAINABILITY_NOTE


E31_EXPLAINABILITY_NOTE = (
    "Exact breakdown of the served estimate (PCF21), not a SHAP approximation: the estimate's margin over the "
    "threshold equals (regional hunger - threshold) + 2 x provincial relative food-price pressure. Regional hunger "
    "is one SWS Balance Luzon value shared by all five provinces; only the price term differs between provinces. "
    "These are the model's inputs, not causes. Shares are rescaled to 100%; read `direction`, not bar size alone. "
    "`color`: yellow below the 20% line, red above it while raising the estimate, green while lowering it."
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

    if code is None:
        result = svc.explainability_region(q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        risk_score = svc.region_forecast(q)["riskScore"]
    else:
        result = svc.explainability(code, q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        slug = ref.province_slug(code)
        match = [p for p in svc.province_summary(q) if p["id"] == slug]
        risk_score = match[0]["riskScore"] if match else 0.0

    return ExplainabilityResponse(
        scope=scope,
        id=id.lower(),
        name=name,
        quarter=q,
        riskScore=risk_score,
        triggers=triggers,
        articleCount=article_count,
        triggerMatchedArticles=matched,
        narrative=svc.compose_narrative(name, q, triggers),
        note=_served_note(q) if svc.e31_active() else EXPLAINABILITY_NOTE,
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
    province's corpus.
    """
    q = svc.resolve_quarter(quarter)
    code, _ = _resolve_province(scope, id)
    body = svc.news(code, q, page, pageSize)
    return NewsResponse(
        scope=scope,
        id=id.lower(),
        quarter=q,
        page=page,
        pageSize=pageSize,
        **body,
    )
