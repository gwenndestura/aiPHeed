// E24v2 forecast-page helpers. Pure functions shared by the page and its tests.
export type Evidence = { status: "NOT_ESTABLISHED" | "SUPPORTED" | "SUPPORTED_STRICT" | "NOT_EVALUATED"; basis?: string };
export type ProvinceForecast = {
  province: string;
  risk: {
    p_high: number; decision: "HIGH" | "LOW"; signal: "STRONG" | "MODERATE" | "UNCERTAIN"; S1_forecast: number;
    S1_80pct_interval: [number, number]; threshold: number; evidence: Evidence;
    components: Record<string, { value: number; kind: string; contribution: number }>;
  };
  price_pressure: {
    p_above_regional_mean: number; D_forecast: number; D_80pct_interval: [number, number];
    signal: "STRONG" | "MODERATE" | "UNCERTAIN"; evidence: Evidence;
    latest_measured_D: { quarter: string; value: number; kind: string };
    latest_measured_Dnow: { months: string; value: number; kind: string };
  };
};
export type LeadForecast = {
  target_quarter: string;
  H: { mu_H: number; V_H: number; sigma_eta: number; gap_quarters: number; n_rounds: number; last_round_quarter: string };
  provinces: Record<string, ProvinceForecast>;
};
export type RankRow = {
  lgu_code: string; lgu_name: string; lgu_type: string; province: string; risk_index: number | null;
  rank_region: number; rank_in_province: number; vulnerability_index: number; poverty_value_used: number;
  poverty_value_kind: string; density: number; limitation: string;
};
export type Forecast = { origin: string; threshold: number; leads: Record<string, LeadForecast>; lgu_ranking: RankRow[] };
export type Period = {
  reference_quarter: string; target_quarter: string; cutoff: string; target_display: string; news_display: string;
  news_window_start: string; news_window_end: string;
};
export type CycleRecord = {
  period: Period; status: "READY" | "INSUFFICIENT_DATA" | "BLOCKED"; missing: string[]; context_missing: string[];
  labels: { target: string; news: string; cutoff: string; caveat: string; mode: string }; mode: "LIVE" | "REPLAY";
  forecast: Forecast | null; content_sha256: string; cutoff_reached?: boolean;
};
export type Seal = {
  seal_id: string; sha256: string; created_utc: string; origin: string; targets: string[]; threshold_T1: number;
  status: string; rows: { target: string; lead: number; target_quarter: string; province: string; model: string; score: number }[];
};
export type Confirm = { model: string; baseline: string; metric: string; effect: number; p_holm: number; supported: boolean;
                        stable_both_halves: boolean };
export type V2Data = {
  generated_from: Record<string, string>;
  live: CycleRecord; replay: CycleRecord; seals: Seal[];
  evidence: { T1: Record<string, Evidence>; T2: Record<string, Evidence>; _rule: string };
  goal: { target: string; criteria: Record<string, boolean | string>; goal_met: boolean;
          metrics: Record<string, { accuracy: number; balanced_accuracy: number | null; Brier: number; ROC_AUC: number | null }>;
          always_HIGH_accuracy: number; n_test_quarters: number; HIGH: number; LOW: number };
  confirmatory: Record<string, Confirm>;
  backcast_lead1: Record<string, { accuracy: number; balanced_accuracy: number | null; Brier: number; ROC_AUC: number | null }>;
  backcast_lead_time: Record<string, { furthest_reliable_lead: number; per_lead_pass: Record<string, boolean> }>;
  backcast_quarters: number;
  noise_ceiling: { rows: number; expected_sampling_flips_all_rows: number; persistence_errors: number; label_change_rows: number };
  provincial_validity: Record<string, unknown> & {
    "Subsistence Incidence": { province: string; year: number; value: number; ci_low: number; ci_high: number; cv: number }[];
    "Poverty Incidence": { province: string; year: number; value: number; ci_low: number; ci_high: number; cv: number }[];
  };
  lgu_analysis: { province_mean_substitute: number; with_municipal_estimate: number;
                  municipal_estimate_rows: { n: number; spearman_poverty_vs_density: number } };
  caveats: string[];
};

export const fmt = (x: number | null | undefined, d = 3) => (x === null || x === undefined ? "—" : x.toFixed(d));

export function nextQuarter(q: string): string {
  const [y, n] = q.split("-Q").map(Number);
  return n === 4 ? `${y + 1}-Q1` : `${y}-Q${n + 1}`;
}

/** Banner, record and labels must name the same quarters. */
export function periodsConsistent(r: CycleRecord): boolean {
  const p = r.period;
  return nextQuarter(p.reference_quarter) === p.target_quarter && r.labels.target.includes(p.target_display) &&
    r.labels.news.includes(p.news_display) && Date.parse(p.news_window_end) <= Date.parse(p.cutoff);
}

/** A forecast is never presented as validated unless its lead's evidence says so. */
export function evidenceText(e: Evidence | undefined): string {
  switch (e?.status) {
    case "SUPPORTED_STRICT": return "Validated on unseen back-cast quarters (strict rule)";
    case "SUPPORTED": return "Validated on unseen back-cast quarters (E23 rule)";
    case "NOT_ESTABLISHED": return "Indicative only — reliability not established at this lead";
    default: return "Not evaluated";
  }
}

export function goalText(d: V2Data): string {
  return d.goal.goal_met && Object.values(d.goal.criteria).every((v) => v === true) ? "Goal met" : "Goal NOT met";
}

export function statusText(r: CycleRecord): string {
  if (r.status === "READY") return r.mode === "REPLAY" ? "Replay of a past cycle (not a live forecast)" : "Forecast available";
  if (r.status === "BLOCKED") return "Blocked: an input is unauthorized or failed its integrity check";
  return "Insufficient data: no forecast is shown for this period";
}
