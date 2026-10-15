import { existsSync, readFileSync } from "fs";
import path from "path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { E31BriefView } from "@/pages/E31Brief";
import { NewsEvidenceView } from "@/pages/NewsEvidence";
import { E31Record, PROVINCE_ORDER } from "@/lib/e31Record";

const file = path.resolve(__dirname, "../../public/e31_record.json");
const rec = (existsSync(file) ? JSON.parse(readFileSync(file, "utf-8")) : null) as E31Record | null;

describe.skipIf(!rec)("E31 DA brief", () => {
  it("labels the nowcast and the forecast with their cutoff and news window", () => {
    render(<E31BriefView rec={rec!} />);
    expect(screen.getByTestId("mode-NOWCAST").textContent).toContain("2026-Q4: Nowcast");
    expect(screen.getByTestId("mode-FORECAST").textContent).toContain("2027-Q1: Forecast");
    expect(screen.getByTestId("window-NOWCAST").textContent).toContain("2026-Q4 articles");
    expect(screen.getByTestId("window-FORECAST").textContent).toContain("2026-Q4 articles");   // forecast uses the previous quarter
  });

  it("shows each province's estimate with exact drivers and never a HIGH/LOW category", () => {
    render(<E31BriefView rec={rec!} />);
    PROVINCE_ORDER.forEach((c) => {
      const now = rec!.provinces_now[c].nowcast_2026Q4;
      const box = screen.getByTestId(`now-${c}`);
      expect(box.textContent).toContain(`${Math.round(now.p_high * 100)}%`);
      expect(box.textContent).not.toMatch(/\b(HIGH|LOW)\b/);
      const sum = now.drivers!.reduce((a, d) => a + d.contribution, 0);
      expect(Math.abs(sum - (now.S1_forecast! - rec!.quarters.find((q) => q.mode === "NOWCAST")!.threshold))).toBeLessThan(1e-3);
    });
  });

  it("states the 75% verdict and the disclaimer", () => {
    render(<E31BriefView rec={rec!} />);
    expect(screen.getByTestId("threshold-verdict").textContent).toContain("always-HIGH");
    expect(screen.getByTestId("disclaimer").textContent).toContain("not official");
  });
});

describe.skipIf(!rec)("E31 news evidence page", () => {
  it("lists only validated articles with outlet, date, province and a link", () => {
    render(<NewsEvidenceView rec={rec!} />);
    fireEvent.change(screen.getByTestId("f-quarter"), { target: { value: "all" } });
    const items = screen.getAllByTestId("article");
    expect(items.length).toBe(rec!.news.articles.length);
    items.slice(0, 5).forEach((li) => expect(within(li).getByRole("link").getAttribute("href")).toMatch(/^https:\/\//));
  });

  it("filters by province, quarter and relevance and keeps the funnel consistent", () => {
    render(<NewsEvidenceView rec={rec!} />);
    fireEvent.change(screen.getByTestId("f-province"), { target: { value: "Quezon" } });
    fireEvent.change(screen.getByTestId("f-quarter"), { target: { value: "all" } });
    fireEvent.change(screen.getByTestId("f-relevance"), { target: { value: "DIRECT" } });
    const want = rec!.news.articles.filter((a) => a.province === "Quezon" && a.relevance === "DIRECT").length;
    expect(screen.queryAllByTestId("article").length).toBe(want);
    const fssi = rec!.news.by_province_quarter.filter((r) => r.province === "Quezon").reduce((a, r) => a + r.admitted_after_dedup, 0);
    expect(screen.getByTestId("n-fssi").textContent).toBe(String(fssi));
    expect(Number(screen.getByTestId("n-relevant").textContent)).toBeLessThanOrEqual(Number(screen.getByTestId("n-attributed").textContent));
  });

  it("says when a province-quarter has no usable evidence instead of showing low risk", () => {
    render(<NewsEvidenceView rec={rec!} />);
    const none = rec!.news.by_province_quarter.find((r) => r.evidence_status_v2 === "NO_USABLE_EVIDENCE")!;
    fireEvent.change(screen.getByTestId("f-province"), { target: { value: none.province } });
    fireEvent.change(screen.getByTestId("f-quarter"), { target: { value: none.quarter } });
    expect(screen.getByTestId("pq-status").textContent).toContain("no usable evidence");
    expect(screen.getByTestId("empty")).toBeTruthy();
  });
});

describe("E31 record loader", () => {
  it("asks the API under /api/v1 first and falls back to the identical static copy", async () => {
    const { loadE31 } = await import("@/lib/e31Record");
    const calls: string[] = [];
    const orig = globalThis.fetch;
    globalThis.fetch = (async (u: string) => {
      calls.push(String(u));
      if (String(u).includes("/api/v1/quarterly/e31/record")) return { ok: false, status: 503 } as Response;
      return { ok: true, json: async () => ({ schema: "e31/1" }) } as unknown as Response;
    }) as typeof fetch;
    try {
      const r = await loadE31();
      expect(r.schema).toBe("e31/1");
      expect(calls[0]).toMatch(/\/api\/v1\/quarterly\/e31\/record$/);
      expect(calls[1]).toBe("/e36_record.json");   // E36: the served record's static copy
    } finally {
      globalThis.fetch = orig;
    }
  });
});
