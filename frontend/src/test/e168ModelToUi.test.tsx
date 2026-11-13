import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import type { ExplainabilityResponse, ProvinceSummary } from "@/lib/apiTypes";

// FINAL model -> API -> UI: the panels show exactly what the API returns, label it as food-insecurity risk, never invent a
// contribution, and never turn a missing forecast into 0 / Low.
let explain: Partial<ExplainabilityResponse> | undefined;
let explainError: unknown = null;
let outlook: { provinces: Array<Record<string, unknown>> } | undefined;
let shap: { data?: unknown; isLoading: boolean; error: unknown } = { data: undefined, isLoading: false, error: null };
vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: { thresholds: { riskDisplayCutoff: 0.5 } } }),
  useExplainability: () => ({ data: explain, isLoading: false, error: explainError }),
  useForecast: () => ({ data: undefined, error: null }),
  useNews: () => ({ data: undefined, isLoading: false, isError: false, refetch: () => undefined }),
  useFoodInsecurityStatus: () => ({ data: outlook }),
}));
vi.mock("@/lib/finalShap", async (orig) => ({
  ...(await orig<typeof import("@/lib/finalShap")>()),
  useFinalShap: () => shap,
}));

import { RiskDriversCardBody, ProvinceRankingCardBody } from "@/components/LeftPanel";
import { MapLegend } from "@/components/MapLegend";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RISK_LABELS } from "@/data/types";
import { provinceToRegion } from "@/lib/adapters";

// Served 2027-Q1 values as /api/v1/provinces returns them (map value = forecast share 0-1) and the outlook's shares in %.
const API_2027Q1: Record<string, number> = { quezon: 0.268, rizal: 0.248, laguna: 0.237, cavite: 0.243, batangas: 0.232 };
const NAMES: Record<string, string> = { quezon: "Quezon", rizal: "Rizal", laguna: "Laguna", cavite: "Cavite", batangas: "Batangas" };

const province = (id: string, riskScore: number | null): ProvinceSummary =>
  ({ id, name: NAMES[id], riskScore, riskLevel: riskScore == null ? null : riskScore >= 0.5 ? "high" : "low",
     centroid: { lat: 14, lng: 121 }, limitedSignal: false, articleCount: 6 }) as unknown as ProvinceSummary;
const group = (key: string, label: string, pct: number) =>
  ({ key, label, pct, signedContribution: 0.05, direction: "increases_risk", status: "contributes", plainEvidence: `${label} text.`, inputs: [] });

describe("FINAL values reach the screen unchanged", () => {
  it("the province ranking shows each API forecast share, sorted by it, with food-insecurity labels", () => {
    outlook = { provinces: Object.entries(API_2027Q1).map(([id, v]) => ({ province: NAMES[id], lead: 1, target_quarter: "2027-Q1",
      score_pct: Math.round(v * 1000) / 10, range90_pct: [10, 40], p_high: 0.01, risk_class: "LOW" })) };
    const regions = Object.entries(API_2027Q1).map(([id, p]) => provinceToRegion(province(id, p)));
    render(<ProvinceRankingCardBody onRegionClick={() => undefined} regionsData={regions.slice().reverse()} />);
    const rows = [...document.querySelectorAll("button")].map((b) => b.textContent ?? "");
    const order = Object.entries(API_2027Q1).sort((a, b) => b[1] - a[1]).map(([id]) => NAMES[id]);
    expect(rows.map((t) => t.match(/^(Quezon|Rizal|Laguna|Cavite|Batangas)/)?.[1])).toEqual(order);
    rows.forEach((t, i) => {
      const id = order[i].toLowerCase();
      expect(t).toContain(`${Math.round(API_2027Q1[id] * 1000) / 10}%`);
      expect(t).toContain("Low risk");
      expect(t).not.toMatch(/price/i);
    });
  });

  it("a province with no forecast is shown as 'No forecast' and '—', never 0.00 or Low", () => {
    outlook = { provinces: [] };
    const regions = [provinceToRegion(province("quezon", 0.268)), provinceToRegion(province("rizal", null))];
    expect(regions[1].hasForecast).toBe(false);
    render(<ProvinceRankingCardBody onRegionClick={() => undefined} regionsData={regions} />);
    const rizal = [...document.querySelectorAll("button")].find((b) => b.textContent?.startsWith("Rizal"))!;
    expect(rizal.textContent).toContain("No forecast");
    expect(rizal.textContent).toContain("—");
    expect(rizal.textContent).not.toContain("0.00");
    expect(rizal.textContent).not.toMatch(/Low/);
  });
});

describe("driver bars use the API's shares and disclose the rest", () => {
  it("shows the top five API groups and Other factors, adding to 100; Poverty only when the API lists it", () => {
    shap = { isLoading: false, error: null, data: { available: true, otherPct: 5, groups: [
      group("hunger", "Hunger & Food Stress", 41), group("climate", "Climate Stress", 38), group("ag_production", "Agricultural Production", 12),
      group("market", "Market / Prices", 2), group("employment", "Employment", 1), group("household_economy", "Regional Economy", 1)] } };
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    for (const lab of ["Hunger & Food Stress", "Climate Stress", "Agricultural Production", "Market / Prices", "Employment"])
      expect(screen.getByText(lab)).toBeTruthy();
    expect(screen.queryByText("Regional Economy")).toBeNull();             // sixth largest group: under Other until "See all"
    expect(screen.queryByText("Poverty and Vulnerability")).toBeNull();    // not used by this forecast: not shown
    const bars = screen.getByTestId("shap-top-bars").textContent ?? "";
    expect(bars).toContain("Other factors6%");                             // 100 - (41 + 38 + 12 + 2 + 1)
  });

  it("an unavailable explanation shows its reason, never invented bars", () => {
    shap = { isLoading: false, error: null, data: { available: false, reason: "No explanation for this quarter." } };
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    expect(screen.getByText("No explanation for this quarter.")).toBeTruthy();
    expect(screen.queryByTestId("shap-top-bars")).toBeNull();
  });

  it("an API failure shows the load error, not stale or demo bars", () => {
    shap = { isLoading: false, data: undefined, error: Object.assign(new Error("network"), { status: 0 }) };
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    expect(screen.queryByTestId("shap-top-bars")).toBeNull();
    expect(screen.queryByText("Climate Stress")).toBeNull();
  });
});

describe("labels describe the FINAL target", () => {
  it("risk labels are plain High / Low risk, never price risk", () => {
    for (const v of Object.values(RISK_LABELS)) {
      expect(v).toMatch(/^(Low|High) risk$/);
      expect(v).not.toMatch(/price/i);
    }
  });

  it("the map legend defines High with the FNRI HFIAS target, not the retired hunger-and-price rule", () => {
    render(<TooltipProvider><MapLegend /></TooltipProvider>);
    const text = document.body.innerHTML;
    expect(text).toContain("trouble getting enough food");
    expect(text).not.toContain("11.3%");
    expect(text).not.toMatch(/food-price rises/);
  });
});

describe("no production code imports demo or legacy prediction data", () => {
  const SRC = join(__dirname, "..");
  const files: string[] = [];
  const walk = (d: string) => readdirSync(d).forEach((f) => {
    const p = join(d, f);
    if (statSync(p).isDirectory()) { if (f !== "test") walk(p); } else if (/\.(ts|tsx)$/.test(f)) files.push(p);
  });
  walk(SRC);

  it("nothing imports mock data or the static province predictions", () => {
    const offenders = files.filter((f) => {
      const s = readFileSync(f, "utf8");
      return /data\/mockData/.test(s) || (/PROVINCE_QUARTER_DATA|getTriggerBreakdown/.test(s) && !f.endsWith(join("data", "quarterData.ts")));
    }).map((f) => relative(SRC, f));
    expect(offenders).toEqual([]);
  });

  it("quarterData is used only for the timeline's quarter list", () => {
    const users = files.filter((f) => /from "@\/data\/quarterData"/.test(readFileSync(f, "utf8"))).map((f) => relative(SRC, f));
    expect(users).toEqual([join("components", "QuarterTimeSlider.tsx")]);
    expect(readFileSync(join(SRC, "components", "QuarterTimeSlider.tsx"), "utf8")).toMatch(/import \{ QUARTER_IDS \} from "@\/data\/quarterData"/);
  });
});
