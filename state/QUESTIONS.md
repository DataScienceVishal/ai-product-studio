# Questions for Vishal

Add new questions at the bottom. The Desk sends up to 3 per digest, most important first.

Format:

    ## Q-<n> (status: open)
    - Decision: one sentence
    - Context: two lines at most
    - Options: A) ... B) ... C) ...
    - Recommended: A, because ...
    - If no answer: B after 12 hours (reversible; changed from A on 2026-11-24 because round 6 showed A repeats the same failure). The studio would start the restaurant margin copilot spec (G2) from the shared starter, scoped against Jelly's published features | waits (ask-first list)

Status moves through: open → sent <UTC> → answered | defaulted.

## Q-1 (status: answered 2026-11-23T21:49:23Z)
- Decision: How should this session's work reach `main`, where the scheduled runs start?
- Context: Today's work (kit moved to the repo root, 15 ideas, T-2 spend report, T-6 starter) is on branch `vishal/blissful-cray-v1s3ys`. `main` still has the old nested `files/ai-product-studio/` layout, so scheduled runs would fail at step 1.
- Options: A) You merge the branch into `main` on GitHub (a PR or a fast-forward), and switch on "Allow unrestricted branch pushes" for the scheduled tasks B) Ask this session to open a PR for you to review and merge C) Keep the branch separate for now, and don't start the scheduled tasks yet
- Recommended: A, because the branch only adds to main (no conflicts) and the scheduled runs need it to work at all
- If no answer: waits (needs you on GitHub)
- Answer: Vishal in chat: always commit everything and push to `main`. Done: `main` fast-forwarded from 14a1f3a to af446d6. Still yours to do: let the scheduled tasks push to `main` (SETUP.md step 6, "Allow unrestricted branch pushes").

## Q-2 (status: defaulted A 2026-11-24T14:59Z; sent 2026-11-23T22:39:50Z)
- Decision: Does the studio have any way to sell outside the UK (India, Indonesia or elsewhere)?
- Context: The validator scored every India and Indonesia idea 2 or 3 out of 10 on reach, because selling goes through your friend's UK business. Without a channel there, those ideas can't reach the 70-point bar however good the evidence gets.
- Options: A) No: prioritise UK and English-speaking ideas, and keep non-UK ideas parked B) Yes: I (Vishal) can sell in India myself, so score Indian ideas with that channel C) Yes, through a partner I'll name
- Recommended: A, because it matches the plan in CLAUDE.md, and B or C can be switched on later
- If no answer: A after 12 hours (reversible)

## Q-3 (status: withdrawn 2026-11-23: pEPR was parked after T-13 found Repackd already sells the workflow)
- Decision: 25 ideas have been scored and none has reached the 70-point G1 bar (best: pEPR packaging data at 68). What should the studio do while pEPR's evidence comes in?
- Context: pEPR is 2 points short. The validator thinks it reaches about 73 if competitor pages confirm the spec-sheet gap (T-13, desk research, can start now) and an extraction benchmark hits 90% (T-14, needs your Azure OpenAI setup). The shared product starter is nearly through its review gates.
- Options: A) Start specification work on pEPR now (customer profile, core flow, MVP scope, architecture and cost), with no product code until G1 passes B) Keep the rules as they are: only desk research and new scouting until an idea passes C) Lower the G1 bar to 65 for the first product, so pEPR (68) and the restaurant margin copilot (66) can go ahead now
- Recommended: A, because the spec work is cheap and reversible, it makes the product buildable the day the benchmark passes, and it keeps the 70-point bar intact
- If no answer: A after 12 hours (reversible)

## Q-4 (status: answered 2026-11-23T23:02:54Z)
- Decision: Which customers should the next scouting round (round 3) look for problems among?
- Context: 25 ideas have been scored and none reached the 70-point bar. Every one lost most points on Competition (incumbents already sell it) and Reach (no way in to buyers). Your friend's UK business is the sales channel, but the studio doesn't know what it sells or to whom. Ideas built for its existing customers would start with a way in and first-hand pain.
- Options: A) My friend's own customers: I'll reply with the business's sector and who it sells to B) My own finance and tax network (accountancy practices and small firms I know) C) Keep scouting broadly, with the lessons from rounds 1 and 2
- Recommended: A, because a channel that already reaches the buyers is the one advantage incumbents can't copy, and it lifts Reach and evidence quality together
- If no answer: C after 12 hours (reversible; round 3 runs on the broad lessons until you reply)
- Answer: C (Telegram reply "1C" to the 23:05 digest, 22:59:50Z). Keep scouting broadly with the round 1-4 lessons.

## Q-5 (status: answered 2026-11-23T23:02:54Z)
- Decision: May the studio create its shared Azure resources (Postgres, container registry, Container Apps) in rg-ai-studio when the first product needs a demo?
- Context: ADR 0002 (products/_starter/ADR/0002-azure-deploy.md) costs it at $5.07 a month if the Azure for Students free allowance covers Postgres (12 months, new customers), or $23.20 a month if not, which uses the $80 in about 3.4 months and puts Postgres ($18.13) over the $10-per-resource rule. Nothing is created until you set the repository variable STUDIO_AZURE_APPROVED to yes.
- Options: A) Yes: create them when a product reaches G3 (check the portal's "Free services" page first; the infra README lists the 10 minutes of one-time steps) B) Yes, but use ACR Standard while the allowance lasts ($0 for 12 months, then $20.28 a month) C) Not yet: keep demos local until a product passes G1
- Recommended: A, because it is the cheapest path that meets the security rules, and nothing runs until a product needs it
- If no answer: waits (spending money is on the ask-first list)
- Answer: A (Telegram reply "2A" to the 23:05 digest, 23:00:09Z). Create the shared resources when a product reaches G3. Still needed from Vishal at that point: the one-time steps in products/_starter/infra/README.md (check Free services, AZURE_CREDENTIALS, STUDIO_DB_SEED, and the STUDIO_AZURE_APPROVED=yes variable, which agents can't set).


## Q-6 (status: answered 2026-11-24T10:04:29Z)
- Decision: 39 ideas scored across six scouting rounds and none reached the 70-point bar; how should the studio get to a first product?
- Context: Every round fails the same way: by late 2026 the vertical system vendors (or an AI-native rival) already sell "AI over your documents" for each niche, so Competition scores 1-5. Desk research alone can't prove the gaps that remain. Best parked ideas: restaurant margin copilot 66, MTD quarterly prep 65, holiday-pay look-back audit 63. Update 2026-11-24 (run e5f5): round 6 tried option A early (only ideas the studio can evidence from public data) and all four were killed at 51-57 on the same Competition/Pay grounds, so A is no longer a credible default.
- Options: A) Keep scouting, but only ideas where the studio can collect evidence itself (public datasets, open APIs, published case law/complaints), and accept slower progress B) Build the best parked idea anyway as a "better, cheaper, UK-small-business" entrant (restaurant margin copilot vs Jelly at £129/site), using the shared starter, and let a demo to your friend be the evidence C) Tell us your friend's business sector and customers, so round 6 starts from a channel incumbents can't copy (re-asks Q-4 A)
- Recommended: C, because Reach and Competition are what sink every idea and a real channel fixes both; B is the fallback if you'd rather not share it
- If no answer: B after 12 hours (reversible; default changed from A on 2026-11-24T05:41Z, see DECISIONS; B is treated as an explicit exception to the G1 gate for this one idea, and still needs Q-7 A to be affordable)
- Answer: A (Telegram reply "1A" to the 08:00 digest, 10:04:29Z). Keep scouting, only ideas where the studio can collect the evidence itself. T-40 (restaurant margin build) is shelved; scout round 7 (T-42) follows A with round 6's lessons.

## Q-7 (status: answered 2026-11-24T10:04:31Z)
- Decision: Can you add a cheap model deployment (e.g. gpt-5-mini or gpt-4.1-mini) next to gpt-5.4-pro on the Azure OpenAI resource, and give its name in AZURE_OPENAI_DEPLOYMENT_MINI?
- Context: The only model the studio can reach is a premium reasoning model. The 5-document T-12 pilot used ~28k output tokens (~$3.40 at an assumed pro price); the full MTD benchmark would cost about the whole $80 credit, and product features would be slow (70-150 s per document). A mini model is typically 50-100x cheaper per token. The OpenAI resource isn't in rg-ai-studio and the studio has no Azure login, so agents can't add it.
- Options: A) Add a mini deployment and the env var (about 5 minutes in Azure AI Foundry; recommended) B) Keep pro only: the studio runs the full benchmark at most 20 documents (~$15) and stops C) No more model spend for now: T-12 stays at the pilot
- Recommended: A, because it makes the benchmark and every product affordable and keeps pro for rare hard cases
- If no answer: waits (spending money is on the ask-first list); until then the studio behaves as C
- Answer: B (Telegram reply "2B" to the 08:00 digest, 10:04:31Z). No mini deployment; the studio may run the MTD benchmark on the pro model, at most 20 documents (about $15), then stops. Model spend cap for T-12: $15.

## Q-8 (status: sent 2026-11-24T15:00Z as 1; 2026-11-24T23:14Z Vishal asked how to add the sign-in, steps given in chat; treat as leaning A, waits for him to confirm it's added)
- Decision: How should GitHub deploy jobs sign in to Azure once Postgres uses Entra ID (T-18)?
- Context: In the new design the deploy service principal is also the database admin. Its secret (AZURE_CREDENTIALS) can be read by a workflow on any branch, agent branches included. Security says the "demo data only" limit can't end while that is true. The fix is a federated (OIDC) credential that trusts only main. Adding one is a directory change, which needs your yes.
- Options: A) Add a federated credential limited to main on the deploy app registration (about 5 minutes in the portal; the studio writes the exact steps and switches the workflow to OIDC), then delete the client secret (recommended) B) Keep the secret and accept the risk in writing: demo data only stays in force until handover C) Leave it for now and decide before the first real deploy
- Recommended: A, because it takes the only long-lived database admin credential out of reach of non-main branches
- If no answer: waits (ask-first list). The studio builds T-18 behind the demo-data condition (behaves as C), and nothing is deployed until Q-5's approval setting is flipped anyway

## Q-9 (status: answered 2026-11-24T23:14Z)
- Decision: May the studio sign up for free trials (no card, studio email) of incumbent tools, to test whether their weak spots are real?
- Context: After 11 rounds and 47 ideas, none has reached 70. A wedge check on the five best near-misses (round11-wedge-summary.md) found no new segment that lifts any of them; the deciding question for the best one (pEPR packaging data, 68) is whether Repackd's spec-sheet extraction is weak on messy real documents, and desk research can't answer that. Creating accounts is on the ask-first list.
- Options: A) Yes to free, no-card trials of named incumbents (Repackd first, then Jelly for the restaurant idea), test data only, nothing in your name; the studio logs each sign-up in DECISIONS.md (recommended) B) No trials; keep scouting new niches only C) Build the best parked idea anyway (restaurant margin copilot, 66) and let a demo to your friend be the evidence
- Recommended: A, because it is the only cheap way to turn a 66-68 near-miss into a pass or a clean kill
- If no answer: waits (ask-first). Meanwhile the studio keeps scouting (behaves as B)
- Answer: A (Vishal in chat, 2026-11-24T23:14Z). Free, no-card trials of named incumbents (Repackd first, then Jelly), test data only, nothing in Vishal's name; log each sign-up in DECISIONS.md.

## Q-10 (status: answered 2026-11-24T20:10:27Z)
- Decision: Should the G1 rubric score Competition on the studio's wedge against incumbents (price, fit, segment they don't serve) rather than on whether a rival exists?
- Context: 17 rounds, 53 ideas scored, 0 passed. The validator re-scored five real, paying UK AI products as launch-day ideas and they land at 57-66 too (Jelly 62, Dext 62, RemitClear 66), so the bar as written rejects products that are succeeding. See state/ideas/META-REVIEW.md.
- Options: A) Yes: Competition is scored on a nameable, evidenced wedge; the 70 bar stays; parked ideas are re-scored, with pEPR (68) first after its benchmark (recommended) B) Keep the rubric as it is and keep scouting new theses C) Skip the gate for one bet: build pEPR now as a cheaper Repackd alternative and let a demo be the evidence
- Recommended: A, because it fixes the measured calibration fault without lowering the bar, and the pEPR benchmark (T-56) supplies the evidence either way
- If no answer: A after 12 hours (reversible; pipeline.md is edited and the change logged)
- Answer: A (Telegram reply "1A" to the 19:30 digest, 20:10:27Z). Competition is now scored on an evidenced wedge in playbooks/pipeline.md; 70 bar unchanged; parked ideas re-scored, pEPR first after T-56.

## Q-11 (status: answered 2026-11-24T20:10:29Z)
- Decision: May the pEPR proof test (T-56) spend up to $12 of Azure OpenAI credit on the gpt-5.4-pro model?
- Context: The benchmark is built and reviewed: 30 synthetic packaging spec sheets plus 5 tuning sheets, with a pass mark written before any run. A pass lifts pEPR (68) towards the 70 bar; a fail kills it. At the assumed pro price a sheet costs about $0.25-0.30, so the run is ~$9.50 plus ~$2.50 of tuning. The extractor's guard stops before any call could cross $12 or 3M tokens. Spend so far: T-12 ~$3.40 of its $15.
- Options: A) Yes, up to $12 for T-56 (recommended) B) Yes, but test set only, no tuning (~$9.50) C) No model spend: pEPR stays parked at 68
- Recommended: A, because $12 settles the studio's best near-miss idea either way, and tuning on 5 held-out sheets is what makes a fair score possible
- If no answer: waits (spending is on the ask-first list); the studio builds and tests the extractor on the fake model meanwhile and makes no Azure call
- Answer: A (Telegram reply "2A" to the 19:30 digest, 20:10:29Z). T-56 may spend up to $12 on gpt-5.4-pro (tuning + one test run); the extractor's guard enforces the cap.

## Q-12 (status: answered 2026-11-24T23:14Z)
- Decision: The pEPR test costs more than we thought. How should it run?
- Context: The model is dearer than the studio assumed. gpt-5.4-pro lists at $30/$180 per million tokens (OpenAI and Microsoft pages), not $15/$120. At the real price, total model spend so far is about $15 of the $80 credit, not the ~$10 reported. T-56 has used $3.09 of your $12. Tuning was accurate (97.9% of fields right, every conflict flagged), but it cost $0.62 a sheet, twice the cost pass mark of $0.316 that was written before any run. So the 30-sheet test on this model would cost about $18.50 and would fail the cost mark even if accuracy passes.
- Options: A) Add a cheap deployment (gpt-5-mini or similar, about 5 minutes in Azure AI Foundry) and name it in AZURE_OPENAI_DEPLOYMENT_MINI. The studio writes a dated amendment switching the test to it before running. Expected cost about $1-2 inside the $12 already approved, and it is the model a product would use (recommended). B) Raise T-56's cap to $30 and run once on gpt-5.4-pro as pre-registered. That settles accuracy, but the cost mark will almost surely fail, which kills pEPR on cost. C) Stop: pEPR stays parked at 68 with tuning evidence only.
- Recommended: A, because on the pro model the test can only end in a cost failure. A mini model tests what a sellable product would actually run on, for about a tenth of the money.
- If no answer: waits (spending and Azure changes are on the ask-first list). No model calls are made meanwhile.
- Answer: A (Vishal in chat, 2026-11-24T23:14Z). Vishal adds a cheap deployment and sets AZURE_OPENAI_DEPLOYMENT_MINI; until that variable exists, no T-56 model calls. Then write the dated amendment and run inside the existing $12.

## Q-13 (status: answered 2026-11-25T09:04:22Z)
- Decision: The pEPR idea is dead (it missed its test by 0.7 points). What should the studio do next for ideas?
- Context: 52 ideas scored from public web pages, none passed. The two ideas left in the 63-69 range are both stuck: restaurant (66) is shelved by your Q-6 answer, and holiday-pay (64) waits on a government response with no date (re-checked 2026-11-25). Desk research keeps finding problems that everyone else has already found.
- Options: A) You have a 15-minute chat with your UK-business friend using state/ideas/BUYER-INTERVIEW.md. Each pain with money attached becomes an idea and gets a cheap proof test (recommended) B) Bring restaurant back as a proof test: free Jelly trial (already allowed by Q-9) plus a synthetic-invoice benchmark, kill test written first, under $5 of model spend C) One more desk round, aimed only at your edges (finance/tax data, RL dynamic pricing, RAG agents)
- Recommended: A, because your friend is both the buyer's voice and the future seller, and the meta-review found desk-only scouting is the reason nothing passes. It costs you 15 minutes and spends no money.
- If no answer: C after 12 hours (reversible, no spend). A stays open, because only you can have the chat.
- Answer: B (Telegram "1B", 2026-11-25T09:04:22Z). Restaurant comes back as a proof test: kill test written first, synthetic-invoice benchmark, free Jelly trial if a studio email exists, under $5 model spend. T-80 and T-81.

## Q-14 (status: answered 2026-11-25T09:04:24Z)
- Decision: The studio wrote a narrower Azure role for the GitHub deploy identity (it can deploy but can't grant access or delete the database). Only you (Owner) can switch it on. When?
- Context: today the deploy identity holds Contributor on rg-ai-studio, so a bad workflow change on main could delete anything in the group. The new role is on main (products/_starter/infra/deploy-role.bicep); the 3 Cloud Shell steps and rollback are in products/_starter/infra/README.md, "Least-privilege deploy role (T-65)". About 10 minutes, no cost. A missing action would show as a failed deploy naming it, which the studio then adds.
- Options: A) Apply it the next time you run a deploy (recommended) B) Wait for T-69 (deploy identity in its own resource group, separate shared-deploy role) and apply both together C) Leave Contributor until handover
- Recommended: A, because it removes the delete-everything risk now and T-69 builds on it.
- If no answer: nothing changes (Contributor stays); it waits for you because only an Owner can apply it. The studio carries on with other work.
- Answer: A (Telegram "2A", 2026-11-25T09:04:24Z). Vishal applies the deploy role at his next deploy; T-65 waits on that, then the studio watches the next deploy for a missing action.
