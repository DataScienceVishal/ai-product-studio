// Shared steps for the e2e scenarios (tender_refusal.cjs, tender_limits.cjs, tender_unicode.cjs). Real browser, ScriptedFakeAI.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const BASE = process.env.E2E_BASE_URL || "http://127.0.0.1:4173";
const FIX = process.env.E2E_FIXTURES;
const PYTHON = process.env.PYTHON || "python3";
const LONG = 90_000; // background tasks poll every 3 s

// Click a button that queues a background task and wait for the server to accept it (202).
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

// Call the API from the signed-in page (cookie session). Returns {status, json}.
async function call(page, method, url, body) {
  return page.evaluate(async ([m, u, b]) => {
    const r = await fetch(u, { method: m, headers: b ? { "Content-Type": "application/json", "X-Requested-With": "fetch" } : { "X-Requested-With": "fetch" }, body: b ? JSON.stringify(b) : undefined });
    let json = null;
    try { json = await r.json(); } catch { /* no body */ }
    return { status: r.status, json };
  }, [method, url, body]);
}

// Upload an evidence file through the API (the UI path is covered by tender_flow.cjs; this keeps big fixtures quick).
async function uploadEvidence(page, file) {
  const text = fs.readFileSync(file, "utf8");
  const r = await page.evaluate(async ([name, content]) => {
    const form = new FormData();
    form.append("file", new File([content], name, { type: "text/plain" }));
    form.append("category", "policy");
    const res = await fetch("/api/evidence/documents", { method: "POST", body: form, headers: { "X-Requested-With": "fetch" } });
    return res.status;
  }, [path.basename(file), text]);
  assert.equal(r, 201, `evidence upload of ${file} gave ${r}`);
}

async function signUp(page, company) {
  await page.goto(`${BASE}/signup`);
  await page.getByLabel("Company name").fill(company);
  await page.getByLabel("Work email").fill(`tender+${Date.now()}${Math.floor(Math.random() * 1e6)}@e2e.test`);
  await page.getByLabel("Password").fill("a long enough passphrase");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByRole("heading", { name: "Tender packs" }).waitFor();
}

// Create a pack with the tender file, extract and confirm the checklist. Returns the pack id.
async function createConfirmedPack(page, title, tenderFile, expectedItems) {
  await page.goto(`${BASE}/packs`);
  await page.getByLabel("Pack title").fill(title);
  await page.getByLabel("Buyer (council)").fill("Northfield Council");
  await page.getByLabel(/Tender document/).setInputFiles(tenderFile);
  await page.getByRole("button", { name: "Create pack" }).click();
  await page.getByRole("heading", { name: title }).waitFor();
  const packId = new URL(page.url()).searchParams.get("id");
  assert.ok(packId, `no pack id in ${page.url()}`);
  await page.getByText(path.basename(tenderFile)).first().waitFor();
  await queueTask(page, "Find the requirements", "/extract");
  await page.getByRole("link", { name: "Review the checklist" }).click();
  await page.getByRole("button", { name: "Confirm the checklist" }).waitFor({ timeout: LONG });
  await page.getByRole("button", { name: "Confirm the checklist" }).click();
  await page.getByText(new RegExp(`Checklist confirmed \\(${expectedItems} items`)).waitFor();
  return packId;
}

async function draftAll(page, packId) {
  await page.goto(`${BASE}/pack?id=${packId}`);
  await queueTask(page, "Draft the answers", "/draft");
  await waitIdle(page, packId);
}

async function checkAll(page, packId) {
  await page.goto(`${BASE}/pack?id=${packId}`);
  await queueTask(page, "Check the claims", "/check");
  await waitIdle(page, packId);
}

// Read the docx at `file` with python-docx and return {header, footer, body, rows}.
function readDocx(file) {
  const code = `
import sys, json, zipfile, docx
p = sys.argv[1]
assert zipfile.ZipFile(p).testzip() is None
d = docx.Document(p)
print(json.dumps({
  "header": "\\n".join(x.text for s in d.sections for x in s.header.paragraphs),
  "footer": "\\n".join(x.text for s in d.sections for x in s.footer.paragraphs),
  "body": "\\n".join(x.text for x in d.paragraphs),
  "rows": [[c.text for c in r.cells] for t in d.tables for r in t.rows],
}, ensure_ascii=False))
`;
  return JSON.parse(execFileSync(PYTHON, ["-I", "-c", code, file], { encoding: "utf8" }));
}

// Run one scenario: fresh browser, page-error capture, screenshot on failure.
async function runScenario(name, fn) {
  const { chromium } = require("playwright");
  const browser = await chromium.launch();
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(30_000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const step = (s) => console.log(`- ${s}`);
  try {
    await fn({ page, context, step, errors });
    assert.deepEqual(errors, [], `page errors: ${errors.join("; ")}`);
    console.log(`E2E PASS: ${name}`);
  } catch (error) {
    const shot = (process.env.E2E_SCREENSHOT || "e2e-failure.png").replace(/\.png$/, `-${name.replace(/\W+/g, "_")}.png`);
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    console.error(`E2E FAIL (${name}):`, error.message);
    console.error("URL:", page.url());
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

module.exports = { BASE, FIX, LONG, queueTask, waitIdle, call, uploadEvidence, signUp, createConfirmedPack, draftAll, checkAll, readDocx, runScenario };
