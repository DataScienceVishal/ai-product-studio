import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch, ME } from "./test-utils";
import App from "./App";
import { SESSION_ENDED, setBillingEnabledForTest } from "./api";
import { SIGN_IN_PAGES } from "./pages/auth";

let fetchMock: ReturnType<typeof vi.fn>;
const signedOut = () => fetchMock.mockImplementation(async () => reply(401, { error: "not_signed_in", message: "Sign in." }));
const signedIn = () => fetchMock.mockImplementation(async (path: string) =>
  path === "/api/auth/me" ? reply(200, ME) : reply(200, { plans: [], members: [], invitations: [] }));

beforeEach(() => {
  setBillingEnabledForTest(true); // billing pages are tested with the flag on; the flag-off tests set it false
  fetchMock = stubFetch();
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

describe("App routing when signed out", () => {
  it.each(["/", "/billing", "/billing/done", "/settings", "/team", "/billing/mock-checkout"])("sends %s to /login", async (path) => {
    window.history.replaceState({}, "", path);
    signedOut();
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("redirects to /login with replaceState, not pushState", async () => {
    window.history.replaceState({}, "", "/billing");
    signedOut();
    const push = vi.spyOn(window.history, "pushState");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(push).not.toHaveBeenCalled();
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
    fetchMock.mockImplementation(async (path: string) => path === "/api/auth/logout" ? reply(204) : reply(200, { plans: [] }));
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
      return reply(200, { plans: [] });
    });
    (await screen.findByRole("button", { name: "Sign out" })).click();
    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't sign you out/i);
    expect(window.location.pathname).toBe("/billing");
  });
});

describe("App routing when signed in (T-87)", () => {
  const signedInWithItems = () => fetchMock.mockImplementation(async (path: string) =>
    path === "/api/auth/me" ? reply(200, ME) : reply(200, { items: [], total: 0 }));

  it.each(["/login", "/signup"])("sends %s to the dashboard", async (path) => {
    window.history.replaceState({}, "", path);
    signedInWithItems();
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
    expect(screen.queryByRole("heading", { name: /start your free trial/i })).toBeNull();
  });

  it("redirects /login and /signup with replaceState, not pushState (no Back bounce)", async () => {
    window.history.replaceState({}, "", "/login");
    signedInWithItems();
    const push = vi.spyOn(window.history, "pushState");
    const replace = vi.spyOn(window.history, "replaceState");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(replace).toHaveBeenCalledWith({}, "", "/");
    expect(push).not.toHaveBeenCalled();
  });

  it("sends a signed-in user on /login?next=/billing to /billing", async () => {
    window.history.replaceState({}, "", "/login?next=/billing");
    signedIn(); // the Billing page needs plans in its replies
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/billing"));
  });

  it("ignores an unsafe ?next= when signed in", async () => {
    window.history.replaceState({}, "", "/login?next=//evil.com");
    signedInWithItems();
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/"));
  });

  it.each([...SIGN_IN_PAGES])("sends a signed-in user away from %s (App.tsx signInPage matches SIGN_IN_PAGES)", async (page) => {
    window.history.replaceState({}, "", page);
    signedInWithItems();
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(await screen.findByRole("heading", { name: "Tender packs" })).toBeTruthy();
  });

  it.each(["/login?next=/login", "/login?next=/signup", "/signup?next=/login/", "/login?next=%2Flogin%3Fnext%3D%2F%2Fevil.com"])(
    "sends a signed-in user on %s home instead of a blank sign-in page", async (url) => {
      window.history.replaceState({}, "", url);
      signedInWithItems();
      render(<App />);
      await waitFor(() => expect(window.location.pathname).toBe("/"));
      expect(window.location.search).toBe("");
      expect(await screen.findByRole("heading", { name: "Tender packs" })).toBeTruthy(); // the dashboard renders, not a blank page
    });

  it("shows Page not found with a link home for an unknown path, and keeps the URL", async () => {
    window.history.replaceState({}, "", "/does-not-exist");
    signedInWithItems();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
    expect(window.location.pathname).toBe("/does-not-exist");
    expect(screen.getByRole("link", { name: /go to your tender packs/i }).getAttribute("href")).toBe("/");
  });

  it("still shows the dashboard at /", async () => {
    window.history.replaceState({}, "", "/");
    signedInWithItems();
    render(<App />);
    expect(await screen.findByRole("heading", { name: /tender packs/i })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Page not found" })).toBeNull();
  });
});

describe("App with prices off (billing_enabled false, T-185)", () => {
  beforeEach(() => setBillingEnabledForTest(false));
  const signedInNoBilling = () => fetchMock.mockImplementation(async (path: string) =>
    path === "/api/auth/me" ? reply(200, ME) : reply(200, {}));

  it.each(["/billing", "/billing/done", "/billing/mock-checkout", "/billing/mock-portal"])("%s is Page not found", async (path) => {
    window.history.replaceState({}, "", path);
    signedInNoBilling();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
    expect(fetchMock.mock.calls.some((c) => String(c[0]).startsWith("/api/billing"))).toBe(false);
  });

  it("shows no trial countdown and no billing words in the privacy notice", async () => {
    window.history.replaceState({}, "", "/privacy");
    signedInNoBilling();
    render(<App />);
    await screen.findByRole("heading", { name: "Privacy notice (DRAFT)" });
    expect(document.body.textContent).not.toMatch(/\bplan\b|bill you|payment provider/i);
    cleanup();
    window.history.replaceState({}, "", "/");
    render(<App />);
    await screen.findByRole("heading", { name: "Tender packs" });
    expect(document.body.textContent).not.toMatch(/free trial:|choose a plan/i);
  });

  it("shows no Billing link, plan or price text on the dashboard", async () => {
    window.history.replaceState({}, "", "/");
    signedInNoBilling();
    render(<App />);
    await screen.findByRole("heading", { name: "Tender packs" });
    expect(screen.queryByRole("link", { name: "Billing" })).toBeNull();
    expect(document.body.textContent).not.toMatch(/£|\bplans?\b|upgrade|pricing|per month/i);
  });
});
