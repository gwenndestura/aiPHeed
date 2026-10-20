import { describe, expect, it } from "vitest";
import { summaryHeadline } from "@/lib/summaryHeadline";

describe("summary headline", () => {
  it("keeps only the first sentence and puts the all-caps lead in sentence case", () => {
    const s =
      "ESTIMATED FOOD-INSECURITY RISK for Batangas, 2027-Q1: HIGH (risk index 0.71 on a 0-1 scale; HIGH at 0.50). " +
      "Domain scores (0.5 = the historical middle): Regional hunger 0.88 (weight 24%).";
    expect(summaryHeadline(s)).toBe("Estimated food-insecurity risk for Batangas, 2027-Q1: HIGH (risk index 0.71 on a 0-1 scale; HIGH at 0.50).");
  });

  it("handles the regional lead, which is followed by a comma", () => {
    const s = "ESTIMATED FOOD-INSECURITY RISK, 2027-Q1: HIGH in Cavite 0.76, Laguna 0.80 (regional mean index 0.74; HIGH at 0.50). An evidence-weighted proxy.";
    expect(summaryHeadline(s)).toBe("Estimated food-insecurity risk, 2027-Q1: HIGH in Cavite 0.76, Laguna 0.80 (regional mean index 0.74; HIGH at 0.50).");
  });

  it("does not split on decimals and leaves a normal-case sentence alone", () => {
    const s = "Food-insecurity risk in Laguna for 2027-Q1 is forecast LOW (7% probability): hunger stays above 11.3% (96%). Slower food inflation.";
    expect(summaryHeadline(s)).toBe("Food-insecurity risk in Laguna for 2027-Q1 is forecast LOW (7% probability): hunger stays above 11.3% (96%).");
  });
});
