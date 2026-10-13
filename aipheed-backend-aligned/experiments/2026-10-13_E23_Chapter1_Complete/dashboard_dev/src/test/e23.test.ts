import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { eligibleArticles, periodsConsistent, type E23Data } from "@/lib/e23";

const file = path.resolve(__dirname, "../../public/e23_dashboard.json");
const data: E23Data = JSON.parse(fs.readFileSync(file, "utf-8"));

describe("e23_dashboard.json (actual E23 forecast record)", () => {
  it("targets 2027-Q1 with 2026-Q4 supporting news and consistent labels", () => {
    expect(data.period.reference_quarter).toBe("2026-Q4");
    expect(data.period.target_quarter).toBe("2027-Q1");
    expect(data.labels.target).toBe("Forecast target: Q1 2027 (January–March 2027)");
    expect(data.labels.news.startsWith("Supporting news: Q4 2026 (October–December 2026)")).toBe(true);
    expect(periodsConsistent(data)).toBe(true);
  });
  it("shows no forecast and lists what is missing while data are insufficient", () => {
    expect(data.status).toBe("INSUFFICIENT_DATA");
    expect(data.forecast).toBeNull();
    expect(data.missing.some((m) => m.startsWith("news_reference_quarter"))).toBe(true);
    expect(data.rankings.for_target_quarter.startsWith("UNAVAILABLE")).toBe(true);
  });
  it("never shows an article outside the declared news window", () => {
    const fake: E23Data = { ...data, supporting_articles: [
      { title: "in", link: "a", province_code: "PH040100000", published_ph: "2026-11-02T10:00:00+08:00" },
      { title: "after cutoff", link: "b", province_code: "PH040100000", published_ph: "2027-01-01T00:00:01+08:00" },
      { title: "before", link: "c", province_code: "PH040100000", published_ph: "2026-09-30T23:59:59+08:00" },
      { title: "undated", link: "d", province_code: "PH040100000", published_ph: "" }] };
    expect(eligibleArticles(fake).map((a) => a.title)).toEqual(["in"]);
  });
  it("detects a label/period mismatch", () => {
    expect(periodsConsistent({ ...data, labels: { ...data.labels, target: "Forecast target: Q2 2027" } })).toBe(false);
  });
  it("carries all 142 LGUs with the poverty-source disclosure", () => {
    expect(data.rankings.rows.length).toBe(142);
    expect(data.rankings.verification.same_order_as_backend).toBe(true);
    expect(data.rankings.rows.filter((r) => r.poverty_is_province_fallback === "True").length)
      .toBe(data.rankings.verification.poverty_province_fallback_lgus);
  });
  it("PDF exists for the same target quarter", () => {
    expect(fs.existsSync(path.resolve(__dirname, `../../public/aiPHeed_forecast_report_${data.period.target_quarter}.pdf`))).toBe(true);
  });
});
