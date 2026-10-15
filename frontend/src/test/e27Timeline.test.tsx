import { readFileSync } from "fs";
import path from "path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E27TimelineView } from "@/pages/E27Timeline";
import { E27Record, PROVINCE_CODES, RiskView, riskWording } from "@/lib/e27Record";
import { municipalityToData } from "@/lib/adapters";
import type { MunicipalitySummary } from "@/lib/apiTypes";

const rec = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../public/e27_timeline_record.json"), "utf-8"),
) as E27Record;

describe("E27 forecast timeline (reads the single E27 record)", () => {
  it("shows the nine quarters, the record hash and the evidence banner", () => {
    render(<E27TimelineView rec={rec} />);
    expect(rec.quarters.map((q) => q.quarter)).toEqual([
      "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1",
    ]);
    expect(screen.getByTestId("record-hash").textContent).toBe(rec.content_sha256);
    expect(screen.getByTestId("evidence-banner").textContent).toContain("No forecast is validated");
  });

  it("never classifies an experimental estimate as HIGH or LOW and never colours it as risk", () => {
    render(<E27TimelineView rec={rec} />);
    const blocks = document.querySelectorAll("[data-evidence]");
    expect(blocks.length).toBeGreaterThanOrEqual(25);
    blocks.forEach((b) => {
      expect(b.getAttribute("data-evidence")).toBe("EXPERIMENTAL");
      expect(b.className).not.toMatch(/amber|sky|red|orange/);
      expect(b.querySelector(".font-semibold")!.textContent).toMatch(/^P\(above threshold\) \d+%$/);
      expect(b.textContent).toContain("EXPERIMENTAL — not validated");
    });
  });

  it("would classify only a VALIDATED lead", () => {
    const base = rec.quarters[0].provinces[PROVINCE_CODES[0]].risk as RiskView;
    expect(riskWording(base).classified).toBe(false);
    const v = { ...base, decision: "HIGH" as const, evidence: { ...base.evidence, status: "VALIDATED" as const } };
    expect(riskWording(v)).toEqual({ headline: `HIGH (P ${Math.round(base.p_above_threshold * 100)}%)`, classified: true });
  });

  it("displays exactly the record's probabilities", () => {
    render(<E27TimelineView rec={rec} />);
    for (const q of rec.quarters.filter((x) => x.state === "BACKTEST")) {
      for (const c of PROVINCE_CODES) {
        const r = q.provinces[c].risk;
        if (!r) continue;
        expect(screen.getByTestId(`risk-${q.quarter}-${c}`).textContent).toContain(
          `P(above threshold) ${Math.round(r.p_above_threshold * 100)}%`,
        );
      }
    }
  });

  it("keeps the constructed price-pressure indicator in its own row, out of the risk cell", () => {
    render(<E27TimelineView rec={rec} />);
    const q = rec.quarters.find((x) => x.quarter === "2025-Q1")!;
    for (const c of PROVINCE_CODES) {
      expect(screen.getByTestId(`cell-2025-Q1-${c}`).textContent).not.toMatch(/D>0|price/i);
      const pp = q.provinces[c].price_pressure!;
      expect(screen.getByTestId(`pp-2025-Q1-${c}`).textContent).toContain(`P(D>0) ${Math.round(pp.p_above_regional_mean * 100)}%`);
    }
  });

  it("2027-Q1: missing inputs, every dependency listed with whether it blocks, and the estimate labelled as not operational", () => {
    render(<E27TimelineView rec={rec} />);
    const op = rec.quarters.find((x) => x.quarter === "2027-Q1")!;
    expect(op.state).toBe("MISSING_INPUTS");
    for (const d of op.dependencies!) {
      const row = screen.getByTestId(`dep-${d.id}`);
      expect(row.textContent).toContain(d.needs);
      expect(row.textContent).toContain(d.blocking ? "yes" : "no (display context only)");
    }
    for (const c of PROVINCE_CODES) {
      const cell = screen.getByTestId(`cell-2027-Q1-${c}`);
      expect(cell.textContent).toContain("not a low-risk state");
      expect(cell.textContent).toContain("not the operational forecast");
      expect(cell.textContent).not.toMatch(/\bHIGH\b|\bLOW\b/);
    }
  });

  it("shows the official anchor as face validity only", () => {
    render(<E27TimelineView rec={rec} />);
    expect(screen.getByTestId("official-anchor").textContent).toContain("face validity only");
    expect(screen.getByTestId("local-note").textContent).toContain("not local assessments");
  });
});

describe("municipal poverty disclosure (E27 fix)", () => {
  const m: MunicipalitySummary = {
    id: "cavite-gma", name: "Gen. Mariano Alvarez", provinceId: "cavite", lguCode: "042123000",
    classification: "Municipality", population: 172433, densityPerKm2: 18344, povertyRate: null, quarter: "2026-Q2",
    riskIndex: 0.4, riskLevel: "moderate", disaggregationLabel: "reweighted province figure", limitedSignal: false,
  } as MunicipalitySummary;

  it("a missing municipal estimate stays missing (never 0%) and carries its limitation", () => {
    const d = municipalityToData(m, "Cavite");
    expect(d.povertyRate).toBeNull();
    expect(d.povertyNote).toContain("province-mean substitute");
  });

  it("an LGU with its own estimate keeps it and has no note", () => {
    const d = municipalityToData({ ...m, povertyRate: 18.7 }, "Quezon");
    expect(d.povertyRate).toBe(18.7);
    expect(d.povertyNote).toBeNull();
  });
});
