// src/lib/auth.tsx
// -----------------
// Session state. The token lives in memory (api.ts), never localStorage,
// never a cookie -- this component is the only thing that reads or writes it.
// On mount it calls GET /auth/me rather than trusting a stored identity
// object, so a session that was revoked server-side (logout elsewhere,
// deactivated account) is noticed immediately rather than on next expiry.

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { api, ApiError, setToken, getToken, onSessionExpired } from "./api";
import type { AuthUser, LoginResponse } from "./apiTypes";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: AuthUser | null;
  status: Status;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Set by login()/the 401 handler when there's something worth showing on the login form. */
  lastError: string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [lastError, setLastError] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  // Global 401 handling: any call anywhere in the app that gets a 401 drops
  // the session here. Login/route guards react to `status` changing.
  useEffect(() => onSessionExpired(clearSession), [clearSession]);

  // On mount: if a token is already held (e.g. survived a hot reload in dev),
  // confirm it against the server rather than assuming it's still good.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!getToken()) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        const me = await api.get<AuthUser>("/api/v1/auth/me");
        if (!cancelled) {
          setUser(me);
          setStatus("authenticated");
        }
      } catch {
        if (!cancelled) clearSession();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    setLastError(null);
    try {
      const res = await api.post<LoginResponse>(
        "/api/v1/auth/login",
        { email, password },
        { auth: false }
      );
      setToken(res.token);
      setUser(res.user);
      setStatus("authenticated");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "server_misconfigured") {
          setLastError("The server is not configured for sign-in — contact the administrator.");
        } else if (err.code === "rate_limited") {
          setLastError(`Too many attempts. Try again in ${err.retryAfter ?? 60}s.`);
        } else {
          // invalid_credentials and everything else: the backend's own
          // message is deliberately generic (it doesn't say which part was
          // wrong, to avoid account enumeration) -- show it verbatim.
          setLastError(err.message);
        }
      } else {
        setLastError("Could not reach the server.");
      }
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/api/v1/auth/logout");
    } catch {
      // Revocation failing server-side shouldn't trap the user in a "signed
      // in" state client-side -- clear the local session regardless.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  return (
    <AuthContext.Provider value={{ user, status, login, logout, lastError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth() must be used inside <AuthProvider>");
  return ctx;
}
