import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { isLoadFailure } from "@/lib/loadError";

describe("isLoadFailure", () => {
  it("is false when there is no error", () => {
    expect(isLoadFailure(null)).toBe(false);
    expect(isLoadFailure(undefined)).toBe(false);
  });

  it("treats a 404 as an answer, not a failure", () => {
    // forecast_not_found / forecast_withheld: nothing published, already shown as such.
    expect(isLoadFailure(new ApiError(404, "forecast_withheld", "withheld"))).toBe(false);
  });

  it("treats network errors, timeouts and server errors as failures", () => {
    expect(isLoadFailure(new ApiError(0, "network_error", "Could not reach the server."))).toBe(true);
    expect(isLoadFailure(new ApiError(0, "timeout", "too slow"))).toBe(true);
    expect(isLoadFailure(new ApiError(500, "unknown_error", "boom"))).toBe(true);
    expect(isLoadFailure(new Error("anything else"))).toBe(true);
  });
});
