// src/lib/adapters.ts
// ---------------------
// Maps backend API shapes (apiTypes.ts) onto the existing UI-local shapes
// (data/types.ts, QuarterTimeSlider's Quarter) the map components already
// render, so this is the only file that needs to change if a backend field
// is renamed.
//
// data/types.ts is left untouched on purpose: RegionData/MunicipalityData
// declare several fields (unemploymentRate, cropYieldIndex, fpsi,
// historicalTrend, featureImportance, shapValues, whatIfFeatures,
// householdsAtRisk) that only a handful of already-unreferenced components
// read (DashboardOverview, NationalTrendChart, RegionalRankingsTable,
// RegionSidebar, WhatIfSandbox -- none imported from any route). No
// backend endpoint produces those numbers. Rather than invent values for
// them, every live, rendered screen (PhilippineMap, LeftPanel,
// RightAnalyticsPanel, MapDashboard) only ever reads the fields populated
// below from the real API; the rest are filled with inert placeholders
// purely so the type still satisfies those unused components' props.

import type { MunicipalitySummary, ProvinceSummary, Quarter as ApiQuarter } from "./apiTypes";
import type { MunicipalityData, RegionData } from "@/data/types";
import type { Quarter as SliderQuarter } from "@/components/QuarterTimeSlider";

export function provinceToRegion(p: ProvinceSummary): RegionData {
  return {
    id: p.id,
    name: p.name,
    riskScore: p.riskScore ?? 0,
    riskLevel: (p.riskLevel as RegionData["riskLevel"]) ?? "low",
    population: p.population ?? 0,
    povertyRate: p.povertyRate ?? 0,
    momChange: p.qoqChangePct ?? 0,
    limitedSignal: p.limitedSignal,
    articleCount: p.articleCount,
    seriesMonitored: p.seriesMonitored,
    seriesNeedingReview: p.seriesNeedingReview,
    lat: p.centroid.lat,
    lng: p.centroid.lng,
    // Not produced by the API -- see file header. Left inert; no rendered
    // screen reads these off a province.
    unemploymentRate: 0,
    cropYieldIndex: 0,
    accessToFood: 0,
    householdsAtRisk: 0,
    fpsi: 0,
    historicalTrend: [],
    featureImportance: [],
    shapValues: [],
    whatIfFeatures: [],
  };
}

export function municipalityToData(m: MunicipalitySummary, provinceName: string): MunicipalityData {
  return {
    id: m.id,
    name: m.name,
    provinceId: m.provinceId,
    provinceName,
    riskScore: m.riskIndex,
    riskLevel: m.riskLevel as MunicipalityData["riskLevel"],
    population: m.population,
    povertyRate: m.povertyRate ?? 0,
    classification: m.classification as MunicipalityData["classification"],
    limitedSignal: m.limitedSignal,
    disaggregationLabel: m.disaggregationLabel,
    // Not produced by the API -- see file header.
    householdsAtRisk: 0,
    fpsi: 0,
    momChange: 0,
  };
}

// The backend's Quarter (state: "actual" | "current") -> the slider's Quarter
// (forecast / current / past booleans). The API never returns a "forecast"
// state today -- every scorable quarter is an observed one -- but the slider
// keeps the field so it degrades gracefully if that ever changes.
export function apiQuarterToSlider(q: ApiQuarter): SliderQuarter {
  return {
    id: q.id,
    year: q.year,
    q: q.q as 1 | 2 | 3 | 4,
    label: q.label,
    monthsLabel: q.monthsLabel,
    current: q.state === "current",
    past: q.state === "actual",
    forecast: false,
    locked: false,
  };
}
