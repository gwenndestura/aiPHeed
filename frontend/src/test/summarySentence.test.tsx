import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ExplainabilityResponse } from "@/lib/apiTypes";

// E61: the explanation of a two-part forecast reaches the dashboard through the backend's summary sentence, shown in
// the approved plain-summary paragraph verbatim. No new element is added to the SHAP card.
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
  it("shows the backend sentence, explanation included, in the existing paragraph", () => {
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
    expect(p.tagName).toBe("P");
    expect(p.textContent).toContain(SENTENCE);
    expect(p.textContent).toContain("Data: limited (Some inputs not available at the issue date for OFW Remittance.)");
    expect(container.querySelector("details")).toBeNull();
  });
});
