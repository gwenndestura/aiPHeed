"""
app/schemas/public.py
----------------------
The public dashboard contract.

These models are camelCase and address subjects by slug ("quezon",
"quezon-infanta") because that is how the frontend addresses them. The
internal schemas in forecasts.py / shap.py stay snake_case and PSGC-keyed for
the DB and ML layers; app/services/reference.py is the only translation point.

Every forecast response carries `indicator`. The number is the province's food
insecurity RISK PROBABILITY — an indicative, relative ordinal estimate, not a
definitive determination of food insecurity status — and the label travels with
the value so no screen can rename it in isolation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_serializer

# AIPHEED_LEAD2_PREVIEW=1 (app/quarterly/preview.py): optional fields, omitted from the JSON when unset, so responses
# are unchanged with the flag off and the current frontend ignores them.
PREVIEW_KEYS = ("isPreview", "belowAccuracyTarget", "previewNote", "defaultQuarter")


class _PreviewFields(BaseModel):
    isPreview: bool | None = None
    belowAccuracyTarget: bool | None = None
    previewNote: str | None = None

    @model_serializer(mode="wrap")
    def _omit_unset_preview(self, handler):
        data = handler(self)
        if isinstance(data, dict):
            for k in PREVIEW_KEYS:
                if k in data and data[k] is None:
                    data.pop(k)
        return data


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class Indicator(BaseModel):
    """What the score on screen actually measures."""
    id: str
    name: str
    definition: str
    unit: str
    horizon: str
    source: str
    caveat: str


class Centroid(BaseModel):
    lat: float
    lng: float


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


# ---------------------------------------------------------------------------
# Config & timeline
# ---------------------------------------------------------------------------

class Thresholds(BaseModel):
    riskDisplayCutoff: float
    alertThreshold: float
    triggerRedCutoff: int
    limitedSignalMinArticles: int


class ConfigResponse(BaseModel):
    """
    Server-owned display rules, so the frontend stops hardcoding them.

    `riskLevelsActive` reports the bands the model actually produces. The
    frontend type carries four; only two are ever returned.
    """
    region: str
    thresholds: Thresholds
    riskLevelsActive: list[str]
    riskLevelsDefined: list[str]
    indicator: Indicator
    quarterRange: dict
    # Both served models, keyed by horizon: what each answers, the quarters it
    # reaches, and its metrics with baselines.
    horizons: dict
    modelPerformance: dict


class Quarter(_PreviewFields):
    id: str
    year: int
    q: int
    label: str
    monthsLabel: str
    state: str  # "actual" | "current" | "forecast" | "unavailable"
    # Why an "unavailable" quarter has no score; None on every other state (main backend 1658d31, restored in E34).
    reason: str | None = None


class QuartersResponse(_PreviewFields):
    """
    The quarters the model can score. `current` is the newest of those, not the
    calendar quarter — PSA's publication lag, not the clock, sets the edge.

    `horizon` says which model's timeline this is: the forecast horizon reaches
    one quarter further than the nowcast, because its inputs all predate the
    quarter being scored.
    """
    current: str
    horizon: str = "nowcast"
    serverTime: str
    calendarQuarter: str
    lagQuarters: int
    # The dynamic next-quarter target (app/quarterly/target.py) and whether its forecast exists.
    forecastTarget: dict | None = None
    quarters: list[Quarter]
    # lead-2 preview on (the default; AIPHEED_LEAD2_PREVIEW=0 turns it off): the quarter the dashboard opens on (2027-Q1)
    defaultQuarter: str | None = None


# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------

class ProvinceSummary(BaseModel):
    id: str
    name: str
    provinceCode: str
    centroid: Centroid
    population: int | None = None
    povertyRate: float | None = None
    # E35-D7: how povertyRate was derived (population-weighted PSA 2021 municipal SAE; not a PSA province figure)
    povertyRateBasis: str | None = None
    currentQuarter: str
    # Null when withheld. The province still appears so the map can draw it,
    # but the number an admin held back is not served alongside a flag.
    riskScore: float | None = None
    riskLevel: str | None = None
    qoqChange: float | None = None
    qoqChangePct: float | None = None
    riskLabel: str | None = None
    # E41 (only with AIPHEED_LEAD2_MODEL=e41, for its target quarter): what riskScore is, and the documented band
    scoreType: str | None = None
    scoreDefinition: str | None = None
    riskBand: str | None = None
    # E46: "forecast" | "earlier_forecast" | "backtest" (candidate mode) and, for a backtest, the observed outcome of
    # the same event ("HIGH" | "LOW"): an estimate and an observation are never presented as one number
    estimateKind: str | None = None
    observedOutcome: str | None = None
    # E35-D1: what the riskLevel band is (a model estimate at the display cutoff, never a validated class)
    riskLevelBasis: str | None = None
    evidenceStatus: str | None = None
    forecastHorizonQuarters: int | None = None
    horizonLabel: str | None = None
    confidenceStatement: str | None = None
    verificationDate: str | None = None
    articleCount: int = 0
    limitedSignal: bool = False
    horizon: str = "nowcast"
    withheld: bool = False
    # Ranking of the published provinces by the model's probability (Section
    # 1.2: the system "will estimate and rank" potential risk). Null when
    # withheld, so a withheld score cannot be inferred from its position.
    rank: int | None = None
    # E39 (A. Melindo): true when another published province has the same score (they share the rank)
    rankTied: bool | None = None
    rankOf: int | None = None
    gapToNextLower: float | None = None
    tiedWithNextLower: bool | None = None


class ProvincesResponse(_PreviewFields):
    quarter: str
    horizon: str = "nowcast"
    indicator: Indicator
    data: list[ProvinceSummary]


class MunicipalitySummary(BaseModel):
    id: str
    name: str
    provinceId: str
    lguCode: str
    classification: str
    population: int
    densityPerKm2: float | None = None
    povertyRate: float | None = None
    quarter: str
    # E31 fix: null when the province has no estimate (E28 removed the zero fill but not this type).
    riskIndex: float | None = None
    # E28/E31: LGUs are never banded (the province estimate is not validated), so this is null. The schema still
    # required a string, which made the endpoint return 500 for every quarter.
    riskLevel: str | None = None
    # Never null. These are reweighted province numbers, not independent
    # municipal forecasts, and the label says so on every row.
    disaggregationLabel: str
    limitedSignal: bool = False
    # E31: the ranking and provenance fields the service returns were silently dropped by the schema
    rankRegion: int | None = None
    rankInProvince: int | None = None
    tied: bool = False
    evidenceStatus: str | None = None
    riskLevelBasis: str | None = None
    povertyEstimateKind: str | None = None
    povertyValueUsed: float | None = None
    povertyLimitation: str | None = None
    noProvinceEstimate: bool = False
    # E64 (Objective 3 traceability, review-branch port): the province estimate the index scales and where it came
    # from, the LGU's vulnerability index, the ranking method and the hash of the ranked rows
    provinceEstimate: float | None = None
    provinceEstimateSource: dict | None = None
    vulnerabilityIndex: float | None = None
    rankingMethod: str | None = None
    rankingRowsSha256: str | None = None


class MunicipalitiesResponse(_PreviewFields):
    provinceId: str
    quarter: str
    indicator: Indicator
    data: list[MunicipalitySummary]


class SearchHit(BaseModel):
    type: str  # "province" | "municipality"
    id: str
    name: str
    provinceId: str | None = None
    provinceName: str | None = None


class SearchResponse(BaseModel):
    data: list[SearchHit]


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ForecastResponse(_PreviewFields):
    scope: str  # "region" | "province" | "municipality"
    id: str
    name: str
    quarter: str
    quarterLabel: str
    indicator: Indicator
    # Null only for a region whose every province is withheld; a withheld
    # province or municipality 404s instead.
    riskScore: float | None = None
    riskLevel: str | None = None
    qoqChange: float | None = None
    isForecast: bool = False
    isCurrent: bool = False
    limitedSignal: bool = False
    alert: bool = False
    provinceId: str | None = None
    provinceCounts: dict | None = None
    provincesIncluded: int | None = None
    horizon: str = "nowcast"
    riskLabel: str | None = None
    forecastHorizonQuarters: int | None = None
    horizonLabel: str | None = None
    confidenceStatement: str | None = None
    verificationDate: str | None = None
    disaggregationLabel: str | None = None
    derivation: str | None = None
    estimateKind: str | None = None
    observedOutcome: str | None = None


class TimeseriesPoint(BaseModel):
    quarter: str
    riskScore: float
    riskLevel: str | None = None
    isForecast: bool = False
    scoreType: str | None = None


class TimeseriesResponse(BaseModel):
    scope: str
    id: str
    name: str
    indicator: Indicator
    series: list[TimeseriesPoint]


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

class MeasuredCondition(BaseModel):
    """The measured condition behind a driver's condition input (served models with condition inputs only, E53):
    a 0-100 rank of the measured indicator against earlier quarters. It describes the input, not its contribution."""
    score: float | None = None
    dataQuarter: str | None = None
    summary: str | None = None
    level: str | None = None          # "province" | "national"
    source: str | None = None


class Trigger(BaseModel):
    """
    One SHAP driver group.

    `pct` values across the list are integers summing to exactly 100.
    `direction` is "increases_risk" or "protective" — a group can hold a large
    share of the explanation while pushing risk DOWN, so bar size alone does
    not tell the reader the sign.
    """
    key: str
    label: str
    share: float
    pct: int
    signedContribution: float
    direction: str
    # E42: contributes | no_effect | no_model_input | no_data, and the plain note for it (the dashboard builds its
    # card text from the status, never a fixed direction, for a group that has no model input or no data)
    status: str | None = None
    statusNote: str | None = None
    # E44: the observed evidence behind a model-attributed trigger (province scope, candidate records only)
    evidenceNote: str | None = None
    color: str
    newsSignalProportion: float | None = None
    measuredCondition: MeasuredCondition | None = None


class ExplainabilityResponse(_PreviewFields):
    scope: str
    id: str
    name: str
    quarter: str
    riskScore: float
    triggers: list[Trigger]
    articleCount: int
    triggerMatchedArticles: int
    narrative: str
    note: str


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class Topic(BaseModel):
    key: str
    label: str
    count: int
    pct: int


class Article(BaseModel):
    id: str
    title: str
    source: str
    date: str | None = None
    url: str
    excerpt: str
    topicKey: str
    topicLabel: str
    relevanceScore: float | None = None
    # E45: why the article is in the feed, where it is attributed, which triggers its title matches
    relevanceStatus: str | None = None          # validated | trigger_match
    relevanceLabel: str | None = None
    province: str | None = None
    provinceCode: str | None = None
    triggers: list[str] = []
    quarter: str | None = None
    collectedRetrospectively: bool | None = None


class NewsTopic(BaseModel):
    topic: int
    label: str
    share: float
    keywords: list[str] = []


class TopicsResponse(BaseModel):
    """Descriptive BERTopic patterns of the news for a subject-quarter (Objective 1). Never a forecast input; when the
    topic model failed its publication gate, `status` says so, `topics` is empty and `note` gives the numbers."""
    scope: str
    id: str
    quarter: str
    status: str
    note: str | None = None
    use: str | None = None
    nArticles: int = 0
    topics: list[NewsTopic] = []
    model: dict | None = None


class NewsResponse(BaseModel):
    scope: str
    id: str
    quarter: str
    articleCount: int
    # How many of those are geocoded to a CALABARZON province. Most of the
    # corpus is not: at region scope this is far below articleCount, which is
    # why the five province counts do not add up to the regional one.
    provinceAttributed: int = 0
    topics: list[Topic]
    data: list[Article]
    page: int
    pageSize: int
    total: int
    # E31: which quarter's articles these are and why (a forecast is supported by the PREVIOUS quarter's news;
    # a nowcast by the same quarter up to its cutoff; an observed quarter by its own news)
    evidenceQuarter: str | None = None
    sourceQuarter: str | None = None      # the frontend contract's name for evidenceQuarter
    evidenceMode: str | None = None
    evidenceNote: str | None = None
    # E45: the quarters the feed covers (the evidence quarter, extended back when it holds fewer than 5 articles)
    windowQuarters: list[str] = []
    validatedCount: int = 0
    triggerMatchCount: int = 0
    feedNote: str | None = None
    # view=published on a forecast quarter: the quarter's own news so far, NOT used by its forecast
    usedByForecast: bool | None = None
    forecastEvidenceQuarter: str | None = None   # the quarter whose news the quarter's forecast was built from
    windowEnd: str | None = None                 # latest publication date covered for the articles shown
    forecastOrigin: str | None = None            # the origin date of the quarter's forecast (its information cutoff)


# ---------------------------------------------------------------------------
# Province ranking (Section 1.2, Equation 7)
# ---------------------------------------------------------------------------

class ShapDifference(BaseModel):
    feature: str
    label: str
    difference: float
    value: float | None = None
    valueNextLower: float | None = None


class RankingRow(BaseModel):
    id: str
    name: str
    provinceCode: str
    riskScore: float
    riskLevel: str
    rank: int
    rankOf: int
    qoqChange: float | None = None
    gapToNextLower: float | None = None
    tiedWithNextLower: bool | None = None
    nextLowerId: str | None = None
    whyAboveNextLower: list[ShapDifference] = Field(default_factory=list)
    limitedSignal: bool = False


class RankingResponse(_PreviewFields):
    quarter: str
    indicator: Indicator
    method: str
    horizonLabel: str
    data: list[RankingRow]
