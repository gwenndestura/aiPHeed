// src/lib/demoTypes.ts
// --------------------
// Shapes of /api/v1/demo/scenarios (E178 Part A). Every response is synthetic
// and labelled; nothing here is the real outlook.

export interface DemoProduction {
  model_id: string;
  folder: string;
  issue: string;
  cutoff: string;
  published: string;
  artifact_sha256: string;
}

export interface DemoFirstHigh {
  scenario_id: "S3" | "S3-B";
  variant: string;
  param: number;
  province: string;
}

export interface DemoIndex {
  synthetic: true;
  label: string;
  notice: string;
  production: DemoProduction;
  firstHigh: DemoFirstHigh;
  s3bUsed: boolean;
  scenarios: { id: string; title: string }[];
}

export interface DemoRow {
  province: string;
  lead: number;
  quarter: string;
  score_pct: number;
  range90_low: number;
  range90_high: number;
  probability: number;
  class: "HIGH" | "LOW";
  top_driver_1: string;
  top_driver_2: string;
  top_driver_3: string;
}

export interface DemoS1 {
  shifts: { province: string; lead: number; group: string; param: number; probability: number; score_pct: number; class: string; clipped_cells: number }[];
  noise: { province: string; lead: number; p_mean: number; p_p05: number; p_p95: number; score_p05: number; score_p95: number; p_s0: number; n_high: number }[];
}

export interface DemoS2 {
  masks: { province: string; lead: number; masked_share: number; p_mean: number; p_min: number; p_max: number; range90_width_mean: number; range90_width_s0: number; p_s0: number }[];
  all_missing: { province: string; lead: number; probability: number; score_pct: number; range90_width_pts: number; class: string }[];
  latest_missing: { province: string; lead: number; probability: number; score_pct: number; range90_low: number; range90_high: number; range90_width_pts: number; gap_q: number; gap_q_s0: number; range90_width_s0: number; p_s0: number; class: string }[];
  what_the_system_warns: Record<string, string>;
}

export interface DemoS3 {
  ladder: { scenario_id: string; shock: string; lead: number; param: number; max_p: number; highest_province: string; high_provinces: string[]; extrapolated: boolean }[];
  first_high: DemoFirstHigh;
  s3b_used: boolean;
}

export interface DemoS4 {
  label: string;
  source_variant: string;
  high_rows: { province: string; quarter: string }[];
  alerts: { quarter: string; province_code: string; alert_reason: string; evidence: { lead: number; p_high: number; score_pct: number }; statement: string }[];
  alert_rule: string;
  review_flow: string[];
  ranking: Record<string, { rank: number; province: string; p_high: number; band: string }[]>;
  explanations: {
    province: string;
    quarter: string;
    lead: number;
    drivers: { driver_group: string; driver_label: string; group_shap: number; direction: string }[];
    other_pct: number;
    plain_evidence: Record<string, string | null>;
    evidence_note: string;
    statement: string;
  }[];
  report_text: Record<string, string[]>;
}

export interface DemoS5Row {
  province: string;
  quarter: string;
  lead: number;
  rank_in_province: number;
  municipality: string;
  risk_index: number;
  risk_level: string;
  province_p_high: number;
  poverty_rate: number | null;
  population: number;
  disaggregation_label: string;
  note: string;
}

export interface DemoScenario<T = unknown> {
  synthetic: true;
  label: string;
  notice: string;
  id: string;
  title: string;
  meta: {
    groups: Record<string, { label: string; columns: Record<string, number> }>;
    shocks: Record<string, { label: string; columns: Record<string, number> }>;
    unsigned_columns: string[];
    s3_first_high: DemoFirstHigh;
    s3b_used: boolean;
    production: DemoProduction;
  };
  data: T;
}
