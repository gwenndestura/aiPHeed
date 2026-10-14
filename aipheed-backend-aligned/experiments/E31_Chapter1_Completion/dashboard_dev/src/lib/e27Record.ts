/**
 * E27 forecast timeline record (schema 2). ONE record is produced by runner/build_record_e27.py; the API
 * (/api/v1/quarterly/timeline), this page and the PDF (/api/v1/quarterly/timeline.pdf) all read the same bytes.
 */
import { API_BASE_URL } from "@/lib/api";

export type EvidenceStatus = "EXPERIMENTAL" | "VALIDATED";

export interface Evidence {
  status: EvidenceStatus;
  basis: string;
  unseen_scored_dates: number;
}

export interface RiskView {
  p_above_threshold: number;
  S1_80pct_interval: [number, number] | null;
  S1_forecast: number | null;
  threshold: number | null;
  lead_quarters: number;
  origin: string | null;
  information_cutoff: string | null;
  evidence: Evidence;
  /** Only ever set for a VALIDATED lead. */
  decision: "HIGH" | "LOW" | null;
  display_label: string;
  kind?: string;
  approved_label_measured?: "HIGH" | "LOW" | null;
  S1_measured?: number;
  what?: string;
  ledger?: { file: string; seq: number; entry_hash: string };
}

export interface SealedEntry {
  target: "T1" | "T2";
  target_meaning: string;
  arm: string;
  lead: number;
  origin: string;
  information_cutoff: string | null;
  p: number;
  seal: string;
  outcome: string;
  final: boolean;
  ledger?: { seq: number; entry_hash: string };
}

export interface Dependency {
  id: string;
  status: string;
  blocking: boolean;
  needs: string;
  data_through_quarter: string | null;
  affects: string;
  supplier: string;
  normal_release: string;
}

export interface ProvinceRow {
  province: string;
  risk: RiskView | null;
  risk_state?: string;
  price_pressure: {
    kind: string;
    model: string;
    p_above_regional_mean: number;
    measured_direction: string;
    evidence: string;
  } | null;
  measured?: { food_cpi_yoy_pct: number | null; D_relative_food_inflation_pp: number | null; ci: string } | null;
  sealed?: SealedEntry[];
  experimental_estimate?: RiskView;
}

export interface QuarterRow {
  quarter: string;
  display: string;
  kind: string;
  state: "BACKTEST" | "SEALED_PENDING" | "MISSING_INPUTS" | "READY";
  status?: string;
  information_cutoff?: string;
  dependencies?: Dependency[];
  regional_layer: { what: string; measured_pct: number | null; approx_95ci: [number, number] | null; status: string };
  provinces: Record<string, ProvinceRow>;
}

export interface E27Record {
  schema: 2;
  title: string;
  content_sha256: string;
  score_is_constructed: string;
  evidence_summary: {
    status: string;
    statement: string;
    unseen_scored_quarters: number;
    adviser_approval_A1: boolean;
    accuracy_note: string;
  };
  layers: Record<"regional_risk" | "price_pressure" | "local", string>;
  official_anchor: {
    what: string;
    use: string;
    publication_date: string;
    values: Record<string, Record<"2021" | "2023", { pct: number; cv_pct: number }>>;
  };
  quarters: QuarterRow[];
}

export const PROVINCE_CODES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"];

/** How one risk value may be shown. A HIGH/LOW word appears only for a validated lead. */
export function riskWording(r: RiskView): { headline: string; classified: boolean } {
  const pct = `${Math.round(r.p_above_threshold * 100)}%`;
  if (r.evidence.status === "VALIDATED" && r.decision) {
    return { headline: `${r.decision} (P ${pct})`, classified: true };
  }
  return { headline: `P(above threshold) ${pct}`, classified: false };
}

export async function loadE27Record(fetchImpl: typeof fetch = fetch): Promise<E27Record> {
  try {
    const r = await fetchImpl(new URL("/api/v1/quarterly/timeline", API_BASE_URL).toString());
    if (r.ok) return (await r.json()) as E27Record;
  } catch {
    /* fall back to the static copy of the same record */
  }
  const r = await fetchImpl("/e27_timeline_record.json");
  if (!r.ok) throw new Error("E27 forecast record not available");
  return (await r.json()) as E27Record;
}
