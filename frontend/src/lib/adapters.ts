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
import { quarterOrdinal } from "./quarters";

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
    // E28: the API sends riskLevel null for every LGU (no band for an unvalidated, disaggregated index) and
    // riskIndex null when its province has no estimate; neither becomes a band or a zero here.
    riskScore: m.riskIndex ?? Number.NaN,
    riskLevel: (m.riskLevel ?? "unrated") as MunicipalityData["riskLevel"],
    population: m.population,
    // E27 fix: a missing municipal estimate stays missing (it used to become 0%).
    povertyRate: m.povertyRate ?? null,
    povertyNote: m.povertyRate == null
      ? (m.povertyLimitation ??
        "No PSA municipal poverty estimate; the ranking uses a province-mean substitute, so this LGU's position within its province reflects population density only.")
      : null,
    classification: m.classification as MunicipalityData["classification"],
    limitedSignal: m.limitedSignal,
    disaggregationLabel: m.disaggregationLabel,
    // Not produced by the API -- see file header.
    householdsAtRisk: 0,
    fpsi: 0,
    momChange: 0,
  };
}

// The backend's Quarter (state: "actual" | "current" | "forecast" |
// "unavailable") -> the slider's Quarter (forecast / current / past booleans).
// "forecast" is the E20 quarter (2027-Q1) appended after the nowcast's newest
// quarter; "unavailable" is a quarter with no score: selectable, shown gray.
// Given the calendar quarter, `current` is the quarter that contains today --
// the slider's meaning -- rather than the newest scored one.
export function apiQuarterToSlider(q: ApiQuarter, calendarQuarter?: string): SliderQuarter {
  const o = quarterOrdinal(q.id);
  const now = calendarQuarter ? quarterOrdinal(calendarQuarter) : null;
  return {
    id: q.id,
    year: q.year,
    q: q.q as 1 | 2 | 3 | 4,
    label: q.label,
    monthsLabel: q.monthsLabel,
    current: now === null ? q.state === "current" : o === now,
    past: now === null ? q.state === "actual" : o < now,
    forecast: q.state === "forecast" || (now !== null && o > now),
    locked: false,
    noData: q.state === "unavailable",
    reason: q.reason ?? undefined,
  };
}
