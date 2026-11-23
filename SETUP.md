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
4. Keep both private for step 5. If the token ever leaks, send `/revoke` to @BotFather and update step 5.

## 3. Azure (10 min)

In the Azure portal, open **Cloud Shell** (the `>_` icon, Bash) and run:

```bash
az group create --name rg-ai-studio --location uksouth
SUB=$(az account show --query id -o tsv)
az ad sp create-for-rbac --name sp-ai-studio-deployer --role Contributor \
  --scopes /subscriptions/$SUB/resourceGroups/rg-ai-studio --json-auth
```

Copy the JSON the last command prints. Then in GitHub open the repo's **Settings → Secrets and variables → Actions → New repository secret** and add:

| Name | Value |
|---|---|
| `AZURE_CREDENTIALS` | the JSON from Cloud Shell |
| `AZURE_OPENAI_ENDPOINT` | your Azure OpenAI endpoint, such as `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | your Azure OpenAI key |
| `AZURE_OPENAI_DEPLOYMENT` | your deployment name, such as `gpt-5-mini` |

Optional: also add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` here as Actions secrets (the same values as step 5). The daily `azure-spend` workflow then pings you the first time spend passes 50%, 75% and 95% of the $80 cap. Without them it still writes the figures to `state/BUDGET.md` every morning.

If `create-for-rbac` fails with a permissions error (some university tenants block it), skip `AZURE_CREDENTIALS`. The team will log a hurdle and suggest another deploy route.

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
| limits run out too fast | switch Studio Run to Sonnet 5.5, change `model: opus` to `model: sonnet` in `.claude/agents/`, or run every two hours with `7 */2 * * *` |

## Daily use

The Telegram commands are in README.md. From December, use your 1 to 2 hours a day on the digest questions, demos and reviews.
