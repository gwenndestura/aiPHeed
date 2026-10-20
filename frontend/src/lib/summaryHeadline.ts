/**
 * The backend's plain-language summary (explainability `summary.sentence`) is
 * a full report of several paragraphs. The Why panel shows only its first
 * sentence, the headline, with an all-caps lead ("ESTIMATED FOOD-INSECURITY
 * RISK") in sentence case like the rest of the site.
 */
export function summaryHeadline(sentence: string): string {
  const first = sentence.trim().split(/(?<=\.)\s+(?=[A-Z])/)[0] ?? "";
  return first.replace(/^[A-Z][A-Z\s-]+?(?=[,:]|\s+for\b)/, (lead) => lead.charAt(0) + lead.slice(1).toLowerCase());
}
