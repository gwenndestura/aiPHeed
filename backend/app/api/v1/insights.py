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


E46_EXPLAINABILITY_NOTE = (
    "The bars show how much each of five factor groups moved this experimental forecast, measured as the change in "
    "the forecast's log-odds when that group's inputs are set to their historical average (all else fixed). Market / "
    "Prices includes the projected food inflation and food-minus-headline gap built from PSA CPI, which is the "
    "model's main price input. The latest regional hunger level (SWS) is not one of the five groups and is left out "
    "of the bars. The five shares add up to 100 percent of the five groups' combined effect; each card states whether "
    "the group raised or lowered the forecast and the official observation behind it. Employment and OFW figures are "
    "national. These are model attributions, not causes and not shares of food insecurity."
)


E52_EXPLAINABILITY_NOTE = (
    "This experimental forecast is the probability of food-price pressure (PSA food inflation, or food minus headline "
    "inflation, above the province's usual 2021-2022 level), not of hunger or household food insecurity. The bars "
    "show how much each of five factor groups moved it, measured as the change in the forecast's log-odds when that "
    "group's inputs are set to their historical average (all else fixed). Market / Prices includes the projected food "
    "inflation and food-minus-headline gap built from PSA CPI. The five shares add up to 100 percent of the five "
    "groups' combined effect; each card states whether the group raised or lowered the forecast and the official "
    "observation behind it. Employment and OFW figures are national. These are model attributions, not causes."
)


E53_EXPLAINABILITY_NOTE = (
    "This experimental forecast is the probability of food-price pressure (PSA food inflation, or food minus headline "
    "inflation, above the province's usual 2021-2022 level), not of hunger or household food insecurity. The bars "
    "show how much each of five factor groups moved it, measured as the change in the forecast's log-odds when that "
    "group's inputs are set to their historical average (all else fixed). Market / Prices includes the projected food "
    "inflation and food-minus-headline gap built from PSA CPI and the rice-policy orders; each group includes its own "
    "news share; the total volume of news is not one of the five groups and is left out of the bars. Each card states "
    "whether the group raised or lowered the forecast and the official observation behind it. Employment and OFW "
    "figures are national. These are model attributions, not causes."
)


# from backend-e53-final (used by app.services.report_data_e31 for a calibrated record)
CALIBRATION_SENTENCE = (
    "The bars explain the model's estimate before calibration. Calibration pulls every estimate toward the long-run "
    "rate, so it lowers or raises the index but does not change the shares."
)


E55_EXPLAINABILITY_NOTE = (
    "This experimental forecast is the probability of HIGH food-insecurity risk: the regional SWS hunger rate staying "
    "above 11.3% AND food-price pressure in the province (PSA food inflation, or food minus headline inflation, above "
    "the province's usual 2021-2022 level). Hunger is measured for the whole region only, so differences between "
    "provinces come from food prices. The bars are exact SHAP values (TreeSHAP) of the LightGBM model's food-price "
    "part, in log-odds, grouped into the five factor groups: Market / Prices also includes the projected food "
    "inflation built from PSA CPI (the model's starting point) and the rice-policy orders; each group includes its own "
    "news share; the total volume of news is left out of the bars. A group with no observed input at the issue date is "
    "shown as insufficient data. Employment and OFW figures are national. These are model attributions, not causes."
)


E56_EXPLAINABILITY_NOTE = E55_EXPLAINABILITY_NOTE.replace(
    "the total volume of news is left out of the bars",
    "the total volume of news and, at origins where the model selected it, PSA 2021 poverty are left out of the bars")


E58_EXPLAINABILITY_NOTE = E56_EXPLAINABILITY_NOTE + (
    " Early warning (E58): ALERT when HIGH food-insecurity risk is forecast; EMERGING when food-price pressure is likely "
    "but the hunger condition is not confirmed by the latest (older) hunger reading. Warnings support DA review and "
    "planning; they are not official classifications."
)


# THESIS: the bars show the exact push of each of the five approved factor groups on the served FIRI v2 index away
# from its neutral 0.5 (thesis_system.firi_drivers); vulnerability, regional hunger and news are named in the summary
# text (no new UI element)
THESIS_EXPLAINABILITY_NOTE = (
    "The risk score shown is the estimated food-insecurity risk index (FIRI v2), a proxy composite on a 0-1 scale in "
    "which 0.5 means every indicator is at its historical middle. Each bar is a factor group's exact share of how far "
    "the index moved from 0.5: red groups are above their usual level and raise the estimate, green groups are below it "
    "and lower it. Market / Prices = the LightGBM food-price-pressure forecast, headline inflation and rice prices; "
    "Climate Stress = PAGASA El Nino status, typhoons, palay and corn production; Fish Kill = fisheries production (not "
    "fish-kill events); Employment and OFW Remittance = national figures. Household vulnerability, regional hunger (SWS, "
    "Balance Luzon) and news are also in the index but not among the five bars; their share and every domain score and "
    "weight are in the summary text. Shares describe how the estimate is built from the evidence; they are not causes."
)


# E64: the Objectives 1-3 candidate (improved news pipeline v3); the product of the two parts is a model score
E64_EXPLAINABILITY_NOTE = (
    "This experimental forecast is a model score for HIGH food-stress risk: the regional SWS hunger rate staying above "
    "11.3% AND food-price pressure in the province (PSA food inflation, or food minus headline inflation, above the "
    "province's usual 2021-2022 level). The two parts are estimated separately and multiplied; because they are not "
    "independent, the product is a score, not a tested probability. Hunger is measured for the whole region only, so "
    "differences between provinces come from food prices. The bars are exact SHAP values (TreeSHAP) of the food-price "
    "part, in log-odds, grouped into the five factor groups; Market / Prices also includes the projected food "
    "inflation built from PSA CPI. Each group includes its own news signals from the improved news pipeline (E60 "
    "classifier v2, articles published before the issue date, syndicated copies removed) when the model uses them; "
    "news coverage, outlet count and FSSI-v3 are left out of the bars. Employment and OFW figures are national. These "
    "are model attributions, not causes. Early warning: ALERT when HIGH risk is forecast; EMERGING when food-price "
    "pressure is likely but the hunger condition is not confirmed; model warnings for DA review, not official "
    "classifications."
)


NOT_RECORDED_EXPLAINABILITY_NOTE = (
    "This quarter shows the experimental model's backtest or an earlier forecast. Factor contributions were not "
    "recorded for it, so no factor is described as raising or lowering the score."
)


def _served_note(quarter: str | None = None) -> str:
    from app.ml.inference import e31_engine as E31
    from app.ml.inference import e41_lead2 as LEAD2

    # E47: any five-trigger candidate (e44, e46, e52) on a quarter whose attribution it carries (the issued forecast or
    # a past quarter refitted at its own issue date); a past quarter without one says so instead of the E38/E31 note
    if quarter and LEAD2.mode() == "e64" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E64_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "thesis" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return THESIS_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() in ("e58", "e66", "e67", "e68", "e69", "thesis") and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E58_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "e56" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E56_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "e55" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E55_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "e53" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E53_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "e52" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E52_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() == "e46" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E46_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() in ("e44", "e46", "e52", "e53") and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return CANDIDATE_EXPLAINABILITY_NOTE
    if quarter and LEAD2.governs():
        return NOT_RECORDED_EXPLAINABILITY_NOTE
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

    # E52: plain-language summary of an experimental candidate's estimate. A municipality has no forecast of its own,
    # so its summary is the parent province's, named as such.
    subject = name if scope != "municipality" else f"{ref.province_name(ref.province_slug(code))} (province of {name})"
    summary = svc.plain_summary(code, q, subject, triggers) if svc.e31_active() else None
    return ExplainabilityResponse(
        scope=scope,
        id=id.lower(),
        name=name,
        quarter=q,
        riskScore=risk_score,
        triggers=triggers,
        articleCount=article_count,
        triggerMatchedArticles=matched,
        narrative=(f"{summary['sentence']} These are model attributions, not causes." if summary
                   else svc.compose_narrative(name, q, triggers)),
        note=_served_note(q) if svc.e31_active() else EXPLAINABILITY_NOTE,
        summary=summary,
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
