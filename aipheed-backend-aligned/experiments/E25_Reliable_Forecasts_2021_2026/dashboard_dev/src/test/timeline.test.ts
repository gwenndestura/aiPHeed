import { describe, expect, it } from "vitest";
import { TIMELINE_DOTS, timelineWindow } from "@/lib/quarters";

const ids = (from: number, to: number) => {
  const out: string[] = [];
  for (let o = from; o <= to; o++) out.push(`${Math.floor(o / 4)}-Q${(o % 4) + 1}`);
  return out;
};
const ord = (y: number, q: number) => y * 4 + (q - 1);

describe("timelineWindow", () => {
  it("shows the newest five quarters, ending at the forecast", () => {
    // Forecast reaches 2027-Q2: the timeline is 2026-Q2 .. 2027-Q2.
    const all = ids(ord(2025, 1), ord(2027, 2));
    expect(timelineWindow(all)).toEqual(["2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1", "2027-Q2"]);
  });

  it("moves forward when a new forecast quarter is added", () => {
    const all = ids(ord(2025, 1), ord(2027, 3));
    expect(timelineWindow(all)[0]).toBe("2026-Q3");
    expect(timelineWindow(all)).toHaveLength(TIMELINE_DOTS);
  });

  it("shows every quarter when there are fewer than five", () => {
    expect(timelineWindow(["2025-Q1", "2025-Q2"])).toEqual(["2025-Q1", "2025-Q2"]);
  });
});
