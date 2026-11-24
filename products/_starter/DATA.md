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
| `notes` (example) | whatever users type | the product's core job | the user or the account deletes it | user; cascade |
| `subscriptions` | provider customer and subscription ids | billing | account deletion (the provider customer is deleted first) | account deletion |
| `billing_events` | provider event ids only | applying each webhook once | 400 days | purge job |
| `ai_usage` | tenant id, token counts | per-customer caps, the studio-wide daily AI budget, cost | 400 days; on account deletion the tenant link is cleared but the counts stay, so the global budget still counts them | purge job |

**AI provider:** the Azure OpenAI Responses API is called with `store=false`, so Azure keeps no copy of the prompt
or the answer for the response object (Azure's separate abuse-monitoring retention is covered in ADR 0002).

**Logs** hold request ids, tenant ids and user ids, never emails, names, note text, tokens or SQL parameters
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
- Microsoft Azure: hosting and database, UK region.
- Azure OpenAI: note text sent for summaries.
- The payment provider (Stripe test mode until `unlock selling`).
- An email provider, once one is approved.

**Run the purge daily:** `python -m app.maintenance purge`. Deployed, it is the scheduled job `caj-<slug>-purge`
(03:17 UTC). It runs the same image and email settings as the web revision that serves traffic.

**Subject requests:**
- Owners: Settings → Download my data (`GET /api/account/export`).
- Members: `GET /api/account/me/export`.
- Deletion: `DELETE /api/account` (owner, whole company) or `DELETE /api/account/me` (member).
