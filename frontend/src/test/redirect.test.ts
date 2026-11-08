import { describe, expect, it } from "vitest";
import { safeRedirectPath } from "@/lib/redirect";

describe("safeRedirectPath", () => {
  it("follows an internal path, query included", () => {
    expect(safeRedirectPath("/admin/feedback")).toBe("/admin/feedback");
    expect(safeRedirectPath("/admin/review?quarter=2026-Q3")).toBe("/admin/review?quarter=2026-Q3");
  });

  it("falls back to /admin when nothing was requested", () => {
    expect(safeRedirectPath(undefined)).toBe("/admin");
    expect(safeRedirectPath(null)).toBe("/admin");
    expect(safeRedirectPath(42)).toBe("/admin");
    expect(safeRedirectPath("")).toBe("/admin");
  });

  it("refuses anything that leaves the site", () => {
    for (const bad of [
      "https://evil.example/admin",
      "//evil.example",
      "/\\evil.example",
      "/\t/evil.example",
      "javascript:alert(1)",
      "admin",
    ]) {
      expect(safeRedirectPath(bad)).toBe("/admin");
    }
  });
});
