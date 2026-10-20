import { describe, expect, it, vi } from "vitest";
import { cloneElement, isValidElement, type ReactElement, type ReactNode } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";

vi.mock("@/components/TopNavbar", () => ({ TopNavbar: () => <header>header</header> }));
vi.mock("@/components/PageTours", () => ({ VizTour: () => null }));

// jsdom has no layout: give the charts a fixed size so Recharts draws its SVG.
vi.mock("recharts", async (importOriginal) => {
  const mod = await importOriginal<typeof import("recharts")>();
  return {
    ...mod,
    ResponsiveContainer: ({ children }: { children: ReactNode }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children) ? cloneElement(children as ReactElement, { width: 800, height: 400 }) : children}
      </div>
    ),
  };
});

const q = (id: string, state: "actual" | "current" | "forecast" | "unavailable") => {
  const [y, n] = id.split("-Q");
  return { id, year: Number(y), q: Number(n), label: `Q${n}`, monthsLabel: "", state, reason: null };
};
// As the merged backend serves them: 2026-Q4 and 2027-Q1 are "forecast"; the map opens on 2027-Q1.
const QUARTERS = {
  current: "2027-Q1",
  calendarQuarter: "2026-Q4",
  quarters: [
    q("2024-Q4", "actual"), // before the selectable window
    q("2025-Q3", "actual"),
    q("2025-Q4", "actual"),
    q("2026-Q1", "unavailable"),
    q("2026-Q2", "actual"),
    q("2026-Q3", "actual"),
    q("2026-Q4", "forecast"),
    q("2027-Q1", "forecast"),
  ],
};
const SERIES = {
  series: [
    { quarter: "2026-Q2", riskScore: 0.65, riskLevel: "high", isForecast: false },
    { quarter: "2026-Q3", riskScore: 0.63, riskLevel: "high", isForecast: false },
    { quarter: "2026-Q4", riskScore: 0.65, riskLevel: "high", isForecast: true },
    { quarter: "2027-Q1", riskScore: 0.72, riskLevel: "high", isForecast: true },
  ],
};
const explainCalls: (string | undefined)[] = [];

vi.mock("@/lib/queries", () => ({
  useConfig: () => ({ data: { thresholds: { alertThreshold: 0.6, riskDisplayCutoff: 0.5, triggerRedCutoff: 20 } } }),
  useQuarters: () => ({ data: QUARTERS, error: null }),
  useMunicipalities: () => ({ data: { data: [] } }),
  useTimeseries: (_scope: string, id: string) => ({ data: id ? SERIES : undefined, error: null }),
  useExplainability: (_scope: string, id: string, quarter?: string) => {
    if (id) explainCalls.push(quarter);
    return {
      data: id ? { triggers: [{ key: "employment", label: "Jobs and employment", pct: 54, color: "red" }] } : undefined,
      error: null,
    };
  },
}));

import VisualizationPage from "@/pages/Visualization";

// jsdom has no SVG geometry; Recharts reads a path's length to draw (and dash) its lines.
(SVGElement.prototype as unknown as { getTotalLength: () => number }).getTotalLength = () => 100;

const selects = () => screen.getAllByRole("combobox") as HTMLSelectElement[];
const optionTexts = (s: HTMLSelectElement) => [...s.options].map((o) => o.textContent);

describe("Visualization: Province Risk Level Trend", () => {
  it("lists the map's quarters through the forecast, labelled, and defaults the range to them", () => {
    render(<VisualizationPage />);
    const [, , from, to] = selects();
    const expected = ["2025-Q3", "2025-Q4", "2026-Q2", "2026-Q3", "Q4 2026 (forecast)", "Q1 2027 (forecast)"];
    expect(optionTexts(from)).toEqual(expected);
    expect(optionTexts(to)).toEqual(expected);
    // Unavailable quarters and quarters outside the selectable window stay out.
    expect([...to.options].map((o) => o.value)).not.toContain("2026-Q1");
    expect([...to.options].map((o) => o.value)).not.toContain("2024-Q4");
    // The list ends at the quarter the map shows.
    expect(to.value).toBe("2027-Q1");
    expect(from.value).toBe("2025-Q3");
  });

  it("draws forecast quarters as a dashed segment of the same colour, with the Observed / Forecast key", async () => {
    const { container } = render(<VisualizationPage />);
    fireEvent.change(selects()[0], { target: { value: "Quezon" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate Chart" }));
    await act(async () => { await new Promise((r) => setTimeout(r, 1800)); }); // let the line animation finish
    const curves = [...container.querySelectorAll("path.recharts-line-curve")];
    const quezon = curves.filter((c) => c.getAttribute("stroke") === "#ef4444");
    expect(quezon).toHaveLength(2);
    // Recharts animates the line with stroke-dasharray; when it ends, a dashed line keeps its
    // "6 5" pattern repeated along the path and a solid line is one dash the path's whole length.
    const dash = (c: Element) => c.getAttribute("stroke-dasharray") ?? "";
    const dashed = quezon.filter((c) => dash(c).startsWith("6px, 5px"));
    const solid = quezon.filter((c) => dash(c) === "100px 0px");
    expect(dashed).toHaveLength(1);
    expect(solid).toHaveLength(1);
    // The key sits under the chart, inside the exported figure.
    const key = screen.getByTestId("trend-key");
    expect(key.textContent).toBe("ObservedForecast");
    expect(key.querySelector(".qt-line-observed")).not.toBeNull();
    expect(key.querySelector(".qt-line-forecast")).not.toBeNull();
    // The province legend lists each series once (the dashed part has no legend entry).
    const legend = [...container.querySelectorAll(".recharts-legend-item-text")].map((e) => e.textContent);
    expect(legend).toEqual(["Quezon"]);
    // Exports are enabled for a range that includes forecast quarters.
    expect((screen.getByRole("button", { name: /Download PNG/ }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: /Download PDF/ }) as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("Visualization: Driver groups", () => {
  it("defaults to the quarter the map opens on and offers the forecast quarters", async () => {
    render(<VisualizationPage />);
    fireEvent.click(screen.getByRole("button", { name: "Feature Contribution Breakdown" }));
    const [, quarter] = selects();
    expect(quarter.value).toBe("2027-Q1");
    expect(quarter.selectedOptions[0].textContent).toBe("Q1 2027 (forecast)");
    expect(optionTexts(quarter).slice(-2)).toEqual(["Q4 2026 (forecast)", "Q1 2027 (forecast)"]);
    explainCalls.length = 0;
    fireEvent.click(screen.getByRole("button", { name: "Generate Chart" }));
    // The same explainability request as the map's Why panel for this quarter.
    expect(explainCalls).toContain("2027-Q1");
    expect(screen.getByText(/Quezon · Q1 2027 \(forecast\) — trigger contributions/)).toBeTruthy();
    expect((screen.getByRole("button", { name: /Download PDF/ }) as HTMLButtonElement).disabled).toBe(false);
  });
});
