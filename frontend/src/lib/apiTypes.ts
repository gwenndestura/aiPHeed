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
  riskIndex: number;
  riskLevel: string;
  // Never null -- a reweighted province number, not an independent forecast.
  disaggregationLabel: string;
  limitedSignal: boolean;
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
  provinceId?: string | null;
  provinceName?: string | null;
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
}

export type TriggerStatus =
  | "contributes"
  | "no_effect"
  | "data_not_in_model"
  | "stale"
  | "no_model_input"
  | "no_data";

export interface ExplainabilityResponse {
  scope: Scope;
  id: string;
  name: string;
  quarter: string;
  riskScore: number;
  triggers: Trigger[];
  otherPct: number;
  articleCount: number;
  triggerMatchedArticles: number;
  narrative: string;
  /** Third-person interpretation for the PDF report. Plain ASCII. */
  formalInterpretation: string;
  note: string;
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
