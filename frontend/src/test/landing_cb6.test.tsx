import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// The evaluation the backend serves for the MAIN model C-B6 (OBJECTIVES_AUDIT/runner/export_cb6.py output).
const EVAL = JSON.parse(
  readFileSync(resolve(__dirname, "../../../backend/data/foodinsecurity_engine_cb6/evaluation.json"), "utf-8"),
);

vi.mock("@/components/TopNavbar", () => ({ TopNavbar: () => <header>header</header> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ status: "anonymous" }) }));
vi.mock("@/lib/tour", () => ({ requestTour: vi.fn() }));
vi.mock("@/lib/queries", async (orig) => {
  const real = await orig<typeof import("@/lib/queries")>();
  return {
    ...real,
    useConfig: () => ({ data: { indicator: { id: "regional_food_insecurity_forecast" } } }),
    useFinalRiskEvaluation: () => ({ data: EVAL }),
    useFinalOverview: () => ({ data: undefined }),
    useFinalEvaluation: () => ({ data: undefined }),
  };
});

import Landing from "@/pages/Landing";
import { cbFaqs, cbResults } from "@/pages/landingCb";
import { AboutModal } from "@/components/AboutModal";

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

describe("Landing page with the main model C-B6", () => {
  it("names C-B6, shows its own figures and none of C-b's claims that are false for it", () => {
    expect(EVAL.model).toBe("ALLBASE-CB6");
    const { container } = wrap(<Landing />);
    const text = container.textContent ?? "";
    const l1 = EVAL.leads["1"].metrics;
    expect(text).toContain(l1.accuracy.toFixed(3));
    expect(text).toContain(l1.brier.toFixed(3));
    expect(text).toContain("C-B6 (served forecast)");
    expect(text).toContain("model C-B6");
    expect(text).toContain("23 inputs");
    expect(text).toContain("PSA Rice Stocks Inventory");
    expect(text).toContain("C-B6 has no sealed forecast yet");
    for (const wrong of ["neither met the stricter stability rule", "(model C-b)", "21 inputs", "C-b (served forecast)"]) {
      expect(text).not.toContain(wrong);
    }
  });

  it("FAQ and results text follow C-B6's own rules and lead", () => {
    const faq = cbFaqs(EVAL).map((x) => x.a).join(" ");
    expect(faq).toContain("both met the stricter reliability rules, narrowly");
    expect(faq).not.toContain("neither met the stricter stability rule");
    const res = cbResults(EVAL).map((x) => x.d).join(" ");
    expect(res).toContain(`Lead 3 does not (${EVAL.leads["3"].metrics.accuracy.toFixed(3)})`);
    expect(res).toContain("met the 0.60 stability requirement only narrowly");
  });

  it("the About dialog describes C-B6 and its R1-R7 pass", () => {
    wrap(<AboutModal />);
    fireEvent.click(screen.getByText("About & Methodology"));
    const d = screen.getByRole("dialog").textContent ?? "";
    expect(d).toContain("C-B6: one LightGBM, 23 inputs");
    expect(d).toContain("also meet the stricter R1-R7 rules");
    expect(d).not.toContain("none meets the stricter R1-R7 rules");
  });
});
