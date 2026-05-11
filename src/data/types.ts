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
  momChange: number; // Month-over-month change %
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
