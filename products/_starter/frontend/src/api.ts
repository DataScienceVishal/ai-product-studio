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

const TIMEOUT_MS = 30_000;

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
  } catch {
    throw new ApiError(0, "network", "Can't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, data.error ?? "error", data.message ?? "Something went wrong.", data.fields ?? []);
  }
  return data as T;
}

export const formatPrice = (pence: number, currency: string) =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency: currency.toUpperCase() }).format(pence / 100);
