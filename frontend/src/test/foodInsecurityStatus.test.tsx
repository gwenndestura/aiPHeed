import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { FoodInsecurityStatus } from "@/lib/apiTypes";

const PENDING: FoodInsecurityStatus = {
  status: "validation_pending",
  forecast: null,
  reason: "no model has passed the release gate",
  message: "No food-insecurity forecasting model has passed all acceptance tests yet, so no official food-insecurity forecast is shown.",
  candidates: [{ model_id: "pfi-1.0", status: "rejected", failed_checks: ["B2", "B3", "B6"] }],
  acceptance_checks_total: 16,
};

const state: { data: FoodInsecurityStatus | undefined; error: unknown; isLoading: boolean } = {
  data: PENDING,
  error: null,
  isLoading: false,
};
vi.mock("@/lib/queries", () => ({ useFoodInsecurityStatus: () => state }));

import { FoodInsecurityStatusCardBody } from "@/components/FoodInsecurityStatus";

describe("Official food-insecurity forecast area", () => {
  beforeEach(() => {
    state.data = PENDING;
    state.error = null;
    state.isLoading = false;
  });

  it("shows Validation pending with no forecast numbers", () => {
    render(<FoodInsecurityStatusCardBody />);
    const card = screen.getByTestId("fi-status-pending");
    expect(card.textContent).toMatch(/validation pending/i);
    expect(card.textContent).not.toMatch(/\d+(\.\d+)?%/);
    expect(card.textContent).toMatch(/price-pressure risk index/);
    expect(card.textContent).toMatch(/not a food-insecurity forecast/);
    expect(screen.getByTestId("fi-status-candidates").textContent).toContain("pfi-1.0 (rejected; 3 of 16 checks not yet passed)");
  });

  it("shows nothing forecast-like when the status cannot be loaded", () => {
    state.data = undefined;
    state.error = new Error("network");
    render(<FoodInsecurityStatusCardBody />);
    expect(screen.getByTestId("fi-status-unavailable").textContent).toMatch(/No forecast is shown/);
  });
});

// Source-level guard: the dashboard must not mount unapproved forecast cards or read their routes.
const SRC = resolve(__dirname, "..");
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? (f === "test" ? [] : files(p)) : /\.(ts|tsx)$/.test(f) ? [p] : [];
  });
}

describe("No unapproved forecast on the dashboard", () => {
  const all = files(SRC).map((p) => ({ p: p.replace(/\\/g, "/"), s: readFileSync(p, "utf-8") }));

  it("MapDashboard mounts neither the removed status card nor the FI9 or FI10 cards", () => {
    const dash = all.find((f) => f.p.endsWith("components/MapDashboard.tsx"))!.s;
    expect(dash).not.toContain("<FoodInsecurityStatusCardBody />");     // removed 2026-11-06 (owner request; E166 on the map)
    expect(dash).not.toMatch(/NextQuarterOutlookCardBody|ProvincialOutlookCardBody/);
  });

  it("no mounted component imports the preserved FI9 or FI10 cards", () => {
    const importers = all.filter((f) => /from "@\/components\/(NextQuarterOutlook|ProvincialOutlook)"/.test(f.s));
    expect(importers.map((f) => f.p)).toEqual([]);
  });

  it("the only food-insecurity forecast route the app reads is the release-gated one", () => {
    const q = all.find((f) => f.p.endsWith("lib/queries.ts"))!.s;
    expect(q).toContain('"/api/v1/final/food-insecurity/outlook"');
    const used = all
      .filter((f) => !/components\/(NextQuarterOutlook|ProvincialOutlook)\.tsx$|lib\/queries\.ts$/.test(f.p))
      .filter((f) => /useNextQuarterOutlook|useProvincialOutlook|useProvincialMeasurements|useFinalEvaluation|useFinalArchive/.test(f.s));
    expect(used.map((f) => f.p)).toEqual([]);
  });
});
