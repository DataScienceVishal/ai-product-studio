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
    await page.getByRole("heading", { name: "Tender packs" }).waitFor();

    step("the dashboard shows tender packs and no trial banner, prices, plans or billing link");
    assert.equal(await page.getByText("Free trial:").count(), 0);  // billing is off in the demo, so no trial countdown
    assert.equal(await page.getByRole("link", { name: "Billing" }).count(), 0);
    assert.doesNotMatch(await page.locator("body").innerText(), /£|upgrade|pricing|per month/i);
    assert.equal(await page.evaluate(async () => (await fetch("/api/billing/plans")).status), 404);

    step("sign out and back in");
    const email = await page.evaluate(async () => (await (await fetch("/api/auth/me")).json()).user.email);
    await page.getByRole("button", { name: "Sign out" }).click();
    await page.getByRole("heading", { name: "Sign in" }).waitFor();
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("a long enough passphrase");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.getByRole("heading", { name: "Tender packs" }).waitFor();

    step("a wrong password on delete shows an error and keeps you signed in");
    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByLabel("Your password").fill("not my password at all");
    await page.getByLabel("Type DELETE to confirm").fill("DELETE");
    await page.getByRole("button", { name: "Delete everything" }).click();
    await page.getByText("That password isn't right.").waitFor();
    assert.equal(await page.evaluate(async () => (await fetch("/api/auth/me")).status), 200);

    step("delete the account");
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
