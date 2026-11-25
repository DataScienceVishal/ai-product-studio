# Setup (about 40 minutes, once)

Eight steps: pick the account, make the repo, make the Telegram bot, prepare Azure, check usage settings, create the cloud environment, create two scheduled tasks, start the first run.

Never paste a key or token into a chat with Claude. They only go where these steps say.

## 0. Use a personal Claude plan for the studio

Run the studio on a personal Pro or Max plan in your own name, not your Northeastern seat:

- Northeastern's appropriate-use policy doesn't allow commercial use of university systems without written approval from the Provost and General Counsel.
- On Enterprise, cloud sessions (which scheduled tasks run on) need a premium or Chat + Claude Code seat, and only an organization admin can add network secrets.
- It keeps the studio's usage completely separate from your studies.

Pro works in shorter bursts; Max gives the team much more room. A personal plan has a weekly limit as well as the five-hour one. The team simply waits and resumes.

## 1. GitHub repo (5 min)

1. On github.com, create a **private** repo named `ai-product-studio`, with no README or .gitignore.
2. On your Mac, unzip the kit and push it:
   ```bash
   cd ~/Downloads/ai-product-studio
   git init && git add . && git commit -m "studio: initial kit"
   git branch -M main
   git remote add origin https://github.com/DataScienceVishal/ai-product-studio.git
   git push -u origin main
   ```
3. Open claude.ai/code with your personal account. The first visit asks you to connect GitHub: give it access to `ai-product-studio`. If it asks you to install the Claude GitHub App, install it on this repo.

## 2. Telegram bot (5 min)

1. In Telegram, open @BotFather, send `/newbot`, and pick a name and a username ending in `bot`. Copy the token.
2. Open your new bot and send it `hi`.
3. In a browser, open `https://api.telegram.org/bot<TOKEN>/getUpdates` with your token in place of `<TOKEN>`. Find `"from":{"id":` followed by a number. That number is your chat id.
4. Keep both private for step 5. If the token ever leaks, send `/revoke` to @BotFather and update step 5, and also the `TELEGRAM_BOT_TOKEN` Actions secret if you added it in step 3.

## 3. Azure (10 min)

Azure for Students only allows new resources in `francecentral`, `swedencentral`, `spaincentral`, `polandcentral` and `italynorth`. The studio uses `francecentral`. The resource group `rg-ai-studio` itself is in `uksouth` (a group's region only holds its metadata, so that is fine; the resources in it go to francecentral).

GitHub signs in to Azure with **OIDC**: no password or JSON secret is stored anywhere. In the Azure portal, open **Cloud Shell** (the `>_` icon, Bash) and run:

```bash
az group create --name rg-ai-studio --location uksouth   # skip if it exists
SUB=$(az account show --query id -o tsv)
az identity create --resource-group rg-ai-studio --name id-github-deploy --location francecentral
PRINCIPAL=$(az identity show -g rg-ai-studio -n id-github-deploy --query principalId -o tsv)
az identity federated-credential create --resource-group rg-ai-studio --identity-name id-github-deploy \
  --name github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:DataScienceVishal@102427114/ai-product-studio@1468636475:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange
az role assignment create --assignee-object-id $PRINCIPAL --assignee-principal-type ServicePrincipal \
  --role Contributor --scope /subscriptions/$SUB/resourceGroups/rg-ai-studio
# Print the three values for GitHub:
az identity show -g rg-ai-studio -n id-github-deploy --query clientId -o tsv
az account show --query tenantId -o tsv
echo $SUB
```

Then in GitHub open the repo's **Settings → Secrets and variables → Actions → New repository secret** and add:

| Name | Value |
|---|---|
| `AZURE_CLIENT_ID` | the identity's client id (first printed value) |
| `AZURE_TENANT_ID` | the tenant id (second value) |
| `AZURE_SUBSCRIPTION_ID` | the subscription id (third value) |
| `AZURE_OPENAI_ENDPOINT` | your Azure OpenAI endpoint, such as `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | your Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT` | your deployment name, such as `gpt-5-mini` |

These three IDs are not secrets in themselves; the trust lives in the federated credential. That credential matches **only** runs on `main` (`...:ref:refs/heads/main`), so the Azure workflows sign in from `main` only and refuse to run anywhere else.

**Do not add `environment:` to a job that signs in to Azure.** A job with an environment gets the subject `repo:DataScienceVishal@102427114/ai-product-studio@1468636475:environment:<name>`, which does not match, and the login fails. If you later want a GitHub environment (for example `production` with a required reviewer), add one more federated credential first:

```bash
az identity federated-credential create --resource-group rg-ai-studio --identity-name id-github-deploy \
  --name github-env-production \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:DataScienceVishal@102427114/ai-product-studio@1468636475:environment:production \
  --audiences api://AzureADTokenExchange
```

Optional: also add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` here as Actions secrets (the values from step 2). The daily `azure-spend` workflow then pings you when spend first passes 50%, 75% and 95% of the $80 cap, and when the report fails. Without them, alerts still reach you through the next digest.

The daily spend report has its own read-only identity, `id-github-spend`, so a scheduled job never holds deploy rights. Create it in the same Cloud Shell (it reuses `$SUB` from above; run `SUB=$(az account show --query id -o tsv)` first if you opened a new shell). Its federated credential uses the same subject as `id-github-deploy` above, including the immutable IDs (`DataScienceVishal@102427114`, `@1468636475`), and trusts `main` only:

```bash
az identity create --resource-group rg-ai-studio --name id-github-spend --location francecentral
SPEND_PRINCIPAL=$(az identity show -g rg-ai-studio -n id-github-spend --query principalId -o tsv)
az identity federated-credential create --resource-group rg-ai-studio --identity-name id-github-spend \
  --name github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:DataScienceVishal@102427114/ai-product-studio@1468636475:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange
for ROLE in "Reader" "Cost Management Reader"; do
  az role assignment create --assignee-object-id $SPEND_PRINCIPAL --assignee-principal-type ServicePrincipal \
    --role "$ROLE" --scope /subscriptions/$SUB/resourceGroups/rg-ai-studio
done
az identity show -g rg-ai-studio -n id-github-spend --query clientId -o tsv   # the value for AZURE_SPEND_CLIENT_ID
```

Add that client id as one more Actions secret, `AZURE_SPEND_CLIENT_ID`. The tenant and subscription secrets are shared. Both roles are scoped to `rg-ai-studio` only. Once the secret and the shared tenant and subscription secrets are set, `azure-spend` signs in as `id-github-spend` and never uses the deploy identity. Until then it falls back to `id-github-deploy`.

Temporary fallback, only if you already created one: an Actions secret `AZURE_COST_CREDENTIALS` (service principal JSON) is used only when no OIDC secrets are set. Once `id-github-spend` works (one green azure-spend run), delete it, and delete the old `AZURE_CREDENTIALS` secret and its client secret (`sp-ai-studio-deployer`) too.

Put your Azure OpenAI resource in `rg-ai-studio` (or move it there), so its token spend counts in the daily report. The report covers that resource group only.

After the secrets are in place and the studio's work is on `main`, run the **azure-spend** workflow once by hand (repo → Actions → azure-spend → Run workflow). Then open `state/BUDGET.md`: it either shows figures or says why it can't get them (Microsoft's docs disagree on whether Azure for Students supports the Cost Management API). From then on, a bot (`github-actions[bot]`) commits the report to `main` every morning.

If `az identity create`, the federated credential or the role assignment is refused by policy (for example a region outside the allowed list above), tell the team: it logs a hurdle and suggests another deploy route.

If Cost Management offers **Budgets** for your subscription, add one for $80 with email alerts at 50%, 75% and 95%. Either way, Azure for Students switches off when the credit runs out, so it can't overspend.

## 4. Claude usage settings (1 min)

At claude.ai/settings/usage, keep usage credits off. With them on, runs carry on into paid usage after your limits.

## 5. Cloud environment (5 min)

At claude.ai/code, open the environment selector under the message box and choose **New environment**:

- **Name:** `studio`
- **Network access:** Full. The scouts need the open web, which is why every credential here is scoped narrowly.
- **Environment variables:**
  ```
  TELEGRAM_BOT_TOKEN=<your bot token>
  TELEGRAM_CHAT_ID=<your chat id>
  AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
  AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
  AZURE_OPENAI_API_KEY=proxy-injected
  ```
  Anyone who uses this environment can read these values. It's your personal environment, so that's only you, and the bot ignores everyone except your chat id.

Save, then open the environment again and add the Azure OpenAI key as a **network secret**, so runs can use the key without ever seeing it:

- **Name:** Azure OpenAI
- **Allowed websites:** the host in your endpoint, such as `<resource>.openai.azure.com` (use whatever host your endpoint shows)
- **Custom headers:** change the header name to `api-key`, clear the Prefix, and paste your key as the Value

## 6. Two scheduled tasks (10 min)

Go to claude.ai/code/routines and click **New task**. It may say New routine; if it offers Create with Claude or Set up manually, choose Set up manually. Labels can differ slightly, but the fields are the same.

**Task 1: Studio Run**
- **Name:** Studio Run
- **Prompt:** everything below the line in `prompts/studio-run.md`
- **Model:** Opus 5.5, effort medium to start
- **Advanced settings:** repository `ai-product-studio`, cloud environment `studio`
- **Connectors tab:** remove all; the studio doesn't use them
- **Trigger:** Schedule, hourly. If you can set the minute, use Custom `7 * * * *`

**Task 2: Studio Desk**
- **Name:** Studio Desk
- **Prompt:** everything below the line in `prompts/studio-desk.md`
- **Model:** Sonnet 5.5; digests don't need Opus
- Same repository, environment and connectors as Task 1
- **Trigger:** create it with any schedule, then **Edit → Custom** and enter `CRON_TZ=Europe/London 57 7,14 * * *`. Add a second schedule trigger with **+** and enter `CRON_TZ=Europe/London 27 19 * * *`. If it won't accept a second schedule, duplicate the task as "Studio Desk evening" with that cron. If it rejects the `CRON_TZ=` prefix, drop it: the times are then UTC, which matches London in winter and runs an hour late in summer.

The times start a few minutes early so digests land by 08:00, 15:00 and 19:30. If you see **Allow unrestricted branch pushes** for the repo, switch it on: the studio commits its state to `main`.

## 7. First run (5 min)

1. Open **Studio Run** and click **Run now**, then open the run to watch. You should get a hello on Telegram during it, because task T-1 checks every connection.
2. When it finishes, click **Run now** on **Studio Desk**. Your first digest arrives, with any setup problems listed under Hurdles.
3. Send `status` to the bot to test the round trip. The reply comes within the hour.

## If something's off

| Symptom | Fix |
|---|---|
| tg.py says a variable is not set | step 5, environment variables |
| tg.py reports a network error | step 5, network access must be Full |
| Azure OpenAI returns 401 | step 5, network secret host and the `api-key` header name |
| a run "didn't start" | GitHub access from step 1, or you're at a usage limit |
| digests arrive at the wrong hour | the `CRON_TZ=` prefix in step 6 |
| a workflow shows instant failures named after its file path | GitHub rejected the workflow file; open the run to see the line, fix it, push |
| `state/BUDGET.md` says the spend report is unavailable | the reason is on the Status line; if it's the offer, read the credit in the Azure Sponsorships portal instead |
| limits run out too fast | switch Studio Run to Sonnet 5.5, change `model: opus` to `model: sonnet` in `.claude/agents/`, or run every two hours with `7 */2 * * *` |

## Daily use

The Telegram commands are in README.md. From December, use your 1 to 2 hours a day on the digest questions, demos and reviews.
