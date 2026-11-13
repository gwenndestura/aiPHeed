import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ShapGroup } from "@/lib/finalShap";

// The right panel's factor cards (FINAL): one card per factor group from the exact SHAP explanation of the served issue
// (/api/v1/final/shap/province): the group's share, its direction section, and the backend's plain sentence. No technical note.
let shap: { available: boolean; groups?: ShapGroup[]; reason?: string } | undefined;
vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: undefined }),
  useExplainability: () => ({ data: { triggers: [], riskScore: 0.27, note: "" }, isLoading: false, error: null }),
  useNews: () => ({ data: undefined, isLoading: false, isError: false, refetch: () => undefined }),
}));
vi.mock("@/lib/finalShap", async (orig) => ({
  ...(await orig<typeof import("@/lib/finalShap")>()),
  useFinalShap: () => ({ data: shap, isLoading: false, error: null }),
}));

import { ShapNarrativeCardBody } from "@/components/RightAnalyticsPanel";

const QUARTER = { id: "2027-Q1", label: "Q1", year: 2027, months: "Jan-Mar" } as never;
const QUEZON = { id: "quezon", name: "Quezon", riskScore: 0.27 } as never;
const g = (key: string, label: string, pct: number, s: number, text: string): ShapGroup =>
  ({ key, label, pct, signedContribution: s, direction: s >= 0.01 ? "increases_risk" : s <= -0.01 ? "protective" : "no_effect",
     status: Math.abs(s) >= 0.01 ? "contributes" : "no_effect", plainEvidence: text, inputs: [] }) as ShapGroup;

const GROUPS = [
  g("hunger", "Hunger & Food Stress", 41, 0.08, "There were more national news reports on food shortages than usual. This raised the risk moderately."),
  g("climate", "Climate Stress", 38, 0.07, "The soil has been wetter than normal since the last survey. This raised the risk moderately."),
  g("market", "Market / Prices", 2, -0.004, "Food prices here rose more slowly than the national average (by 0.7 percentage points). This had almost no effect on the risk."),
  g("ag_production", "Agricultural Production", 12, -0.02, "Palay and corn harvests were 2% higher than their 3-year average. This lowered the risk slightly."),
];

describe("factor cards (FINAL)", () => {
  it("shows each group's share in its section with the backend's plain sentence", () => {
    shap = { available: true, groups: GROUPS };
    render(<ShapNarrativeCardBody quarter={QUARTER} selectedRegion={QUEZON} />);
    const headings = screen.getAllByText(/^(What is raising the risk|What is lowering the risk|No effect this time)$/).map((e) => e.textContent);
    expect(headings).toEqual(["What is raising the risk", "What is lowering the risk", "No effect this time"]);
    const body = document.body.textContent ?? "";
    for (const x of GROUPS) {
      expect(body).toContain(x.plainEvidence);
      expect(body).toContain(`${x.pct}%`);
    }
    expect(body.indexOf("Hunger & Food Stress")).toBeLessThan(body.indexOf("Climate Stress"));
    expect(body).not.toMatch(/log-odds|SHAP value|FIRI v2|evidence note/);
    expect(screen.queryByRole("button", { name: /Details/ })).toBeNull();
  });

  it("states why there is no explanation instead of showing stale bars", () => {
    shap = { available: false, reason: "An exact SHAP explanation exists only for the served forecasts." };
    render(<ShapNarrativeCardBody quarter={QUARTER} selectedRegion={null} />);
    expect(screen.getByText(/exists only for the served forecasts/)).toBeTruthy();
    expect(screen.queryByText("What is raising the risk")).toBeNull();
  });
});
