// E2E: a unicode tender (curly quotes, accents, pound sign, en dash) and a larger tender (8 questions over 4 pages) go through
// extract -> draft -> check -> sign off -> export, and the exported .docx text is checked. ScriptedFakeAI, fixtures from make_fixtures.py.
const assert = require("node:assert/strict");
const path = require("node:path");
const h = require("./helpers.cjs");

async function signAndExport(page, packId, reviewer, saveAs) {
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  await page.getByLabel(/I have read this statement/).check();
  await page.getByLabel("Your full name").fill(reviewer);
  await page.getByRole("button", { name: "Sign off this pack" }).click();
  await page.getByRole("button", { name: "Export Word document" }).waitFor();
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export Word document" }).click()]);
  assert.match(download.suggestedFilename(), /\.docx$/i);
  await download.saveAs(saveAs);
  return readBack(saveAs);
}
const readBack = (file) => h.readDocx(file);

const unicode = () => h.runScenario("tender unicode", async ({ page, step }) => {
  const fx = path.join(h.FIX, "unicode");
  await h.signUp(page, "Café Grounds & Co Ltd");
  step("extract: curly quotes, accents, pound sign and en dash survive into the checklist");
  const packId = await h.createConfirmedPack(page, "Quartier – Zoë’s pack", path.join(fx, "tender.docx"), 2);
  await page.goto(`${h.BASE}/checklist?id=${packId}`);
  await page.getByTestId("req-1").getByText(/“Zoë Café” contract – worth up to £2m/).first().waitFor();
  assert.equal(await page.getByTestId("req-1").getByText("150 words", { exact: true }).count(), 1);
  await page.getByTestId("req-2").getByText(/local charities/).first().waitFor();

  step("evidence, draft and claim check on unicode text");
  await page.goto(`${h.BASE}/evidence`);
  await page.getByRole("heading", { name: "Evidence library" }).waitFor();
  for (const name of ["evidence1.txt", "evidence2.txt"]) await h.uploadEvidence(page, path.join(fx, name));
  await h.draftAll(page, packId);
  await page.getByRole("link", { name: "Open answer" }).first().click();
  await page.getByText(/Zoë O’Brien–Núñez/).first().waitFor();
  await page.goBack();
  await h.checkAll(page, packId);
  await page.getByText("Ready to sign off").first().waitFor({ timeout: h.LONG });

  step("sign off as an accented name and export: the .docx keeps every character");
  const doc = await signAndExport(page, packId, "Zoë Núñez–O’Brien", path.join(h.FIX, "unicode-export.docx"));
  assert.ok(doc.header.includes("reviewed by Zoë Núñez–O’Brien"), `header: ${doc.header}`);
  assert.match(doc.footer, /I understand that my firm, not the software, is responsible/);
  for (const want of ["Zoë O’Brien–Núñez", "£1,250,000", "“Zoë Café”", "£75,000", "“Aroma Bär”", "venue in Besançon Road", "–"]) {
    assert.ok(doc.body.includes(want), `exported text is missing ${want}: ${doc.body}`);
  }
  assert.doesNotMatch(doc.body, /�|Ã|â€|\?\?/, "mojibake or replacement characters in the export");
  const appendix = doc.rows.map((r) => r.join(" / ")).join("\n");
  assert.ok(appendix.includes("£1,250,000"), `appendix missing the pound figure: ${appendix}`);
  assert.ok(appendix.includes("evidence1.txt"), "appendix missing the document name");
});

const larger = () => h.runScenario("tender larger pack", async ({ page, step }) => {
  const fx = path.join(h.FIX, "large");
  const topics = ["beekeeping", "irrigation", "pesticide", "hedgerow", "drainage", "playground", "signage", "composting"];
  await h.signUp(page, "Large Grounds Ltd");
  step("extract 8 questions from a 4-page tender, with their word limits");
  const packId = await h.createConfirmedPack(page, "Large pack", path.join(fx, "tender.docx"), 8);
  await page.goto(`${h.BASE}/checklist?id=${packId}`);
  for (let n = 1; n <= 8; n++) {
    const card = page.getByTestId(`req-${n}`);
    await card.getByText(topics[n - 1]).first().waitFor();
    await card.getByText(`${100 + 10 * n} words`, { exact: true }).waitFor();
  }
  step("evidence, draft and check all 8");
  for (let n = 1; n <= 8; n++) await h.uploadEvidence(page, path.join(fx, `evidence${n}.txt`));
  await h.draftAll(page, packId);
  await h.checkAll(page, packId);
  await page.getByText("Ready to sign off").first().waitFor({ timeout: h.LONG });
  step("coverage lists all 8, then sign off and export: every answer is in the document, in order");
  await page.goto(`${h.BASE}/coverage?id=${packId}`);
  await page.getByLabel("Responsibility statement").waitFor({ timeout: h.LONG });
  for (let n = 1; n <= 8; n++) {
    const row = await page.getByTestId(`cov-${n}`).innerText();
    assert.match(row, new RegExp(`\\d+ / ${100 + 10 * n}`), `cov-${n}: ${row}`);
    assert.match(row, /Yes\s*$/, `cov-${n} not checked: ${row}`);
  }
  const doc = await signAndExport(page, packId, "Alex Reviewer", path.join(h.FIX, "large-export.docx"));
  let at = -1;
  for (let n = 1; n <= 8; n++) {
    const sites = 10 + n * 7;
    const i = doc.body.indexOf(`Our ${topics[n - 1]} work was reviewed in 2025 and covers ${sites} sites`);
    assert.ok(i > at, `answer ${n} (${topics[n - 1]}) missing or out of order`);
    at = i;
  }
  assert.ok(doc.rows.length >= 9, `appendix should have a header and one row per claim, got ${doc.rows.length} rows`);
  const cited = new Set((doc.body.match(/\[E-\d+\]/g) || []));
  assert.ok(cited.size >= 8, `expected 8 distinct evidence markers, got ${[...cited]}`);
});

(async () => { await unicode(); await larger(); })();
