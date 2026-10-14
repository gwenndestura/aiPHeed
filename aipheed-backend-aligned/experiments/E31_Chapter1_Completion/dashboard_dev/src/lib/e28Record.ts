/**
 * E28 DA brief record (schema 3). ONE record is produced by runner/build_record_e28.py; the API
 * (/api/v1/quarterly/e28/brief), this page and the PDF (/api/v1/quarterly/e28/brief.pdf) read the same bytes.
 */
import { API_BASE_URL } from "@/lib/api";

export interface Driver {
  factor: string;
  contribution: number;
  direction: "raises" | "lowers";
  explanation: string;
}

export interface ProvinceBrief {
  province: string;
  target: string;
  geographic_scope: string;
  target_quarter: string;
  origin: string;
  lead_quarters: number;
  information_cutoff: string;
  evidence_status: "EXPERIMENTAL" | "VALIDATED";
  horizon_determination: string;
  estimate: { p_above_threshold: number; S1_80pct_interval: [number, number] | null; tau: number } | null;
  signal: "STRONG" | "MODERATE" | "UNCERTAIN" | null;
  /** Only ever set for a VALIDATED lead. */
  category: "HIGH" | "LOW" | null;
  category_withheld_reason?: string | null;
  headline: string;
  drivers: Driver[];
  driver_method?: string;
  price_trend?: string;
  missing_inputs: string[];
  data_coverage: Record<string, string | number | null>;
  evidence_sufficiency: string;
  limitations: string[];
  attention: string;
  suggested_use: string;
  disclaimer: string;
}

export interface LguRow {
  lgu_code: string;
  lgu_name: string;
  lgu_type: string;
  province: string;
  density_per_km2: number;
  poverty_lgu_estimate: number | null;
  poverty_value_used: number;
  poverty_value_kind: string;
  risk_index: number | null;
  rank_region: number | null;
  rank_in_province: number | null;
  tied: boolean;
  limitation: string;
  evidence_status: string;
}

export interface EvalRow {
  arm: string;
  lead1_accuracy: number;
  lead1_brier: number;
  lead1_auc: number | null;
  lead1_auc_flag: string;
  pooled_accuracy: number;
  pooled_brier: number;
  furthest_reliable_horizon: number | string | null;
  qualifies: boolean;
}

export interface E28Record {
  schema: 3;
  title: string;
  status_banner: string;
  content_sha256: string;
  signal_rule: string;
  forecast_quarter: { quarter: string; kind: string; provinces: Record<string, ProvinceBrief> };
  operational_quarter: { quarter: string; status: string; missing: string[]; provinces: Record<string, ProvinceBrief> };
  target_validity: { what_the_target_can_support: string[]; what_it_cannot_support: string[]; what_would_be_needed: string[] };
  evaluation: Record<string, { rows: EvalRow[] }>;
  news_coverage: {
    quarters: [string, string];
    province_quarters: number;
    coverage_status_counts: Record<string, number>;
    latest_quarter: string;
    note: string;
    rows: { province: string; quarter: string; coverage_status: string; included_in_fssi: number }[];
  };
  lgu_ranking: { meaning: string; does_not_mean: string[]; method: string; rows: LguRow[]; rows_sha256: string };
  disclaimer: string;
}

export const PROVINCE_ORDER = ["PH040500000", "PH040100000", "PH040200000", "PH040300000", "PH040400000"];

/** The only words a brief may use for its estimate: a category only for a VALIDATED lead. */
export function estimateWording(b: ProvinceBrief): { text: string; classified: boolean } {
  if (!b.estimate) return { text: "No estimate (missing inputs)", classified: false };
  const pct = Math.round(b.estimate.p_above_threshold * 100);
  if (b.evidence_status === "VALIDATED" && b.category) return { text: `${b.category} (P ${pct}%)`, classified: true };
  return { text: `P(above threshold) ${pct}%`, classified: false };
}

export async function loadE28Record(): Promise<E28Record> {
  try {
    const r = await fetch(`${API_BASE_URL}/quarterly/e28/brief`);
    if (r.ok) return (await r.json()) as E28Record;
  } catch {
    /* fall back to the identical static copy */
  }
  const s = await fetch("/e28_da_brief_record.json");
  return (await s.json()) as E28Record;
}
