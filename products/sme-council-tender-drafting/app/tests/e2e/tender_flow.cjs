// End-to-end test of the 7 SPEC core-flow steps in a real browser, on ScriptedFakeAI (no model calls).
// Run through scripts/e2e.sh (needs AI_WORKER_THREADS>0 on the API and fixtures from make_fixtures.py in E2E_FIXTURES).
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const BASE = process.env.E2E_BASE_URL || "http://127.0.0.1:4173";
const FIX = process.env.E2E_FIXTURES;
const PYTHON = process.env.PYTHON || "python3";
const LONG = 90_000; // background tasks poll every 3 s

// Click a button that queues a background task and wait for the server to accept it (202), so the next page's
// first status read already sees the task and polls.
async function queueTask(page, buttonName, suffix) {
  await Promise.all([
    page.waitForResponse((r) => r.url().endsWith(suffix) && r.request().method() === "POST" && r.status() === 202),
    page.getByRole("button", { name: buttonName }).click(),
  ]);
}

// Wait until the pack has no queued or running background task.
async function waitIdle(page, packId) {
  const deadline = Date.now() + LONG;
  for (;;) {
    const s = await page.evaluate(async (id) => (await (await fetch(`/api/packs/${id}/status`)).json()), packId);
    if (!s.tasks.some((t) => t.status === "queued" || t.status === "running")) return s;
    if (Date.now() > deadline) throw new Error(`pack still busy: ${JSON.stringify(s.tasks)}`);
    await page.waitForTimeout(500);
  }
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(30_000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const step = (name) => console.log(`- ${name}`);
  try {
    step("1. sign up and sign in");
    await page.goto(`${BASE}/signup`);
    await page.getByLabel("Company name").fill("E2E Grounds Ltd");
    await page.getByLabel("Work email").fill(`tender+${Date.now()}@e2e.test`);
    await page.getByLabel("Password").fill("a long enough passphrase");
    await page.getByRole("button", { name: "Create account" }).click();
    await page.getByRole("heading", { name: "Tender packs" }).waitFor();

    step("1. create a pack and upload the tender document");
    await page.goto(`${BASE}/packs`);
    await page.getByLabel("Pack title").fill("Northfield grounds");
    await page.getByLabel("Buyer (council)").fill("Northfield Council");
    await page.getByLabel(/Tender document/).setInputFiles(path.join(FIX, "tender.docx"));
    await page.getByRole("button", { name: "Create pack" }).click();
    await page.getByRole("heading", { name: "Northfield grounds" }).waitFor();
    await page.getByText("tender.docx").first().waitFor();
    const packId = new URL(page.url()).searchParams.get("id");
    assert.ok(packId, `no pack id in ${page.url()}`);

    step("2. extract the checklist, then confirm it");
    await queueTask(page, "Find the requirements", "/extract");
    await page.getByRole("link", { name: "Review the checklist" }).click();
    await page.getByRole("heading", { name: "Checklist" }).waitFor();
    await page.getByRole("button", { name: "Confirm the checklist" }).waitFor({ timeout: LONG });
    assert.ok((await page.getByText(/safeguarding policy/i).count()) >= 1);
    assert.ok((await page.getByText(/social value/i).count()) >= 1);
    await page.getByRole("button", { name: "Confirm the checklist" }).click();
    await page.getByText(/Checklist confirmed \(2 items/).waitFor();

    step("3. upload evidence");
    await page.getByRole("link", { name: "Evidence", exact: true }).click();
    await page.getByRole("heading", { name: "Evidence library" }).waitFor();
    for (const name of ["evidence1.txt", "evidence2.txt"]) {
      await page.getByLabel(/^File/).setInputFiles(path.join(FIX, name));
      await page.getByRole("button", { name: "Upload" }).click();
      await page.getByText(name).first().waitFor();
    }

    step("4. draft answers");
    await page.getByRole("link", { name: "Tender packs" }).or(page.getByRole("link", { name: "Dashboard" })).first().click().catch(() => {});
    await page.goto(`${BASE}/packs`);
    await page.getByRole("link", { name: "Northfield grounds" }).click();
    await queueTask(page, "Draft the answers", "/draft");
    await waitIdle(page, packId);
    await page.reload();
    await page.getByRole("link", { name: "Open answer" }).first().click();
    await page.getByText(/\[E-\d+\]/).first().waitFor({ timeout: LONG });
    const answer = await page.locator("body").innerText();
    assert.match(answer, /42 staff/); // drafted from evidence1, not just the question text
    await page.goBack();

    step("5. claim check shows claims");
    await page.getByRole("button", { name: "Check the claims" }).waitFor();
    await queueTask(page, "Check the claims", "/check");
    await waitIdle(page, packId);
    await page.getByText("Ready to sign off").first().waitFor({ timeout: LONG }); // pack badge once the check task is done
    await page.getByRole("link", { name: "Open answer" }).first().click();
    await page.getByRole("columnheader", { name: "Verdict" }).waitFor({ timeout: LONG });
    const claims = await page.locator("body").innerText();
    assert.match(claims, /\bSupported\b/);
    assert.doesNotMatch(claims, /unsupported|contradicted|not checked/i);

    step("6. coverage and sign-off");
    await page.goBack();
    await page.getByRole("link", { name: "Coverage and sign-off" }).click();
    await page.getByRole("heading", { name: "Coverage and sign-off" }).waitFor();
    const statement = page.getByLabel("Responsibility statement");
    await statement.waitFor({ timeout: LONG });
    const cov = [];
    for (const n of [1, 2]) {
      const row = await page.getByTestId(`cov-${n}`).innerText();
      cov.push(row);
      assert.match(row, /Yes/, `cov-${n} not answered: ${row}`);
      assert.match(row, /\d+ \/ 150/, `cov-${n} words: ${row}`);
      assert.match(row, /\t0\t/, `cov-${n} gaps: ${row}`);
      assert.match(row, /Yes\s*$/, `cov-${n} not checked: ${row}`);
    }
    assert.match(cov[0], /safeguarding/i);
    assert.match(cov[1], /social value/i);
    const covText = await page.locator("body").innerText();  // the only "compliant" on the page is the disclaimer
    assert.match(covText, /It does not say the bid is compliant\./);
    assert.equal((covText.match(/compliant/gi) || []).length, 1);
    await page.getByLabel(/I have read this statement/).check();
    await page.getByLabel("Your full name").fill("Alex Reviewer");
    await page.getByRole("button", { name: "Sign off this pack" }).click();
    await page.getByRole("button", { name: "Export Word document" }).waitFor();

    step("7. export the Word file and check it");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export Word document" }).click(),
    ]);
    const target = path.join(FIX, "export.docx");
    await download.saveAs(target);
    assert.match(download.suggestedFilename(), /\.docx$/i);
    const check = `
import sys, zipfile, docx
p = sys.argv[1]
assert zipfile.ZipFile(p).testzip() is None
d = docx.Document(p)
body = "\\n".join(x.text for x in d.paragraphs)
header = "\\n".join(x.text for s in d.sections for x in s.header.paragraphs)
footer = "\\n".join(x.text for s in d.sections for x in s.footer.paragraphs)
rows = [[c.text for c in r.cells] for t in d.tables for r in t.rows]
print("HEADER:" + header)
print("FOOTER:" + footer)
print("BODY:" + body)
print("TABLEROWS:%d" % len(rows))
print("TABLE:" + " | ".join(" / ".join(r) for r in rows))
`;
    const out = execFileSync(PYTHON, ["-c", check, target], { encoding: "utf8" });
    assert.ok(out.includes("HEADER:Draft prepared with AI assistance; reviewed by Alex Reviewer"), "docx header missing");
    assert.match(out, /FOOTER:I understand that my firm, not the software, is responsible/, "docx footer missing");
    const body = out.split("BODY:")[1];
    const i42 = body.indexOf("42 staff"), i12 = body.indexOf("12 apprenticeships");
    assert.ok(i42 >= 0 && i12 > i42, "answers missing or out of order");
    assert.match(body, /\[E-\d+\]/);
    assert.match(body, /Appendix: claims and their sources/);
    assert.ok(Number(/TABLEROWS:(\d+)/.exec(out)[1]) >= 3, "claims appendix needs a header row and one row per claim");
    assert.match(out, /TABLE:Claim \/ Evidence \/ Document \/ Page \/ Supporting quote/, "appendix header row");
    assert.match(out, /\[E-\d+\] \/ evidence1\.txt \/ 1 \/ Our safeguarding policy/, "appendix row for the safeguarding claim");

    assert.deepEqual(errors, [], `page errors: ${errors.join("; ")}`);
    console.log("E2E PASS: tender core flow (7 steps)");
  } catch (error) {
    await page.screenshot({ path: process.env.E2E_SCREENSHOT || "e2e-tender-failure.png", fullPage: true }).catch(() => {});
    console.error("E2E FAIL:", error.message);
    console.error("URL:", page.url());
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
