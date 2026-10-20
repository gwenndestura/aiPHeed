import { describe, expect, it } from "vitest";
import { driverCopy, isContributing } from "@/lib/driverCopy";

describe("trigger card copy (E42)", () => {
  it("never claims weather is hurting supply for a 0% group without model input", () => {
    const c = driverCopy({ key: "climate", direction: "increases_risk", status: "no_model_input", pct: 0 });
    expect(c.title).toBe("Weather and farm supply: not used in this forecast");
    expect(c.title).not.toMatch(/hurting/);
  });

  it("says missing OFW data is not low risk", () => {
    const c = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "no_data", pct: 0 });
    expect(c.title).toBe("OFW remittances: no official data");
    expect(c.description).toMatch(/not a sign of low risk/);
  });

  it("keeps the approved directional copy for a contributing group", () => {
    expect(driverCopy({ key: "market", direction: "protective", status: "contributes", pct: 100 }).title)
      .toBe("Food and rice prices are stable");
    expect(driverCopy({ key: "market", direction: "increases_risk", status: "contributes", pct: 60 }).title)
      .toBe("Food and rice prices are too high");
  });

  it("falls back to neutral copy at 0% when an older backend sends no status", () => {
    expect(isContributing({ pct: 0 })).toBe(false);
    expect(driverCopy({ key: "fish_kill", direction: "increases_risk", pct: 0 }).title)
      .toBe("Fish kills and fisheries: no measurable effect");
    expect(isContributing({ pct: 12 })).toBe(true);
  });

  it("describes available-but-unused and stale data without a direction", () => {
    expect(driverCopy({ key: "employment", direction: "protective", status: "data_not_in_model", pct: 0 }).title)
      .toBe("Jobs and livelihoods: data shown, not in the model");
    expect(driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "stale", pct: 0 }).title)
      .toBe("OFW remittances: data out of date");
  });

  it("describes a model-attributed trigger by its effect and the actual evidence", () => {
    const c = driverCopy({ key: "climate", direction: "increases_risk", status: "contributes", pct: 30,
      evidenceNote: "0 typhoon(s) within 300 km in 2026-Q3; ENSO Neutral in the previous quarter." });
    expect(c.title).toBe("Weather and farm supply: raises the forecast");
    expect(c.description).toMatch(/0 typhoon/);
    expect(c.title).not.toMatch(/hurting/);
  });
});

describe("insufficient data vs negligible effect (E47)", () => {
  it("separates missing inputs from a computed, negligible contribution", () => {
    const missing = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "insufficient_data", pct: 0 });
    const negligible = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "no_effect", pct: 0 });
    expect(missing.title).toBe("OFW remittances: insufficient data");
    expect(missing.description).toMatch(/not a sign of low risk/);
    expect(negligible.title).toBe("OFW remittances: no measurable effect");
  });

  it("states that past-quarter contributions were not recorded instead of a direction", () => {
    const c = driverCopy({ key: "climate", direction: "increases_risk", status: "not_recorded", pct: 0 });
    expect(c.title).toBe("Weather and farm supply: not recorded for this quarter");
  });
});
