// E18 development research view: types and pure helpers (tested in src/test/research.test.ts).

export interface ProvinceValue {
  code: string;
  name: string;
  F: number | null;
  D: number | null;
  S1: number | null;
}

export interface QuarterHistory {
  quarter: string;
  hunger_balance_luzon: number | null;
  provinces: ProvinceValue[];
  complete_five: boolean;
}

export interface ResearchData {
  generated_from_run: string;
  status: string;
  caveats: string[];
  history: QuarterHistory[];
  forecast_2027Q1: Record<string, any>;
  classification_metrics: Array<Record<string, any>>;
  classification_selection: Record<string, any>;
  continuous_metrics: Array<Record<string, any>>;
  lead_time: { max_supported: number | null; note: string };
}

export const LABEL_THRESHOLD = 14.6;

/** Rank provinces by relative price pressure D (1 = highest). Returns [] when any D is missing (no imputation). */
export function rankByD(provinces: ProvinceValue[]): Array<ProvinceValue & { rank: number }> {
  if (provinces.length !== 5 || provinces.some((p) => p.D === null || Number.isNaN(p.D))) return [];
  const sorted = [...provinces].sort((a, b) => (b.D as number) - (a.D as number));
  return sorted.map((p) => ({ ...p, rank: 1 + sorted.filter((q) => (q.D as number) > (p.D as number)).length }));
}

/** Constructed label from S1; null stays null (shown as "insufficient data", never LOW). */
export function constructedLabel(s1: number | null): "HIGH" | "LOW" | null {
  if (s1 === null || Number.isNaN(s1)) return null;
  return s1 > LABEL_THRESHOLD ? "HIGH" : "LOW";
}

export function fmt(x: number | null | undefined, digits = 2): string {
  return x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(digits);
}

/** Colour for D: diverging around 0 (relative pressure), never a risk colour. */
export function dColor(d: number | null): string {
  if (d === null) return "#9ca3af";
  if (d > 1) return "#b45309";
  if (d > 0) return "#f59e0b";
  if (d > -1) return "#60a5fa";
  return "#1d4ed8";
}
