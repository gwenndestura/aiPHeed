// The HIGH/LOW band is judged on the score as shown (two decimals), the same
// rule the backend applies: 0.4982 reads "0.50", so it is HIGH.

/** True when `score`, rounded as displayed, is at or above `cutoff`. */
export function isHighRisk(score: number, cutoff = 0.5): boolean {
  return Number(score.toFixed(2)) >= cutoff;
}

/** A 0-1 value shown as a percentage (owner 2026-11-13: percentages, not decimals). */
export function pct(x: number, digits = 1): string {
  return fmtPct(x * 100, digits);
}

/** A value already in percent, shown without a trailing ".0" (owner 2026-11-13: 25% not 25.0%; 26.8% stays). */
export function fmtPct(v: number, digits = 1): string {
  return `${v.toFixed(digits).replace(/\.0+$/, "")}%`;
}
