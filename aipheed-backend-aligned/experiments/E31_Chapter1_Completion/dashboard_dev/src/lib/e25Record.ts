/**
 * E25 forecast timeline record (2025-Q1 .. 2027-Q1).
 *
 * ONE record is produced by runner/build_outputs.py. The API (/api/v1/quarterly/e25-timeline), this page and the
 * PDF report all read the same bytes; the record carries its own content SHA-256, shown on the page.
 */
import { API_BASE_URL } from "@/lib/api";

export type Signal = "STRONG" | "MODERATE" | "UNCERTAIN";

export interface BacktestForecast {
  model: string;
  lead_quarters: number;
  origin: string;
  information_cutoff: string;
  p_high: number;
  decision: "HIGH" | "LOW";
  signal: Signal;
  z: number;
  S1_forecast: number;
  S1_80pct_interval: [number, number];
  regional_part_H_minus_tau: number;
  provincial_part_2D: number;
  variance_share_regional: number;
  indicative_only: boolean;
  correct: boolean;
}

export interface SealedForecast {
  seal: string;
  origin: string;
  information_cutoff?: string;
  target: string;
  arm: string;
  lead: number;
  p: number;
  signal?: Signal;
  indicative_only: boolean;
  outcome: string;
  FINAL_T1?: boolean;
  S1_forecast?: number;
  S1_80pct_interval?: [number, number];
  threshold?: number;
  regional_part_H_minus_tau?: number;
  provincial_part_2D?: number;
}

export interface ProvinceEntry {
  province: string;
  measured?: { food_cpi_yoy_pct: number | null; D_relative_food_inflation_pp: number | null; ci: string };
  actual_label?: "HIGH" | "LOW" | null;
  S1_measured?: number;
  threshold?: number;
  forecast?: BacktestForecast | null;
  persistence?: number | null;
  proposed_lgbm_p_high?: number | null;
  state?: string;
  sealed?: SealedForecast[];
  sealed_evaluation_forecasts?: { seal: string; arm: string; lead: number; p: number; note: string }[];
  price_pressure_forecast?: { model: string; p_above_regional_mean: number; actual: string; indicative_only: boolean };
}

export interface QuarterEntry {
  quarter: string;
  display: string;
  kind: string;
  status?: string;
  missing_inputs?: string[];
  information_cutoff?: string;
  who_supplies?: Record<string, string>;
  measured_regional?: {
    sws_hunger_balance_luzon_pct?: number | null;
    approx_95ci_n600_srs?: [number, number] | null;
    ci_note?: string;
    status: string;
  };
  provinces: Record<string, ProvinceEntry>;
}

export interface E25Record {
  title: string;
  run_id: string;
  protocol_sha256: string;
  label_definition: string;
  score_is_constructed: string;
  indicative_only_reason: string;
  signal_rule: string;
  content_sha256: string;
  quarters: QuarterEntry[];
}

export type TileState =
  | { kind: "BACKTEST"; f: BacktestForecast; actual: "HIGH" | "LOW" | null | undefined }
  | { kind: "NO_LABEL"; reason: string }
  | { kind: "SEALED_PENDING"; sealed: SealedForecast[] }
  | { kind: "MISSING_INPUTS"; missing: string[] };

/** Classify one quarter x province cell. A cell without a forecast is never shown as LOW risk. */
export function tileState(q: QuarterEntry, provinceCode: string): TileState {
  const p = q.provinces[provinceCode];
  if (q.kind.startsWith("OPERATIONAL")) return { kind: "MISSING_INPUTS", missing: q.missing_inputs ?? [] };
  if (q.kind.startsWith("SEALED")) return { kind: "SEALED_PENDING", sealed: p?.sealed ?? [] };
  if (p?.forecast) return { kind: "BACKTEST", f: p.forecast, actual: p.actual_label };
  return { kind: "NO_LABEL", reason: p?.state ?? "no forecast" };
}

export async function loadE25Record(fetchImpl: typeof fetch = fetch): Promise<E25Record> {
  try {
    const r = await fetchImpl(new URL("/api/v1/quarterly/e25-timeline", API_BASE_URL).toString());
    if (r.ok) return (await r.json()) as E25Record;
  } catch {
    /* fall back to the static copy of the same record */
  }
  const r = await fetchImpl("/e25_forecast_record.json");
  if (!r.ok) throw new Error("E25 forecast record not available");
  return (await r.json()) as E25Record;
}

export const pct = (x: number) => `${Math.round(x * 100)}%`;
