import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// The review queue holds forecast quarters, so its Year filter must offer forecast years (2026-11-04 audit).
describe("Admin review year filter", () => {
  const src = readFileSync(resolve(__dirname, "../pages/Admin.tsx"), "utf8");
  it("does not drop forecast quarters from the years it offers", () => {
    expect(src).not.toContain('filter((q) => q.state !== "forecast").map((q) => q.year)');
  });
  it("asks for staged values with the reviewer's session", () => {
    expect(src).toContain("useMunicipalities(item.provinceId, item.quarter, true)");
    expect(src).toContain('useExplainability("province", item.provinceId, item.quarter, true)');
  });
});
