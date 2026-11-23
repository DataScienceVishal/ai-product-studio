// End-to-end test of the starter's core flow in a real browser.
// Run through scripts/e2e.sh, which starts the API and the built frontend first.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

const BASE = process.env.E2E_BASE_URL || "http://127.0.0.1:4173";

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const step = (name) => console.log(`- ${name}`);
  try {
    step("sign up");
    await page.goto(`${BASE}/signup`);
    await page.getByLabel("Company name").fill("E2E Bakery Ltd");
    await page.getByLabel("Work email").fill(`owner+${Date.now()}@e2e.test`);
    await page.getByLabel("Password").fill("a long enough passphrase");
    await page.getByRole("button", { name: "Create account" }).click();
    await page.getByText("Free trial:").waitFor();

    step("empty state offers sample data, then a guided first task");
    await page.getByText("No notes yet.").waitFor();
    await page.getByRole("button", { name: "Add two sample notes" }).click();
    await page.getByText("Supplier price rise").waitFor();

    step("create a note and get an AI summary");
    await page.getByLabel("Title").fill("Oven repair");
    await page.getByLabel("Details").fill("The deck oven needs a new thermostat. Engineer can come Tuesday for 180 pounds.");
    await page.getByRole("button", { name: "Save note" }).click();
    const item = page.locator("li", { hasText: "Oven repair" });
    await item.waitFor();
    await item.getByRole("button", { name: "Summarise" }).click();
    const summary = item.getByTestId("summary");
    await summary.waitFor();
    assert.match(await summary.innerText(), /Summary:/);

    step("choose a plan with the early-customer offer and pay in test mode");
    await page.getByRole("link", { name: "Billing" }).click();
    await page.getByLabel("Offer code (optional)").fill("EARLY50");
    await page.getByRole("button", { name: "Choose Pro" }).click();
    await page.getByRole("button", { name: "Pay (test)" }).click();
    await page.getByText("Status: active").waitFor();
    await page.getByText("Offer: EARLY50").waitFor();

    step("sign out and back in");
    const email = await page.evaluate(async () => (await (await fetch("/api/auth/me")).json()).user.email);
    await page.getByRole("button", { name: "Sign out" }).click();
    await page.getByRole("heading", { name: "Sign in" }).waitFor();
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("a long enough passphrase");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.getByRole("heading", { name: "Oven repair" }).waitFor();

    step("delete the account");
    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByLabel("Your password").fill("a long enough passphrase");
    await page.getByLabel("Type DELETE to confirm").fill("DELETE");
    await page.getByRole("button", { name: "Delete everything" }).click();
    await page.getByRole("heading", { name: "Start your free trial" }).waitFor();
    const me = await page.evaluate(async () => (await fetch("/api/auth/me")).status);
    assert.equal(me, 401);

    assert.deepEqual(errors, [], `page errors: ${errors.join("; ")}`);
    console.log("E2E PASS: core flow");
  } catch (error) {
    await page.screenshot({ path: process.env.E2E_SCREENSHOT || "e2e-failure.png", fullPage: true }).catch(() => {});
    console.error("E2E FAIL:", error.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
