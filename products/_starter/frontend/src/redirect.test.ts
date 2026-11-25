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
    expect(assign).toHaveBeenCalledWith("/billing/mock-portal?customer=mock_cus_1");
  });
  it("follows a same-origin absolute URL (mock base_url in dev)", () => {
    expect(safeRedirect("http://localhost:3000/billing/mock-portal")).toBe(true);
  });
  it.each(["javascript:alert(1)", "http://evil.example/x", "//evil.example/x", "data:text/html,hi"])(
    "refuses %j and does not navigate", (url) => {
      expect(safeRedirect(url)).toBe(false);
      expect(assign).not.toHaveBeenCalled();
    });
});
