import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Me } from "../api";
import { AcceptInvite } from "./team";
import { ForgotPassword, ResetPassword, SignIn, SignUp, VerifyEmail } from "./auth";

const ME: Me = {
  user: { id: "u1", email: "a@example.com", role: "owner", email_verified: true },
  tenant: { id: "t1", name: "Acme" },
  subscription: { plan: "trial", status: "trialing", offer: null, trial_ends_at: null, current_period_end: null },
};

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const type = (label: string | RegExp, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const lastBody = () => JSON.parse(fetchMock.mock.calls.at(-1)![1].body);

describe("SignIn", () => {
  it("posts the credentials, hands over the session and goes home", async () => {
    fetchMock.mockResolvedValue(reply(200, ME));
    const onSignedIn = vi.fn();
    render(<SignIn onSignedIn={onSignedIn} />);
    type("Email", "a@example.com");
    type("Password", "correct horse battery");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(ME));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/login");
    expect(lastBody()).toEqual({ email: "a@example.com", password: "correct horse battery" });
    expect(window.location.pathname).toBe("/");
  });

  it("follows a safe ?next= after signing in", async () => {
    window.history.replaceState({}, "", `/login?next=${encodeURIComponent("/verify-email?token=t1")}`);
    fetchMock.mockResolvedValue(reply(200, ME));
    render(<SignIn onSignedIn={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(window.location.pathname).toBe("/verify-email"));
    expect(window.location.search).toBe("?token=t1");
  });

  it.each(["//evil.example", "/\\evil.example", "https://evil.example"])("ignores the hostile ?next=%s", async (next) => {
    window.history.replaceState({}, "", `/login?next=${encodeURIComponent(next)}`);
    fetchMock.mockResolvedValue(reply(200, ME));
    render(<SignIn onSignedIn={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(window.location.hostname).not.toContain("evil");
  });

  it("shows the server's message on a wrong password and does not sign in", async () => {
    fetchMock.mockResolvedValue(reply(401, { error: "invalid_credentials", message: "Email or password is wrong." }));
    const onSignedIn = vi.fn();
    render(<SignIn onSignedIn={onSignedIn} />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Email or password is wrong.");
    expect(onSignedIn).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy(); // not stuck on "Working…"
  });

  it("shows a friendly message when the network is down", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    render(<SignIn onSignedIn={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/can't reach the server/i);
  });

  it("disables the button while the request is in flight", async () => {
    let finish: (r: Response) => void = () => {};
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => { finish = resolve; }));
    render(<SignIn onSignedIn={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    const busy = await screen.findByRole("button", { name: "Working…" });
    expect((busy as HTMLButtonElement).disabled).toBe(true);
    finish(reply(401, { error: "invalid_credentials", message: "No." }));
    await screen.findByRole("alert");
  });
});

describe("SignUp", () => {
  it("posts company, email and password and signs the new user in", async () => {
    fetchMock.mockResolvedValue(reply(201, ME));
    const onSignedIn = vi.fn();
    render(<SignUp onSignedIn={onSignedIn} />);
    type("Company name", "Acme Ltd");
    type("Work email", "boss@acme.example");
    type("Password", "a-long-password");
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(ME));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/signup");
    expect(lastBody()).toEqual({ company_name: "Acme Ltd", email: "boss@acme.example", password: "a-long-password" });
  });

  it("shows the server's field problems joined as one message (short password, bad email)", async () => {
    fetchMock.mockResolvedValue(reply(422, {
      error: "validation", message: "Please fix the highlighted fields.",
      fields: [{ field: "email", problem: "Enter a valid email." }, { field: "password", problem: "Use at least 10 characters." }],
    }));
    const onSignedIn = vi.fn();
    render(<SignUp onSignedIn={onSignedIn} />);
    type("Password", "short");
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Enter a valid email. Use at least 10 characters.");
    expect(onSignedIn).not.toHaveBeenCalled();
  });

  it("states the password rule next to the field and marks fields required", () => {
    render(<SignUp onSignedIn={vi.fn()} />);
    const password = screen.getByLabelText("Password") as HTMLInputElement;
    expect(password.type).toBe("password");
    expect(password.required).toBe(true);
    expect(password.autocomplete).toBe("new-password");
    expect(document.getElementById(password.getAttribute("aria-describedby")!)!.textContent).toMatch(/at least 10 characters/i);
    expect((screen.getByLabelText("Work email") as HTMLInputElement).type).toBe("email");
  });

  it("clears an earlier error on the next attempt", async () => {
    fetchMock.mockResolvedValueOnce(reply(409, { error: "taken", message: "That email is already registered." }));
    fetchMock.mockResolvedValueOnce(reply(201, ME));
    render(<SignUp onSignedIn={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });
});

describe("ForgotPassword", () => {
  it("shows the same non-revealing confirmation after sending", async () => {
    fetchMock.mockResolvedValue(reply(204));
    render(<ForgotPassword />);
    type("Email", "a@example.com");
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect((await screen.findByRole("status")).textContent).toMatch(/if that email has an account/i);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/password-reset/request");
    expect(lastBody()).toEqual({ email: "a@example.com" });
  });
});

describe("ResetPassword (/reset-password?token=)", () => {
  it("takes the token from the URL, strips it from the address bar and sends it with the new password", async () => {
    window.history.replaceState({}, "", "/reset-password?token=tok123");
    fetchMock.mockResolvedValue(reply(204));
    render(<ResetPassword />);
    expect(window.location.search).toBe("");
    type("New password", "brand-new-password");
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect((await screen.findByRole("status")).textContent).toMatch(/password changed/i);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/password-reset/confirm");
    expect(lastBody()).toEqual({ token: "tok123", new_password: "brand-new-password" });
  });

  it("blocks submit and explains when the link has no token", () => {
    window.history.replaceState({}, "", "/reset-password");
    render(<ResetPassword />);
    expect(screen.getByRole("alert").textContent).toMatch(/incomplete/i);
    expect((screen.getByRole("button", { name: "Save new password" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows an expired-link error from the server", async () => {
    window.history.replaceState({}, "", "/reset-password?token=old");
    fetchMock.mockResolvedValue(reply(400, { error: "invalid_token", message: "This link has expired." }));
    render(<ResetPassword />);
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect((await screen.findByRole("alert")).textContent).toBe("This link has expired.");
  });
});

describe("AcceptInvite (/accept-invite?token=)", () => {
  it("sends token and chosen password, then signs in", async () => {
    window.history.replaceState({}, "", "/accept-invite?token=inv1");
    fetchMock.mockResolvedValue(reply(200, ME));
    const onSignedIn = vi.fn();
    render(<AcceptInvite onSignedIn={onSignedIn} />);
    expect(window.location.search).toBe("");
    type("Choose a password", "my-new-password");
    fireEvent.click(screen.getByRole("button", { name: "Join" }));
    await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith(ME));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/invitations/accept");
    expect(lastBody()).toEqual({ token: "inv1", password: "my-new-password" });
  });

  it("disables Join when the link has no token", () => {
    window.history.replaceState({}, "", "/accept-invite");
    render(<AcceptInvite onSignedIn={vi.fn()} />);
    expect((screen.getByRole("button", { name: "Join" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("alert").textContent).toMatch(/incomplete/i);
  });
});

describe("VerifyEmail (/verify-email?token=)", () => {
  it("signed out: does not call the API and sends the user to sign in with a safe next that keeps the token", () => {
    window.history.replaceState({}, "", "/verify-email?token=a%26b");
    render(<VerifyEmail me={null} onVerified={vi.fn()} />);
    expect(fetchMock).not.toHaveBeenCalled();
    const link = screen.getByText("Sign in to confirm").getAttribute("href")!;
    expect(link.startsWith("/login?next=")).toBe(true);
    const next = new URLSearchParams(link.split("?")[1]).get("next")!;
    expect(next).toBe("/verify-email?token=a%26b");
  });

  it("signed in: verifies once and refreshes the session", async () => {
    window.history.replaceState({}, "", "/verify-email?token=v1");
    fetchMock.mockResolvedValue(reply(204));
    const onVerified = vi.fn().mockResolvedValue(undefined);
    render(<VerifyEmail me={ME} onVerified={onVerified} />);
    expect((await screen.findByRole("status")).textContent).toMatch(/email is confirmed/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(lastBody()).toEqual({ token: "v1" });
    expect(onVerified).toHaveBeenCalledTimes(1);
  });

  it("signed in with a bad link: shows the server error", async () => {
    window.history.replaceState({}, "", "/verify-email?token=bad");
    fetchMock.mockResolvedValue(reply(400, { error: "invalid_token", message: "This link is no longer valid." }));
    render(<VerifyEmail me={ME} onVerified={vi.fn()} />);
    expect((await screen.findByRole("alert")).textContent).toBe("This link is no longer valid.");
  });

  it("signed in with no token: fails without calling the API", async () => {
    window.history.replaceState({}, "", "/verify-email");
    render(<VerifyEmail me={ME} onVerified={vi.fn()} />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/incomplete/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
