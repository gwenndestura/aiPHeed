import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// lib/tour.ts remembers finished tours for the page's life, so each test
// loads a fresh copy.
const load = () => import("@/lib/tour");

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("tour storage", () => {
  it("keeps one key per page, the map's unchanged", async () => {
    const { TOUR_DONE_KEYS } = await load();
    expect(TOUR_DONE_KEYS).toEqual({
      map: "aipheed_tour_v1_done",
      data: "aipheed_tour_data_v1_done",
      viz: "aipheed_tour_viz_v1_done",
    });
  });

  it("marks each tour done on its own", async () => {
    const { isTourDone, markTourDone } = await load();
    expect(isTourDone("data")).toBe(false);
    markTourDone("data");
    expect(isTourDone("data")).toBe(true);
    expect(localStorage.getItem("aipheed_tour_data_v1_done")).toBe("1");
    expect(isTourDone("map")).toBe(false);
    expect(isTourDone("viz")).toBe(false);
  });

  it("reads a tour finished in an earlier visit", async () => {
    localStorage.setItem("aipheed_tour_viz_v1_done", "1");
    const { isTourDone } = await load();
    expect(isTourDone("viz")).toBe(true);
  });

  it("does not throw when storage is blocked, and remembers for the page's life", async () => {
    const boom = () => {
      throw new DOMException("denied", "SecurityError");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(boom);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(boom);
    const { isTourDone, markTourDone } = await load();
    expect(isTourDone("map")).toBe(false);
    expect(() => markTourDone("map")).not.toThrow();
    expect(isTourDone("map")).toBe(true);
    expect(isTourDone("data")).toBe(false);
  });
});

describe("requestTour", () => {
  it("knows each page's tour", async () => {
    const { tourForPath } = await load();
    expect(tourForPath("/dashboard")).toBe("map");
    expect(tourForPath("/data")).toBe("data");
    expect(tourForPath("/visualization")).toBe("viz");
    expect(tourForPath("/admin")).toBeNull();
  });

  it("starts the tour of the page being viewed", async () => {
    vi.useFakeTimers();
    const { requestTour, TOUR_START_EVENT } = await load();
    const navigate = vi.fn();
    const started: unknown[] = [];
    const onStart = (e: Event) => started.push((e as CustomEvent).detail);
    window.addEventListener(TOUR_START_EVENT, onStart);
    requestTour(navigate, "/data");
    requestTour(navigate, "/visualization");
    vi.runAllTimers();
    window.removeEventListener(TOUR_START_EVENT, onStart);
    expect(started).toEqual(["data", "viz"]);
    expect(navigate).not.toHaveBeenCalled();
  });

  it("opens the map page for the map tour from elsewhere", async () => {
    const { requestTour } = await load();
    const navigate = vi.fn();
    requestTour(navigate, "/admin");
    requestTour(navigate, "/data", 300, "map");
    expect(navigate).toHaveBeenNthCalledWith(1, "/dashboard", { state: { tour: true } });
    expect(navigate).toHaveBeenNthCalledWith(2, "/dashboard", { state: { tour: true } });
  });
});
