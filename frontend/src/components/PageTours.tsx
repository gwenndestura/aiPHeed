import { GuidedTour, type Area, type TourDef } from "@/components/GuidedTour";
import { whenPageReady, tourElement } from "@/lib/tour";

/**
 * Guided tours of the Data and Visualization pages. Their steps outline
 * elements marked data-tour="…" in pages/Data.tsx and pages/Visualization.tsx.
 */

const DATA_TOUR: TourDef = {
  id: "data",
  pageScrolls: true,
  // Once the provinces are listed (or the page has said it could not load them).
  whenReady: (ready) =>
    whenPageReady((waited) => !!document.querySelector('[data-tour="data-table"] tbody tr, [data-tour="data-table"] li') || waited > 6000, ready),
  steps: [
    {
      title: "Filter the list",
      body: () =>
        "Show one province or one risk level, or choose another quarter. The search box finds a province by name.",
      target: () => "data-filters",
    },
    {
      title: "Sort",
      body: ({ layout }) =>
        layout === "phone"
          ? "Choose the order of the provinces, for example by risk score from high to low."
          : "Click a column heading to sort the table by it. Click it again to reverse the order.",
      target: () => "data-sort",
    },
    {
      title: "The provinces",
      body: ({ layout }) =>
        layout === "phone"
          ? "Each card is one province: its risk score, its change from the previous quarter and the number of news articles analyzed. Tap a card to open that province on the map."
          : "Each row is one province: its risk score and level, its change from the previous quarter and the number of news articles analyzed. Click a row to open that province on the map.",
      // Phones: the first card (the whole list is taller than the screen).
      target: (l) => (l === "phone" ? "data-row" : "data-table"),
    },
    {
      title: "Export",
      body: () => "Export CSV downloads the rows shown, with your filters applied, as a file for a spreadsheet.",
      target: () => "data-export",
    },
  ],
};

/** The High risk and Alert lines across the trend chart, together. */
function thresholdLinesArea(): Area | null {
  const chart = tourElement("viz-chart");
  const lines = chart ? [...chart.querySelectorAll(".recharts-reference-line")].map((l) => l.getBoundingClientRect()).filter((b) => b.width > 0) : [];
  if (!lines.length) return null;
  return lines.reduce(
    (a, b) => ({ top: Math.min(a.top, b.top), left: Math.min(a.left, b.left), right: Math.max(a.right, b.right), bottom: Math.max(a.bottom, b.bottom) }),
    { top: Infinity, left: Infinity, right: -Infinity, bottom: -Infinity },
  );
}

const VIZ_TOUR: TourDef = {
  id: "viz",
  pageScrolls: true,
  whenReady: (ready) => whenPageReady(() => !!document.querySelector('[data-tour="viz-filters"] select option'), ready),
  steps: [
    {
      title: "Two kinds of chart",
      body: () =>
        "Province Risk Level Trend draws risk scores quarter by quarter. Feature Contribution Breakdown shows how much each group of factors, such as food prices or the weather, added to one province's risk in a quarter.",
      target: () => "viz-tabs",
      layout: { vizTab: "trend" },
    },
    {
      title: "Choose what to chart",
      body: () =>
        "Pick a province or all five, a city or municipality in it, and the range of quarters, from and to.",
      target: () => "viz-filters",
      layout: { vizTab: "trend" },
    },
    {
      title: "Generate the chart",
      body: () => "Generate Chart draws the chart for your choices. Clear Filters starts again from all provinces and every quarter.",
      target: () => "viz-generate",
      layout: { vizTab: "trend" },
    },
    {
      title: "Reading the chart",
      body: ({ cutoff, alert }) =>
        `Each line is a risk score from 0 to 1. At or above the High risk line (${cutoff}) a province is high risk; at or above the Alert line (${alert}) it has an active alert, a call for early action.`,
      target: () => "viz-chart",
      // Phones: just the two lines, so the card has room beside them.
      area: (l) => (l === "phone" ? thresholdLinesArea() : null),
      layout: { vizTab: "trend", generate: true },
    },
    {
      title: "Download",
      body: () => "Download PNG saves the chart as an image. Download PDF makes a printable report with the chart.",
      target: () => "viz-download",
      layout: { vizTab: "trend" },
    },
  ],
};

export function DataTour() {
  return <GuidedTour tour={DATA_TOUR} />;
}

export function VizTour() {
  return <GuidedTour tour={VIZ_TOUR} />;
}
