import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Me } from "../api";
import { Billing, BillingDone, MockCheckout } from "./app";

const me = (over: Partial<Me["subscription"]> = {}, role = "owner"): Me => ({
  user: { id: "u1", email: "a@example.com", role, email_verified: true },
  tenant: { id: "t1", name: "Acme" },
  subscription: { plan: "trial", status: "trialing", offer: null, trial_ends_at: null, current_period_end: null, ...over },
});

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const PLANS = { plans: [{ id: "pro", name: "Pro", price_pence: 4900, currency: "gbp", interval: "month", ai_monthly_tokens: 1000000 }] };

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Billing", () => {
  it("lists plans with formatted prices and token allowance", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={me()} refresh={vi.fn()} />);
    expect(await screen.findByText("£49.00")).toBeTruthy();
    expect(screen.getByText(/1,000,000 AI tokens a month/)).toBeTruthy();
  });

  it("only owners can choose a plan", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={me({}, "member")} refresh={vi.fn()} />);
    const button = await screen.findByRole("button", { name: "Choose Pro" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("a mock checkout goes to the in-app test page with the session id encoded", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { checkout_id: "mock_a&b", url: "https://unused.example" }));
    render(<Billing me={me()} refresh={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/offer code/i), { target: { value: "EARLY50" } });
    fireEvent.click(await screen.findByRole("button", { name: "Choose Pro" }));
    await waitFor(() => expect(window.location.pathname).toBe("/billing/mock-checkout"));
    expect(new URLSearchParams(window.location.search).get("session")).toBe("mock_a&b");
    const [path, init] = fetchMock.mock.calls[1];
    expect(path).toBe("/api/billing/checkout");
    expect(JSON.parse(init.body)).toEqual({ plan: "pro", offer_code: "EARLY50" });
  });

  it("sends offer_code null when no code is typed", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { checkout_id: "mock_1", url: "x" }));
    render(<Billing me={me()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Choose Pro" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).offer_code).toBeNull();
  });

  it("shows the server error when checkout fails", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(400, { error: "bad_offer", message: "That offer code isn't valid." }));
    render(<Billing me={me()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Choose Pro" }));
    expect((await screen.findByRole("alert")).textContent).toBe("That offer code isn't valid.");
  });
});

describe("MockCheckout (billing return)", () => {
  it("completes the session from ?session=, refreshes and returns to /billing", async () => {
    window.history.replaceState({}, "", "/billing/mock-checkout?session=mock_xyz");
    fetchMock.mockResolvedValue(reply(204));
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<MockCheckout refresh={refresh} />);
    fireEvent.click(screen.getByRole("button", { name: "Pay (test)" }));
    await waitFor(() => expect(window.location.pathname).toBe("/billing"));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/billing/mock/complete/mock_xyz");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(refresh).toHaveBeenCalled();
  });

  it("encodes a hostile session id so it cannot change the API path", async () => {
    window.history.replaceState({}, "", `/billing/mock-checkout?session=${encodeURIComponent("../../auth/logout")}`);
    fetchMock.mockResolvedValue(reply(204));
    render(<MockCheckout refresh={vi.fn().mockResolvedValue(undefined)} />);
    fireEvent.click(screen.getByRole("button", { name: "Pay (test)" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][0]).toBe("/api/billing/mock/complete/..%2F..%2Fauth%2Flogout");
  });

  it("Cancel goes back to billing without calling the API", () => {
    window.history.replaceState({}, "", "/billing/mock-checkout?session=mock_xyz");
    render(<MockCheckout refresh={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(window.location.pathname).toBe("/billing");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the server error and stays put on failure", async () => {
    window.history.replaceState({}, "", "/billing/mock-checkout?session=mock_xyz");
    fetchMock.mockResolvedValue(reply(404, { error: "not_found", message: "Unknown checkout." }));
    render(<MockCheckout refresh={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Pay (test)" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Unknown checkout.");
    expect(window.location.pathname).toBe("/billing/mock-checkout");
  });
});

describe("BillingDone (/billing/done)", () => {
  it("shows success once the subscription is active", () => {
    render(<BillingDone me={me({ plan: "pro", status: "active" })} refresh={vi.fn()} />);
    expect(screen.getByRole("status").textContent).toMatch(/you're on the pro plan/i);
  });

  it("polls refresh every 2s while waiting, then gives up with a clear message after 15 tries", async () => {
    vi.useFakeTimers();
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<BillingDone me={me()} refresh={refresh} />);
    expect(screen.getByText(/confirming your payment/i)).toBeTruthy();
    for (let i = 0; i < 15; i++) await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(refresh).toHaveBeenCalledTimes(15);
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(refresh).toHaveBeenCalledTimes(15);
    expect(screen.getByRole("alert").textContent).toMatch(/haven't had confirmation/i);
  });
});
