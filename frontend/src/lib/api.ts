// src/lib/api.ts
// ----------------
// The single fetch wrapper every query/mutation goes through. Centralising
// this is what makes the token-storage, error-envelope and 401 rules apply
// uniformly instead of being reimplemented (and drifting) per call site.

import type { LoginResponse } from "./apiTypes";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Token storage — in memory only. Never localStorage, never a readable
// cookie: an XSS payload must not be able to read the access token out of
// storage. What survives a reload is the server's httpOnly refresh cookie,
// which page scripts cannot read; refreshSession() trades it for a new
// access token (on page load, and when the access token expires).
// ---------------------------------------------------------------------------

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

// ---------------------------------------------------------------------------
// Session-expired pub/sub — so any 401 from any call anywhere in the app
// (not just the one the user is currently looking at) drops the session and
// the route guard reacts, instead of only the triggering screen noticing.
// ---------------------------------------------------------------------------

type Listener = () => void;
const listeners = new Set<Listener>();

export function onSessionExpired(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function emitSessionExpired() {
  listeners.forEach((fn) => fn());
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;
  retryAfter?: number;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// ---------------------------------------------------------------------------
// URL building
// ---------------------------------------------------------------------------

export function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

// ---------------------------------------------------------------------------
// Core request
// ---------------------------------------------------------------------------

interface RequestOptions {
  auth?: boolean; // default true — send the bearer token when one is held
  timeoutMs?: number;
  /** Send/accept cookies cross-origin: sign-in and sign-out, which set and clear the refresh cookie. */
  withCredentials?: boolean;
  /** Internal: this is the retry after renewing an expired access token. */
  retried?: boolean;
}

const DEFAULT_TIMEOUT_MS = 20_000;

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  { params, body, opts }: { params?: Record<string, unknown>; body?: unknown; opts?: RequestOptions } = {}
): Promise<T> {
  const { auth = true, timeoutMs = DEFAULT_TIMEOUT_MS, withCredentials = false, retried = false } = opts ?? {};

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const sentToken = auth ? getToken() : null;
  if (sentToken) headers["Authorization"] = `Bearer ${sentToken}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(buildUrl(path, method === "GET" ? params : undefined), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      credentials: withCredentials ? "include" : "same-origin",
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "timeout", "The server took too long to respond.");
    }
    throw new ApiError(0, "network_error", "Could not reach the server.");
  }
  clearTimeout(timer);

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const json = text ? safeParse(text) : null;

  if (!res.ok) {
    // Two shapes to handle: our own {error:{code,message,details}} envelope,
    // and FastAPI's native 422 validation error {detail:[...]}.
    let code = "unknown_error";
    let message = `Request failed (${res.status}).`;
    let details: Record<string, unknown> = {};

    if (json && typeof json === "object" && "error" in json) {
      const e = (json as { error: { code?: string; message?: string; details?: Record<string, unknown> } }).error;
      code = e.code ?? code;
      message = e.message ?? message;
      details = e.details ?? {};
    } else if (json && typeof json === "object" && "detail" in json) {
      const detail = (json as { detail: unknown }).detail;
      code = "validation_error";
      message = Array.isArray(detail)
        ? detail.map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d))).join("; ")
        : String(detail);
    }

    const apiErr = new ApiError(res.status, code, message, details);

    if (res.status === 401) {
      // The access token ran out while working: renew it from the refresh
      // cookie once and repeat the request, rather than signing the admin out.
      if (sentToken && code === "token_expired" && !retried && (await refreshSession())) {
        return request<T>(method, path, { params, body, opts: { ...opts, retried: true } });
      }
      emitSessionExpired();
    }
    if (res.status === 429) {
      const retryAfterHeader = res.headers.get("Retry-After");
      apiErr.retryAfter = retryAfterHeader ? Number(retryAfterHeader) : undefined;
    }

    throw apiErr;
  }

  return json as T;
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Session refresh
// ---------------------------------------------------------------------------

let refreshing: Promise<LoginResponse | null> | null = null;

/**
 * Trade the httpOnly refresh cookie for a new access token (POST
 * /auth/refresh). Resolves to the session, or null when there is none to
 * restore. Concurrent callers share one request: the server rotates the
 * cookie on every use, so two parallel refreshes from one tab would race.
 * The X-CSRF-Protection header is required by the server (see
 * backend/app/services/sessions.py).
 */
export function refreshSession(): Promise<LoginResponse | null> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(buildUrl("/api/v1/auth/refresh"), {
          method: "POST",
          credentials: "include",
          headers: { "X-CSRF-Protection": "1" },
        });
        // 204: no cookie, nothing to restore (a public visitor). 401: the
        // cookie was invalid, expired or revoked, and the server cleared it.
        if (res.status === 204 || !res.ok) {
          setToken(null);
          return null;
        }
        const session = (await res.json()) as LoginResponse;
        setToken(session.token);
        return session;
      } catch {
        return null;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>, opts?: RequestOptions) =>
    request<T>("GET", path, { params, opts }),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("POST", path, { body: body ?? {}, opts }),
  delete: <T>(path: string, opts?: RequestOptions) => request<T>("DELETE", path, { opts }),
};
