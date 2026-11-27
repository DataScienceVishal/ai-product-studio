# Data inventory and retention (starter)

What the starter stores, why, for how long, and how it is deleted. Products copy this file, add their own
tables, and keep it current. It supports UK GDPR and India DPDP basics. It isn't legal advice: get a legal
review before launch.

| Table | Personal data | Why | Kept until | Deleted by |
|---|---|---|---|---|
| `tenants` | company name | the customer account | account deletion; once real email is sent and verification is required, accounts whose owner never verified, hasn't signed in for 30 days and has no payment-provider customer are removed | owner: Settings → Delete account; purge job |
| `users` | email, role, argon2 password hash, last sign-in time | sign-in; the sign-in time protects active accounts from the purge | account deletion, or the member leaves or is removed | owner (whole account or a member), member (themselves) |
| `auth_sessions` | link to a user, hashed token | staying signed in | expiry (7 days), sign-out, password reset | purge job; sign-out; cascade |
| `password_resets` | link to a user, hashed token | password reset | 7 days after use or expiry | purge job; cascade |
| `email_verifications` | link to a user, hashed token | proving the address | 7 days after use or expiry | purge job; cascade |
| `invitations` | invitee email | adding team members | 30 days after accepted, cancelled or expired; at once when the member is removed or leaves | purge job; member removal; cascade |
| `subscriptions` | provider customer and subscription ids | billing | account deletion (the provider customer is deleted first) | account deletion |
| `billing_events` | provider event ids only | applying each webhook once | 400 days | purge job |
| `pending_cancels` | provider name, subscription ref, tenant id (cleared if the account is deleted), attempt count, time of the last attempt, last error text (fixed messages, no provider text) | retrying the cancel of a lapsed subscription that a new checkout replaced, so the customer is not billed twice | deleted when the cancel works, or is skipped because that subscription became the current one; normally minutes. A row that keeps failing stays: logged at ERROR, one CRITICAL line ("pending cancel needs operator") at the 10th failure, then WARNING; the sweep backs off min(2^attempts minutes, 24 h) between attempts | cancel sweep (`python -m app.maintenance cancels`, every 30 min); the tenant's next billing event (only rows with fewer than 3 failures) |
| `ai_usage` | tenant id, token counts | per-customer caps, the studio-wide daily AI budget, cost | 400 days; a reservation still "pending" after 15 minutes (process died mid-call) is zeroed by the purge job or the tenant's next call; on account deletion the tenant link is cleared but the counts stay, so the global budget still counts them | purge job |
| `tender_packs` | pack title, buyer name (customer content); `confirmed_by` user id | one tender response | account deletion (cascade); the user deleting the pack | owner or member deleting the pack; account deletion |
| `source_documents` | uploaded tender and evidence files: filename, sha256, size, `created_by` user id (customer content, may hold names in the text) | the source of requirements and evidence | with its pack, or the user deleting the document; account deletion. A document that requirements still reference cannot be deleted until they are removed (migration 0014) | user (pack or document delete); account deletion |
| `document_pages` | the full extracted text of each page (customer content) | quote checks and page references | with its document | cascade |
| `requirements` | requirement text and source quote (customer content); `edited_by` user id | the checklist the draft answers | with its pack; account deletion | cascade from the pack; account deletion |
| `evidence_counters` | none | per-tenant E-n numbering, never reused | account deletion | cascade |
| `evidence_items` | passages of the company's own evidence files (customer content) | retrieval for drafting | with its document; account deletion | cascade; user soft-deleting a passage |
| `drafts` | model-written and user-edited answer text (customer content) | the bid answers | with its requirement, pack or account | cascade |
| `claims` | spans of draft text with support status (customer content) | the claim check | with its draft | cascade |
| `signoffs` | `reviewer_name`, typed at sign-off, and `reviewer_user_id`: the only new personal data | recorded human review before export | with its pack; account deletion (the user link is cleared if the member leaves, the typed name stays with the pack) | cascade from the pack; account deletion |
| `export_records` | export file hash, `created_by` user id | proving what was exported and signed off | with its pack | cascade |
| `ai_tasks` | pack link, kind, status, error text (fixed messages, no document text) | tracking background AI work | with its pack; account deletion | cascade |
| `ai_cache` | model output for a prompt hash, per tenant (customer content derived from uploads) | avoiding repeat AI cost | 90 days from creation; account deletion | purge job (`python -m app.maintenance purge` deletes rows older than 90 days, `maintenance.AI_CACHE_DAYS`); cascade |

Everything in the 12 tender tables is customer content. Account export (`GET /api/account/export`) includes all of
them except `ai_tasks`, `ai_cache` and `evidence_counters`.

**AI provider:** the Azure OpenAI Responses API is called with `store=false`, so Azure does not store the response object
for later retrieval. Azure's abuse monitoring is separate and may keep flagged content for human review (Microsoft
Learn, "Data, privacy, and security for Azure OpenAI"); check its terms before real customer data.

**Logs** hold request ids, tenant ids and user ids, never emails, names, document text, tokens or SQL parameters
(see `app/logs.py`). Database error messages are reduced to their SQLSTATE code. When deployed (ADR 0002):
- The app's and jobs' console output and the platform's system logs go to Log Analytics (`log-studio`). They are
  kept 30 days, then deleted.
- The ingress's HTTP access log is not collected. It would hold client IP addresses and full URLs, including the
  tokens in email links.
- The Postgres server logs each connection attempt: the database role, and the address it came from (the app's
  Azure address, or whoever tried to connect). It keeps these files 7 days, for spotting attacks on the database.
  Error details that could quote row values are switched off.

**Backups:** the database keeps 7 days of backups for point-in-time restore. A deleted row stays in them until
they expire, up to 7 days after the deletion.

**Processors.** Before launch, list them in the privacy notice with each one's terms:
- Microsoft Azure: hosting and database. While on the Student subscription these are in Azure France Central (EU), not the UK; UK hosting is a handover decision.
- Azure OpenAI: note text sent for summaries. The deployment type is not recorded in the repo, so prompts may be processed outside the UK and EU depending on the deployment type (a Global Standard deployment can process them in any Azure region worldwide; data at rest stays in the resource's geography).
- The payment provider (Stripe test mode until `unlock selling`).
- An email provider, once one is approved.

**Run the purge daily:** `python -m app.maintenance purge`. Deployed, it is the scheduled job `caj-<slug>-purge`
(03:17 UTC). It runs the same image and email settings as the web revision that serves traffic.

**Subject requests:**
- Owners: Settings → Download my data (`GET /api/account/export`).
- Members: `GET /api/account/me/export`.
- Deletion: `DELETE /api/account` (owner, whole company) or `DELETE /api/account/me` (member).
