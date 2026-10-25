import { GuidedTour, type Area, type TourDef } from "@/components/GuidedTour";
import { whenPageReady, visible } from "@/lib/tour";

/**
 * Guided tour of the map page. Its steps outline elements marked data-tour="…"
 * in MapDashboard, RightAnalyticsPanel and the header, and ask MapDashboard
 * (TOUR_LAYOUT_EVENT) for the side panel, the phone sheet's tab and height,
 * or the open news card each one needs.
 */

/** The CALABARZON outline: the union of the province shapes, within the map area the panels leave uncovered. */
function provincesArea(): Area | null {
  const mapEl = document.querySelector('[data-tour="map"]');
  if (!mapEl) return null;
  const shapes = [...document.querySelectorAll(".leaflet-overlay-pane path.leaflet-interactive")].map((p) => p.getBoundingClientRect()).filter((b) => b.width > 0);
  const m = mapEl.getBoundingClientRect();
  const clip = { top: m.top, left: m.left, right: m.right, bottom: m.bottom };
  const panel = (n: string) => [...document.querySelectorAll(`[data-tour="${n}"]`)].find(visible)?.getBoundingClientRect();
  const left = panel("summary"), right = panel("why"), sheet = panel("sheet");
  // The side panels float 12px in from the map's edges.
  if (left && left.left <= clip.left + 16) clip.left = Math.max(clip.left, left.right);
  if (right && right.right >= clip.right - 16) clip.right = Math.min(clip.right, right.left);
  if (sheet) clip.bottom = Math.min(clip.bottom, sheet.top);
  const r = shapes.length
    ? shapes.reduce((a, b) => ({ top: Math.min(a.top, b.top), left: Math.min(a.left, b.left), right: Math.max(a.right, b.right), bottom: Math.max(a.bottom, b.bottom) }), { top: Infinity, left: Infinity, right: -Infinity, bottom: -Infinity })
    : clip;
  return { top: Math.max(r.top, clip.top), left: Math.max(r.left, clip.left), right: Math.min(r.right, clip.right), bottom: Math.min(r.bottom, clip.bottom) };
}

const MAP_TOUR: TourDef = {
  id: "map",
  // Once the timeline and the provinces are drawn.
  whenReady: (ready) =>
    whenPageReady((waited) => {
      const timeline = !!document.querySelector('[data-tour="timeline"]');
      const shapes = !!document.querySelector(".leaflet-overlay-pane path.leaflet-interactive");
      return (timeline && shapes) || (timeline && waited > 6000);
    }, ready),
  // Back to the page's usual layout: summary panel, phone sheet collapsed, news card as it was.
  resetLayout: { panel: "summary", sheet: "collapsed" },
  steps: [
    {
      title: "Welcome to aiPHeed",
      body: () =>
        "aiPHeed shows a quarterly food-insecurity priority score for the five provinces of CALABARZON, built from published indicators. The scores are estimates, not measured hunger rates, reviewed by Department of Agriculture staff before they are published.",
      layout: { panel: "summary", sheet: "collapsed" },
    },
    {
      title: "The map",
      body: ({ layout }) =>
        `Each province is coloured by its priority score. ${layout === "phone" ? "Tap" : "Click"} a province to see its details.`,
      area: provincesArea,
      layout: { sheet: "collapsed" },
    },
    {
      title: "Reading the colours",
      body: ({ cutoff }) =>
        `Red means high priority: a priority score of ${cutoff} or more, on a scale from 0 to 1. Yellow means low priority. Grey means there is no forecast for that province this quarter.`,
      target: () => "legend",
      layout: { sheet: "collapsed" },
    },
    {
      title: "Province summary",
      body: ({ layout }) =>
        `${layout === "phone" ? "The Summary tab" : "This panel"} shows the regional picture. Select a province to see its priority score, its change from the previous quarter and its population.`,
      target: (l) => (l === "phone" ? "sheet" : "summary"),
      layout: { panel: "summary", sheet: "half" },
    },
    {
      title: "Why this score",
      body: ({ layout }) =>
        `${layout === "phone" ? "The Why tab" : "This panel"} lists the factors pushing the score up or down, such as food prices or the weather.`,
      target: (l) => (l === "phone" ? "sheet" : "why"),
      layout: { panel: "why", sheet: "half" },
    },
    {
      title: "News articles analyzed",
      body: () =>
        "The news is sorted into topics such as fish kill or typhoon and disaster; each percentage is that topic's share of the articles analyzed. The list below shows the news the forecast was built from.",
      target: () => "news",
      // At the top of its panel or tab, so the article list shows below it.
      scroll: "start",
      layout: { panel: "why", sheet: "full", news: true },
    },
    {
      title: "Choose a quarter",
      body: ({ layout }) =>
        layout === "phone"
          ? "Pick a quarter here. Forecast quarters have a dashed outline, and Current marks the quarter we are in now. History lists every quarter."
          : "Pick a quarter on the timeline. The solid line marks observed quarters, the dashed line forecasts, and Today marks where we are now. View history lists every quarter.",
      target: () => "timeline",
      layout: { panel: "summary", sheet: "collapsed" },
    },
    {
      title: "Search",
      body: () => "Type the name of a province, city or municipality to find it on the map.",
      target: () => "search",
      layout: { sheet: "collapsed" },
    },
    {
      title: "Data and charts",
      body: ({ linksInMenu }) =>
        `${linksInMenu ? "Open the menu for the Data and Visualization pages." : "Two more pages:"} Data lists every province in a table you can export as CSV. Visualization draws trend charts you can download as PNG or PDF.`,
      target: () => "pages",
      layout: { sheet: "collapsed" },
    },
    {
      title: "About and feedback",
      body: () =>
        "About & Methodology explains how the forecasts are made and their limits. Send Feedback tells us how the site worked for you. You can replay this tour from About & Methodology or the menu.",
      target: () => "about",
      layout: { panel: "summary", sheet: "full" },
    },
  ],
};

export function MapTour() {
  return <GuidedTour tour={MAP_TOUR} />;
}
