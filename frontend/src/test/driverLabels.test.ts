import { describe, expect, it } from "vitest";

import { driverCopy } from "@/lib/driverCopy";

// FINAL_ARCHITECTURE: C4 is fisheries production (not fish kills), and the families that used to be hidden have
// their own plain names and sentences.
describe("driver labels", () => {
  it("names C4 as fisheries production", () => {
    const c = driverCopy({ key: "fish_kill", direction: "increases_risk", status: "contributes", pct: 10, plainEvidence: null });
    expect(c.title).toBe("Fisheries production");
    expect(c.description).toContain("Fisheries production fell");
  });

  it.each(["poverty", "news", "hunger_indicator"])("has copy for %s", (key) => {
    const c = driverCopy({ key, direction: "protective", status: "contributes", pct: 5, plainEvidence: null });
    expect(c.title).not.toBe(key);
    expect(c.description.length).toBeGreaterThan(10);
  });
});
