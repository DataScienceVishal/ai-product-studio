# Data inventory and retention (starter)

What the starter stores, why, for how long, and how it is deleted. Products copy this file, add their own
tables, and keep it current. It supports UK GDPR and India DPDP basics. It isn't legal advice: get a legal
review before launch.

| Table | Personal data | Why | Kept until | Deleted by |
|---|---|---|---|---|
| `tenants` | company name | the customer account | account deletion; accounts whose owner never verified their email are removed after 30 days when verification is required | owner: Settings → Delete account; purge job |
| `users` | email, role, argon2 password hash | sign-in | account deletion, or the member leaves or is removed | owner (whole account or a member), member (themselves) |
| `auth_sessions` | link to a user, hashed token | staying signed in | expiry (7 days), sign-out, password reset | purge job; sign-out; cascade |
| `password_resets` | link to a user, hashed token | password reset | 7 days after use or expiry | purge job; cascade |
| `email_verifications` | link to a user, hashed token | proving the address | 7 days after use or expiry | purge job; cascade |
| `invitations` | invitee email | adding team members | 30 days after accepted, cancelled or expired; at once when the member is removed or leaves | purge job; member removal; cascade |
| `notes` (example) | whatever users type | the product's core job | the user or the account deletes it | user; cascade |
| `subscriptions` | provider customer and subscription ids | billing | account deletion (the provider customer is deleted first) | account deletion |
| `billing_events` | provider event ids only | applying each webhook once | 400 days | purge job |
| `ai_usage` | tenant id, token counts | per-customer caps, the studio-wide daily AI budget, cost | 400 days; on account deletion the tenant link is cleared but the counts stay, so the global budget still counts them | purge job |

**Logs** hold request ids, tenant ids and user ids, never emails, names, note text, tokens or SQL parameters
(see `app/logs.py`). Database error messages are reduced to their SQLSTATE code.

**Processors.** Before launch, list them in the privacy notice with each one's terms:
- Microsoft Azure: hosting and database, UK region.
- Azure OpenAI: note text sent for summaries.
- The payment provider (Stripe test mode until `unlock selling`).
- An email provider, once one is approved.

**Run the purge daily:** `python -m app.maintenance purge`, for example as a scheduled Container Apps job (T-7).

**Subject requests:**
- Owners: Settings → Download my data (`GET /api/account/export`).
- Members: `GET /api/account/me/export`.
- Deletion: `DELETE /api/account` (owner, whole company) or `DELETE /api/account/me` (member).
