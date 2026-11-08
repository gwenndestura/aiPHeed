import { describe, expect, it } from "vitest";
import { ADMIN_NAV, ADMIN_SECTIONS, adminPath, isActivePath, sectionFromPath } from "@/lib/adminNav";

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

describe("signed-in admin links", () => {
  it("lists Mapping, Data, Visualization, Review, Feedback in that order", () => {
    expect(ADMIN_NAV.map((l) => l.label)).toEqual(["Mapping", "Data", "Visualization", "Review", "Feedback"]);
    expect(ADMIN_NAV.map((l) => l.path)).toEqual(["/admin", "/data", "/visualization", "/admin/review", "/admin/feedback"]);
  });

  it("marks only the page being shown as active", () => {
    expect(ADMIN_NAV.filter((l) => isActivePath("/data", l.path)).map((l) => l.label)).toEqual(["Data"]);
    expect(ADMIN_NAV.filter((l) => isActivePath("/admin/", l.path)).map((l) => l.label)).toEqual(["Mapping"]);
    expect(ADMIN_NAV.filter((l) => isActivePath("/", l.path))).toEqual([]);
  });
});
