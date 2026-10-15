import { existsSync, readFileSync } from "fs";
import path from "path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E28BriefView } from "@/pages/E28Brief";
import { E28Record, ProvinceBrief, estimateWording } from "@/lib/e28Record";
import { municipalityToData } from "@/lib/adapters";
import type { MunicipalitySummary } from "@/lib/apiTypes";

const file = path.resolve(__dirname, "../../public/e28_da_brief_record.json");
const rec = (existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : null) as E28Record | null;

describe.skipIf(!rec)("E28 DA brief (reads the single E28 record)", () => {
  it("shows the record hash and the experimental banner", () => {
    render(<E28BriefView rec={rec!} />);
    expect(screen.getByTestId("record-hash").textContent).toBe(rec!.content_sha256);
    expect(screen.getByTestId("status-banner").textContent).toContain("EXPERIMENTAL");
  });

  it("never classifies an experimental estimate and shows its drivers and a proportionate use", () => {
    render(<E28BriefView rec={rec!} />);
    const cards = document.querySelectorAll("[data-evidence]");
    expect(cards.length).toBe(6);
    Object.entries(rec!.forecast_quarter.provinces).forEach(([code]) => {
      const est = screen.getByTestId(`brief-${code}-estimate`).textContent!;
      expect(est).toMatch(/P\(above threshold\) \d+%$/);
      expect(est).not.toMatch(/\b(HIGH|LOW)\b/);
      expect(screen.getByTestId(`brief-${code}-drivers`).querySelectorAll("li").length).toBe(2);
      expect(screen.getByTestId(`brief-${code}-use`).textContent).toContain("Indicative only");
    });
    cards.forEach((c) => expect(c.className).not.toMatch(/amber|red|orange|sky/));
  });

  it("shows the operational quarter's missing inputs and no estimate", () => {
    render(<E28BriefView rec={rec!} />);
    expect(screen.getByTestId("brief-operational-estimate").textContent).toContain("No estimate");
    expect(screen.getByTestId("brief-operational-missing").textContent).toContain("not a low-risk state");
  });

  it("lists all 142 LGUs as relative positions and marks substitute poverty values", () => {
    render(<E28BriefView rec={rec!} />);
    const rows = screen.getAllByTestId("lgu-row");
    expect(rows.length).toBe(142);
    expect(rows.filter((r) => r.getAttribute("data-kind") === "substitute").length).toBe(126);
    expect(screen.getByTestId("lgu-ranking").textContent).not.toMatch(/High risk|Low risk/);
  });

  it("would classify only a VALIDATED lead", () => {
    const b = Object.values(rec!.forecast_quarter.provinces)[0] as ProvinceBrief;
    expect(estimateWording(b).classified).toBe(false);
    expect(estimateWording({ ...b, evidence_status: "VALIDATED", category: "HIGH" }).classified).toBe(true);
  });
});

describe("E28: the main dashboard never bands an LGU", () => {
  it("maps a null LGU level to 'unrated' and a null index to NaN, never to a band or 0", () => {
    const m = {
      id: "cavite-x", name: "X", provinceId: "cavite", lguCode: "042101000", classification: "Municipality",
      population: 1, densityPerKm2: 1, povertyRate: null, quarter: "2026-Q4", riskIndex: null, riskLevel: null,
      disaggregationLabel: "d", limitedSignal: false,
    } as unknown as MunicipalitySummary;
    const d = municipalityToData(m, "Cavite");
    expect(d.riskLevel).toBe("unrated");
    expect(Number.isNaN(d.riskScore)).toBe(true);
  });
});
