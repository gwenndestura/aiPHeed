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
