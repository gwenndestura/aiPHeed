import { readFileSync } from "fs";
import path from "path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E25TimelineView } from "@/pages/E25Timeline";
import { E25Record, tileState } from "@/lib/e25Record";

const rec = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../public/e25_forecast_record.json"), "utf-8"),
) as E25Record;
const PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"];

describe("E25 forecast timeline (reads the single forecast record)", () => {
  it("shows the nine quarters 2025-Q1 .. 2027-Q1 in order", () => {
    render(<E25TimelineView rec={rec} />);
    const want = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"];
    expect(rec.quarters.map((q) => q.quarter)).toEqual(want);
    for (const q of want) expect(screen.getByTestId(`col-${q}`)).toBeTruthy();
  });

  it("never shows a probability or LOW for 2027-Q1 when inputs are missing; lists them", () => {
    render(<E25TimelineView rec={rec} />);
    const op = rec.quarters.find((q) => q.quarter === "2027-Q1")!;
    expect(op.status).toBe("INSUFFICIENT_DATA");
    for (const c of PROVS) {
      const cell = screen.getByTestId(`cell-2027-Q1-${c}`);
      expect(cell.textContent).toContain("MISSING INPUTS");
      expect(cell.textContent).toContain("not a low-risk state");
      expect(cell.textContent).not.toMatch(/P\(HIGH\)|\bLOW\b/);
    }
    const box = screen.getByTestId("op-missing");
    for (const m of op.missing_inputs ?? []) expect(box.textContent).toContain(m);
  });

  it("marks 2026-Q3 and 2026-Q4 as sealed with outcome pending", () => {
    render(<E25TimelineView rec={rec} />);
    for (const q of ["2026-Q3", "2026-Q4"]) {
      for (const c of PROVS) expect(screen.getByTestId(`cell-${q}-${c}`).textContent).toContain("outcome pending");
    }
  });

  it("gives disputed-round quarters their own NO LABEL state, not a risk level", () => {
    for (const q of ["2025-Q2", "2025-Q3"]) {
      const e = rec.quarters.find((x) => x.quarter === q)!;
      for (const c of PROVS) expect(tileState(e, c).kind).toBe("NO_LABEL");
    }
  });

  it("displays exactly the record's probabilities, flags and hash", () => {
    render(<E25TimelineView rec={rec} />);
    expect(screen.getByTestId("record-hash").textContent).toBe(rec.content_sha256);
    expect(screen.getByTestId("constructed-note").textContent).toContain("NOT a measured food-insecurity rate");
    for (const q of rec.quarters.filter((x) => x.kind.startsWith("BACKTEST"))) {
      for (const c of PROVS) {
        const f = q.provinces[c].forecast;
        if (!f) continue;
        const cell = screen.getByTestId(`cell-${q.quarter}-${c}`);
        expect(within(cell).getByText(new RegExp(`P\\(HIGH\\) ${Math.round(f.p_high * 100)}%`))).toBeTruthy();
        expect(cell.textContent).toContain("indicative only");
        expect(f.indicative_only).toBe(true);
      }
    }
  });
});
