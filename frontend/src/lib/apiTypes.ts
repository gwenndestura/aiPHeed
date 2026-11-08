// src/lib/apiTypes.ts
// ---------------------
// TypeScript mirrors of the backend's Pydantic response/request schemas
// (backend/app/schemas/public.py and backend/app/schemas/admin.py). Kept as
// one file so a backend schema change is one obvious diff to match, rather
// than a hunt across component-local interfaces.

export type Horizon = "nowcast" | "forecast";
export type Scope = "region" | "province" | "municipality";

export interface Indicator {
  id: string;
  name: string;
  definition: string;
  unit: string;
  horizon: string;
  source: string;
  caveat: string;
}

export interface Centroid {
  lat: number;
  lng: number;
}

// ---------------------------------------------------------------------------
// /config
// ---------------------------------------------------------------------------

export interface Thresholds {
  riskDisplayCutoff: number;
  alertThreshold: number;
  triggerRedCutoff: number;
  limitedSignalMinArticles: number;
}

export interface Baselines {
  majorityClass: number;
  seasonalPersistence: number;
  naivePersistence: number;
}

export interface SkillVs {
  vsMajority: number;
  vsSeasonal: number;
  vsNaive: number;
}

export interface HorizonPerformance {
  horizon: Horizon;
  evaluation: string;
  n: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  weightedAvg: { precision: number; recall: number; f1: number };
  confusion: { tp: number; fp: number; fn: number; tn: number };
  rocAuc: number;
  baselines: Baselines;
  skill: SkillVs;
  abstainPct: number;
}

export interface HorizonInfo {
  id: Horizon;
  name: string;
  question: string;
  definition: string;
  resultsFile: string;
  earliest: string | null;
  latest: string | null;
  count: number;
  performance: HorizonPerformance;
}

export interface ConfigResponse {
  region: string;
  thresholds: Thresholds;
  riskLevelsActive: string[];
  riskLevelsDefined: string[];
  indicator: Indicator;
  quarterRange: {
    earliest: string | null;
    latest: string | null;
    count: number;
    forecastQuarters: string[];
    note: string;
  };
  horizons: { nowcast: HorizonInfo; forecast: HorizonInfo };
  modelPerformance: HorizonPerformance;
  // The E20 headline forecast (2027-Q1); null when the backend does not serve it.
  forecast?: ForecastMeta | null;
}

export interface ForecastMeta {
  period: string;
  periodLabel: string;
  generatedAt: string | null;
  informationCutoff: string;
  informationCutoffReason: string | null;
  horizonQuarters: number;
  horizonCalculation: string | null;
  model: string;
  modelName: string;
  selectionRule: string | null;
  status: string;
  statusLabel: string;
  backtest: { roc_auc: number | null; roc_auc_ci95: [number, number] | null; brier: number | null };
  evaluationQuarters: number | null;
  differentiatesProvinces: boolean;
  probabilityRange: [number, number];
  limitations: string[];
  target: { name: string; definition: string; caveat: string } | null;
  notDisplayed: { lead: number; targetQuarter: string; reason: string }[];
  context: { text: string; source: string; url: string } | null;
}

// ---------------------------------------------------------------------------
// /quarters
// ---------------------------------------------------------------------------

export interface Quarter {
  id: string;
  year: number;
  q: number;
  label: string;
  monthsLabel: string;
  state: "actual" | "current" | "forecast" | "unavailable";
  // Why an "unavailable" quarter has no score; null on every other state.
  reason?: string | null;
}

export interface QuartersResponse {
  current: string;
  horizon: Horizon;
  serverTime: string;
  calendarQuarter: string;
  lagQuarters: number;
  quarters: Quarter[];
}

// ---------------------------------------------------------------------------
// /provinces, /provinces/{id}/municipalities
// ---------------------------------------------------------------------------

export interface ProvinceSummary {
  id: string;
  name: string;
  provinceCode: string;
  centroid: Centroid;
  population: number | null;
  povertyRate: number | null;
  currentQuarter: string;
  // Null when withheld -- the province still appears (for its geometry) with
  // withheld:true and no score, rather than being dropped from the list.
  riskScore: number | null;
  riskLevel: string | null;
  qoqChange: number | null;
  qoqChangePct: number | null;
  /** E168: the score the change is measured from, its quarter and which forecast made it. */
  qoqPreviousScore?: number | null;
  qoqPreviousQuarter?: string | null;
  qoqPreviousBasis?: string | null;
  seriesMonitored: number | null;
  seriesAtRisk: number | null;
  // Of seriesMonitored, how many scored below the model's own confidence
  // cutoff -- real per-commodity uncertainty, disclosed rather than hidden.
  // riskScore still counts every monitored series regardless.
  seriesNeedingReview: number | null;
  topAtRiskCommodities: string[];
  articleCount: number;
  limitedSignal: boolean;
  horizon: Horizon;
  withheld: boolean;
  // Set on an E20 forecast quarter (2027-Q1).
  isForecast?: boolean;
  lead?: number | null;
  originQuarter?: string | null;
  modelId?: string | null;
  confidenceNote?: string | null;
}

export interface ProvincesResponse {
  quarter: string;
  horizon: Horizon;
  indicator: Indicator;
  data: ProvinceSummary[];
}

export interface MunicipalitySummary {
  id: string;
  name: string;
  provinceId: string;
  lguCode: string;
  classification: string;
  population: number;
  densityPerKm2: number | null;
  povertyRate: number | null;
  quarter: string;
  riskIndex: number | null;
  riskLevel: string | null;
  // Never null -- a reweighted province number, not an independent forecast.
  disaggregationLabel: string;
  limitedSignal: boolean;
  /** E45: what colours the LGU on the map. */
  vulnerabilityIndex?: number | null;
  mapStatus?: "vulnerability" | "insufficient_data" | null;
  mapCategory?: "low" | "medium" | "high" | null;
  mapLabel?: string | null;
  mapNote?: string | null;
}

export interface MunicipalitiesResponse {
  provinceId: string;
  quarter: string;
  indicator: Indicator;
  data: MunicipalitySummary[];
}

// ---------------------------------------------------------------------------
// /search
// ---------------------------------------------------------------------------

export interface SearchHit {
  type: "province" | "municipality";
  id: string;
  name: string;
  /** "Province" | "City" | "Municipality" */
  classification?: string | null;
  provinceId?: string | null;
  provinceName?: string | null;
  /** Nothing matched closely: one of the nearest names ("Did you mean"). */
  suggestion?: boolean;
}

export interface SearchResponse {
  data: SearchHit[];
}

// ---------------------------------------------------------------------------
// /forecast, /forecast/timeseries
// ---------------------------------------------------------------------------

export interface ForecastResponse {
  scope: Scope;
  id: string;
  name: string;
  quarter: string;
  quarterLabel: string;
  indicator: Indicator;
  // Null only for a region whose every province is withheld. A withheld
  // province/municipality 404s (forecast_withheld) instead of returning this.
  riskScore: number | null;
  riskLevel: string | null;
  qoqChange: number | null;
  isForecast: boolean;
  isCurrent: boolean;
  limitedSignal: boolean;
  alert: boolean;
  provinceId?: string | null;
  provinceCounts?: Record<string, number> | null;
  provincesIncluded?: number | null;
  horizon: Horizon;
  seriesMonitored?: number | null;
  seriesAtRisk?: number | null;
  seriesNeedingReview?: number | null;
  topAtRiskCommodities?: string[] | null;
  disaggregationLabel?: string | null;
  derivation?: string | null;
}

export interface TimeseriesPoint {
  quarter: string;
  riskScore: number;
  riskLevel: string;
  isForecast: boolean;
}

export interface TimeseriesResponse {
  scope: Scope;
  id: string;
  name: string;
  indicator: Indicator;
  series: TimeseriesPoint[];
}

// ---------------------------------------------------------------------------
// /explainability, /news
// ---------------------------------------------------------------------------

export interface Trigger {
  key: string;
  label: string;
  share: number;
  pct: number;
  signedContribution: number;
  direction: "increases_risk" | "protective";
  color: "yellow" | "red" | "green";
  newsSignalProportion: number | null;
  /** E42: what the group is in this forecast. Absent from older backends. */
  status?: TriggerStatus;
  statusNote?: string;
  /** E44: the observed evidence behind a model-attributed trigger (province scope, candidate models only). */
  evidenceNote?: string | null;
  /** E87: the card's plain sentence with the measured values behind the group (province scope). */
  plainEvidence?: string | null;
}

export type TriggerStatus =
  | "contributes"
  | "no_effect"
  | "data_not_in_model"
  | "stale"
  | "no_model_input"
  | "no_data"
  | "insufficient_data"
  | "not_recorded";

export interface ExplainabilityResponse {
  scope: Scope;
  id: string;
  name: string;
  quarter: string;
  riskScore: number;
  triggers: Trigger[];
  /** % of the model's absolute attribution outside the five trigger groups; null when not reported. */
  otherPct?: number | null;
  articleCount: number;
  triggerMatchedArticles: number;
  narrative: string;
  /** Third-person interpretation for the PDF report. Plain ASCII. */
  formalInterpretation: string;
  note: string;
  /** E52: plain-language reading of an experimental candidate's estimate. Absent/null otherwise. */
  summary?: PlainSummary | null;
}

export interface PlainSummary {
  event: string;
  targetQuarter: string;
  estimateKind: "forecast" | "earlier_forecast" | "backtest";
  issued: string | null;
  probability: number;
  result: "HIGH" | "LOW";
  observedOutcome: "HIGH" | "LOW" | null;
  reasons: { key: string; label: string; direction: "increases_risk" | "protective"; pct: number; evidence: string | null }[];
  dataStatus: "sufficient" | "limited" | "unavailable";
  dataStatusNote: string;
  sentence: string;
}

export interface NewsTopic {
  key: string;
  label: string;
  count: number;
  pct: number;
}

export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  date: string | null;
  url: string;
  excerpt: string;
  topicKey: string;
  topicLabel: string;
  relevanceScore: number | null;
  /** E45: why the article is in the feed and where it is attributed. Absent from older backends. */
  relevanceStatus?: "validated" | "trigger_match" | "classifier_v2" | null;
  relevanceLabel?: string | null;
  province?: string | null;
  triggers?: string[];
  quarter?: string | null;
  collectedRetrospectively?: boolean | null;
}

export interface NewsResponse {
  scope: Scope;
  id: string;
  quarter: string;
  /** Publication quarter of the articles; a forecast quarter shows its information-cutoff quarter. */
  sourceQuarter: string;
  articleCount: number;
  provinceAttributed: number;
  topics: NewsTopic[];
  data: NewsArticle[];
  page: number;
  pageSize: number;
  total: number;
  /** E45: quarters covered (the evidence quarter, extended back when it holds fewer than 5 articles). */
  windowQuarters?: string[];
  validatedCount?: number;
  triggerMatchCount?: number;
  feedNote?: string | null;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: string;
  /** The view-only presentation account: every change is refused by the server. */
  isDemo?: boolean;
}

export const DEMO_READ_ONLY_NOTE = "Not available in the demo account.";

/** Sign-in refusals that mean "right password, account not active yet" (see SignInNotice). */
export const PENDING_SIGN_IN_CODES: ReadonlySet<string> = new Set(["email_not_verified", "account_pending_approval"]);

export interface LoginResponse {
  token: string;
  expiresIn: number;
  expiresAt: string;
  user: AuthUser;
}

export interface LogoutResponse {
  revoked: boolean;
  message: string;
}

// ---------------------------------------------------------------------------
// Admin — review pipeline
// ---------------------------------------------------------------------------

export interface ReviewItem {
  id: string;
  provinceId: string;
  provinceCode: string;
  province: string;
  quarter: string;
  riskScore: number;
  riskLevel: string;
  status: "Staged" | "Approved" | "Rejected";
  rejectionReason: string | null;
  rejectionNotes: string | null;
  updatedAt: string | null;
  updatedBy: number | null;
  updatedByName: string | null;
}

export interface ReviewListResponse {
  quarter: string | null;
  status: string | null;
  statuses: string[];
  rejectionReasons: string[];
  data: ReviewItem[];
}

// Public rejections endpoint. The backend's RejectionRow also carries the
// province name; the map only needs provinceId + quarter to grey a tile out.
// It deliberately carries no reviewer id or name -- those are admin-only.
export interface PublicRejectionRow {
  provinceId: string;
  quarter: string;
  reason?: string | null;
  notes?: string | null;
  timestamp?: string | null;
}

export interface RejectionsResponse {
  quarter: string | null;
  data: PublicRejectionRow[];
}

export interface AuditRow {
  id: number;
  actorEmail: string;
  actorId: number | null;
  action: string;
  subjectType: string;
  subjectId: string | null;
  provinceId: string | null;
  quarter: string | null;
  reason: string | null;
  notes: string | null;
  timestamp: string | null;
}

export interface AuditResponse {
  data: AuditRow[];
  page: number;
  pageSize: number;
  total: number;
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export interface Demographics {
  fullName?: string | null;
  email?: string | null;
  agency?: string | null;
  designation?: string | null;
  age?: string | null;
  sex?: string | null;
  clientType?: string | null;
  province?: string | null;
  municipality?: string | null;
}

export interface FeedbackSubmitBody {
  demographics: Demographics;
  // qIndex "0".."9" -> 1..5.
  answers: Record<string, number>;
  liked?: string | null;
  improvements?: string | null;
}

export interface FeedbackCreated {
  id: number;
  date: string;
  score: number;
  susVersion: string;
}

export interface FeedbackRow {
  id: number;
  date: string;
  score: number;
  susVersion: string;
  answers: Record<string, number>;
  demographics: Demographics;
  liked: string | null;
  improvements: string | null;
}

export interface FeedbackSummary {
  count: number;
  meanScore: number | null;
  medianScore: number | null;
  byClientType: Record<string, number>;
  susVersion: string;
}

export interface FeedbackListResponse {
  summary: FeedbackSummary;
  questions: string[];
  data: FeedbackRow[];
  page: number;
  pageSize: number;
  total: number;
}

// ---------------------------------------------------------------------------
// Account self-service (ACCT-1)
// ---------------------------------------------------------------------------

export interface MessageResponse {
  message: string;
}

export interface VerifyEmailResponse {
  status: string;
  message: string;
}

export interface AccountRow {
  id: number;
  email: string;
  name: string;
  office: string | null;
  status: string;
  createdAt: string | null;
  emailVerifiedAt: string | null;
  approvedAt: string | null;
  lastLoginAt: string | null;
  isDemo: boolean;
  isSelf: boolean;
}

export interface AccountsResponse {
  pending: AccountRow[];
  active: AccountRow[];
  pendingCount: number;
}

// ---------------------------------------------------------------------------
// Final forecasting engine (/api/v1/final/*): regional SWS hunger, the LightGBM evaluation and the forecast archive.
// ---------------------------------------------------------------------------

export interface SwsRound {
  quarter: string;
  fieldwork: string;
  fieldworkEnd?: string;
  published: string;
  respondentBase: string;
  national: number | null;
  ncr: number | null;
  balanceLuzon: number | null;
  visayas: number | null;
  mindanao: number | null;
  balanceLuzonMarginPts: number | null;
  ageDaysAtAsOf?: number;
}

export interface FinalOverview {
  asOf: string;
  regionalHunger: { measure: string; geography: string; latest: SwsRound; notes: string[] };
  // Not public since the release gate (2026-11-03): research hunger forecasts need an admin login.
  outlook?: {
    target: string;
    latestReadingOutlook: { area: string; targetQuarter: string; trueHorizon: number; level: number; range80: [number, number] }[];
    lightgbmForecast: { area: string; issueDate: string; lead: number; targetQuarter: string; newestSwsQuarterUsed: string; forecastLevel: number }[];
    status: string;
    reliableHorizon: number | null;
    accuracyTarget: number;
    accuracyTargetReached: boolean;
  };
  foodPrices: { definition: string; latestMonth: string; linkToHunger: string; latest: { province: string; fpd: number; squeeze: boolean }[] };
  localEvidence: string;
}

export interface FinalLeadEvaluation {
  lead: number;
  rows: number;
  metrics: { accuracy: number; balanced_accuracy: number; precision: number; recall: number; f1: number; auc: number };
  baselineAccuracy: Record<string, number>;
  maePts: number;
  persistenceMaePts: number;
  reliable: boolean;
}

export interface FinalEvaluation {
  model: string;
  target: string;
  accuracyTarget: number;
  accuracyTargetReached: boolean;
  maxReliableLead: number | null;
  leads: FinalLeadEvaluation[];
  evidenceStatus: string;
}

export interface FinalArchiveRow {
  kind: string;
  model: string;
  area: string;
  issue_date: string;
  lead: number;
  target_quarter: string;
  forecast_level: number | null;
  persistence_level: number | null;
  actual_level: number | null;
  forecast_elevated: number | null;
  actual_elevated: number | null;
}

export interface FinalArchive {
  rows: FinalArchiveRow[];
  note: string;
}

/** /api/v1/final/risk/evaluation: the Chapter I province risk forecast (CH1-LGBM), per lead. */
export interface FinalRiskLead {
  n: number;
  n_quarters: number;
  high_share: number;
  metrics: { accuracy: number; balanced_accuracy: number; precision: number; recall: number; f1: number; auc: number };
  accuracy_ci90: [number, number];
  baseline_accuracy: Record<string, number>;
  reliable: boolean;
}

/** Addendum 3: every lead the data can evaluate, with the operational meaning of each. */
export interface FinalRiskHorizonLead {
  n: number;
  n_quarters: number;
  accuracy: number;
  always_low_accuracy: number;
  reliable: boolean;
  criteria: Record<string, boolean>;
  quarters_after_issue: number;
  quarters_after_newest_sws: number[];
}

export interface FinalRiskHorizon {
  leads_evaluated: number[];
  testable_horizon_R1: number | null;
  max_reliable_lead: number | null;
  individually_passing_leads: number[];
  why_not_longer: string;
  leads: Record<string, FinalRiskHorizonLead>;
}

export interface FinalRiskEvaluation {
  max_reliable_lead: number | null;
  leads: Record<string, FinalRiskLead>;
  horizon?: FinalRiskHorizon;
}

export interface FinalRiskRow {
  province: string;
  quarter: string;
  issue_date: string;
  lead: string;
  probability: string;
  class: "HIGH" | "LOW";
  observed: string;
  kind: "forecast" | "retrospective";
  reliable_horizon: boolean;
}

export interface FinalRiskRows {
  count: number;
  maxReliableLead: number | null;
  rows: FinalRiskRow[];
}

// ---------------------------------------------------------------- FI9 Lead-1 outlook (GET /api/v1/fi9/outlook)
export interface Fi9ContextIndicator {
  indicator: string;
  value: number | null;
  unit: string;
  geographic_level: string;
}

export interface Fi9Outlook {
  note: string;
  status: "provisional" | "validated";
  current_quarter: string;
  issue_quarter: string;
  issue_date: string;
  target_quarter: string;
  horizon: string;
  model: string;
  model_version: string;
  artifact_sha256: string;
  training_data_cutoff: string;
  latest_observation_quarter: string;
  latest_observation_published: string;
  latest_data_publication_date: string | null;
  what_is_forecast: string;
  geographic_scope: string;
  measurement_type: string;
  validation_status: string;
  validation_checks: Record<string, boolean>;
  forecast: {
    class: "HIGH" | "LOW";
    p_high: number | null;
    probability_note: string;
    projected_hunger_pct: number;
    projected_hunger_interval95_pct: [number, number];
    significance_line_pct: number;
    decision_threshold_tau: number;
    class_rule: string;
    interval_note: string | null;
  };
  baseline_comparison: {
    statement: string;
    naive_persistence_accuracy: number;
    model_accuracy: number;
    always_low_accuracy: number;
    model_balanced_accuracy: number;
  } | null;
  limitations: string[];
  survey_design_note: string | null;
  p_low?: number;
  class_performance?: {
    period: string;
    n_quarters: number;
    n_high: number;
    n_low: number;
    high_caught: number;
    high_missed: number;
    false_high: number;
    low_correct: number;
    high_recall: number;
    high_precision: number;
    low_recall: number;
    low_precision: number;
    balanced_accuracy: number;
    macro_f1: number;
    accuracy: number;
    requirements_failed: string[];
    plain: string;
  };
  news_context?: { news_stress_index_z: number | null; status: string; lightgbm_with_news_p_high?: number | null };
  latest_reading_pct: number;
  normal_pct: number;
  explanation: string;
  domain_context: { note: string; domains: Record<string, Fi9ContextIndicator[]> };
}

// GET /api/v1/fi9/provincial-measurements (historical survey measurements; never forecasts)
export interface Fi9HfiasRow {
  geography: string;
  category: string;
  percent: number;
  ci95_low: number;
  ci95_high: number;
  n_households: number;
}

export interface Fi9ProvincialMeasurements {
  note: string;
  fnri_2015_hfias: Fi9HfiasRow[];
}

// ---------------------------------------------------------------- FI10 provincial outlooks (GET /api/v1/fi10/provinces)
export interface Fi10ProvinceLead {
  province: string;
  target_quarter: string;
  class: "HIGH" | "LOW";
  p_high: number;
  p_low: number;
  decision_threshold: number;
  projected_food_inflation_pct: number;
  province_high_line_pct: number;
  latest_food_inflation_pct: number;
  latest_cpi_month: string;
  drivers: { group: string; pp: number }[];
  track_record: { period: string; high_caught: number; n_high: number; false_high: number; n_low: number; balanced_accuracy: number };
}

export interface Fi10Provinces {
  issue_quarter: string;
  issue_date: string;
  what_is_forecast: string;
  lead_status: Record<string, string>;
  provinces: {
    province: string;
    lead1: Fi10ProvinceLead;
    lead2: Fi10ProvinceLead;
    poverty_incidence_pct: number;
    priority_score: number;
    priority_rank: number;
    food_access_pressure_view: string;
  }[];
  regional_hunger_reference: { area: string; target_quarter: string; class: string; p_high: number; status: string };
  food_access_pressure_note: string;
  poverty_median_pct: number;
}

// GET /api/v1/final/food-insecurity/outlook (release gate): an approved model, or validation_pending with no values.
export interface FoodInsecurityStatus {
  status: "validation_pending" | "approved";
  forecast?: null;
  reason?: string;
  message?: string;
  candidates: { model_id: string; status: string; failed_checks: string[]; checks_total?: number | null }[];
  acceptance_checks_total?: number;
  production?: { model_id: string; version: string; approved_utc: string };
  /** Approved model only: tested accuracy by lead ("1" = one quarter ahead). */
  accuracy_by_lead?: Record<string, { accuracy: number }>;
  /** Approved model only: information cut-off of the served issue (a live refresh moves it to the day of the refresh). */
  origin_date?: string;
  /** Last day of the newest period used (the cut-off minus one day) and the day the figures were checked online. */
  data_through?: string;
  data_published_by?: string;
  /** The newest period of every input the served forecast used (app.ml.inference.e168_system.data_used). */
  data_used?: { group: string; name: string; source: string; level: string; period: string; note?: string; label?: string; when?: string }[];
}
