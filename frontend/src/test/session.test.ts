import { afterEach, describe, expect, it, vi } from "vitest";
import { api, getToken, refreshSession, setToken } from "@/lib/api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const session = (token: string) => ({ token, expiresIn: 3600, expiresAt: "2026-10-14T12:00:00Z", user: { id: 1, email: "a@calabarzon.da.gov.ph", name: "A", role: "admin" } });

afterEach(() => {
  vi.unstubAllGlobals();
  setToken(null);
});

describe("refreshSession", () => {
  it("trades the cookie for an access token, sending credentials and the CSRF header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, session("fresh")));
    vi.stubGlobal("fetch", fetchMock);
    const s = await refreshSession();
    expect(s?.token).toBe("fresh");
    expect(getToken()).toBe("fresh");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/auth/refresh");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-CSRF-Protection"]).toBe("1");
  });

  it("shares one request between concurrent callers (the cookie rotates on each use)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(200, session("once")));
    vi.stubGlobal("fetch", fetchMock);
    const [a, b] = await Promise.all([refreshSession(), refreshSession()]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(a?.token).toBe("once");
    expect(b?.token).toBe("once");
  });

  it("resolves to null on 204 (no cookie: a public visitor)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await refreshSession()).toBeNull();
    expect(getToken()).toBeNull();
  });

  it("resolves to null and holds no token when the session is gone", async () => {
    setToken("stale");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(401, { error: { code: "no_session", message: "x" } })));
    expect(await refreshSession()).toBeNull();
    expect(getToken()).toBeNull();
  });
});

describe("expired access token", () => {
  it("is renewed once from the cookie and the request repeated", async () => {
    setToken("old");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(401, { error: { code: "token_expired", message: "expired" } }))
      .mockResolvedValueOnce(json(200, session("new")))
      .mockResolvedValueOnce(json(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await api.get<{ ok: boolean }>("/api/v1/admin/review");
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer new");
  });

  it("is not retried for other 401s (revoked, signed out)", async () => {
    setToken("revoked");
    const fetchMock = vi.fn().mockResolvedValue(json(401, { error: { code: "token_revoked", message: "signed out" } }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.get("/api/v1/admin/review")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
