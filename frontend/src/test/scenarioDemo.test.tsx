import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// The scenario page reads only its own hooks; the real outlook hooks are never mocked or called here.
const index = {
  data: {
    synthetic: true,
    label: "SYNTHETIC – FOR DEMONSTRATION",
    notice: "Synthetic scenario inputs run through the frozen E168 procedure.",
    production: { model_id: "e168-lgbm-1.0", folder: "2026-Q4_2026-11-01", issue: "2026-Q4", cutoff: "2026-11-01", published: "2026-11-08", artifact_sha256: "x" },
    firstHigh: { scenario_id: "S3", variant: "combined:t=1", param: 1, province: "Quezon" },
    s3bUsed: false,
    scenarios: [{ id: "S0", title: "Baseline (real latest inputs)" }],
  },
  isError: false,
  isLoading: false,
};
const scenario = {
  data: {
    synthetic: true,
    label: "SYNTHETIC – FOR DEMONSTRATION",
    notice: "",
    id: "S0",
    title: "Baseline (real latest inputs)",
    meta: { groups: {}, shocks: {}, unsigned_columns: [], s3_first_high: index.data.firstHigh, s3b_used: false, production: index.data.production },
    data: [
      { province: "Quezon", lead: 1, quarter: "2027-Q1", score_pct: 35.5, range90_low: 23.3, range90_high: 49.9, probability: 0.064, class: "LOW", top_driver_1: "market", top_driver_2: "climate", top_driver_3: "employment" },
    ],
  },
  isLoading: false,
};
const calls: string[] = [];
vi.mock("@/lib/queries", () => ({
  useDemoScenarios: () => {
    calls.push("index");
    return index;
  },
  useDemoScenario: (id: string) => {
    calls.push(`scenario:${id}`);
    return scenario;
  },
}));

import { ScenarioDemo } from "@/components/ScenarioDemo";
import { DEMO_MODE_KEY, SYNTHETIC_LABEL, readDemoMode, writeDemoMode } from "@/lib/demoMode";

describe("Scenario / Demo mode toggle", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("is off by default", () => {
    expect(readDemoMode()).toBe(false);
  });

  it("is remembered for this browser session only", () => {
    writeDemoMode(true);
    expect(readDemoMode()).toBe(true);
    expect(window.sessionStorage.getItem(DEMO_MODE_KEY)).toBe("on");
    expect(window.localStorage.getItem(DEMO_MODE_KEY)).toBeNull();
    writeDemoMode(false);
    expect(readDemoMode()).toBe(false);
  });
});

describe("Scenario page", () => {
  it("carries the SYNTHETIC banner and reads only the demo hooks", () => {
    // jsdom has no ResizeObserver; Recharts' ResponsiveContainer needs one to mount.
    globalThis.ResizeObserver ??= class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
    calls.length = 0;
    render(<ScenarioDemo />);
    const banners = screen.getAllByTestId("synthetic-banner");
    expect(banners.length).toBeGreaterThanOrEqual(2);
    for (const b of banners) expect(b.textContent).toBe(SYNTHETIC_LABEL);
    expect(SYNTHETIC_LABEL).toBe("SYNTHETIC – FOR DEMONSTRATION");
    expect(calls.every((c) => c === "index" || c.startsWith("scenario:"))).toBe(true);
    expect(screen.getByText("Quezon")).toBeInTheDocument();
  });
});

// Source-level guards: synthetic data has its own endpoint and never reaches the public pages.
const SRC = resolve(__dirname, "..");
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? (f === "test" ? [] : files(p)) : /\.(ts|tsx)$/.test(f) ? [p] : [];
  });
}
const all = files(SRC).map((p) => ({ p: p.replace(/\\/g, "/"), s: readFileSync(p, "utf-8") }));

describe("Synthetic scenarios stay separate", () => {
  it("only the demo hooks request /demo/scenarios", () => {
    // a string literal holding the route (comments that mention it do not count)
    const users = all.filter((f) => /[`"']\/api\/v1\/demo\/scenarios/.test(f.s)).map((f) => f.p.split("/src/")[1]);
    expect(users.sort()).toEqual(["lib/queries.ts"]);
  });

  it("the demo hooks call nothing but /api/v1/demo/scenarios", () => {
    const q = all.find((f) => f.p.endsWith("lib/queries.ts"))!.s;
    const block = q.slice(q.indexOf("export function useDemoScenarios"));
    const urls = Array.from(block.matchAll(/api\.(?:get|post|delete)\b[^(]*\(\s*[`"]([^`"$]+)/g)).map((m) => m[1]);
    expect(urls.length).toBe(2);
    for (const u of urls) expect(u.startsWith("/api/v1/demo/scenarios")).toBe(true);
  });

  it("public pages never import the scenario page or the demo toggle", () => {
    const publicPages = ["pages/Index.tsx", "pages/Data.tsx", "pages/Visualization.tsx", "pages/Landing.tsx"];
    for (const p of publicPages) {
      const s = all.find((f) => f.p.endsWith(p))!.s;
      expect(s).not.toMatch(/ScenarioDemo|demoMode/);
    }
    const importers = all.filter((f) => /from "@\/components\/ScenarioDemo"|from "@\/lib\/demoMode"/.test(f.s)).map((f) => f.p.split("/src/")[1]);
    expect(importers.sort()).toEqual(["components/ScenarioDemo.tsx", "pages/Admin.tsx"]);
  });
});
