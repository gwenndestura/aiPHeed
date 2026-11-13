import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import type { ForecastHistory, ForecastPeriod, HistoryForecast } from "@/lib/apiTypes";

// Forecast history and the forecasting period come from the backend (no quarter label is fixed in the frontend).
let history: ForecastHistory | undefined;
let period: ForecastPeriod | undefined;
vi.mock("@/lib/queries", () => ({
  useForecastHistory: () => ({ data: history, isLoading: false, error: null }),
  useForecastPeriod: () => ({ data: period }),
}));

import { ForecastHistoryModal } from "@/components/ForecastHistoryModal";
import { ForecastPeriodLines } from "@/components/FoodInsecurityStatus";

const f = (issue: string, target: string, province: string, extra: Partial<HistoryForecast> = {}): HistoryForecast => ({
  model_id: "final-rate-mind-1.0", model_version: "e1f8675fdaf48335", issue_quarter: issue, information_cutoff: "2026-11-01",
  target_quarter: target, lead: 1, province, p_high: 0.002, risk_class: "LOW", share_pct: 23.2, range90_pct: [13.3, 37.3],
  generated_utc: "2026-11-13T15:00:00+00:00", data_version: "d", withdrawn: false, validation_status: "awaiting outcome",
  observed_share_pct: null, observed_class: null, correct: null, error_pp: null, issue_status: "historical", target_status: "future", ...extra,
});

describe("forecast history", () => {
  it("lists issues newest first, keeps the earlier issue, and marks results awaiting an outcome", () => {
    history = {
      current_quarter: "2027-Q1", served_issue_quarter: "2027-Q1", issues: ["2026-Q4", "2027-Q1"], count: 3, ledger: { ok: true },
      forecasts: [
        f("2027-Q1", "2027-Q2", "Quezon", { issue_status: "current issue" }),
        f("2026-Q4", "2027-Q2", "Quezon"),
        f("2026-Q4", "2027-Q1", "Quezon", { target_status: "current", validation_status: "validated", observed_share_pct: 55,
          observed_class: "HIGH", correct: false }),
      ],
    };
    render(<ForecastHistoryModal open onOpenChange={() => undefined} quarters={[]} value="2027-Q2" onSelect={() => undefined} />);
    const sections = screen.getAllByTestId(/^history-issue-/);
    expect(sections.map((s) => s.getAttribute("data-testid"))).toEqual(["history-issue-2027-Q1", "history-issue-2026-Q4"]);
    expect(within(sections[0]).getByText("Current issue")).toBeTruthy();
    expect(within(sections[1]).getByText("Earlier issue")).toBeTruthy();
    expect(within(sections[0]).getByText("awaiting outcome")).toBeTruthy();
    expect(within(sections[1]).getByText("55% measured · class wrong")).toBeTruthy();
    expect(within(sections[1]).getByText(/Q2 2027/)).toBeTruthy();       // the original Q4 2026 forecast of Q2 2027 stays listed
  });

  it("states the current quarter, the served issue and a stale forecast plainly", () => {
    period = {
      now_ph: "2027-02-03T10:00:00+08:00", current_quarter: "2027-Q1", issue_quarter: "2027-Q1", issue_date: "2027-02-01T00:00:00+08:00",
      next_issue_quarter: "2027-Q2", next_issue_date: "2027-05-01T00:00:00+08:00", max_lead: 2, targets: [], served_targets: [],
      served_issue_quarter: "2026-Q4", served_generated_utc: "2026-11-13T15:00:00+00:00", stale: true,
      stale_reason: "the 2027-Q1 issue has not been generated yet; the 2026-Q4 issue (generated 2026-11-13) is shown",
      latest_data_update_utc: "2027-02-02T22:30:00+00:00", last_successful_run_utc: null, model: { id: "final-rate-mind-1.0" },
    };
    render(<ForecastPeriodLines />);
    const box = screen.getByTestId("forecast-period");
    expect(box.textContent).toContain("Now: Q1 2027");
    expect(box.textContent).toContain("forecast issued Q4 2026");
    expect(screen.getByTestId("forecast-period-stale").textContent).toContain("has not been generated yet");
    expect(box.textContent).toContain("next forecast 1 May 2027");
  });
});
