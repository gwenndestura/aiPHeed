import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ExplainabilityResponse } from "@/lib/apiTypes";

// The backend's plain summary reaches the Why panel as ONE short line: the data status, then the summary's first
// sentence (the rest of the report is not shown). The data note is kept for screen readers and the hover title.
let explain: Partial<ExplainabilityResponse> | undefined;
vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: undefined }),
  useExplainability: () => ({ data: explain, isLoading: false, error: null }),
  useNews: () => ({ data: undefined, isLoading: false, isError: false, refetch: () => undefined }),
}));

import { ShapNarrativeCardBody } from "@/components/RightAnalyticsPanel";

const QUARTER = { id: "2027-Q1", label: "Q1", year: 2027, months: "Jan-Mar" } as never;
const SENTENCE =
  "Food-insecurity risk in Laguna for 2027-Q1 is forecast LOW (7% probability): regional hunger is likely to stay above " +
  "11.3% (96%) and provincial food-price pressure is unlikely (7%); the target needs both. Slower food inflation does not " +
  "mean food has become affordable; it means prices are rising more slowly.";

describe("plain summary", () => {
  it("shows the data status and the summary's first sentence on one line", () => {
    explain = {
      triggers: [], riskScore: 0.07, note: "note",
      summary: {
        event: "food-insecurity risk", targetQuarter: "2027-Q1", estimateKind: "forecast", issued: "2026-10-01",
        probability: 0.07, result: "LOW", observedOutcome: null, reasons: [], dataStatus: "limited",
        dataStatusNote: "Some inputs not available at the issue date for OFW Remittance.", sentence: SENTENCE,
      },
    };
    const { container } = render(<ShapNarrativeCardBody quarter={QUARTER} selectedRegion={null} />);
    const p = screen.getByTestId("plain-summary");
    const first = SENTENCE.split(/(?<=\.)\s+(?=[A-Z])/)[0];
    expect(p.tagName).toBe("P");
    expect(p.className).toContain("truncate");
    expect(p.textContent).toContain(first);
    expect(p.textContent).not.toContain("Slower food inflation");
    expect(p.textContent).toContain("Data: limited (Some inputs not available at the issue date for OFW Remittance.)");
    expect(container.querySelector("details")).toBeNull();
  });
});
