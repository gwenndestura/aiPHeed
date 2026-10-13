import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import { ForecastV2View } from "@/pages/ForecastV2";
import { evidenceText, goalText, periodsConsistent, type V2Data } from "@/lib/e24v2";

const pub = path.resolve(__dirname, "../../public");
const data: V2Data = JSON.parse(fs.readFileSync(path.join(pub, "e24v2_dashboard.json"), "utf-8"));

describe("e24v2_dashboard.json (actual E24v2 outputs)", () => {
  it("live cycle targets 2027-Q1 with 2026-Q4 news, consistent labels and no forecast", () => {
    expect(data.live.period.target_quarter).toBe("2027-Q1");
    expect(data.live.period.reference_quarter).toBe("2026-Q4");
    expect(periodsConsistent(data.live)).toBe(true);
    expect(data.live.status).toBe("INSUFFICIENT_DATA");
    expect(data.live.forecast).toBeNull();
    expect(data.live.mode).toBe("LIVE");
    expect(fs.existsSync(path.join(pub, `aiPHeed_forecast_report_${data.live.period.target_quarter}_v2.pdf`))).toBe(true);
  });
  it("replay is labelled REPLAY, is READY and covers five provinces and 142 LGUs", () => {
    expect(data.replay.mode).toBe("REPLAY");
    expect(data.replay.status).toBe("READY");
    expect(periodsConsistent(data.replay)).toBe(true);
    const k1 = data.replay.forecast!.leads["1"];
    expect(Object.keys(k1.provinces).length).toBe(5);
    expect(data.replay.forecast!.lgu_ranking.length).toBe(142);
    for (const v of Object.values(k1.provinces)) {
      expect(v.risk.p_high).toBeGreaterThanOrEqual(0);
      expect(v.risk.p_high).toBeLessThanOrEqual(1);
      expect(v.risk.S1_80pct_interval[0]).toBeLessThan(v.risk.S1_80pct_interval[1]);
    }
  });
  it("never shows the approved composite forecast as validated", () => {
    for (const e of Object.values(data.evidence.T1)) expect(e.status).toBe("NOT_ESTABLISHED");
    for (const v of Object.values(data.replay.forecast!.leads["1"].provinces))
      expect(evidenceText(v.risk.evidence)).toContain("Indicative only");
  });
  it("never reports the goal as met while a criterion is unmet or C9 is not assessable", () => {
    expect(data.goal.goal_met).toBe(false);
    expect(goalText(data)).toBe("Goal NOT met");
    expect(typeof data.goal.criteria.C9_generalizes_unseen).toBe("string");
  });
  it("lists sealed prospective forecasts with full hashes and pending status", () => {
    expect(data.seals.length).toBeGreaterThanOrEqual(1);
    for (const s of data.seals) {
      expect(s.sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(s.status).toBe("PENDING_OUTCOME_AUTHORIZATION");
    }
  });
  it("labels every province-mean substitute", () => {
    const sub = data.replay.forecast!.lgu_ranking.filter((r) => r.poverty_value_kind.startsWith("province-mean substitute"));
    expect(sub.length).toBe(data.lgu_analysis.province_mean_substitute);
    expect(sub.every((r) => r.limitation.includes("density only"))).toBe(true);
  });
});

describe("rendered E24v2 page (jsdom)", () => {
  it("shows status, missing inputs, replay label, evidence, goal and rankings", () => {
    render(<ForecastV2View d={data} />);
    expect(screen.getByTestId("target").textContent).toBe("Forecast target: Q1 2027 (January–March 2027)");
    expect(screen.getByTestId("status").textContent).toContain("INSUFFICIENT_DATA");
    expect(screen.getByTestId("missing").textContent).toContain("sws_rounds: STALE");
    expect(screen.queryByTestId("mismatch")).toBeNull();
    expect(screen.getByTestId("replay-mode").textContent).toContain("not a live forecast");
    expect(within(screen.getByTestId("province-rows")).getAllByRole("row").length).toBe(5);
    expect(screen.getAllByTestId("risk-evidence").every((e) => e.textContent!.startsWith("Indicative only"))).toBe(true);
    expect(screen.getByTestId("goal").textContent).toBe("Goal NOT met");
    expect(within(screen.getByTestId("confirmatory")).getAllByRole("row").length).toBe(4);
    expect(within(screen.getByTestId("ranking-rows")).getAllByRole("row").length).toBe(142);
    fireEvent.change(screen.getByLabelText("province"), { target: { value: "Quezon" } });
    expect(within(screen.getByTestId("ranking-rows")).getAllByRole("row").length).toBe(41);
    expect(within(screen.getByTestId("psa-rows")).getAllByRole("row").length).toBe(15);
  });
});
