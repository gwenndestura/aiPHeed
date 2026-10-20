import { describe, expect, it } from "vitest";
import { explanationMethod } from "@/lib/explanationMethod";
import type { ConfigResponse } from "@/lib/apiTypes";

describe("explanationMethod (E73)", () => {
  it("keeps SHAP when the backend names no method (default service)", () => {
    expect(explanationMethod(undefined).title).toBe("SHAP Explainability");
    expect(explanationMethod({ servingModel: null } as unknown as ConfigResponse).isShap).toBe(true);
  });
  it("names the thesis index breakdown truthfully", () => {
    const c = { servingModel: { explanationMethod: { label: "Index contribution", isShap: false } } } as unknown as ConfigResponse;
    const m = explanationMethod(c);
    expect(m.isShap).toBe(false);
    expect(m.title).toBe("Index Contribution Breakdown");
    expect(m.title).not.toMatch(/SHAP/);
  });
});

describe("driver panel wording (E74)", () => {
  it("keeps the ranked wording only for SHAP", () => {
    expect(explanationMethod(undefined).panelTitle).toBe("Why is this province at risk?");
    expect(explanationMethod(undefined).orderLabel).toBe("Ranked");
  });
  it("uses neutral wording for the index breakdown", () => {
    const c = { servingModel: { explanationMethod: { label: "Index contribution", isShap: false, panelTitle: "Contributing indicators", orderLabel: "Index contribution, not causes" } } } as unknown as ConfigResponse;
    const m = explanationMethod(c);
    expect(m.panelTitle).toBe("Contributing indicators");
    expect(m.orderLabel).not.toMatch(/Ranked/);
  });
});
