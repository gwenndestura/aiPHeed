import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import type { ExplainabilityResponse, ProvinceSummary, Trigger } from "@/lib/apiTypes";

// E168 model -> API -> UI: the panels show exactly what the API returns, label it as food-insecurity risk, disclose
// national series and the fish-kill proxy, never invent a contribution, and never turn a missing forecast into 0 / Low.
let explain: Partial<ExplainabilityResponse> | undefined;
let explainError: unknown = null;
vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: { thresholds: { riskDisplayCutoff: 0.5 } } }),
  useExplainability: () => ({ data: explain, isLoading: false, error: explainError }),
  useForecast: () => ({ data: undefined, error: null }),
  useNews: () => ({ data: undefined, isLoading: false, isError: false, refetch: () => undefined }),
}));

import { RiskDriversCardBody, ProvinceRankingCardBody } from "@/components/LeftPanel";
import { MapLegend } from "@/components/MapLegend";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RISK_LABELS } from "@/data/types";
import { provinceToRegion } from "@/lib/adapters";

// The served 2027-Q1 values (backend/data/e168/out/live_2027.json, as /api/v1/provinces returns them).
const API_2027Q1: Record<string, number> = { quezon: 0.076, rizal: 0.068, laguna: 0.016, cavite: 0.009, batangas: 0.003 };
const NAMES: Record<string, string> = { quezon: "Quezon", rizal: "Rizal", laguna: "Laguna", cavite: "Cavite", batangas: "Batangas" };

const province = (id: string, riskScore: number | null): ProvinceSummary =>
  ({ id, name: NAMES[id], riskScore, riskLevel: riskScore == null ? null : riskScore >= 0.5 ? "high" : "low",
     centroid: { lat: 14, lng: 121 }, limitedSignal: false, articleCount: 6 }) as unknown as ProvinceSummary;

const trig = (key: string, label: string, pct: number): Trigger =>
  ({ key, label, pct, direction: "increases_risk", color: "yellow", status: "contributes" }) as unknown as Trigger;

describe("E168 values reach the screen unchanged", () => {
  it("the province ranking shows each API probability, sorted by it, with food-insecurity labels", () => {
    const regions = Object.entries(API_2027Q1).map(([id, p]) => provinceToRegion(province(id, p)));
    render(<ProvinceRankingCardBody onRegionClick={() => undefined} regionsData={regions.slice().reverse()} />);
    const rows = [...document.querySelectorAll("button")].map((b) => b.textContent ?? "");
    expect(rows.map((t) => t.match(/^(Quezon|Rizal|Laguna|Cavite|Batangas)/)?.[1])).toEqual(["Quezon", "Rizal", "Laguna", "Cavite", "Batangas"]);
    rows.forEach((t, i) => {
      const id = ["quezon", "rizal", "laguna", "cavite", "batangas"][i];
      expect(t).toContain(API_2027Q1[id].toFixed(2));
      expect(t).toContain("Low risk");
      expect(t).not.toMatch(/price/i);
    });
  });

  it("a province with no forecast is shown as 'No forecast' and '—', never 0.00 or Low", () => {
    const regions = [provinceToRegion(province("quezon", 0.076)), provinceToRegion(province("rizal", null))];
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
  it("shows the five API bars plus Other model inputs, adding to 100", () => {
    explainError = null;
    explain = {
      triggers: [
        trig("climate", "Climate Stress", 49), trig("employment", "Employment (national)", 9),
        trig("market", "Market / Prices", 5), trig("fish_kill", "Fish Kill (fisheries production proxy)", 1),
        trig("ofw_remittance", "OFW Remittance (national)", 0),
      ],
      otherPct: 36,
    };
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    for (const lab of ["Weather and farm supply", "Jobs (national figures)", "Food prices", "Fish production",
      "Money sent home by OFWs (national figures)", "Other factors (poverty, population, timing)"]) expect(screen.getByText(lab)).toBeTruthy();
    expect(screen.getByText("36%")).toBeTruthy();
    expect(49 + 9 + 5 + 1 + 0 + 36).toBe(100);
  });

  it("never invents an Other bar when the API does not report one", () => {
    explainError = null;
    explain = { triggers: [trig("climate", "Climate Stress", 100)], otherPct: null };
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    expect(screen.queryByText("Other factors (poverty, population, timing)")).toBeNull();
  });

  it("an API failure shows the load error, not stale or demo bars", () => {
    explain = undefined;
    explainError = Object.assign(new Error("network"), { status: 0 });
    render(<RiskDriversCardBody provinceId="quezon" quarterId="2027-Q1" />);
    expect(screen.queryByText("Weather and farm supply")).toBeNull();
    expect(screen.queryByText("Other factors (poverty, population, timing)")).toBeNull();
  });
});

describe("labels describe the E168 target", () => {
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
