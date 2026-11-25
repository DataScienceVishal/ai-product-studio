import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch, makeMe } from "../test-utils";
import { setBillingProviderForTest } from "../api";
import { Billing, BillingDone, MockCheckout, MockPortal } from "./app";

const PLANS = { plans: [{ id: "pro", name: "Pro", price_pence: 4900, currency: "gbp", interval: "month", ai_monthly_tokens: 1000000 }] };

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = stubFetch();
});
afterEach(() => {
  setBillingProviderForTest("");
  vi.useRealTimers();
});

describe("Billing: Manage billing", () => {
  it("owner sees the button; click POSTs the portal endpoint and goes to the returned url", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { url: "https://billing.stripe.example/p/session_1" }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://billing.stripe.example/p/session_1"));
    const [path, init] = fetchMock.mock.calls[1];
    expect(path).toBe("/api/billing/portal");
    expect(init.method).toBe("POST");
    expect(init.headers["X-Requested-With"]).toBe("fetch");  // the CSRF header, sent by the api helper
  });

  it("members do not see the button", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={makeMe({}, "member")} refresh={vi.fn()} />);
    await screen.findByText("£49.00");
    expect(screen.queryByRole("button", { name: "Manage billing" })).toBeNull();
  });

  it("shows the server error and re-enables the button when the portal fails", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(409, { error: "no_billing_customer", message: "No billing account yet." }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    expect((await screen.findByRole("alert")).textContent).toBe("No billing account yet.");
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Manage billing" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("is disabled while the request is pending", async () => {
    vi.stubGlobal("location", { ...window.location, assign: vi.fn() });
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockReturnValueOnce(new Promise(() => {}));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    const busy = await screen.findByRole("button", { name: "Working…" });
    expect((busy as HTMLButtonElement).disabled).toBe(true);
  });

  it("past_due message points owners at the button and members at the owner", async () => {
    fetchMock.mockImplementation(async () => reply(200, PLANS));  // a Response body can be read once
    const { unmount } = render(<Billing me={makeMe({ status: "past_due" })} refresh={vi.fn()} />);
    expect((await screen.findByRole("status")).textContent).toMatch(/Manage billing/);
    expect(screen.getByRole("button", { name: "Manage billing" })).toBeTruthy();
    unmount();
    render(<Billing me={makeMe({ status: "past_due" }, "member")} refresh={vi.fn()} />);
    expect((await screen.findByRole("status")).textContent).toMatch(/account owner/);
  });
});

describe("Billing", () => {
  it("lists plans with formatted prices and token allowance", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    expect(await screen.findByText("£49.00")).toBeTruthy();
    expect(screen.getByText(/1,000,000 AI tokens a month/)).toBeTruthy();
  });

  it("only owners can choose a plan", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={makeMe({}, "member")} refresh={vi.fn()} />);
    const button = await screen.findByRole("button", { name: "Choose Pro" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("a mock checkout goes to the in-app test page with the session id encoded", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { checkout_id: "mock_a&b", url: "https://unused.example" }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
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
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Choose Pro" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).offer_code).toBeNull();
  });

  it("shows the server error when checkout fails", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(400, { error: "bad_offer", message: "That offer code isn't valid." }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
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

describe("MockPortal (/billing/mock-portal)", () => {
  beforeEach(() => setBillingProviderForTest("mock"));

  it.each(["stripe", ""])("renders no attacker text and no customer ref when billing is %j", (provider) => {
    setBillingProviderForTest(provider);
    const spoof = "Payment failed - call 0800 000 000";
    window.history.replaceState({}, "", `/billing/mock-portal?customer=${encodeURIComponent(spoof)}`);
    const { container } = render(<MockPortal />);
    expect(container.textContent).not.toContain("0800");
    expect(screen.queryByText(/Mock billing portal/)).toBeNull();
    expect(screen.getByText("Page not found")).toBeTruthy();
  });

  it("says it is the mock portal, shows the customer ref and links back to billing", () => {
    window.history.replaceState({}, "", "/billing/mock-portal?customer=mock_cus_42");
    render(<MockPortal />);
    expect(screen.getByRole("heading", { name: "Mock billing portal" })).toBeTruthy();
    expect(screen.getByText("mock_cus_42")).toBeTruthy();
    const link = screen.getByRole("link", { name: "Back to billing" });
    fireEvent.click(link);
    expect(window.location.pathname).toBe("/billing");
  });

  it("renders a hostile ?customer= as literal text, never as markup", () => {
    const hostile = "<img src=x onerror=alert(1)>";
    window.history.replaceState({}, "", `/billing/mock-portal?customer=${encodeURIComponent(hostile)}`);
    const { container } = render(<MockPortal />);
    expect(screen.getByText(hostile)).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
  });
});

describe("Billing: unsafe redirects and unverified owners", () => {
  it("refuses a javascript: portal url, shows an error and re-enables the button", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { url: "javascript:alert(1)" }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/unexpected billing link/i);
    expect(assign).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Manage billing" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("refuses an http://evil checkout url", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { checkout_id: "cs_1", url: "http://evil.example/pay" }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Choose Pro" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/unexpected billing link/i);
    expect(assign).not.toHaveBeenCalled();
  });

  it("disables Manage billing with a hint when the owner's email is unverified", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    const me = makeMe();
    me.user.email_verified = false;
    render(<Billing me={me} refresh={vi.fn()} />);
    const button = (await screen.findByRole("button", { name: "Manage billing" })) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(screen.getByText("Verify your email to manage billing")).toBeTruthy();
  });

  it("shows no hint for a verified owner", async () => {
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    await screen.findByRole("button", { name: "Manage billing" });
    expect(screen.queryByText(/verify your email/i)).toBeNull();
  });
});

describe("Billing: mock portal in-app navigation", () => {
  it.each(["http://localhost:5173/billing/mock-portal?customer=mock_cus_9", "/billing/mock-portal?customer=mock_cus_9"])(
    "navigates in-app for %s without a full-page redirect, whatever the origin", async (url) => {
      const assign = vi.fn();
      vi.stubGlobal("location", { origin: "http://localhost:4173", assign });  // vite preview, not APP_BASE_URL's origin
      const push = vi.spyOn(window.history, "pushState");
      fetchMock.mockResolvedValueOnce(reply(200, PLANS));
      fetchMock.mockResolvedValueOnce(reply(200, { url }));
      render(<Billing me={makeMe()} refresh={vi.fn()} />);
      fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
      await waitFor(() => expect(push).toHaveBeenCalledWith({}, "", "/billing/mock-portal?customer=mock_cus_9"));
      expect(assign).not.toHaveBeenCalled();
    });

  it("maps a hostile-origin https url to the in-app path only, dropping origin and hash", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { origin: "http://localhost:4173", assign });
    const push = vi.spyOn(window.history, "pushState");
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { url: "https://evil.example/billing/mock-portal?customer=mock_cus_9#x" }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith({}, "", "/billing/mock-portal?customer=mock_cus_9"));
    expect(assign).not.toHaveBeenCalled();
  });

  it.each([
    "javascript:/billing/mock-portal?customer=mock_cus_9",
    "data:/billing/mock-portal?customer=mock_cus_9",
    "blob:/billing/mock-portal?customer=mock_cus_9",
  ])("does not treat %s as the mock portal: refused, no navigation", async (url) => {
    const assign = vi.fn();
    vi.stubGlobal("location", { origin: "http://localhost:4173", assign });
    const push = vi.spyOn(window.history, "pushState");
    fetchMock.mockResolvedValueOnce(reply(200, PLANS));
    fetchMock.mockResolvedValueOnce(reply(200, { url }));
    render(<Billing me={makeMe()} refresh={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Manage billing" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/unexpected billing link/i);
    expect(push).not.toHaveBeenCalled();
    expect(assign).not.toHaveBeenCalled();
  });
});

describe("Billing: email verification gate (REQUIRE_EMAIL_VERIFICATION)", () => {
  const meWith = (required: boolean, verified: boolean) => {
    const me = makeMe();
    me.user.email_verification_required = required;
    me.user.email_verified = verified;
    return me;
  };
  const disabled = (name: string) => (screen.getByRole("button", { name }) as HTMLButtonElement).disabled;

  it("required and unverified: both Manage billing and Choose are disabled, with the hint", async () => {
    fetchMock.mockResolvedValue(reply(200, PLANS));
    render(<Billing me={meWith(true, false)} refresh={vi.fn()} />);
    await screen.findByRole("button", { name: "Choose Pro" });
    expect(disabled("Manage billing")).toBe(true);
    expect(disabled("Choose Pro")).toBe(true);
    expect(screen.getByText("Verify your email to manage billing")).toBeTruthy();
  });

  it.each([[true, true], [false, false], [false, true]])(
    "required=%s verified=%s: both buttons enabled and no hint", async (required, verified) => {
      fetchMock.mockResolvedValue(reply(200, PLANS));
      render(<Billing me={meWith(required, verified)} refresh={vi.fn()} />);
      await screen.findByRole("button", { name: "Choose Pro" });
      expect(disabled("Manage billing")).toBe(false);
      expect(disabled("Choose Pro")).toBe(false);
      expect(screen.queryByText(/verify your email/i)).toBeNull();
    });
});

describe("BillingDone (/billing/done)", () => {
  it("shows success once the subscription is active", () => {
    render(<BillingDone me={makeMe({ plan: "pro", status: "active" })} refresh={vi.fn()} />);
    expect(screen.getByRole("status").textContent).toMatch(/you're on the pro plan/i);
  });

  it("polls refresh every 2s while waiting, then gives up with a clear message after 15 tries", async () => {
    vi.useFakeTimers();
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<BillingDone me={makeMe()} refresh={refresh} />);
    expect(screen.getByText(/confirming your payment/i)).toBeTruthy();
    for (let i = 0; i < 15; i++) await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(refresh).toHaveBeenCalledTimes(15);
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(refresh).toHaveBeenCalledTimes(15);
    expect(screen.getByRole("alert").textContent).toMatch(/haven't had confirmation/i);
  });
});
