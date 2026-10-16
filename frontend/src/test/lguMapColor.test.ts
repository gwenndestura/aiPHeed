import { describe, expect, it } from "vitest";
import { LGU_MAP_COLORS, lguMapColor } from "@/data/types";
import geo from "../../public/calabarzon-municities.json";

describe("municipal map colours (E45)", () => {
  it("colours a vulnerability band and never leaves an LGU transparent", () => {
    expect(lguMapColor({ mapStatus: "vulnerability", mapCategory: "high" })).toBe(LGU_MAP_COLORS.high);
    expect(lguMapColor({ mapStatus: "insufficient_data", mapCategory: null })).toBe(LGU_MAP_COLORS.insufficient_data);
    expect(lguMapColor(undefined)).toBe(LGU_MAP_COLORS.insufficient_data);
    for (const c of Object.values(LGU_MAP_COLORS)) expect(c).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("covers all 142 in-scope cities and municipalities in the boundary file", () => {
    const feats = (geo as { features: Array<{ properties: { province_id: string } }> }).features;
    expect(feats.length).toBe(142);
    const provinces = new Set(feats.map((f) => f.properties.province_id));
    expect([...provinces].sort()).toEqual(["batangas", "cavite", "laguna", "quezon", "rizal"]);
  });
});
