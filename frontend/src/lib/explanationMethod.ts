import type { ConfigResponse } from "@/lib/apiTypes";

/**
 * E73: what the driver bars are. The backend names the method in /api/v1/config (servingModel.explanationMethod):
 * TreeSHAP contributions of a fitted model, or (thesis system) an exact additive breakdown of the FIRI v2 index,
 * which is not SHAP. Without that field (the default service) the bars are SHAP, as before.
 */
export function explanationMethod(config?: ConfigResponse | null): {
  isShap: boolean; title: string; short: string; detail?: string; panelTitle: string; orderLabel: string;
} {
  const m = config?.servingModel?.explanationMethod;
  const isShap = m?.isShap ?? true;
  return isShap
    ? { isShap, title: "SHAP Explainability", short: "SHAP", detail: m?.detail,
        panelTitle: "Why is this province at risk?", orderLabel: "Ranked" }
    : { isShap, title: "Index Contribution Breakdown", short: "Index contribution", detail: m?.detail,
        // E74: the bars cover five evidence groups of an index; they are not an overall ranking of causes
        panelTitle: m?.panelTitle ?? "Contributing indicators", orderLabel: m?.orderLabel ?? "Index contribution, not causes" };
}
