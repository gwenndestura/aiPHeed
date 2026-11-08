import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QuarterTimeSlider, type Quarter } from "@/components/QuarterTimeSlider";
import { quarterMonthRange } from "@/lib/quarters";

const quarter = (year: number, q: 1 | 2 | 3 | 4, state: "past" | "current" | "forecast"): Quarter => ({
  id: `${year}-Q${q}`,
  year,
  q,
  label: `Q${q}`,
  monthsLabel: "",
  past: state === "past",
  current: state === "current",
  forecast: state === "forecast",
});

const QS = [
  quarter(2026, 2, "past"),
  quarter(2026, 3, "past"),
  quarter(2026, 4, "current"),
  quarter(2027, 1, "forecast"),
  quarter(2027, 2, "forecast"),
];

describe("quarterMonthRange", () => {
  it("spells out the months with a spaced en dash", () => {
    expect(quarterMonthRange({ year: 2027, q: 1 })).toBe("January – March 2027");
    expect(quarterMonthRange({ year: 2026, q: 4 })).toBe("October – December 2026");
  });
});

describe("QuarterTimeSlider", () => {
  it("shows the quarter, its months and its status", () => {
    const { container, rerender } = render(<QuarterTimeSlider value="2026-Q3" onChange={() => {}} quarters={QS} />);
    const tag = () => container.querySelector(".qt-tag");
    expect(screen.getByText("July – September 2026")).toBeInTheDocument();
    expect(tag()).toHaveTextContent("Observed");

    rerender(<QuarterTimeSlider value="2026-Q4" onChange={() => {}} quarters={QS} />);
    expect(tag()).toHaveTextContent("Current quarter");

    rerender(<QuarterTimeSlider value="2027-Q1" onChange={() => {}} quarters={QS} />);
    expect(screen.getByText("January – March 2027")).toBeInTheDocument();
    expect(tag()).toHaveTextContent("Forecast");
  });

  it("exposes the points as a radio group with status labels", () => {
    render(<QuarterTimeSlider value="2027-Q1" onChange={() => {}} quarters={QS} />);
    const group = screen.getByRole("radiogroup", { name: "Quarter" });
    expect(group.getAttribute("aria-description")).toMatch(/Dashed line: forecast quarters\. Today is at Q4 2026\./);
    const selected = screen.getByRole("radio", { name: "Q1 2027, forecast" });
    expect(selected).toHaveAttribute("aria-checked", "true");
    expect(selected).toHaveAttribute("tabindex", "0");
    expect(selected).toHaveTextContent("Q1 2027");
    const today = screen.getByRole("radio", { name: "Q4 2026, current quarter, today" });
    expect(today).toHaveAttribute("tabindex", "-1");
    expect(today).toHaveAttribute("title", "October – December 2026 · Today");
    expect(screen.getByTitle("Forecast")).toBeInTheDocument();
  });

  it("moves the selection with the arrow keys, stopping at the ends", () => {
    const onChange = vi.fn();
    render(<QuarterTimeSlider value="2026-Q4" onChange={onChange} quarters={QS} />);
    const radio = (name: string) => screen.getByRole("radio", { name });

    fireEvent.keyDown(radio("Q4 2026, current quarter, today"), { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("2027-Q1");
    expect(radio("Q1 2027, forecast")).toHaveFocus();

    fireEvent.keyDown(radio("Q4 2026, current quarter, today"), { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith("2026-Q3");

    onChange.mockClear();
    fireEvent.keyDown(radio("Q2 2027, forecast"), { key: "ArrowRight" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("opens history from a plain text button", () => {
    const onOpenHistory = vi.fn();
    render(<QuarterTimeSlider value="2026-Q4" onChange={() => {}} quarters={QS} onOpenHistory={onOpenHistory} />);
    fireEvent.click(screen.getByRole("button", { name: "View history" }));
    expect(onOpenHistory).toHaveBeenCalled();
  });
});
