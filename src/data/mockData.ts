import { RegionData, RiskLevel, MunicipalityData } from "./types";
import muniListRaw from "./calabarzon-municipalities.json";

function getRiskLevel(score: number): RiskLevel {
  if (score < 0.35) return "low";
  if (score < 0.50) return "moderate";
  if (score < 0.65) return "high";
  return "severe";
}

function generateTrend(baseScore: number): { year: number; score: number }[] {
  const months = [];
  for (let m = 6; m <= 17; m++) {
    months.push({
      year: m,
      score: Math.max(0.1, Math.min(0.95, baseScore + (Math.random() - 0.4) * 0.15 + (m - 6) * 0.012)),
    });
  }
  return months;
}

const defaultShapValues = (score: number) => [
  { feature: "Engel Coefficient", value: 0.15 + Math.random() * 0.1 },
  { feature: "Income Decile", value: -(0.08 + Math.random() * 0.06) },
  { feature: "FPSI (Price Stress)", value: 0.12 + Math.random() * 0.08 },
  { feature: "Dependency Ratio", value: 0.10 + Math.random() * 0.06 },
  { feature: "Household Size", value: 0.06 + Math.random() * 0.04 },
  { feature: "Income Sources", value: -(0.04 + Math.random() * 0.03) },
  { feature: "OFW Flag", value: -(0.02 + Math.random() * 0.02) },
  { feature: "Housing Tenure", value: -(0.01 + Math.random() * 0.02) },
];

const defaultWhatIf = () => [
  { feature: "Income Decile", value: 3, min: 1, max: 10, step: 1, unit: "" },
  { feature: "Dependency Ratio", value: 0.65, min: 0, max: 1, step: 0.05, unit: "" },
  { feature: "Household Size", value: 5, min: 1, max: 12, step: 1, unit: " members" },
  { feature: "Price Stress (FPSI)", value: 0.03, min: 0, max: 0.2, step: 0.005, unit: "" },
  { feature: "OFW Remittance", value: 0, min: 0, max: 1, step: 1, unit: "" },
];

const defaultFeatures = () => [
  { feature: "Engel Coefficient", importance: 0.28 + Math.random() * 0.1 },
  { feature: "Income Decile", importance: 0.22 + Math.random() * 0.08 },
  { feature: "FPSI", importance: 0.15 + Math.random() * 0.08 },
  { feature: "Dependency Ratio", importance: 0.12 + Math.random() * 0.06 },
  { feature: "Household Size", importance: 0.08 + Math.random() * 0.06 },
  { feature: "Income Sources", importance: 0.05 + Math.random() * 0.04 },
];

// === CALABARZON Provinces (top-level "regions") ===
const provincesRaw: Omit<RegionData, "riskLevel" | "historicalTrend" | "featureImportance" | "shapValues" | "whatIfFeatures">[] = [
  { id: "batangas", name: "Batangas", riskScore: 0.48, population: 2908494, povertyRate: 9.2, unemploymentRate: 6.4, cropYieldIndex: 62, accessToFood: 78, householdsAtRisk: 96000, fpsi: 2.6, momChange: 2.4, lat: 13.7565, lng: 121.0583 },
  { id: "cavite",   name: "Cavite",   riskScore: 0.41, population: 4344829, povertyRate: 5.1, unemploymentRate: 7.8, cropYieldIndex: 45, accessToFood: 88, householdsAtRisk: 88000, fpsi: 2.2, momChange: 1.8, lat: 14.2456, lng: 120.8786 },
  { id: "laguna",   name: "Laguna",   riskScore: 0.39, population: 3382193, povertyRate: 4.8, unemploymentRate: 7.2, cropYieldIndex: 50, accessToFood: 89, householdsAtRisk: 72000, fpsi: 2.1, momChange: 1.4, lat: 14.1652, lng: 121.3308 },
  { id: "quezon",   name: "Quezon",   riskScore: 0.66, population: 2122830, povertyRate: 19.5, unemploymentRate: 5.6, cropYieldIndex: 58, accessToFood: 60, householdsAtRisk: 132000, fpsi: 3.4, momChange: 4.6, lat: 14.0313, lng: 122.1106 },
  { id: "rizal",    name: "Rizal",    riskScore: 0.45, population: 3330143, povertyRate: 7.4, unemploymentRate: 6.9, cropYieldIndex: 38, accessToFood: 84, householdsAtRisk: 81000, fpsi: 2.4, momChange: 2.0, lat: 14.6037, lng: 121.3084 },
];

export const regionsData: RegionData[] = provincesRaw.map((r) => ({
  ...r,
  riskLevel: getRiskLevel(r.riskScore),
  historicalTrend: generateTrend(r.riskScore),
  featureImportance: defaultFeatures().sort((a, b) => b.importance - a.importance),
  shapValues: defaultShapValues(r.riskScore).sort((a, b) => Math.abs(b.value) - Math.abs(a.value)),
  whatIfFeatures: defaultWhatIf(),
}));

// === Municipalities / Cities (drilldown level) ===
// Risk score is generated deterministically per muni so it stays stable across renders
function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

const provinceBaseRisk: Record<string, number> = {
  batangas: 0.48,
  cavite: 0.41,
  laguna: 0.39,
  quezon: 0.66,
  rizal: 0.45,
};

interface RawMuni { id: string; name: string; pid: string; pname: string }

export const municipalitiesData: MunicipalityData[] = (muniListRaw as RawMuni[]).map((m) => {
  const base = provinceBaseRisk[m.pid] ?? 0.5;
  const variance = ((hash(m.id) % 1000) / 1000 - 0.5) * 0.35; // -0.175..+0.175
  const score = Math.max(0.12, Math.min(0.92, base + variance));
  const pop = 15000 + (hash(m.id + "p") % 285000);
  const povertyRate = Math.max(2, Math.min(48, base * 35 + variance * 30));
  const isCity = /city|cabuyao|tagaytay|antipolo|biñan|binan|calamba|santa rosa|santo tomas|san pablo|lucena|tayabas|tanauan|lipa|batangas city|tagbilaran|bacoor|imus|dasmariñas|dasmarinas|trece|general trias|cavite city|sariaya/i.test(m.name);
  return {
    id: m.id,
    name: m.name,
    provinceId: m.pid,
    provinceName: m.pname,
    riskScore: score,
    riskLevel: getRiskLevel(score),
    population: pop,
    povertyRate: Math.round(povertyRate * 10) / 10,
    householdsAtRisk: Math.round(pop * (povertyRate / 100) * 0.6),
    fpsi: Math.round((1.5 + variance * 6 + base * 2) * 10) / 10,
    momChange: Math.round((variance * 8 + 1) * 10) / 10,
    classification: isCity ? "City" : "Municipality",
  };
});

// Lookup helper
export const municipalitiesByProvince = (provinceId: string) =>
  municipalitiesData.filter((m) => m.provinceId === provinceId);

// CALABARZON regional trend data (monthly)
export const nationalTrendData = (() => {
  const months = ["Jul 2024","Aug 2024","Sep 2024","Oct 2024","Nov 2024","Dec 2024","Jan 2025","Feb 2025","Mar 2025","Apr 2025","May 2025","Jun 2025"];
  return months.map((month, i) => ({
    month,
    rfii: 0.42 + i * 0.015 + (Math.random() - 0.5) * 0.03,
    fpsi: 0.02 + i * 0.002 + (Math.random() - 0.5) * 0.005,
  }));
})();
