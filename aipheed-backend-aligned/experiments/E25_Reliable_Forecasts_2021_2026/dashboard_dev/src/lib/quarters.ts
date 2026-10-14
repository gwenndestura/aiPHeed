// The quarter window the public views offer in their selectors.
//
// The model can score earlier quarters, but the dashboard's selectors start
// here. The upper bound is never "today" from the browser clock: it comes from
// the calendarQuarter that /api/v1/quarters returns, plus at most one forecast
// quarter beyond it. Quarters the API does not return are never invented.

/** Earliest quarter any public quarter selector offers. */
export const EARLIEST_SELECTABLE_QUARTER = "2025-Q1";

/** How many quarters past the calendar quarter a selector may reach. */
export const FORECAST_QUARTERS_AHEAD = 1;

/**
 * How many quarters the map timeline shows: the newest ones, ending at the
 * forecast. When a new forecast quarter is added the window moves forward;
 * older quarters stay reachable through the History list.
 */
export const TIMELINE_DOTS = 5;

/** The newest TIMELINE_DOTS quarters of an oldest-first list. */
export function timelineWindow<T>(quarters: T[]): T[] {
  return quarters.slice(-TIMELINE_DOTS);
}

/** Chronological rank of a "YYYY-Qn" id. */
export function quarterOrdinal(id: string): number {
  const [y, q] = id.split("-Q");
  return Number(y) * 4 + (Number(q) - 1);
}

/**
 * The subset of API quarters a selector should show: from
 * EARLIEST_SELECTABLE_QUARTER up to FORECAST_QUARTERS_AHEAD past
 * `calendarQuarter`. Without a calendarQuarter only the start bound applies.
 */
export function selectableQuarters<T extends { id: string }>(quarters: T[], calendarQuarter?: string): T[] {
  const lo = quarterOrdinal(EARLIEST_SELECTABLE_QUARTER);
  const hi = calendarQuarter ? quarterOrdinal(calendarQuarter) + FORECAST_QUARTERS_AHEAD : Infinity;
  return quarters.filter((q) => {
    const o = quarterOrdinal(q.id);
    return o >= lo && o <= hi;
  });
}

const FULL_MONTHS = ["January–March", "April–June", "July–September", "October–December"];

/** "Forecast Period: 2027 Q1 (January–March 2027)" for a forecast quarter on the timeline. */
export function forecastPeriodLabel(q: { year: number; q: number }): string {
  return `Forecast Period: ${q.year} Q${q.q} (${FULL_MONTHS[q.q - 1]} ${q.year})`;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** "January – March 2027": a quarter's month range, as the map timeline shows it. */
export function quarterMonthRange(q: { year: number; q: number }): string {
  const first = (q.q - 1) * 3;
  return `${MONTH_NAMES[first]} – ${MONTH_NAMES[first + 2]} ${q.year}`;
}
