import { beforeEach, describe, expect, it, vi } from "vitest";
import { safeRedirect } from "./redirect";

let assign: ReturnType<typeof vi.fn>;
beforeEach(() => {
  assign = vi.fn();
  vi.stubGlobal("location", { origin: "http://localhost:3000", assign });
});

describe("safeRedirect", () => {
  it("follows an https URL", () => {
    expect(safeRedirect("https://billing.stripe.example/p/1")).toBe(true);
    expect(assign).toHaveBeenCalledWith("https://billing.stripe.example/p/1");
  });
  it("follows a same-origin path (the mock)", () => {
    expect(safeRedirect("/billing/mock-portal?customer=mock_cus_1")).toBe(true);
    expect(assign).toHaveBeenCalledWith("http://localhost:3000/billing/mock-portal?customer=mock_cus_1");
  });
  it("follows a same-origin absolute URL (mock base_url in dev)", () => {
    expect(safeRedirect("http://localhost:3000/billing/mock-portal")).toBe(true);
  });
  it.each(["javascript:alert(1)", "http://evil.example/x", "//evil.example/x", "data:text/html,hi"])(
    "refuses %j on an http origin and does not navigate", (url) => {
      // "//evil.example/x" is refused only because this origin is http: it inherits http and is another origin.
      expect(safeRedirect(url)).toBe(false);
      expect(assign).not.toHaveBeenCalled();
    });
  it("navigates to the parsed, normalised href, not the raw string", () => {
    expect(safeRedirect("HTTPS://Billing.Stripe.Example:443/p/1")).toBe(true);
    expect(assign).toHaveBeenCalledWith("https://billing.stripe.example/p/1");
    expect(safeRedirect("/billing/mock-portal?customer=a b")).toBe(true);
    expect(assign).toHaveBeenLastCalledWith("http://localhost:3000/billing/mock-portal?customer=a%20b");
  });
});

describe("safeRedirect on an https origin (production)", () => {
  beforeEach(() => {
    vi.stubGlobal("location", { origin: "https://app.example.com", assign });
  });
  // Scheme guarantee only: protocol-relative and backslash URLs inherit https, so they are followed like any https URL.
  it.each([
    ["//evil.example", "https://evil.example/"],
    ["/\\evil.example", "https://evil.example/"],
    ["\\\\evil.example", "https://evil.example/"],
  ])("follows %j as %s", (url, href) => {
    expect(safeRedirect(url)).toBe(true);
    expect(assign).toHaveBeenCalledWith(href);
  });
  it.each([
    "JAVASCRIPT:alert(1)",
    " javascript:alert(1)",
    "java\tscript:alert(1)",
    "\u0000javascript:alert(1)",
    "http:evil.example",
    "http://evil.example/x",
    "data:text/html,hi",
  ])("refuses %j and does not navigate", (url) => {
    expect(safeRedirect(url)).toBe(false);
    expect(assign).not.toHaveBeenCalled();
  });
});
