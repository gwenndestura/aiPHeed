"""
app/api/v1/insights.py
-----------------------
Why the score is what it is, and the news corpus behind it.

GET /api/v1/explainability?scope=&id=&quarter=
GET /api/v1/news?scope=&id=&quarter=&page=&pageSize=
GET /api/v1/insights/topics?scope=&id=&quarter=
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.public import ExplainabilityResponse, NewsResponse, TopicsResponse
from app.services import dashboard as svc
from app.services import reference as ref
from app.services import review as rv
from app.quarterly import preview as PV

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
    "the forecast. The served model is a LightGBM with the five trigger proportions (Chapter 3, Eq. 5) and shrinkage "
    "calibration. Driver shares come from how much each input moved this forecast: Market / Prices from the food and "
    "rice price inputs, each other driver from its trigger proportion, and the news inputs by the topic of the news "
    "titles behind them. Part of the forecast also depends on the regional hunger survey, the latest published "
    "risk level and news that matches no driver; that part is not shown in the five groups. These figures are "
    "model estimates, not official government statistics."
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


NOT_RECORDED_EXPLAINABILITY_NOTE = (
    "This quarter shows the experimental model's backtest or an earlier forecast. Factor contributions were not "
    "recorded for it, so no factor is described as raising or lowering the score."
)


E36_REST_SENTENCE = (
    "Part of the forecast also depends on the regional hunger survey, the latest published risk level and news that "
    "matches no driver; that part is not shown in the five groups."
)
REGION_SCALE_SENTENCE = (
    "For CALABARZON, each province's contributions are put on the scale of its probability and averaged, as the "
    "regional index averages the five probabilities."
)
# Region only: the bar size pools the provinces' absolute effects, the colour (direction) their net signed effect
# (app.services.dashboard.explainability_region), so a factor can be large and still net close to zero.
REGION_NET_SENTENCE = (
    "For CALABARZON, a factor can raise the risk in some provinces and lower it in others; its bar shows the total "
    "size of its effect and its colour shows the net direction across the five provinces."
)
# Calibrated records (E49, E53): the drivers are the TreeSHAP of the LightGBM before the shrinkage calibration, which
# is linear with one coefficient per quarter, so it moves the index but leaves the shares unchanged.
CALIBRATION_ANCHOR = "and shrinkage calibration."
CALIBRATION_SENTENCE = (
    "The bars explain the model's estimate before calibration. Calibration pulls every estimate toward the long-run "
    "rate, so it lowers or raises the index but does not change the shares."
)


def _served_note(attribution: dict | None = None, region: bool = False, quarter: str | None = None) -> str:
    """The E36-schema note opens with this forecast's own split (hunger survey inputs / news / the five drivers);
    the general sentence about that part is then dropped, and a 0% driver is said to have had no measurable effect.
    A calibrated record says the bars explain the estimate before calibration; the region note says how a factor's
    bar and colour pool the five provinces. A lead-2 candidate (AIPHEED_LEAD2_MODEL=e44/e46, Angel's E47) on a
    quarter whose attribution it carries keeps its own note; a governing candidate's past quarter says it has none."""
    from app.ml.inference import e31_engine as E31
    from app.ml.inference import e41_lead2 as LEAD2
    from app.quarterly import self_description as SD

    if quarter and LEAD2.mode() == "e46" and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return E46_EXPLAINABILITY_NOTE
    if quarter and LEAD2.mode() in ("e44", "e46") and (LEAD2.serves(quarter) or LEAD2.has_past_drivers(quarter)):
        return CANDIDATE_EXPLAINABILITY_NOTE
    if quarter and LEAD2.governs():
        return NOT_RECORDED_EXPLAINABILITY_NOTE
    if E31.record().get("schema") != "e36/1":
        return E31_EXPLAINABILITY_NOTE
    note = E36_EXPLAINABILITY_NOTE
    # the note names the served model (its short name, from the record's composed engine block)
    short = (SD.served_engine(E31.record(), SD.active_record_key()).get("name") or "").split(" (")[0].strip()
    if short.isascii() and short:
        note = note.replace("The served model is a LightGBM", f"The served model ({short}) is a LightGBM")
    if SD.is_calibrated(SD.active_record_key()):       # E49, E53: shrinkage-calibrated
        note = note.replace(CALIBRATION_ANCHOR, CALIBRATION_ANCHOR + " " + CALIBRATION_SENTENCE)
    if E31.uses_condition_inputs():                    # E53: measured driver-condition inputs
        note += " " + CONDITION_INPUTS_SENTENCE
    if region:
        note = REGION_NET_SENTENCE + " " + note
    split = svc.attribution_sentence(attribution)
    if split:
        note = note.replace(E36_REST_SENTENCE, "A driver shown at 0 percent had no measurable effect on this forecast.")
        if region:
            note = REGION_SCALE_SENTENCE + " " + note
        note = split + " " + note
    return note


CONDITION_INPUTS_SENTENCE = (
    "This model also gives each driver a measured condition score from official data, and the Employment and OFW "
    "Remittance scores are national-level indicators, the same for every province."
)


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
    db: AsyncSession = Depends(get_db),
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
    # Thesis p. 60: a rejected forecast is withheld from the map, the rankings and the regional mean, so it is not
    # explained either; with AIPHEED_REQUIRE_APPROVAL=1 an unapproved one is withheld too (rv.withheld_pairs).
    gate = frozenset(pid for pid, _ in await rv.withheld_pairs(db, q))
    if code is not None and ref.province_slug(code) in gate:
        raise svc.ForecastWithheld(f"The {q} forecast for this area has been withheld from publication.")
    if code is None and gate >= set(ref.PROVINCES):
        raise svc.ForecastWithheld(f"Every province's {q} forecast is withheld from publication.")

    if code is None:
        result = svc.explainability_region(q, gate) if gate else svc.explainability_region(q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        risk_score = svc.region_forecast(q, gate)["riskScore"]
    else:
        result = svc.explainability(code, q)
        triggers = result["triggers"]
        article_count = result["articleCount"]
        matched = result["triggerMatchedArticles"]
        slug = ref.province_slug(code)
        match = [p for p in svc.province_summary(q) if p["id"] == slug]
        risk_score = match[0]["riskScore"] if match else 0.0
    # All five driver groups are returned, including one whose share rounds to 0% (no measurable effect); the shares
    # add up to 100. When every share is 0 (no driver moved the estimate, e.g. 2023-Q1, whose model is a constant)
    # the list is empty, as before the simplified merge (262e81e): five 0% bars would explain nothing.
    # (Only for the served model's own statuses: a candidate's "not_recorded" / "no_data" cards are kept.)
    if not any(t["pct"] > 0 for t in triggers) and all(t.get("status") in (None, "contributes", "no_effect")
                                                         for t in triggers):
        triggers = []
    return ExplainabilityResponse(
        scope=scope,
        id=id.lower(),
        name=name,
        quarter=q,
        riskScore=risk_score,
        triggers=triggers,
        articleCount=article_count,
        triggerMatchedArticles=matched,
        # the narrative describes the drivers with an effect (as before); the list itself shows all five
        narrative=svc.compose_narrative(name, q, svc.nonzero_triggers(triggers)),
        note=(_served_note(result.get("attribution"), region=code is None, quarter=q) if svc.e31_active()
              else EXPLAINABILITY_NOTE),
        **PV.fields(q),
    )


@router.get("/news", response_model=NewsResponse)
async def get_news(
    scope: str = Query("province", pattern="^(region|province|municipality)$"),
    id: str = Query(..., description="calabarzon | quezon | quezon-infanta"),
    quarter: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    view: str = Query("used", pattern="^(used|published)$",
                      description="used: the news the estimate was built from; published: the quarter's own news so far"),
) -> NewsResponse:
    """
    The analysed article corpus for a subject-quarter, with its topic mix.

    Articles are geocoded to province, so municipality scope returns the parent
    province's corpus.
    """
    q = svc.resolve_quarter(quarter)
    code, _ = _resolve_province(scope, id)
    body = svc.news(code, q, page, pageSize, view)
    return NewsResponse(
        scope=scope,
        id=id.lower(),
        quarter=q,
        page=page,
        pageSize=pageSize,
        **body,
    )


@router.get("/insights/topics", response_model=TopicsResponse)
async def get_topics(
    scope: str = Query("region", pattern="^(region|province|municipality)$"),
    id: str = Query("calabarzon", description="calabarzon | quezon | quezon-infanta"),
    quarter: str | None = Query(None),
) -> TopicsResponse:
    """
    Descriptive BERTopic topic patterns of the relevant news (Objective 1), read only.

    The topic model is fitted once on all authorized quarters, so these are
    descriptive and never a forecast input. Municipality scope returns the
    parent province's topics.
    """
    q = svc.resolve_quarter(quarter)
    code, _ = _resolve_province(scope, id)
    return TopicsResponse(scope=scope, id=id.lower(), quarter=q, **svc.news_topics(code, q))
