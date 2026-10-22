import { describe, expect, it } from "vitest";
import { driverCopy, isContributing } from "@/lib/driverCopy";

const contributing = (key: string, direction: "increases_risk" | "protective") =>
  driverCopy({ key, direction, status: "contributes", pct: 20 });

describe("factor card copy: contributing groups", () => {
  it("titles a card with the group's plain name only, never the direction", () => {
    expect(contributing("employment", "increases_risk").title).toBe("Jobs and livelihoods");
    expect(contributing("climate", "increases_risk").title).toBe("Weather and farm supply");
    expect(contributing("market", "protective").title).toBe("Food prices");
    expect(contributing("fish_kill", "protective").title).toBe("Fish kills and fisheries");
    expect(contributing("ofw_remittance", "increases_risk").title).toBe("OFW remittances");
    for (const k of ["employment", "climate", "market", "fish_kill", "ofw_remittance"]) {
      for (const d of ["increases_risk", "protective"] as const) {
        expect(contributing(k, d).title).not.toMatch(/raises|lowers|forecast/);
      }
    }
  });

  it("gives one plain sentence per group and direction", () => {
    const table: [string, string, string][] = [
      ["employment", "Unemployment rose more than usual compared with a year earlier.", "Unemployment changed less than usual compared with a year earlier."],
      ["climate", "Weather and farm-supply conditions were worse than usual.", "Weather and farm-supply conditions were better than usual."],
      ["market", "Food prices were higher than usual.", "Food prices were lower than usual."],
      ["fish_kill", "Fisheries production fell more than usual.", "Fisheries production held up better than usual."],
      ["ofw_remittance", "Money sent home by OFWs grew less than usual.", "Money sent home by OFWs grew more than usual."],
    ];
    for (const [k, raises, lowers] of table) {
      expect(contributing(k, "increases_risk").description).toBe(raises);
      expect(contributing(k, "protective").description).toBe(lowers);
    }
  });

  it("returns only a title and the plain sentence: no evidence note", () => {
    expect(Object.keys(contributing("employment", "increases_risk")).sort()).toEqual(["description", "title"]);
  });
});

describe("factor card copy: groups that did not move the forecast (E42/E47)", () => {
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

  it("separates missing inputs from a computed, negligible contribution", () => {
    const missing = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "insufficient_data", pct: 0 });
    const negligible = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "no_effect", pct: 0 });
    expect(missing.title).toBe("OFW remittances: insufficient data");
    expect(missing.description).toBe("No published data were available when this forecast was issued; this is not a sign of low risk.");
    expect(negligible.title).toBe("OFW remittances: no measurable effect");
  });

  it("states that past-quarter contributions were not recorded instead of a direction", () => {
    const c = driverCopy({ key: "climate", direction: "increases_risk", status: "not_recorded", pct: 0 });
    expect(c.title).toBe("Weather and farm supply: not recorded for this quarter");
  });

  it("keeps every neutral description to one sentence", () => {
    for (const status of ["no_effect", "data_not_in_model", "stale", "no_model_input", "no_data", "insufficient_data", "not_recorded"] as const) {
      const d = driverCopy({ key: "market", direction: "increases_risk", status, pct: 0 }).description;
      expect(d.match(/[.!?](\s|$)/g)?.length, `${status}: ${d}`).toBe(1);
    }
  });
});

describe("driverCopy with measured values (E87)", () => {
  it("uses the backend's plain sentence with values when present, else the generic sentence", () => {
    const withValues = driverCopy({ key: "market", direction: "increases_risk", status: "contributes", pct: 20,
      plainEvidence: "Wholesale rice is 29% higher than a year earlier, a larger rise than usual." });
    expect(withValues.description).toBe("Wholesale rice is 29% higher than a year earlier, a larger rise than usual.");
    const generic = driverCopy({ key: "market", direction: "increases_risk", status: "contributes", pct: 20 });
    expect(generic.description).toBe("Food prices were higher than usual.");
    const missing = driverCopy({ key: "ofw_remittance", direction: "increases_risk", status: "insufficient_data", pct: 0,
      plainEvidence: "ignored" });
    expect(missing.description).toBe("No published data were available when this forecast was issued; this is not a sign of low risk.");
  });
});
