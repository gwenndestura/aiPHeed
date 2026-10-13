import { describe, expect, it } from "vitest";
import { constructedLabel, dColor, fmt, rankByD, type ProvinceValue } from "@/lib/research";
import fs from "node:fs";
import path from "node:path";

const P = (name: string, D: number | null): ProvinceValue => ({ code: name, name, F: 1, D, S1: null });

describe("research helpers", () => {
  it("ranks by D, 1 = highest, ties share the lowest rank", () => {
    const r = rankByD([P("A", 1), P("B", 2), P("C", 2), P("D", -1), P("E", 0)]);
    expect(r.map((x) => [x.name, x.rank])).toEqual([["B", 1], ["C", 1], ["A", 3], ["E", 4], ["D", 5]]);
  });
  it("gives no ranking when any D is missing (no zero fill)", () => {
    expect(rankByD([P("A", 1), P("B", null), P("C", 2), P("D", -1), P("E", 0)])).toEqual([]);
  });
  it("constructed label uses strict > 14.6 and keeps null as insufficient", () => {
    expect(constructedLabel(14.6)).toBe("LOW");
    expect(constructedLabel(14.61)).toBe("HIGH");
    expect(constructedLabel(null)).toBeNull();
  });
  it("formats missing values as a dash and colours D without risk wording", () => {
    expect(fmt(null)).toBe("—");
    expect(dColor(null)).toBe("#9ca3af");
  });
});

describe("e18_dashboard.json (actual E18 outputs)", () => {
  const file = path.resolve(__dirname, "../../public/e18_dashboard.json");
  const data = JSON.parse(fs.readFileSync(file, "utf-8"));
  it("contains the real run outputs and required separations", () => {
    expect(data.generated_from_run).toMatch(/^2026\d{4}T\d{6}Z$/);
    expect(data.forecast_2027Q1.H.label).toMatch(/not a forecast of provincial food insecurity/);
    expect(data.forecast_2027Q1.horizon).toBe(3);
    expect(data.lead_time.max_supported).toBeNull();
  });
  it("shows the regional value once per quarter and no data after 2026-Q2", () => {
    for (const q of data.history) {
      expect(q.quarter <= "2026-Q2").toBe(true);
      expect(q.provinces).toHaveLength(5);
    }
  });
  it("never uses 'food insecure' or 'risk level' wording in outputs", () => {
    const txt = JSON.stringify(data);
    expect(/food[\s-]*insecure(?!ity)/i.test(txt)).toBe(false);
    expect(/risk level/i.test(txt)).toBe(false);
  });
});
