# ADR 0001: Demo architecture for sme-council-tender-drafting

- Status: proposed (architect, T-184, 2026-11-27). Needs reviewer PASS. Decision 7 also needs Vishal's answer before any live model call.
- Context documents: `SPEC.md`, `reviews/T-183-validator.md`, `DESIGN.md`, `products/_starter/README.md`, `products/_starter/ADR/0001-0003`, `state/BUDGET.md`.

## Context
- **What this is:** a private, G3-equivalent portfolio demo of an idea that scored 60 (Vishal, Q-18 C). It must prove the seven-step core flow and the bars A1 to A9, with A6 (the claim check and the export gate) as the headline.
- **Money:** it must cost nearly nothing. The total Azure credit is $80, and the app's AI budget is $6.10 a month at 98,000 tokens a day.
- **Model:** the only affordable model is the gpt-5-mini deployment in `AZURE_OPENAI_DEPLOYMENT_MINI`. Under the cost guard, the gpt-5.4-pro deployment leaves AI off.
- **Inputs:** tender packs are long PDFs and DOCX files from public notices, and their text is untrusted.
- **Starting point:** the studio's starter already provides sign-in, tenancy, AI caps, logs and the deploy path.

## Decisions

### 1. Build on a copy of `products/_starter`; replace `Note` with the product objects
- **Options:**
  - (a) copy the starter;
  - (b) a new FastAPI app;
  - (c) a script-only demo with no app.
- **Chosen:** (a). Sign-in, tenancy, CSRF, rate limits, AI caps, the cost guard, logs and deploy have all passed review and security there. (b) would rebuild them, and (c) can't show the review and sign-off flow.
- **Trade-offs:**
  - It inherits the starter's billing and cancels code, which sits idle while prices are off.
  - One additive change is needed in the AI adapter: an optional `json_schema` argument. It is kept in the product copy and offered back to the starter as a separate reviewed change.
  - Child tables add composite `(tenant_id, parent_id)` foreign keys, a step beyond the starter's application-only scoping.

### 2. Zero new Azure resources; keep page text, not files
- **Options:**
  - (a) Blob Storage for the original files;
  - (b) the bytes in Postgres;
  - (c) extract the text and discard the bytes.
- **Chosen:** (c).
  - Citations and the Word export need only page text.
  - It avoids a new paid resource and a new data store to secure.
  - It also shrinks what a breach or a backup could expose.
- **Trade-offs:**
  - A user can't re-download the original from the app.
  - Re-parsing needs a re-upload.
  - Page images can't be shown. That is acceptable, because OCR is a Won't.

### 3. Retrieval: Postgres full-text first; embeddings later
- **Options:**
  - (a) Postgres FTS (`ts_rank_cd` over an OR tsquery) with a boost for must-have tokens such as accreditation codes;
  - (b) pgvector with an embeddings deployment;
  - (c) BM25 in Python over the tenant's passages;
  - (d) an external search service.
- **Chosen:** (a).
  - It is free and needs no new deployment.
  - It is deterministic, so FakeAI tests cover it fully.
  - It is good at the exact tokens bids depend on (ISO numbers, scheme names).
- **About the others:**
  - Azure Flexible Server has no BM25 extension, but it does list `vector` 0.8.7 and `pg_trgm` 1.6 for PostgreSQL 16 ([extensions by name](https://learn.microsoft.com/en-us/azure/postgresql/extensions/concepts-extensions-versions), updated 2026-07-10). So (b) stays open as a Should.
  - (b) needs Vishal to add an embeddings deployment (ask-first).
  - (c) is the fallback rerank if Recall@8 is weak during tuning.
- **Trade-offs:**
  - Synonyms and paraphrase are weak: "staff vetting" will not find "BS7858 screening" unless both terms appear.
  - The mitigation is query expansion from the question's scoring criteria, plus the user seeing what was found.

### 4. Every AI output passes code checks that fail closed
- **Options:**
  - (a) trust the structured model output;
  - (b) structured output plus deterministic validators;
  - (c) a second model as a judge of the first.
- **Chosen:** (b).
  - Strict JSON schemas are supported for gpt-5-mini on the Responses API ([structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs), updated 2026-08-24).
  - The code checks:
    - quotes must be substrings of the cited page or passage;
    - citations must be in the retrieved set;
    - numbers and codes in a claim must appear in its supporting quote;
    - word counts are counted in code;
    - an unchecked-sentence detector turns any factual-looking sentence that the checker skipped into a blocking `unchecked` claim.
- **Why:** the validator showed (T-183 F1) that a missed claim is never flagged. These checks convert the common model failures (skipping a claim, inventing a quote, drifting a number) into blocks, at no token cost.
- **Against (c):** it doubles the cost and still has no ground truth.
- **Trade-offs:**
  - There will be false blocks: paraphrased but correct claims, numbers written as words. The user then has to edit or add evidence.
  - The rules need careful tests.

### 5. Long AI work runs in an in-process job runner with Postgres leases
- **Options:**
  - (a) synchronous calls inside the request;
  - (b) in-process worker threads plus an `ai_tasks` table with `FOR UPDATE SKIP LOCKED` and leases;
  - (c) a Container Apps job or a queue service.
- **Chosen:** (b).
  - gpt-5-mini calls take tens of seconds (T-80 measured a p95 of 82.9 s per page), past the starter's 25 s request deadline.
  - (b) needs no new resource.
  - The browser's 3 s polling keeps the replica up, because Container Apps waits a 300 s cool-down before scaling to zero ([scale-app](https://learn.microsoft.com/en-us/azure/container-apps/scale-app), updated 2026-05-19).
  - Leases make a restart resumable.
- **Against (c):** a queue would add a paid resource, and a job per pack is heavy.
- **Trade-offs:**
  - Work only progresses while someone is polling or the replica is otherwise up.
  - There is a worst-case double charge for one call after a crash, because a possibly billed call is retried once.

### 6. The export gate is a pure function, and sign-off is bound to a digest of the drafts
- **Options:**
  - (a) a UI-only block;
  - (b) a status flag on the pack;
  - (c) a pure `export_allowed()` re-evaluated on the server at export time from the rows, with the sign-off holding a SHA-256 digest of every latest draft.
- **Chosen:** (c).
  - A6b requires 100% blocking, and a pure function can be property-tested over every state.
  - The digest means any edit after sign-off voids it without extra bookkeeping.
- **Trade-off:** editing one word after sign-off means signing off again. That is intended.

### 7. Live evaluation runs through its own spend ledger, under a one-off budget that Vishal must approve
- **Options:**
  - (a) run the eval through the app's caps;
  - (b) an offline harness calling the same pipeline functions through a ledger provider with a hard dollar cap and worst-case pre-checks (the T-56, T-80 and T-113 pattern), under a one-off approval;
  - (c) no live eval.
- **The measured gap:**
  - The full eval, tuning, recording and the A9 run come to about 4.3M tokens, $3.66 expected (DESIGN section 8).
  - The dollars fit the $6.10 a month. The tokens are 44 days of the 98,000 daily cap.
  - The app's per-tenant trial caps (100k a month, 30k a day) can't run even one pack (about 252k).
  - The cuts SPEC section 3 allows, 2 held-out drafting packs and fewer tuning passes, still leave about 36 days.
- **Recommended:** (b), with a $6.00 hard cap and sub-caps (tuning $2.00, scored reserve $2.60, recording and A9 $1.40).
  - Money is ask-first, so this is queued as a question, not assumed.
  - Without an answer, the slices that need no spend continue on the fake provider.
- **Trade-offs:**
  - The eval spend is outside the app's daily guard. The ledger is the guard instead, and it refuses any call whose worst case would pass a cap.
  - (c) would leave A6 unmeasured, and under the SPEC the demo would then not be shown.

### 8. Model: gpt-5-mini only, with effort and output caps per task, frozen before the scored run
- **Options:**
  - (a) gpt-5-mini;
  - (b) gpt-5.4-pro;
  - (c) a newer mini model.
- **Chosen:** (a).
  - It is the deployment that exists.
  - It costs $0.25 per million input and $2.00 per million output tokens ([OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5-mini), read 2026-11-27).
  - It supports structured outputs and is GA on Azure until 2027-07-13 ([retirement schedule](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule), updated 2026-11-18).
- **Against (b):** at $180 per million output tokens it is unaffordable, and the guard leaves it off.
- **Against (c):** it would need Vishal to add a deployment, for an unmeasured gain.
- **Starting settings:**
  - extract: effort low, 6k output cap;
  - draft: effort low, 4k output cap;
  - claim check: effort medium, 6k output cap.
  - The truncation rule is one retry at twice the cap, then failed.
- **Trade-off:** OpenAI's page now marks gpt-5-mini deprecated in favour of newer models. Azure still lists it as GA, which is enough for the life of this demo.

## Consequences
- **Azure:** no new resources and no new monthly cost for the build and eval. A deployed demo would add $0 per-product rows inside the Container Apps free grant, but it triggers the shared Q-5 resources, which is a later question (DESIGN section 12).
- **Questions for Vishal:** one now, the one-off eval budget (decision 7), which defaults to nothing spent while it waits.
- **Biggest technical risk:** whether gpt-5-mini, with the code checks, catches 38 of 40 seeded false claims (A6a) without so many false blocks that A9's 15-minute target fails. E4 measures the checker on its own, cheaply, so this shows up early in tuning.
- **Follow-ups:**
  - offer `json_schema` and the per-path upload limit back to the starter;
  - consider embeddings only after A6 passes.
