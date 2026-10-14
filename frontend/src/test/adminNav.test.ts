import { describe, expect, it } from "vitest";
import { ADMIN_SECTIONS, adminPath, sectionFromPath } from "@/lib/adminNav";

describe("admin section URLs", () => {
  it("reads the section from the path", () => {
    expect(sectionFromPath("/admin")).toBe("map");
    expect(sectionFromPath("/admin/review")).toBe("review");
    expect(sectionFromPath("/admin/feedback")).toBe("feedback");
    expect(sectionFromPath("/admin/review/")).toBe("review");
  });

  it("round-trips every section", () => {
    for (const s of ADMIN_SECTIONS) expect(sectionFromPath(adminPath(s.section))).toBe(s.section);
  });

  it("shows the map for anything it does not recognise", () => {
    expect(sectionFromPath("/admin/unknown")).toBe("map");
  });
});
