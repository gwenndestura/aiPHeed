import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import type { ExplainabilityResponse, Trigger } from "@/lib/apiTypes";

// The right panel's factor cards: plain name and share, one plain sentence, and the bar. The backend's long
// evidence note is not shown.
let explain: Partial<ExplainabilityResponse> | undefined;
vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: undefined }),
  useExplainability: () => ({ data: explain, isLoading: false, error: null }),
  useNews: () => ({ data: undefined, isLoading: false, isError: false, refetch: () => undefined }),
}));

import { ShapNarrativeCardBody } from "@/components/RightAnalyticsPanel";

const QUARTER = { id: "2027-Q1", label: "Q1", year: 2027, months: "Jan-Mar" } as never;
const QUEZON = { id: "quezon", name: "Quezon", riskScore: 0.72 } as never;
const JOBS_NOTE =
  "In the risk index (FIRI v2: each indicator compared with its own earlier values, 0.5 = its historical middle): " +
  "Unemployment change (national): unemployment rate +0.90 points year on year (higher than 88% of its earlier values; " +
  "raises the estimate). The bar is this group's exact push on the index.";
const REGION_NOTE =
  "In the risk index (FIRI v2): the five provinces' combined push of this factor group (above or below its historical " +
  "middle). Open a province to see each indicator's value, score and status.";

const t = (key: string, label: string, pct: number, direction: Trigger["direction"], color: Trigger["color"],
  status: Trigger["status"], evidenceNote?: string): Trigger =>
  ({ key, label, pct, direction, color, status, evidenceNote }) as unknown as Trigger;

const triggers = (note: (k: string) => string | undefined) => [
  t("employment", "Employment", 54, "increases_risk", "red", "contributes", note("employment")),
  t("climate", "Climate Stress", 28, "increases_risk", "red", "contributes", note("climate")),
  t("market", "Market / Prices", 5, "increases_risk", "yellow", "contributes", note("market")),
  t("fish_kill", "Fisheries production", 13, "protective", "yellow", "contributes", note("fish_kill")),
  t("ofw_remittance", "OFW Remittance", 0, "increases_risk", "yellow", "insufficient_data"),
];

const cards = () => [...document.querySelectorAll(".inner-box")] as HTMLElement[];

describe("factor cards", () => {
  it("province: plain titles with the same percentages, one sentence each, no evidence note", () => {
    explain = { triggers: triggers((k) => (k === "employment" ? JOBS_NOTE : `${k} evidence note`)), riskScore: 0.72, note: "" };
    render(<ShapNarrativeCardBody quarter={QUARTER} selectedRegion={QUEZON} />);

    // Sections, order, titles and percentages.
    const headings = screen.getAllByText(/^(What is raising the risk|What is lowering the risk|No effect this time)$/).map((e) => e.textContent);
    expect(headings).toEqual(["What is raising the risk", "What is lowering the risk", "No effect this time"]);
    const tops = cards().map((c) => c.firstElementChild?.textContent);
    expect(tops).toEqual([
      "Jobs (national figures)54%",
      "Weather and farm supply28%",
      "Food prices5%",
      "Fish catch (instead of fish-kill reports)13%",
      "Money sent home by OFWs (national figures): not enough figures0%",
    ]);
    // Bars keep their widths.
    expect(cards().map((c) => (c.querySelector("[style*='width']") as HTMLElement).style.width)).toEqual(["54%", "28%", "5%", "13%", "0%"]);

    const jobs = cards()[0];
    expect(within(jobs).getByText("Unemployment rose more than usual compared with a year earlier.")).toBeTruthy();
    expect(within(cards()[3]).getByText("The fish catch held up better than usual.")).toBeTruthy();
    expect(within(cards()[4]).getByText("No figures had been published when this forecast was made, which does not mean the risk is low.")).toBeTruthy();
    // The evidence note and any Details control are gone.
    expect(document.body.textContent).not.toContain("FIRI v2");
    expect(document.body.textContent).not.toContain(JOBS_NOTE);
    expect(screen.queryByRole("button", { name: /Details/ })).toBeNull();
  });

  it("region: the same sentences, without the repeated evidence note", () => {
    explain = { triggers: triggers(() => REGION_NOTE), riskScore: 0.74, note: "" };
    render(<ShapNarrativeCardBody quarter={QUARTER} selectedRegion={null} />);
    expect(within(cards()[0]).getByText("Unemployment rose more than usual compared with a year earlier.")).toBeTruthy();
    expect(document.body.textContent).not.toContain("combined push of this factor group");
    expect(screen.queryByRole("button", { name: /Details/ })).toBeNull();
  });
});
