/**
 * Rules for the typed rejection reason. They match clean_reason in
 * backend/app/services/review.py, which checks the same thing on the server.
 */
export const REASON_MIN_CHARS = 10;
export const REASON_MAX_CHARS = 200;

/** Collapse runs of spaces and trim, as the server does before saving. */
export function tidyReason(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** The problem with a reason, or null when it can be sent. */
export function reasonProblem(text: string): string | null {
  const reason = tidyReason(text);
  if (!reason) return "Enter a reason for the rejection.";
  if (reason.length < REASON_MIN_CHARS) return `The reason must be at least ${REASON_MIN_CHARS} characters.`;
  if (reason.length > REASON_MAX_CHARS) return `The reason must be ${REASON_MAX_CHARS} characters or fewer.`;
  const words = reason.split(" ").filter((w) => /\p{L}/u.test(w));
  if (words.length < 2) return "Describe the reason in at least two words.";
  return null;
}
