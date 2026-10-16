export type RiskLevel = "low" | "moderate" | "high" | "severe";

export interface RegionData {
  id: string;
  name: string;
  riskScore: number;
  riskLevel: RiskLevel;
  population: number;
  povertyRate: number;
  unemploymentRate: number;
  cropYieldIndex: number;
  accessToFood: number;
  householdsAtRisk: number;
  fpsi: number; // Food Price Stress Index
  momChange: number; // Quarter-over-quarter change %
  limitedSignal: boolean; // fewer than the minimum geocoded articles this quarter
  articleCount: number;
  seriesMonitored: number | null;
  seriesNeedingReview: number | null; // of seriesMonitored, how many are below the model's confidence cutoff
  historicalTrend: { year: number; score: number }[];
  featureImportance: { feature: string; importance: number }[];
  shapValues: { feature: string; value: number }[]; // positive = increases risk, negative = decreases
  whatIfFeatures: { feature: string; value: number; min: number; max: number; step: number; unit: string }[];
  lat: number;
  lng: number;
}

export interface MunicipalityData {
  id: string;            // e.g. "cavite-tagaytay"
  name: string;          // e.g. "Tagaytay"
  provinceId: string;    // e.g. "cavite"
  provinceName: string;  // e.g. "Cavite"
  riskScore: number;
  riskLevel: RiskLevel;
  population: number;
  povertyRate: number;
  householdsAtRisk: number;
  fpsi: number;
  momChange: number;
  limitedSignal: boolean;
  // Why the province score was reweighted for this LGU (poverty/density).
  disaggregationLabel: string;
  classification: "City" | "Municipality";
  /** E45: the map colour's meaning (vulnerability band or insufficient data). */
  vulnerabilityIndex?: number | null;
  mapStatus?: "vulnerability" | "insufficient_data" | null;
  mapCategory?: "low" | "medium" | "high" | null;
  mapLabel?: string | null;
  mapNote?: string | null;
}

/** E45: municipal map colours. A distinct (purple) scale so a vulnerability band is never read as a forecast risk
 * level; insufficient data is a visible neutral gray, never transparent. */
export const LGU_MAP_COLORS = {
  low: "#c4b5fd",
  medium: "#8b5cf6",
  high: "#5b21b6",
  insufficient_data: "#9ca3af",
} as const;

export function lguMapColor(m: Pick<MunicipalityData, "mapStatus" | "mapCategory"> | null | undefined): string {
  if (!m || m.mapStatus !== "vulnerability" || !m.mapCategory) return LGU_MAP_COLORS.insufficient_data;
  return LGU_MAP_COLORS[m.mapCategory];
}

export interface FilterState {
  year: number;
  riskLevel: RiskLevel | "all";
  region: string;
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  low: "#EAB308",
  moderate: "#eab308",
  high: "#EF4444",
  severe: "#ef4444",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: "Low Risk",
  moderate: "Moderate Risk",
  high: "High Risk",
  severe: "Severe Risk",
};
