// src/lib/api.ts
// ----------------
// The single fetch wrapper every query/mutation goes through. Centralising
// this is what makes the token-storage, error-envelope and 401 rules apply
// uniformly instead of being reimplemented (and drifting) per call site.

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Token storage — in memory only. Never localStorage, never a cookie: a
// token surviving a page reload is not worth an XSS payload being able to
// read it out of storage. The cost is that a hard refresh signs the admin
// out and auth.tsx re-establishes the session via /auth/me on next load.
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
}

const DEFAULT_TIMEOUT_MS = 20_000;

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  { params, body, opts }: { params?: Record<string, unknown>; body?: unknown; opts?: RequestOptions } = {}
): Promise<T> {
  const { auth = true, timeoutMs = DEFAULT_TIMEOUT_MS } = opts ?? {};

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(buildUrl(path, method === "GET" ? params : undefined), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
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

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>, opts?: RequestOptions) =>
    request<T>("GET", path, { params, opts }),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>("POST", path, { body: body ?? {}, opts }),
  delete: <T>(path: string, opts?: RequestOptions) => request<T>("DELETE", path, { opts }),
};
