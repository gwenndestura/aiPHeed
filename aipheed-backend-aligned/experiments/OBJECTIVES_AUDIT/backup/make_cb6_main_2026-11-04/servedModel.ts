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
}

/** The C-b payload, or null when the served evaluation is another model's. */
export function cbEvaluation(ev: FinalRiskEvaluation | undefined): CbEvaluation | null {
  const e = ev as unknown as CbEvaluation | undefined;
  return e && typeof e.model === "string" && e.model.startsWith("NEWS_V2-CB") ? e : null;
}

/** Comparator labels of the Objective 4 family in objective4_lead1 (NEW_MODEL/NEWS_V2/runner/align_cb.py OBJ4). */
export const CB_COMPARATORS: Record<string, string> = {
  PERSIST: "Naive persistence",
  "PSA-only": "Logistic regression, government (PSA) data only",
  LOGIT: "Logistic regression, combined",
  "NLP-only": "Logistic regression, news only (2021 onward)",
  "ALWAYS-HIGH": "Always High",
};

/** Comparator Brier = C-b Brier minus the paired difference (both on the same quarters, except news-only). */
export function cbComparatorRows(e: CbEvaluation): { name: string; diff: number; pHolm: number }[] {
  return Object.entries(e.objective4_lead1 ?? {}).map(([k, v]) => ({
    name: CB_COMPARATORS[k] ?? k,
    diff: v.diff,
    pHolm: v.p_holm,
  }));
}

export const fmt = (x: number | null | undefined, d = 3) => (x == null || Number.isNaN(x) ? "n/a" : x.toFixed(d));
