// Which forecast the backend serves, and the C-b (NEWS_V2-CB) figures read from its evaluation payload.
// The backend chooses the model (AIPHEED_MAP_MODEL); the page only describes what /api/v1/config reports, so the
// deployed default (FIRI v2 map with the P0H4 description) is unchanged and the C-b mode never shows P0H4 text.
import type { FinalRiskEvaluation } from "@/lib/apiTypes";

/** Indicator id of backend/app/ml/inference/foodinsecurity_system.py (the C-b food-insecurity forecast). */
export const CB_INDICATOR = "regional_food_insecurity_forecast";

export function isCbIndicator(id: string | null | undefined): boolean {
  return id === CB_INDICATOR;
}

/** One lead of foodinsecurity_system.evaluation(): metric names as exported by FOOD_INSECURITY_SYSTEM/export_fi.py. */
export interface CbLead {
  n_quarters: number;
  period: string;
  metrics: {
    accuracy: number;
    balanced: number;
    precision: number;
    recall: number;
    f1: number;
    auc: number | null;
    brier: number;
    TP: number;
    FP: number;
    FN: number;
    TN: number;
  };
  persistence_accuracy: number;
  alg3_pass: boolean;
  failed: string[];
  shap_shares: Record<string, number> | null;
}

export interface CbEvaluation {
  model: string;
  target: string;
  max_reliable_lead: number | null;
  max_reliable_lead_r1_r7: number | null;
  leads: Record<string, CbLead>;
  objective4_lead1: Record<string, { diff: number; p_holm: number }>;
  seal_sha256?: string;
  seal_issue_date?: string;
  model_description?: string;
}

/** The food-insecurity models (backend/data/foodinsecurity_engine*), by the `model` id of their evaluation. */
export const MODELS: Record<string, { name: string; inputs: number; riceStocks: boolean }> = {
  "NEWS_V2-CB": { name: "C-b", inputs: 21, riceStocks: false },
  "ALLBASE-CB6": { name: "C-B6", inputs: 23, riceStocks: true },
  "ALLBASE-CE2": { name: "C-E2", inputs: 23, riceStocks: false },
  "ALLBASE-CE6": { name: "C-E6", inputs: 25, riceStocks: true },
};

/** Short name of the served model ("C-B6"), or its id when unknown. */
export function modelName(e: CbEvaluation | null | undefined): string {
  return (e && MODELS[e.model]?.name) ?? e?.model ?? "the model";
}

/** True when the served model fails the stricter rules R1-R7 at the lead (from its own evaluation). */
export function failsStrict(e: CbEvaluation | null | undefined, lead = "1"): boolean {
  return (e?.leads[lead]?.failed?.length ?? 1) > 0;
}

/** The first evaluated lead that fails the 75% rule, if any. */
export function firstFailingLead(e: CbEvaluation | null | undefined): number | null {
  const k = Object.keys(e?.leads ?? {})
    .map(Number)
    .sort((a, b) => a - b)
    .find((x) => !e?.leads[String(x)]?.alg3_pass);
  return k ?? null;
}

/** The served food-insecurity model's payload (C-B6 main, C-b, C-E2, C-E6), or null for any other model. */
export function cbEvaluation(ev: FinalRiskEvaluation | undefined): CbEvaluation | null {
  const e = ev as unknown as CbEvaluation | undefined;
  return e && typeof e.model === "string" && (e.model.startsWith("NEWS_V2-CB") || e.model in MODELS) ? e : null;
}

/** Comparator labels of the Objective 4 family in objective4_lead1 (NEW_MODEL/NEWS_V2/runner/align_cb.py OBJ4). */
export const CB_COMPARATORS: Record<string, string> = {
  PERSIST: "Naive persistence",
  "PSA-only": "Logistic regression, government (PSA) data only",
  LOGIT: "Logistic regression, combined",
  "NLP-only": "Logistic regression, news only (2021 onward)",
  "ALWAYS-HIGH": "Always High",
};

/** Comparator Brier = the served model's Brier minus the paired difference (both on the same quarters, except news-only). */
export function cbComparatorRows(e: CbEvaluation): { name: string; diff: number; pHolm: number }[] {
  return Object.entries(e.objective4_lead1 ?? {}).map(([k, v]) => ({
    name: CB_COMPARATORS[k] ?? k,
    diff: v.diff,
    pHolm: v.p_holm,
  }));
}

export const fmt = (x: number | null | undefined, d = 3) => (x == null || Number.isNaN(x) ? "n/a" : x.toFixed(d));
