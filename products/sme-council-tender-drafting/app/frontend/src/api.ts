// Small API client: same-origin cookies, the CSRF header on every request, friendly errors.

export type Me = {
  user: { id: string; email: string; role: string; email_verified: boolean; email_verification_required: boolean };
  tenant: { id: string; name: string };
  subscription: { plan: string; status: string; offer: string | null; trial_ends_at: string | null; current_period_end: string | null };
};

export type Plan = { id: string; name: string; price_pence: number; currency: string; interval: string; ai_monthly_tokens: number };
/** T-94: while billing is mock or Stripe test mode, every plan uses the free-trial AI allowance. */
export type AiAllowance = { trial_sized: boolean; monthly_tokens: number; daily_tokens: number | null };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields: { field: string; problem: string }[] = []) {
    super(message);
  }
}

// The browser's abort comes from the server (GET /api/config, FRONTEND_TIMEOUT_SECONDS), read once at startup, so the
// startup check that keeps AI_DEADLINE_SECONDS below it guards the real value. Fallback: 30 s. Capped at 600 s: a
// larger setTimeout overflows 2^31-1 ms and fires at once.
const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_TIMEOUT_MS = 600_000;
export function timeoutMs(raw: unknown): number {
  const seconds = typeof raw === "number" ? raw : Number.NaN;
  return Number.isFinite(seconds) && seconds >= 1 ? Math.min(seconds * 1000, MAX_TIMEOUT_MS) : DEFAULT_TIMEOUT_MS;
}
let requestTimeoutMs = DEFAULT_TIMEOUT_MS;
// "mock" only when the server says so; anything else (including a failed /api/config) fails closed.
let billingProvider = "";
// Prices off (T-185): billing pages, links and price text show only when the server says billing is enabled.
let billingEnabled = false;
export const isBillingEnabled = (): boolean => billingEnabled;
export function setBillingEnabledForTest(value: boolean): void { billingEnabled = value; }
export const isMockBilling = (): boolean => billingProvider === "mock";
export function setBillingProviderForTest(value: string): void { billingProvider = value; }
export async function loadClientConfig(): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5_000);
  billingEnabled = false;
  billingProvider = ""; // only a successful config with "mock" turns it on
  try {
    const response = await fetch("/api/config", { credentials: "same-origin", signal: controller.signal });
    if (response.ok) {
      const config = await response.json();
      requestTimeoutMs = timeoutMs(config.api_timeout_seconds);
      billingEnabled = config.billing_enabled === true;
      billingProvider = typeof config.billing_provider === "string" ? config.billing_provider : "";
    }
  } catch {
    requestTimeoutMs = DEFAULT_TIMEOUT_MS; // no config: keep the safe default
  } finally {
    clearTimeout(timer);
  }
}
// Requests where a 401 is an expected answer, not "your session ended".
const AUTH_PATHS = ["/api/auth/me", "/api/auth/login", "/api/auth/signup", "/api/invitations/accept",
  "/api/auth/password-reset/request", "/api/auth/password-reset/confirm"];
export const SESSION_ENDED = "session-ended";

export async function api<T>(path: string, options: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), requestTimeoutMs);
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      // a FormData body sets its own multipart Content-Type (with the boundary)
      headers: options.form ? { "X-Requested-With": "fetch" } : { "Content-Type": "application/json", "X-Requested-With": "fetch" },
      body: options.form ?? (options.body === undefined ? undefined : JSON.stringify(options.body)),
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "timeout", "The server took too long to answer. Please try again.");
    }
    throw new ApiError(0, "network", "Can't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  // Only a real "not signed in" ends the session: a wrong password on a confirm form is also a 401.
  if (response.status === 401 && data.error === "not_signed_in" && !AUTH_PATHS.includes(path)) {
    window.dispatchEvent(new Event(SESSION_ENDED)); // expired session or removed member: back to sign-in
  }
  if (!response.ok) {
    throw new ApiError(response.status, data.error ?? "error", data.message ?? "Something went wrong.", data.fields ?? []);
  }
  return data as T;
}

export const formatPrice = (pence: number, currency: string) =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency: currency.toUpperCase() }).format(pence / 100);
