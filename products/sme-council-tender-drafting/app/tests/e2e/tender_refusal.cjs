// E2E: the export is refused in the browser, with a clear message and no file, when the sign-off is missing, voided by a
// reopen and an edit, or the cited evidence was removed. Runs on ScriptedFakeAI through scripts/e2e.sh.
const assert = require("node:assert/strict");
const path = require("node:path");
const h = require("./helpers.cjs");

h.runScenario("tender export refused", async ({ page, context, step }) => {
  const downloads = [];
  page.on("download", (d) => downloads.push(d.suggestedFilename()));

  step("setup: a drafted and checked pack");
  await h.signUp(page, "Refusal Grounds Ltd");
  const packId = await h.createConfirmedPack(page, "Refusal pack", path.join(h.FIX, "tender.docx"), 2);
  await page.goto(`${h.BASE}/evidence`);
  await page.getByRole("heading", { name: "Evidence library" }).waitFor();
  for (const name of ["evidence1.txt", "evidence2.txt"]) await h.uploadEvidence(page, path.join(h.FIX, name));
  await h.draftAll(page, packId);
  await h.checkAll(page, packId);

  step("1. before sign-off there is no export button, and the API refuses");
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  assert.equal(await page.getByRole("button", { name: "Export Word document" }).count(), 0, "export offered before sign-off");
  assert.equal(await page.getByRole("button", { name: "Sign off this pack" }).isDisabled(), true, "sign-off enabled before the tick and name");
  const early = await h.call(page, "GET", `/api/packs/${packId}/export`);
  assert.equal(early.status, 409);
  assert.equal(early.json.error, "export_blocked");
  assert.match(early.json.message, /no_signoff/);

  step("2. sign off, then a reopen made elsewhere voids it: the stale page's export is refused with a message");
  await page.getByLabel(/I have read this statement/).check();
  await page.getByLabel("Your full name").fill("Alex Reviewer");
  await page.getByRole("button", { name: "Sign off this pack" }).click();
  await page.getByRole("button", { name: "Export Word document" }).waitFor();
  const other = await context.newPage();
  other.setDefaultTimeout(30_000);
  await other.goto(`${h.BASE}/coverage?id=${packId}`);
  other.once("dialog", (d) => d.accept());
  await other.getByRole("button", { name: "Reopen for edits" }).click();
  await other.getByLabel("Responsibility statement").waitFor();
  await page.getByRole("button", { name: "Export Word document" }).click();
  const refusal = page.getByRole("alert").filter({ hasText: /sign|export/i });
  await refusal.first().waitFor();
  const refusalText = await refusal.first().innerText();
  assert.match(refusalText, /sign(ed)? off|sign-off/i, `refusal does not mention the sign-off: ${refusalText}`);
  assert.deepEqual(downloads, [], "a file was downloaded after the sign-off was voided");
  assert.equal(await page.getByText("The Word document was downloaded.").count(), 0, "success note shown for a refused export");

  step("3. an edit after the reopen: the pack needs a new check and a new sign-off");
  await other.goto(`${h.BASE}/pack?id=${packId}`);
  await other.getByRole("link", { name: "Open answer" }).first().click();
  await other.getByRole("button", { name: "Edit", exact: true }).click();
  const box = other.getByLabel("Answer");
  const original = await box.inputValue();
  assert.match(original, /complete safeguarding/);
  await box.fill(original.replace("complete safeguarding", "complete mandatory safeguarding"));
  await other.getByRole("button", { name: "Save as a new version" }).click();
  await other.getByText(/mandatory safeguarding/).first().waitFor();
  await other.close();
  await page.reload();
  const blocked = page.getByRole("status").filter({ hasText: "Sign-off is not possible yet" });
  await blocked.waitFor({ timeout: h.LONG });
  assert.match(await blocked.innerText(), /claim check|not been checked|checked/i);
  assert.equal(await page.getByRole("button", { name: "Export Word document" }).count(), 0);
  const edited = await h.call(page, "GET", `/api/packs/${packId}/export`);
  assert.equal(edited.status, 409);
  assert.equal(edited.json.error, "export_blocked");

  step("4. check and sign again; deleting the evidence then refuses the export");
  await h.checkAll(page, packId);
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  await page.getByLabel(/I have read this statement/).check();
  await page.getByLabel("Your full name").fill("Alex Reviewer");
  await page.getByRole("button", { name: "Sign off this pack" }).click();
  await page.getByRole("button", { name: "Export Word document" }).waitFor();
  const docs = (await h.call(page, "GET", "/api/evidence/documents")).json.documents;
  const target = docs.find((d) => d.filename === "evidence1.txt");
  assert.ok(target, "evidence1.txt not listed");
  const del = await h.call(page, "DELETE", `/api/documents/${target.id}`);
  assert.equal(del.status, 204);
  await page.getByRole("button", { name: "Export Word document" }).click();
  const gone = page.getByRole("alert").filter({ hasText: /evidence/i });
  await gone.first().waitFor();
  assert.match(await gone.first().innerText(), /removed|evidence/i);
  assert.deepEqual(downloads, [], "a file was downloaded after the evidence was removed");
});
