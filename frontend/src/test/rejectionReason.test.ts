import { describe, expect, it } from "vitest";
import { reasonProblem, tidyReason } from "@/lib/rejectionReason";

describe("rejection reason rules", () => {
  it("accepts a typed reason that was never on a preset list", () => {
    expect(reasonProblem("Typhoon damage delayed the provincial survey")).toBeNull();
  });

  it("refuses blank, short, one-word and symbol-only reasons", () => {
    expect(reasonProblem("")).toMatch(/Enter a reason/);
    expect(reasonProblem("    ")).toMatch(/Enter a reason/);
    expect(reasonProblem("too short")).toMatch(/at least 10/);
    expect(reasonProblem("aaaaaaaaaaaaaa")).toMatch(/two words/);
    expect(reasonProblem("!!!! ???? ....")).toMatch(/two words/);
  });

  it("refuses a reason over 200 characters", () => {
    expect(reasonProblem("word ".repeat(41))).toMatch(/200 characters or fewer/);
  });

  it("tidies spaces the way the server does", () => {
    expect(tidyReason("  Data   quality issue \n")).toBe("Data quality issue");
  });
});
