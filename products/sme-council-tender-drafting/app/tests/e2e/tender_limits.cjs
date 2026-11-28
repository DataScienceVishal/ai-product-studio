// E2E: word limits, the gap marker and the "blocked by an unsupported claim" state in the draft and coverage pages.
// Runs on ScriptedFakeAI through scripts/e2e.sh (fixtures in $E2E_FIXTURES/limits).
const assert = require("node:assert/strict");
const path = require("node:path");
const h = require("./helpers.cjs");

h.runScenario("tender limits, gaps and blocked claims", async ({ page, step }) => {
  const fx = path.join(h.FIX, "limits");
  step("setup: 3 questions; evidence only for the first and the third");
  await h.signUp(page, "Limits Grounds Ltd");
  const packId = await h.createConfirmedPack(page, "Limits pack", path.join(fx, "tender.docx"), 3);
  await page.goto(`${h.BASE}/evidence`);
  await page.getByRole("heading", { name: "Evidence library" }).waitFor();
  for (const name of ["evidence1.txt", "evidence3.txt"]) await h.uploadEvidence(page, path.join(fx, name));

  step("checklist shows each word limit");
  await page.goto(`${h.BASE}/checklist?id=${packId}`);
  for (const [n, limit] of [[1, 150], [2, 40], [3, 10]]) {
    await page.getByTestId(`req-${n}`).getByText(`${limit} words`, { exact: true }).waitFor();
  }

  step("draft: word count against the limit, the gap marker and the over-limit badge");
  await h.draftAll(page, packId);
  const open = async (n) => {
    await page.goto(`${h.BASE}/pack?id=${packId}`);
    await page.getByRole("link", { name: "Open answer" }).nth(n - 1).click();
    await page.getByRole("heading", { name: String(n), exact: true }).waitFor();
    await page.getByText(/^Draft \(version/).waitFor();
  };
  await open(1);
  const q1 = await page.locator("body").innerText();
  assert.match(q1, /\d+ words of 150/);
  assert.doesNotMatch(q1, /Over the limit/);
  assert.doesNotMatch(q1, /gaps? to fill/);
  await open(2);
  const q2 = await page.locator("body").innerText();
  assert.match(q2, /\[NEEDS FIRM INPUT: no evidence found for this question\]/);
  assert.match(q2, /\d+ words? of 40/);
  assert.match(q2, /1 gap to fill/);
  assert.match(q2, /This answer cites no evidence\./);
  await open(3);  // the one cited sentence is longer than 10 words: the draft becomes a gap, never a silently cut answer
  const q3gap = await page.locator("body").innerText();
  assert.match(q3gap, /\[NEEDS FIRM INPUT/);
  assert.doesNotMatch(q3gap, /Over the limit/);
  await page.getByRole("button", { name: "Edit", exact: true }).click();  // the user writes a longer answer
  await page.getByLabel("Answer").fill("Our health and safety induction record shows that every operative completes a full accredited induction course before starting any work on a council site [E-2]");
  await page.getByRole("button", { name: "Save as a new version" }).click();
  await page.getByText(/^Draft \(version 2, edited by you\)/).waitFor();
  const q3 = await page.locator("body").innerText();
  assert.match(q3, /\d+ words of 10/);
  assert.match(q3, /Over the limit/);

  step("coverage before any check: gap and over-limit are shown per question and block the sign-off");
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  const c2 = await page.getByTestId("cov-2").innerText();
  assert.match(c2, /\/ 40/);
  assert.match(c2, /\t1\t/, `cov-2 should show 1 gap: ${c2}`);
  const c3 = await page.getByTestId("cov-3").innerText();
  assert.match(c3, /\/ 10\s+Over/, `cov-3 should be marked Over: ${c3}`);
  const blockers = page.getByRole("status").filter({ hasText: "Sign-off is not possible yet" });
  await blockers.waitFor();
  assert.match(await blockers.innerText(), /10-word limit/);
  await page.getByLabel(/I have read this statement/).check();
  await page.getByLabel("Your full name").fill("Alex Reviewer");
  assert.equal(await page.getByRole("button", { name: "Sign off this pack" }).isDisabled(), true, "sign-off enabled while blocked");

  step("an unsupported claim: edit question 1, check, and see it marked and blocking");
  await h.checkAll(page, packId);
  await open(1);
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  const box = page.getByLabel("Answer");
  await box.fill("We hold ISO 9001 certification across 77 depots. " + (await box.inputValue()));
  await page.getByRole("button", { name: "Save as a new version" }).click();
  await page.getByText(/77 depots/).first().waitFor();
  await h.checkAll(page, packId);
  await open(1);
  await page.getByRole("columnheader", { name: "Verdict" }).waitFor({ timeout: h.LONG });
  await page.getByText(/1 claim is not supported by your evidence/).waitFor({ timeout: h.LONG });
  await page.locator("tr[data-verdict='unsupported']").getByText("Unsupported", { exact: true }).waitFor();
  assert.match(await page.locator("tr[data-verdict='unsupported']").innerText(), /77 depots/);
  assert.match(await page.locator("mark[data-verdict='unsupported']").innerText(), /77 depots/);
  assert.equal(await page.locator("tr[data-verdict='supported']").count() >= 1, true, "the original claim should stay supported");

  step("coverage names the unsupported claim and keeps the sign-off shut");
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  const c1 = await page.getByTestId("cov-1").innerText();
  assert.match(c1, /1 unsupported/i, `cov-1 claims: ${c1}`);
  const why = await page.getByRole("status").filter({ hasText: "Sign-off is not possible yet" }).innerText();
  assert.match(why, /not supported by evidence/);
  await page.getByLabel(/I have read this statement/).check();
  await page.getByLabel("Your full name").fill("Alex Reviewer");
  assert.equal(await page.getByRole("button", { name: "Sign off this pack" }).isDisabled(), true);
  const refused = await h.call(page, "POST", `/api/packs/${packId}/signoff`, { reviewer_name: "Alex Reviewer", accept_statement: true, statement_version: "x" });
  assert.ok(refused.status >= 400 && refused.status < 500, `sign-off should be refused, got ${refused.status}`);
  const exp = await h.call(page, "GET", `/api/packs/${packId}/export`);
  assert.equal(exp.status, 409);
});
