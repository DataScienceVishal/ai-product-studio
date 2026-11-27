import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch } from "./test-utils";
import { api, ApiError, formatPrice, isMockBilling, loadClientConfig, SESSION_ENDED, setBillingProviderForTest, timeoutMs } from "./api";

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = stubFetch();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("api: request shape", () => {
  it("sends same-origin cookies and the CSRF header on a GET", async () => {
    fetchMock.mockResolvedValue(reply(200, { ok: 1 }));
    await expect(api("/api/things")).resolves.toEqual({ ok: 1 });
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/things");
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-Requested-With"]).toBe("fetch");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBeUndefined();
  });

  it("JSON-encodes the body and keeps the CSRF header on writes", async () => {
    fetchMock.mockResolvedValue(reply(200, {}));
    await api("/api/notes", { method: "POST", body: { title: "a" } });
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"title":"a"}');
    expect(init.headers["X-Requested-With"]).toBe("fetch");
  });

  it("returns undefined for 204 without parsing a body", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(api("/api/notes/1", { method: "DELETE" })).resolves.toBeUndefined();
  });
});

describe("api: errors", () => {
  it("turns an error response into an ApiError with code, message and fields", async () => {
    fetchMock.mockResolvedValue(reply(422, { error: "validation", message: "Check the form.", fields: [{ field: "password", problem: "Too short." }] }));
    const err = await api("/api/auth/signup", { method: "POST", body: {} }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 422, code: "validation", message: "Check the form.", fields: [{ field: "password", problem: "Too short." }] });
  });

  it("falls back to generic text when the error body is not JSON", async () => {
    fetchMock.mockResolvedValue(new Response("<html>502</html>", { status: 502 }));
    const err = await api("/api/x").catch((e) => e);
    expect(err).toMatchObject({ status: 502, code: "error", message: "Something went wrong.", fields: [] });
  });

  it("reports a network failure in plain English", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await api("/api/x").catch((e) => e);
    expect(err).toMatchObject({ status: 0, code: "network" });
    expect((err as Error).message).toMatch(/can't reach the server/i);
  });

  it("validates the served timeout, falls back to 30 seconds and caps it at 600", () => {
    expect(timeoutMs(undefined)).toBe(30_000);
    expect(timeoutMs("60")).toBe(30_000);
    expect(timeoutMs(0)).toBe(30_000);
    expect(timeoutMs(Number.NaN)).toBe(30_000);
    expect(timeoutMs(60)).toBe(60_000);
    expect(timeoutMs(3_000_000)).toBe(600_000);
    expect(timeoutMs(Number.POSITIVE_INFINITY)).toBe(30_000);
  });

  it("uses the timeout served at /api/config, and the default if that call fails", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValueOnce(reply(200, { api_timeout_seconds: 60 }));
    await loadClientConfig();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/config");
    fetchMock.mockImplementation((_p: string, init: RequestInit) => new Promise((_res, rej) => {
      init.signal!.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
    }));
    let outcome: unknown = "pending";
    const pending = api("/api/slow").catch((e) => (outcome = e));
    await vi.advanceTimersByTimeAsync(30_000);
    expect(outcome).toBe("pending"); // still waiting at 30 s: the served 60 s is in force
    await vi.advanceTimersByTimeAsync(30_000);
    await pending;
    expect(outcome).toMatchObject({ code: "timeout" });
    fetchMock.mockRejectedValueOnce(new TypeError("down"));
    await loadClientConfig();
    const again = api("/api/slow").catch((e) => (outcome = e));
    await vi.advanceTimersByTimeAsync(30_000);
    await again;
    expect(outcome).toMatchObject({ code: "timeout" });
  });

  it("gives up on a hung /api/config after 5 seconds and keeps the 30 second default", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation((_p: string, init: RequestInit) => new Promise((_res, rej) => {
      init.signal!.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
    }));
    let settled = false;
    const loading = loadClientConfig().then(() => { settled = true; });
    await vi.advanceTimersByTimeAsync(4_900);
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(200);
    expect(settled).toBe(true);
    await loading;
    let outcome: unknown = "pending";
    const pending = api("/api/slow").catch((e) => (outcome = e));
    await vi.advanceTimersByTimeAsync(30_000);
    await pending;
    expect(outcome).toMatchObject({ code: "timeout" });
  });

  it("aborts after 30 seconds (the default) and reports a timeout", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation((_path: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    }));
    const pending = api("/api/slow").catch((e) => e);
    await vi.advanceTimersByTimeAsync(30_000);
    const err = await pending;
    expect(err).toMatchObject({ status: 0, code: "timeout" });
  });
});

describe("api: session end", () => {
  let ended: ReturnType<typeof vi.fn<() => void>>;
  beforeEach(() => {
    ended = vi.fn<() => void>();
    window.addEventListener(SESSION_ENDED, ended);
  });
  afterEach(() => window.removeEventListener(SESSION_ENDED, ended));

  it("signals when a normal request gets not_signed_in", async () => {
    fetchMock.mockResolvedValue(reply(401, { error: "not_signed_in", message: "Sign in." }));
    await expect(api("/api/notes")).rejects.toBeInstanceOf(ApiError);
    expect(ended).toHaveBeenCalledTimes(1);
  });

  it.each(["/api/auth/me", "/api/auth/login", "/api/auth/signup", "/api/invitations/accept",
    "/api/auth/password-reset/request", "/api/auth/password-reset/confirm"])("does not signal on a 401 from %s", async (path) => {
    fetchMock.mockResolvedValue(reply(401, { error: "not_signed_in" }));
    await expect(api(path)).rejects.toBeInstanceOf(ApiError);
    expect(ended).not.toHaveBeenCalled();
  });

  it("does not signal on a 401 that is not not_signed_in (e.g. wrong current password)", async () => {
    fetchMock.mockResolvedValue(reply(401, { error: "invalid_credentials", message: "Wrong password." }));
    await expect(api("/api/account/delete", { method: "POST" })).rejects.toMatchObject({ code: "invalid_credentials" });
    expect(ended).not.toHaveBeenCalled();
  });
});

describe("formatPrice", () => {
  it("formats pence as pounds in en-GB", () => {
    expect(formatPrice(4900, "gbp")).toBe("£49.00");
    expect(formatPrice(5, "GBP")).toBe("£0.05");
  });
});

describe("loadClientConfig: billing_provider", () => {
  beforeEach(() => setBillingProviderForTest(""));
  afterEach(() => setBillingProviderForTest(""));

  it("is off before any config is loaded (fails closed)", async () => {
    vi.resetModules();
    const fresh = await import("./api");
    expect(fresh.isMockBilling()).toBe(false);
  });

  it.each([[500], [404]])("is off when /api/config answers %i, even with billing_provider mock in the body", async (status) => {
    setBillingProviderForTest("mock");
    fetchMock.mockResolvedValueOnce(reply(status, { billing_provider: "mock" }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
  });

  it("turns mock billing on only when the server says \"mock\"", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, { api_timeout_seconds: 30, billing_provider: "mock" }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(true);
  });

  it("leaves mock billing off for a real provider or a missing field", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, { billing_provider: "stripe" }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
    setBillingProviderForTest("mock");
    fetchMock.mockResolvedValueOnce(reply(200, { api_timeout_seconds: 30 }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
  });

  it.each([["Mock"], ["MOCK"], [" mock"], ["mock "], ["mockery"], ["not-mock"], [""]])("treats a near-miss string billing_provider (%j) as not mock (exact match only)", async (value) => {
    setBillingProviderForTest("mock");
    fetchMock.mockResolvedValueOnce(reply(200, { billing_provider: value }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
  });

  it.each([[true], [1], [["mock"]], [{ name: "mock" }], [null]])("treats a non-string billing_provider (%j) as not mock", async (value) => {
    setBillingProviderForTest("mock");
    fetchMock.mockResolvedValueOnce(reply(200, { billing_provider: value }));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
  });

  it("is off when /api/config cannot be reached", async () => {
    setBillingProviderForTest("mock");
    fetchMock.mockRejectedValueOnce(new TypeError("down"));
    await loadClientConfig();
    expect(isMockBilling()).toBe(false);
  });
});
