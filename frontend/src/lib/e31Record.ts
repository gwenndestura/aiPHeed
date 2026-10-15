/**
 * Served record. Schema e36/1 (backend/scripts/build_record_e36.py, the E36 LightGBM) is served now; schema e31/1
 * (runner/build_record_e31.py, PCF21) is the earlier record and is still readable. The API (/api/v1/quarterly/e31/*,
 * paths kept), the main map, /da-brief, /news and the PDF read the same bytes.
 */
import { API_BASE_URL } from "@/lib/api";

export type Mode = "BACKTEST" | "RETROSPECTIVE_BLIND" | "NOWCAST" | "FORECAST";

export interface Driver { key: string; factor: string; value: number; contribution: number; kind: string }

export interface ProvinceEstimate {
  province: string;
  p_high: number;
  signal: "STRONG" | "MODERATE" | "UNCERTAIN";
  S1_forecast?: number;
  S1_80pct_interval?: [number, number];
  drivers?: Driver[];
  driver_method?: string;
  observed_S1?: number | null;
  observed_label?: "HIGH" | "LOW" | null;
  persistence_p?: number;
}

export interface EvidenceWindow {
  mode: string; target_quarter: string; lead: number; evidence_quarter: string; window_start_ph: string;
  window_end_excl_ph: string; information_cutoff_ph: string; coverage: "FULL" | "PARTIAL"; days_covered: number;
  days_in_quarter: number; limitation: string;
}

export interface QuarterRow {
  quarter: string;
  mode: Mode;
  lead: number;
  origin: string;
  information_cutoff: string;
  status: string;
  threshold: number;
  provinces: Record<string, ProvinceEstimate>;
  provenance?: {
    mode: string; generated_at: string; information_cutoff: string; news_evidence_window: EvidenceWindow;
    news_version: Record<string, string>; n_articles_used_by_model: number;
    supporting_news: { n_articles_in_window: number; n_province_attributed: number };
  };
  scores?: { source: string; arm: string; lead: number; accuracy: number; brier: number; n_HIGH_outcome: number }[];
  H_forecast?: number;
  p_regional_H_above_threshold?: number;
}

export interface NewsArticle {
  article_key: string; title: string; outlet: string; published_ph: string; quarter: string; province_code: string;
  province: string; relevance: "DIRECT" | "INDIRECT" | "NONE"; link: string; description: string | null;
}

export interface FunnelRow {
  province: string; province_code: string; quarter: string; collected_by_province_queries: number;
  province_attributed: number; relevant_R1: number; admitted_after_dedup: number; direct: number; indirect: number;
  FSSI_v2: number | null; evidence_status_v2: string; in_FSSI_v1: number; evidence_status_v1: string | null;
}

export interface ProvinceNow {
  province: string;
  nowcast_2026Q4: ProvinceEstimate;
  forecast_2027Q1: ProvinceEstimate;
  measured_relative_food_inflation_pp: Record<string, number>;
  price_pressure_text: string;
  news_2026Q4_to_cutoff: FunnelRow | null;
  attention: string;
  suggested_use: string;
  evidence_status: string;
  disclaimer: string;
}

export interface E36ProvinceNow {
  province: string;
  forecast_quarter: string;
  forecast: ProvinceEstimate;
  latest_backtest: ProvinceEstimate & { quarter: string };
  measured_relative_food_inflation_pp: Record<string, number>;
  price_pressure_text: string;
  news_evidence: FunnelRow | null;
  news_evidence_quarter: string;
  explanation_text: string;
  attention: string;
  suggested_use: string;
  evidence_status: string;
  disclaimer: string;
}

export interface ModelEvalRow {
  arm: string; key: string; correct: number; n: number; accuracy_lead1: number; accuracy_ci95: [number, number];
  balanced_accuracy: number | null; precision: number | null; recall: number | null; specificity: number | null;
  f1: number | null; roc_auc: number | null; brier: number; above_75pct: boolean;
}

export interface E36Record extends Omit<E31Record, "schema" | "provinces_now" | "validation" | "served_engine"> {
  schema: "e36/1";
  served_engine: { name: string; version: string; why_served: string; evidence_status: string; sha256: string;
    config: { feature_set: string; features: string[]; grid_id: string; training_rows: number } };
  provinces_now: Record<string, E36ProvinceNow>;
  validation: {
    news_relevance: E31Record["validation"]["news_relevance"];
    model_evaluation: { basis: string; dates: string[]; rows: ModelEvalRow[] };
    threshold_75pct: { verdict: string; point_met: boolean; demonstrated: boolean;
      rows: { arm: string; accuracy_lead1: number; above_75pct: boolean }[] };
    prospective_2026Q4: { frozen_sha256: string; origin: string; status: string };
  };
}

export type ServedRecord = E31Record | E36Record;

export const isE36 = (r: ServedRecord): r is E36Record => r.schema === "e36/1";

export interface E31Record {
  schema: "e31/1";
  title: string;
  generated_at: string;
  information_cutoff: string;
  data_authorization: string;
  served_engine: { name: string; why_served: string; evidence_status: string };
  target_definition: Record<string, string>;
  regional_hunger: {
    what: string; kind: string; geographic_level: string; change_last_two_pp: number;
    rounds: { quarter: string; round: string; hunger_pct: number; published: string; date_type: string }[];
  };
  quarters: QuarterRow[];
  provinces_now: Record<string, ProvinceNow>;
  lgu_ranking: { meaning: string; rows: { lgu_code: string; lgu_name: string; province: string; province_code: string;
    risk_index: number | null; rank_in_province: number | null; poverty_value_kind: string }[] };
  news: { source: string; relevance_rule: string; totals: Record<string, number>; by_province_quarter: FunnelRow[];
    articles: NewsArticle[] };
  validation: {
    news_relevance: { holdout: { gates: Record<string, { precision: number; recall: number; f1: number;
      ci95_precision_recall_f1: [number, number][] }> }; deployed_rule: string };
    threshold_75pct: { verdict: string; rows: { arm: string; accuracy_lead1: number; above_75pct: boolean }[] };
    unseen_quarter_2026Q3: { caveat: string };
  };
  limitations: string[];
  disclaimer: string;
  content_sha256: string;
}

export const PROVINCE_ORDER = ["PH040100000", "PH040200000", "PH040500000", "PH040400000", "PH040300000"];

export const MODE_TEXT: Record<Mode, string> = {
  BACKTEST: "Backtest (development evidence)",
  RETROSPECTIVE_BLIND: "Frozen forecast, scored on the released outcome",
  NOWCAST: "Nowcast: quarter under way",
  FORECAST: "Forecast: one quarter ahead",
};

export async function loadE31(): Promise<ServedRecord> {
  try {
    const r = await fetch(`${API_BASE_URL}/api/v1/quarterly/e31/record`);
    if (r.ok) return (await r.json()) as ServedRecord;
  } catch {
    /* fall back to the identical static copy */
  }
  const s = await fetch("/e36_record.json");
  if (!s.ok) throw new Error(`record unavailable (${s.status})`);
  return (await s.json()) as ServedRecord;
}

export const pct = (p: number | null | undefined) => (p == null ? "–" : `${Math.round(p * 100)}%`);
