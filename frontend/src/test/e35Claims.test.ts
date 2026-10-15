import { readFileSync } from "fs";
import path from "path";
import { describe, expect, it } from "vitest";

const src = (rel: string) => readFileSync(path.resolve(__dirname, "..", rel), "utf-8");

// Regression guards for the E35 claim defects fixed in E36 (the E35 audit folder keeps the original tests).
describe("E35 claim defects stay fixed", () => {
  it("D5: the province panel does not claim same-quarter PSA production data", () => {
    expect(src("components/LeftPanel.tsx")).not.toContain("based on PSA production data already published for that quarter");
    expect(src("components/LeftPanel.tsx")).not.toContain("derived from the validated province forecast");
  });

  it("D6: the landing FAQ makes no unsupported reliability or portability claim", () => {
    const s = src("pages/Landing.tsx");
    expect(s).not.toContain("finest reliable signal");
    expect(s).not.toContain("The pipeline is region-agnostic");
  });

  it("D1: no bare High risk / Low risk band text", () => {
    for (const f of ["components/ui/status-badge.tsx", "data/types.ts", "components/LeftPanel.tsx"]) {
      expect(src(f)).not.toMatch(/"(High|Low) [Rr]isk"/);
    }
  });
});
