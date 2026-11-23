import { vi } from "vitest";
import type { Me } from "./api";

/** A JSON Response, as the API would send it. */
export function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** Replace global fetch with a mock for this test (vitest.config.ts un-stubs it afterwards). */
export function stubFetch() {
  const mock = vi.fn();
  vi.stubGlobal("fetch", mock);
  return mock;
}

export const makeMe = (over: Partial<Me["subscription"]> = {}, role = "owner"): Me => ({
  user: { id: "u1", email: "a@example.com", role, email_verified: true },
  tenant: { id: "t1", name: "Acme" },
  subscription: { plan: "trial", status: "trialing", offer: null, trial_ends_at: null, current_period_end: null, ...over },
});

export const ME: Me = makeMe();
