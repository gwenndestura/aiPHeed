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
  state: "actual" | "current";
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
}

export interface ExplainabilityResponse {
  scope: Scope;
  id: string;
  name: string;
  quarter: string;
  riskScore: number;
  triggers: Trigger[];
  articleCount: number;
  triggerMatchedArticles: number;
  narrative: string;
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
}

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

// Public rejections endpoint. The backend's current RejectionRow also carries
// reason/notes/rejectedBy/rejectedByName; the map only needs provinceId +
// quarter to grey a tile out, so this mirror only declares what's consumed.
export interface PublicRejectionRow {
  provinceId: string;
  quarter: string;
  reason?: string | null;
  notes?: string | null;
  rejectedBy?: number | null;
  rejectedByName?: string | null;
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
