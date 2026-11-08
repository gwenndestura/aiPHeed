// The guided tours for first-time public visitors (components/GuidedTour.tsx):
// one each for the map, Data and Visualization pages.

export type TourId = "map" | "data" | "viz";

/**
 * Set once a tour is finished or skipped. The version lets a redesigned tour
 * show once more: bump it to v2 rather than reusing a key.
 */
export const TOUR_DONE_KEYS: Record<TourId, string> = {
  map: "aipheed_tour_v1_done",
  data: "aipheed_tour_data_v1_done",
  viz: "aipheed_tour_viz_v1_done",
};

/** The page each tour belongs to. */
export const TOUR_PAGES: Record<TourId, string> = {
  map: "/dashboard",
  data: "/data",
  viz: "/visualization",
};

/** "Take the tour" in the menu: what it explains on each page. */
export const TOUR_HINTS: Record<TourId, string> = {
  map: "A short guide to the map",
  data: "A short guide to the Data page",
  viz: "A short guide to the Visualization page",
};

/** The tour for this page, if it has one. */
export function tourForPath(pathname: string): TourId | null {
  const id = (Object.keys(TOUR_PAGES) as TourId[]).find((t) => TOUR_PAGES[t] === pathname);
  return id ?? null;
}

/** Start a tour on its page (it is listening there); the event's detail is the TourId. */
export const TOUR_START_EVENT = "aipheed:tour-start";

/** A tour step asks its page to show a panel, open a card or switch a tab. */
export const TOUR_LAYOUT_EVENT = "aipheed:tour-layout";
export interface TourLayout {
  /** Map: side panel to show (tablets show one at a time) or phone sheet tab. */
  panel?: "summary" | "why";
  /** Map: phone bottom sheet height. */
  sheet?: "collapsed" | "half" | "full";
  /** Map: open the News articles analyzed card (closed again when a later step leaves it out). */
  news?: boolean;
  /** Visualization: the chart tab to show. */
  vizTab?: "trend" | "shap";
  /** Visualization: draw the trend chart for the current choices if none is drawn yet. */
  generate?: boolean;
}

// Private browsing can make localStorage throw: a tour then counts as done for
// the rest of this page's life, so it neither breaks the page nor reappears
// on every navigation.
const doneThisSession = new Set<TourId>();

export function isTourDone(id: TourId): boolean {
  if (doneThisSession.has(id)) return true;
  try {
    return localStorage.getItem(TOUR_DONE_KEYS[id]) === "1";
  } catch {
    return false;
  }
}

export function markTourDone(id: TourId): void {
  doneThisSession.add(id);
  try {
    localStorage.setItem(TOUR_DONE_KEYS[id], "1");
  } catch {
    // Storage unavailable: remembered for this page only.
  }
}

/**
 * "Take the tour" from a menu or dialog: the tour `id`, by default the one for
 * the page being viewed (the map tour on pages without one). On its own page
 * it starts at once (after `delayMs`, so the menu or dialog that was clicked
 * can close and hand focus back first); elsewhere it opens that page, which
 * starts it.
 */
export function requestTour(
  navigate: (to: string, opts?: { state?: unknown }) => void,
  pathname: string,
  delayMs = 250,
  id: TourId = tourForPath(pathname) ?? "map",
): void {
  if (pathname === TOUR_PAGES[id]) {
    window.setTimeout(() => window.dispatchEvent(new CustomEvent<TourId>(TOUR_START_EVENT, { detail: id })), delayMs);
  } else {
    navigate(TOUR_PAGES[id], { state: { tour: true } });
  }
}

// ─── Page helpers for the tours ───

/**
 * Waits until `isReady()` (checked every 250ms) or `giveUpMs`, then for the
 * panels to finish sliding in, and calls `ready`. Returns a cancel.
 */
export function whenPageReady(isReady: (waited: number) => boolean, ready: () => void, giveUpMs = 12000): () => void {
  const started = Date.now();
  let timer = 0;
  const check = () => {
    const waited = Date.now() - started;
    if (isReady(waited) || waited > giveUpMs) {
      timer = window.setTimeout(ready, 500);
    } else {
      timer = window.setTimeout(check, 250);
    }
  };
  check();
  return () => window.clearTimeout(timer);
}

/** On screen: has a size and is not hidden. */
export const visible = (el: Element) => {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && cs.visibility !== "hidden";
};

/** The visible element marked data-tour={name}. */
export const tourElement = (name: string) => [...document.querySelectorAll(`[data-tour="${name}"]`)].find(visible);
