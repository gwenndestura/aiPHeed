// The map page's guided tour for first-time public visitors (components/MapTour.tsx).

/**
 * Set once the tour is finished or skipped. The version lets a redesigned
 * tour show once more: bump it to v2 rather than reusing this key.
 */
export const TOUR_DONE_KEY = "aipheed_tour_v1_done";

/** Start the tour on the map page (it is listening there). */
export const TOUR_START_EVENT = "aipheed:tour-start";

/** The tour asks the map page to show a panel or open the phone sheet. */
export const TOUR_LAYOUT_EVENT = "aipheed:tour-layout";
export interface TourLayout {
  /** Side panel to show (tablets show one at a time) or phone sheet tab. */
  panel?: "summary" | "why";
  /** Phone bottom sheet height. */
  sheet?: "collapsed" | "half" | "full";
}

// Private browsing can make localStorage throw: the tour then counts as done
// for the rest of this page's life, so it neither breaks the page nor reappears
// on every navigation.
let doneThisSession = false;

export function isTourDone(): boolean {
  if (doneThisSession) return true;
  try {
    return localStorage.getItem(TOUR_DONE_KEY) === "1";
  } catch {
    return false;
  }
}

export function markTourDone(): void {
  doneThisSession = true;
  try {
    localStorage.setItem(TOUR_DONE_KEY, "1");
  } catch {
    // Storage unavailable: remembered for this page only.
  }
}

/**
 * "Take the tour" from a menu or dialog. On the map page it starts at once
 * (after `delayMs`, so the menu or dialog that was clicked can close and hand
 * focus back first); elsewhere it opens the map page, which starts it.
 */
export function requestTour(navigate: (to: string, opts?: { state?: unknown }) => void, pathname: string, delayMs = 250): void {
  if (pathname === "/dashboard") {
    window.setTimeout(() => window.dispatchEvent(new Event(TOUR_START_EVENT)), delayMs);
  } else {
    navigate("/dashboard", { state: { tour: true } });
  }
}
