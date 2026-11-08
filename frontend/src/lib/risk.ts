// The HIGH/LOW band is judged on the score as shown (two decimals), the same
// rule the backend applies: 0.4982 reads "0.50", so it is HIGH.

/** True when `score`, rounded as displayed, is at or above `cutoff`. */
export function isHighRisk(score: number, cutoff = 0.5): boolean {
  return Number(score.toFixed(2)) >= cutoff;
}
