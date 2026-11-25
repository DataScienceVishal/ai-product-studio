# Review: T-92 region wording (p/_starter/T-92-region, ddc3e46)

Reviewer: reviewer agent, 2026-11-25. Diff reviewed: `git diff ba66373 ddc3e46` (5 files, +10/-10).

## Verdict: CHANGES

One small thing to fix: the ADR diagram is now misaligned. Everything else is accurate and can merge once that is fixed.

## Evidence

- Frontend: `npx vitest run`, 203 passed (203). `npx tsc --noEmit`, exit 0. The JSX in `legal.tsx` is valid.
- Infra facts checked: `infra/main.bicepparam:7` and `infra/shared.bicepparam:48` both set `location = 'francecentral'`.
  The comments in both files and `state/HURDLES.md:37` confirm `rg-ai-studio` is in uksouth (group metadata only).
  ADR 0002 lines 549-552 and BOARD T-61 ("prices equal or lower than uksouth") back up "checked against francecentral",
  so no numbers were invented.
- Azure OpenAI: nothing in `infra/` records the deployment type. The only inputs are `azureOpenAiEndpoint` and
  `azureOpenAiDeployment` (`main.bicep:47-48`), so the hedged "may be processed outside the UK and EU depending on the
  deployment type" wording is honest. The DATA.md note about Global Standard matches Microsoft's description and
  `SECURITY.md:817`.

## Critical issues

1. **ADR diagram is broken.** `ADR/0002-azure-deploy.md:22`: `rg-ai-studio (meta uksouth)▼` is 2 characters too long
   for the space before the first arrow. All three `▼` arrows and the right-hand box corner have moved from columns
   31/40/50/74 to 29/38/48/72. They no longer sit under the `│` lines on line 21 or above the `ca-starter` box on line 23.
   "meta uksouth" is also unclear, and it is the one label in the picture that still reads as "this is in uksouth".
   Fix: `  rg-ai-studio (francecentral) ▼        ▼         ▼                       ┌──...` (28-character label plus
   one space keeps the `▼` at column 31). Or keep the old text length and say "group in uksouth, resources in
   francecentral" on line 13 only.

## Remaining "UK region" / "uksouth" / "UK South" hits (whole products/_starter, excluding reviews/)

- No "UK region" or "UK South" text is left.
- `uksouth` still appears in ADR 0002 lines 13, 424 and 526 (price labels, now qualified) and in the Region section
  (lines 545-549, correct). It also appears in `infra/main.bicep:21`, `infra/shared.bicep:12` and both `.bicepparam`
  comments. All of these correctly describe the resource group's metadata region. None of them claims resources are
  in the UK. OK.
- `infra/README.md:16` is correct. `BRIEF.md:198` is updated and consistent with `BRIEF.md:271`.

## Suggestions (not blocking)

- `ADR/0002-azure-deploy.md:13`: "Prices are estimates read for uksouth (...), read on 2026-11-23" uses "read" twice.
  Suggest "Prices are uksouth estimates (...), read on 2026-11-23".
- `frontend/src/pages/legal.tsx:19`: "UK hosting is a decision for later" can read like a promise to customers.
  Plainer: "for now our servers and database are in Microsoft's France Central region, in the EU". If the UK
  sentence stays, use "we may move to UK hosting later".
- `frontend/src/pages/app.tsx:454` (Help FAQ) still says "some deployment types process data outside the UK". That
  is still true, but now it differs from the privacy page ("outside the UK and EU"). Align them in a later task. This
  was out of scope for T-92.
- Process: ddc3e46 was pushed to `main` before review. The coordinator says it was reverted in 9e54a63. Merge the
  branch only after this review passes.
