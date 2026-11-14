// Exact SHAP explanation of the official FINAL (RATE + MIND) forecasts: preview API /api/v1/final/shap/*.
// Read-only; the backend reads the sealed-path SHAP tables (research_notes/aiPHeed_final_shap_20261113).
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export interface ShapContributor {
  feature: string;
  name: string;
  group: string;
  measures?: string;
  value?: number | null;
  valueText?: string;
  referenceMedian?: number;
  missing?: boolean;
  shapLogOdds: number;
  direction: "raises" | "lowers" | "near zero";
  seedsUsing?: number;
  explanation: string;
  period: string;
  source: string;
  coverage?: string;
  kind: string;
  component: string;
}

export interface ShapProvince {
  /** The served issue this explanation belongs to (e.g. "2026-Q4"). */
  issue?: string | null;
  available: boolean;
  reason?: string;
  scope?: "province" | "region";
  name?: string;
  quarter: string;
  explainedOutput: string;
  rateMind: string;
  probabilityNote: string;
  nearZeroLogOdds: number;
  official?: { class: "HIGH" | "LOW"; pHigh: number; sharePct: number; riskPct?: number; highAtSharePct: number };
  provinces?: { province: string; class: string; pHigh: number; sharePct: number; riskPct?: number }[];
  waterfall?: {
    anchorLogOdds: number;
    anchorSharePct?: number;
    anchorText?: string;
    expectedLogOdds: number;
    expectedText?: string;
    inputsLogOdds: number;
    forecastLogOdds: number;
    forecastSharePct?: number;
    additivityError?: number;
  };
  contributors?: ShapContributor[];
  inputsUsed?: number;
  summary?: string[];
  groups?: ShapGroup[];
  otherPct?: number;
}

/** One factor group: exact input SHAP summed within the group; pct = share of the total absolute group SHAP. */
export interface ShapGroup {
  key: string;
  label: string;
  pct: number;
  signedContribution: number;
  direction: "increases_risk" | "protective" | "no_effect";
  status: "contributes" | "no_effect";
  plainEvidence: string;
  inputs: string[];
}

export interface ShapGlobal {
  available: boolean;
  reason?: string;
  reference?: string;
  explainedOutput?: string;
  items?: { rank: number; feature: string; name: string; group: string; component: string; meanAbsShapLogOdds: number; fitsUsing: string; interpretation: string }[];
}

export interface ShapContext {
  supportingContext: { indicator: string; role: string }[];
  notUsed: { feature: string; name: string; group: string; reason: string }[];
  notInModel: { name: string; reason: string }[];
}

const HOUR = 60 * 60 * 1000;

export function useFinalShap(id: string, quarter?: string) {
  return useQuery({
    queryKey: ["final-shap", id, quarter],
    queryFn: () => api.get<ShapProvince>("/api/v1/final/shap/province", { id, quarter }, { auth: false }),
    enabled: !!id && !!quarter,
    staleTime: HOUR,
  });
}

export function useFinalShapGlobal() {
  return useQuery({
    queryKey: ["final-shap-global"],
    queryFn: () => api.get<ShapGlobal>("/api/v1/final/shap/global", {}, { auth: false }),
    staleTime: HOUR,
  });
}

export function useFinalShapContext(quarter?: string) {
  return useQuery({
    queryKey: ["final-shap-context", quarter],
    queryFn: () => api.get<ShapContext>("/api/v1/final/shap/context", { quarter }, { auth: false }),
    enabled: !!quarter,
    staleTime: HOUR,
  });
}
