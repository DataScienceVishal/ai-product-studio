import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { SESSION_ENDED, type Me } from "./api";

const ME: Me = {
  user: { id: "u1", email: "a@example.com", role: "owner", email_verified: true },
  tenant: { id: "t1", name: "Acme" },
  subscription: { plan: "trial", status: "trialing", offer: null, trial_ends_at: null, current_period_end: null },
};

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

let fetchMock: ReturnType<typeof vi.fn>;
const signedOut = () => fetchMock.mockImplementation(async () => reply(401, { error: "not_signed_in", message: "Sign in." }));
const signedIn = () => fetchMock.mockImplementation(async (path: string) =>
  path === "/api/auth/me" ? reply(200, ME) : reply(200, { notes: [], plans: [], members: [], invitations: [] }));

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(console, "warn").mockImplementation(() => {});
});
afterEach(() => vi.unstubAllGlobals());

describe("App routing when signed out", () => {
  it.each(["/", "/billing", "/billing/done", "/settings", "/team", "/billing/mock-checkout"])("sends %s to /login", async (path) => {
    window.history.replaceState({}, "", path);
    signedOut();
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it.each([
    ["/signup", "Start your free trial"],
    ["/forgot-password", "Reset your password"],
    ["/reset-password?token=t", "Choose a new password"],
    ["/accept-invite?token=t", "Join your team"],
    ["/verify-email?token=t", "Confirm your email"],
    ["/privacy", "Privacy notice"],
    ["/terms", "Terms"],
  ])("serves the public page %s without redirecting", async (url, heading) => {
    window.history.replaceState({}, "", url);
    signedOut();
    render(<App />);
    expect(await screen.findByRole("heading", { name: new RegExp(heading, "i") })).toBeTruthy();
    expect(window.location.pathname).toBe(url.split("?")[0]);
  });

  it("serves /help signed out", async () => {
    window.history.replaceState({}, "", "/help");
    signedOut();
    render(<App />);
    expect(await screen.findByText("Is my data shared with other companies?")).toBeTruthy();
    expect(window.location.pathname).toBe("/help");
  });
});

describe("App when signed in", () => {
  it("shows the app shell with the tenant name and nav", async () => {
    window.history.replaceState({}, "", "/billing");
    signedIn();
    render(<App />);
    expect(await screen.findByText("Acme")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Billing" })).toBeTruthy();
    expect(await screen.findByText("Your plan")).toBeTruthy();
  });

  it("an expired session (not_signed_in from any API call) returns to sign-in", async () => {
    window.history.replaceState({}, "", "/billing");
    signedIn();
    render(<App />);
    await screen.findByText("Acme");
    await act(async () => { window.dispatchEvent(new Event(SESSION_ENDED)); });
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });

  it("sign out calls logout then returns to /login", async () => {
    window.history.replaceState({}, "", "/billing");
    signedIn();
    render(<App />);
    fetchMock.mockImplementation(async (path: string) => path === "/api/auth/logout" ? reply(204) : reply(200, { plans: [], notes: [] }));
    (await screen.findByRole("button", { name: "Sign out" })).click();
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    const logout = fetchMock.mock.calls.find((c) => c[0] === "/api/auth/logout")!;
    expect(logout[1].method).toBe("POST");
    expect(logout[1].headers["X-Requested-With"]).toBe("fetch");
  });

  it("a failed sign-out keeps the session and says so", async () => {
    window.history.replaceState({}, "", "/billing");
    signedIn();
    render(<App />);
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/api/auth/logout") throw new TypeError("Failed to fetch");
      return reply(200, { plans: [], notes: [] });
    });
    (await screen.findByRole("button", { name: "Sign out" })).click();
    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't sign you out/i);
    expect(window.location.pathname).toBe("/billing");
  });
});
