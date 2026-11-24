// Small API client: same-origin cookies, the CSRF header on every request, friendly errors.

export type Me = {
  user: { id: string; email: string; role: string; email_verified: boolean };
  tenant: { id: string; name: string };
  subscription: { plan: string; status: string; offer: string | null; trial_ends_at: string | null; current_period_end: string | null };
};

export type Note = { id: string; title: string; body: string; summary: string | null; created_at: string; updated_at: string };
export type Plan = { id: string; name: string; price_pence: number; currency: string; interval: string; ai_monthly_tokens: number };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields: { field: string; problem: string }[] = []) {
    super(message);
  }
}

// Build-time VITE_API_TIMEOUT_SECONDS (default 30). The backend's AI_DEADLINE_SECONDS must stay at least 2 s below it
// (FRONTEND_TIMEOUT_SECONDS on the server must carry the same number, or the server refuses to start).
export function timeoutMs(raw: string | undefined = import.meta.env.VITE_API_TIMEOUT_SECONDS): number {
  const seconds = Number(raw);
  return raw && Number.isFinite(seconds) && seconds >= 1 ? seconds * 1000 : 30_000;
}
const TIMEOUT_MS = timeoutMs();
// Requests where a 401 is an expected answer, not "your session ended".
const AUTH_PATHS = ["/api/auth/me", "/api/auth/login", "/api/auth/signup", "/api/invitations/accept",
  "/api/auth/password-reset/request", "/api/auth/password-reset/confirm"];
export const SESSION_ENDED = "session-ended";

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Requested-With": "fetch" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
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
