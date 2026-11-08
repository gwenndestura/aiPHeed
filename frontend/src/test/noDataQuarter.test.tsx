import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QuarterTimeSlider } from "@/components/QuarterTimeSlider";
import { apiQuarterToSlider } from "@/lib/adapters";
import { isHighRisk } from "@/lib/risk";
import type { Quarter as ApiQuarter } from "@/lib/apiTypes";

const REASON =
  "No risk score yet. Scores run through Q3 2026, the newest quarter PSA has published data for, and the published forecast covers Q1 2027 only.";

const api = (id: string, state: ApiQuarter["state"], reason: string | null = null): ApiQuarter => {
  const [y, q] = id.split("-Q");
  return { id, year: Number(y), q: Number(q), label: `Q${q}`, monthsLabel: "", state, reason };
};

const API = [
  api("2026-Q2", "actual"),
  api("2026-Q3", "current"),
  api("2026-Q4", "unavailable", REASON),
  api("2027-Q1", "forecast"),
];

describe("apiQuarterToSlider", () => {
  it("marks a quarter with no score as no-data, still selectable, with its reason", () => {
    const q = apiQuarterToSlider(API[2], "2026-Q4");
    expect(q.noData).toBe(true);
    expect(q.locked).toBe(false);
    expect(q.reason).toBe(REASON);
  });

  it("puts today on the calendar quarter, not the newest scored one", () => {
    const qs = API.map((q) => apiQuarterToSlider(q, "2026-Q4"));
    expect(qs.map((q) => q.current)).toEqual([false, false, true, false]);
    expect(qs[1].past).toBe(true);
    expect(qs[3].forecast).toBe(true);
  });
});

describe("QuarterTimeSlider with a no-data quarter", () => {
  it("draws the quarter gray but keeps it clickable, with no note on the timeline", () => {
    const qs = API.map((q) => apiQuarterToSlider(q, "2026-Q4"));
    const onChange = vi.fn();
    render(<QuarterTimeSlider value="2026-Q3" onChange={onChange} quarters={qs} />);
    const point = screen.getByRole("radio", { name: "Q4 2026, current quarter, today, no data" });
    expect(point).not.toBeDisabled();
    expect(point).toHaveClass("qt-point-nodata");
    fireEvent.click(point);
    expect(onChange).toHaveBeenCalledWith("2026-Q4");
    expect(screen.queryByText(REASON)).not.toBeInTheDocument();
    expect(screen.queryByText("No data")).not.toBeInTheDocument();
  });
});

describe("isHighRisk", () => {
  it("judges the score as displayed: 0.50 is HIGH", () => {
    expect(isHighRisk(0.4982)).toBe(true);
    expect(isHighRisk(0.5)).toBe(true);
    expect(isHighRisk(0.4949)).toBe(false);
  });
});
