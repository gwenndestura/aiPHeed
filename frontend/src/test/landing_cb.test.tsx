import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// The evaluation the backend serves in the C-b mode (FOOD_INSECURITY_SYSTEM/runner/export_fi.py output).
const EVAL = JSON.parse(
  readFileSync(resolve(__dirname, "../../../backend/data/foodinsecurity_engine/evaluation.json"), "utf-8"),
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
import { AboutModal } from "@/components/AboutModal";

const wrap = (ui: React.ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );

describe("Landing page in the C-b (food-insecurity) mode", () => {
  it("shows the served evaluation's figures, not the P0H4 ones", () => {
    const { container } = wrap(<Landing />);
    const text = container.textContent ?? "";
    const l1 = EVAL.leads["1"].metrics;
    expect(text).toContain(l1.accuracy.toFixed(3));
    expect(text).toContain(l1.auc.toFixed(3));
    expect(text).toContain(l1.brier.toFixed(3));
    expect(text).toContain(`${EVAL.leads["1"].n_quarters} quarters, ${EVAL.leads["1"].period}`);
    for (const old of ["0.132", "0.257", "70 province-quarters", "12 indicator families", "food prices are rising unusually fast"]) {
      expect(text).not.toContain(old);
    }
  });

  it("lists every Objective 4 comparator with its comparator Brier and Holm p", () => {
    const { container } = wrap(<Landing />);
    const text = container.textContent ?? "";
    const b1 = EVAL.leads["1"].metrics.brier;
    for (const v of Object.values(EVAL.objective4_lead1) as { diff: number; p_holm: number }[]) {
      expect(text).toContain((b1 - v.diff).toFixed(3));
      expect(text).toContain(`Holm p ${v.p_holm.toFixed(3)}`);
    }
  });

  it("states the regional target and that provinces are vulnerability-weighted, not measured", () => {
    const { container } = wrap(<Landing />);
    const text = container.textContent ?? "";
    expect(text).toContain("Balance Luzon");
    expect(text).toContain("11.3%");
    expect(text).toMatch(/not measured provincial or municipal hunger rates/);
  });

  it("opens the About dialog without error and shows the served lead metrics", () => {
    wrap(<AboutModal />);
    fireEvent.click(screen.getByText("About & Methodology"));
    const d = screen.getByRole("dialog").textContent ?? "";
    expect(d).toContain(`accuracy ${EVAL.leads["1"].metrics.accuracy.toFixed(2)}`);
    expect(d).toContain("C-b");
    expect(d).not.toContain("12 indicator families");
  });
});
