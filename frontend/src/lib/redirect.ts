// src/lib/redirect.ts
// ---------------------
// Where to send someone after sign-in. The requested page travels in router
// state from RequireAdmin, but it is still checked: only a path on this site
// is followed. "//evil.example" and "/\evil.example" both start with "/" yet
// browsers resolve them to another host, so they are refused too.

export const DEFAULT_AFTER_LOGIN = "/admin";

export function safeRedirectPath(candidate: unknown, fallback: string = DEFAULT_AFTER_LOGIN): string {
  if (typeof candidate !== "string") return fallback;
  if (!candidate.startsWith("/")) return fallback;
  if (candidate.startsWith("//") || candidate.startsWith("/\\")) return fallback;
  // Control characters (tab, newline) are stripped by URL parsers and can
  // turn "/\t/evil.example" into "//evil.example".
  if (/[\u0000-\u001f\u007f]/.test(candidate)) return fallback;
  return candidate;
}
