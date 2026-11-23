import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Link, navigate, takeToken, usePath } from "./ui";
import { safeNext } from "./pages/auth";

const at = (url: string) => window.history.replaceState({}, "", url);

describe("safeNext (?next= redirect after sign-in)", () => {
  it("defaults to home when there is no next", () => {
    at("/login");
    expect(safeNext()).toBe("/");
  });

  it.each([
    ["/billing", "/billing"],
    ["/verify-email?token=abc", "/verify-email?token=abc"],
    ["/billing/done?x=1", "/billing/done?x=1"],
  ])("allows the same-site path %s", (next, expected) => {
    at(`/login?next=${encodeURIComponent(next)}`);
    expect(safeNext()).toBe(expected);
  });

  it.each([
    "//evil.example",
    "//evil.example/path",
    "/\\evil.example",
    "/\\/evil.example",
    "\\\\evil.example",
    "\\evil.example",
    "https://evil.example",
    "http://evil.example/x",
    "HTTPS://evil.example",
    "javascript:alert(1)",
    "data:text/html,hi",
    "evil.example",
    "billing",
    " //evil.example",
    "/\t/evil.example",
    "/\n/evil.example",
    "",
  ])("rejects %j and falls back to home", (next) => {
    at(`/login?next=${encodeURIComponent(next)}`);
    expect(safeNext()).toBe("/");
  });

  it("never resolves outside the current origin, whatever is passed", () => {
    for (const next of ["//evil.example", "/\\evil.example", "https://evil.example", "/\t/evil.example", "/%2F/evil.example", "/%5Cevil.example"]) {
      at(`/login?next=${encodeURIComponent(next)}`);
      const url = new URL(safeNext(), window.location.origin);
      expect(url.origin).toBe(window.location.origin);
    }
  });
});

describe("takeToken (email-link secrets)", () => {
  it("reads the token and removes it from the address bar, keeping other params", () => {
    at("/reset-password?token=s3cret&utm=1");
    expect(takeToken()).toBe("s3cret");
    expect(window.location.search).toBe("?utm=1");
    expect(window.location.pathname).toBe("/reset-password");
  });

  it.each(["/verify-email", "/reset-password", "/accept-invite"])("clears the whole query on %s when the token is the only param", (path) => {
    at(`${path}?token=abc`);
    expect(takeToken()).toBe("abc");
    expect(window.location.search).toBe("");
    expect(window.location.pathname).toBe(path);
  });

  it("returns an empty string when there is no token", () => {
    at("/accept-invite");
    expect(takeToken()).toBe("");
  });
});

describe("history router", () => {
  it("usePath follows navigate()", () => {
    at("/");
    const { result } = renderHook(() => usePath());
    expect(result.current).toBe("/");
    act(() => navigate("/billing/done"));
    expect(result.current).toBe("/billing/done");
    expect(window.location.pathname).toBe("/billing/done");
  });

  it("Link navigates without a page load on a plain click", () => {
    at("/");
    render(<Link to="/team">Team</Link>);
    const link = screen.getByText("Team");
    expect(link.getAttribute("href")).toBe("/team");
    expect(fireEvent.click(link)).toBe(false); // default prevented
    expect(window.location.pathname).toBe("/team");
  });

  it.each([{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { button: 1 }])("Link leaves modified click %j to the browser", (mods) => {
    at("/");
    render(<Link to="/team">Team</Link>);
    expect(fireEvent.click(screen.getByText("Team"), mods)).toBe(true);
    expect(window.location.pathname).toBe("/");
  });
});
