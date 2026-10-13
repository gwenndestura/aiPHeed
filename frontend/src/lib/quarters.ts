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
