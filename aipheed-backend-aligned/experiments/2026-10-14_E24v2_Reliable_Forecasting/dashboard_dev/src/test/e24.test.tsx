import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import { ForecastPeriodView } from "@/pages/ForecastPeriod";
import { eligibleArticles, goalMet, periodsConsistent, type E23Data } from "@/lib/e23";

const pub = path.resolve(__dirname, "../../public");
const data: E23Data = JSON.parse(fs.readFileSync(path.join(pub, "e24_dashboard.json"), "utf-8"));

describe("e24_dashboard.json (actual E24 outputs)", () => {
  it("targets 2027-Q1 with 2026-Q4 news and consistent period labels", () => {
    expect(data.period.target_quarter).toBe("2027-Q1");
    expect(data.period.reference_quarter).toBe("2026-Q4");
    expect(periodsConsistent(data)).toBe(true);
    expect(fs.existsSync(path.join(pub, `aiPHeed_forecast_report_${data.period.target_quarter}.pdf`))).toBe(true);
  });
  it("has no forecast and no ranking for the target while data are insufficient", () => {
    expect(data.status).toBe("INSUFFICIENT_DATA");
    expect(data.forecast).toBeNull();
    expect(data.rankings.for_target_quarter.startsWith("UNAVAILABLE")).toBe(true);
  });
  it("never reports the goal as met while C9 is not assessable", () => {
    for (const t of ["T1", "T2"] as const) for (const r of data.evaluation[t]) {
      if (r.criteria && typeof r.criteria.C9_generalizes_unseen === "string") expect(goalMet(r)).toBe(false);
    }
  });
  it("labels every province-mean substitute and keeps all 142 LGUs", () => {
    expect(data.rankings.rows.length).toBe(142);
    const sub = data.rankings.rows.filter((r) => r.poverty_value_kind.startsWith("province-mean substitute"));
    expect(sub.length).toBe(data.rankings.verification.lgus_with_substitute);
    expect(sub.every((r) => r.poverty_lgu_estimate === "")).toBe(true);
  });
  it("filters news strictly by the declared window", () => {
    const fake = { ...data, supporting_articles: [
      { title: "in", link: "a", province_code: "PH040100000", published_ph: "2026-11-02T10:00:00+08:00" },
      { title: "late", link: "b", province_code: "PH040100000", published_ph: "2027-01-01T00:00:01+08:00" }] };
    expect(eligibleArticles(fake).map((a) => a.title)).toEqual(["in"]);
  });
});

describe("rendered page (jsdom)", () => {
  it("shows the banner, status, missing inputs, goal status and rankings", () => {
    render(<ForecastPeriodView d={data} />);
    expect(screen.getByTestId("target").textContent).toBe("Forecast target: Q1 2027 (January–March 2027)");
    expect(screen.getByTestId("news").textContent).toContain("Supporting news: Q4 2026 (October–December 2026)");
    expect(screen.getByTestId("status").textContent).toContain("INSUFFICIENT_DATA");
    expect(screen.queryByTestId("mismatch")).toBeNull();
    expect(screen.getByTestId("article-count").textContent).toBe("0");
    expect(screen.getByTestId("goal").textContent).toBe("Goal NOT met");
    expect(within(screen.getByTestId("ranking-rows")).getAllByRole("row").length).toBe(142);
    fireEvent.change(screen.getByLabelText("province"), { target: { value: "PH040300000" } });
    expect(within(screen.getByTestId("ranking-rows")).getAllByRole("row").length).toBe(41);      // Quezon
    fireEvent.change(screen.getByLabelText("target"), { target: { value: "T2" } });
    expect(screen.getByTestId("criteria").textContent).toContain("C9 Generalizes to unseen quarters");
  });
});
