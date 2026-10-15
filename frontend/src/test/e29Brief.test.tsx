import { existsSync, readFileSync } from "fs";
import path from "path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E29BriefView, E29Record } from "@/pages/E29Brief";

const file = path.resolve(__dirname, "../../public/e29_da_brief_record.json");
const rec = (existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : null) as E29Record | null;

describe.skipIf(!rec)("E29 DA brief: observed evidence vs experimental estimates", () => {
  it("shows the regional hunger observation once, as one regional value", () => {
    render(<E29BriefView rec={rec!} />);
    expect(screen.getAllByTestId("regional-observation").length).toBe(1);
    expect(screen.getByTestId("regional-level").textContent).toContain("ONE value shared by all five provinces");
  });

  it("labels every item MEASURED / EXPERIMENTAL / UNAVAILABLE and keeps price pressure apart from food insecurity", () => {
    render(<E29BriefView rec={rec!} />);
    Object.keys(rec!.forecast_quarter.provinces).forEach((c) => {
      const kinds = Array.from(screen.getByTestId(`evidence-${c}`).querySelectorAll("tr")).map((r) => r.getAttribute("data-kind"));
      expect(kinds).toContain("MEASURED");
      expect(kinds).toContain("EXPERIMENTAL");
      expect(kinds).toContain("UNAVAILABLE");
      expect(screen.getByTestId(`price-${c}`).textContent).toContain("price pressure, not food insecurity");
      expect(screen.getByTestId(`suitability-${c}`).textContent).toMatch(/^MONITORING ONLY/);
    });
  });

  it("never shows a HIGH/LOW category for an experimental estimate", () => {
    render(<E29BriefView rec={rec!} />);
    Object.keys(rec!.forecast_quarter.provinces).forEach((c) => {
      expect(screen.getByTestId(`brief-${c}-estimate`).textContent).not.toMatch(/\b(HIGH|LOW)\b/);
    });
  });
});
