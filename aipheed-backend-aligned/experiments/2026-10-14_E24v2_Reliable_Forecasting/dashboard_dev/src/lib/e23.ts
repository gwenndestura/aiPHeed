// E23 forecast-period helpers. Pure functions; the page and tests share them.
export type Period = {
  reference_quarter: string; target_quarter: string; cutoff: string; timezone: string;
  news_window_start: string; news_window_end: string; quarter_complete: boolean;
  target_display: string; news_display: string;
};
export type ModelMetrics = {
  name: string; accuracy: number | null; balanced_accuracy?: number | null; precision: number | null; recall: number | null; F1: number | null;
  ROC_AUC: number | null; Brier: number | null; TP: number; FP: number; FN: number; TN: number;
};
export type LeadRow = {
  lead: number; n_origins: number; evaluable: boolean; HIGH?: number; LOW?: number; reliable?: boolean;
  strongest_baseline?: string; criteria?: Record<string, boolean | string>; final_choice_share?: Record<string, number>;
  target_quarters?: string[]; models?: Record<string, ModelMetrics>;
  improved?: { accuracy: number; always_HIGH_accuracy: number; strongest_baseline: string;
               strongest_baseline_accuracy: number; beats_strongest: boolean; exceeds_75: boolean;
               ROC_AUC: number | null; Brier: number };
};
export type RankRow = Record<string, string>;
export type E23Data = {
  generated_from: { e23_run: string; e23b_run: string; forecast_record_sha256: string };
  period: Period; status: "READY" | "INSUFFICIENT_DATA" | "BLOCKED"; missing: string[];
  labels: { target: string; news: string; cutoff: string; caveat: string };
  cutoff_reached: boolean;
  supporting_news: { eligible: number; by_province: Record<string, number>; limited_signal: Record<string, boolean>;
                     quarter_complete: boolean; window_start: string; window_end: string };
  supporting_articles: { title: string; link: string; province_code: string; published_ph: string }[];
  forecast: unknown;
  evaluation: { T1: LeadRow[]; T2: LeadRow[] };
  rankings: { quarter: string; rows: RankRow[]; for_target_quarter: string;
              verification: { lgus_with_substitute: number; lgus_with_municipal_estimate: number;
                              max_abs_diff_risk_vs_E23: number } };
  caveats: string[];
};

export const PROVINCES: Record<string, string> = {
  PH040100000: "Cavite", PH040200000: "Laguna", PH040300000: "Quezon", PH040400000: "Rizal", PH040500000: "Batangas",
};

export const fmt = (x: number | null | undefined, d = 3) => (x === null || x === undefined ? "—" : x.toFixed(d));

/** Articles shown as supporting evidence: ONLY those inside the declared news window. */
export function eligibleArticles(d: E23Data) {
  const s = Date.parse(d.period.news_window_start);
  const e = Date.parse(d.period.news_window_end);
  return d.supporting_articles.filter((a) => {
    const t = Date.parse(a.published_ph);
    return Number.isFinite(t) && t >= s && t <= e;
  });
}

/** Periods agree across the banner, the news window and the record. */
export function periodsConsistent(d: E23Data): boolean {
  const p = d.period;
  const [y, q] = p.reference_quarter.split("-Q").map(Number);
  const next = q === 4 ? `${y + 1}-Q1` : `${y}-Q${q + 1}`;
  return next === p.target_quarter && d.labels.target.includes(p.target_display) &&
    d.labels.news.includes(p.news_display) && Date.parse(p.news_window_end) <= Date.parse(p.cutoff) &&
    Date.parse(p.news_window_end) < Date.parse(`${p.target_quarter.split("-Q")[0]}-${String((Number(p.target_quarter.split("-Q")[1]) - 1) * 3 + 1).padStart(2, "0")}-01T00:00:00+08:00`);
}

export function statusText(d: E23Data): string {
  if (d.status === "READY") return "Forecast available";
  if (d.status === "BLOCKED") return "Blocked: an input is unauthorized or failed its integrity check";
  return "Insufficient data: no forecast is shown for this period";
}

/** The forecasting goal is met only when every criterion is literally true (C9 is a string while not assessable). */
export function goalMet(r: LeadRow): boolean {
  return !!r.criteria && Object.values(r.criteria).every((v) => v === true);
}
