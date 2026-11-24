# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- [studio] Telegram messages restyled as you asked: shorter, bold sections, buttons show the option words. Tell me anything you'd change.
- [_starter] Starter app: 104 screen tests added, 3 web fixes and safer image builds merged; a sign-in redirect weakness found by the tests is fixed.
- [studio] Got your answers: scouting stays broad; Azure demo spend approved for when a product is ready (you'll still need to flip one setting then).
- [ideas] Scout round 5: 9 candidates dropped (already sold), 2 ideas killed (tour-operator rate loader, wedding venue replies). Still no idea at the bar.
- [_starter] Starter app can now reach Azure AI without a stored key (managed identity); reviewed and merged. Cookie tests tightened too.
- [studio] Azure AI now answers from the studio: a test call worked. The starter needs a small update to talk to it (queued), and the only model set up is a premium one, so we'll keep usage tiny until a cheaper one is added.
- [ideas] MTD prep pilot benchmark: AI reads clean statements and CSVs well (84-94% of categories right) but doesn't yet halve review time once its confident mistakes are counted; scans and photos untested because the premium model ran out of room. A full test needs a cheaper model (question Q-7).
- [_starter] Starter app can now talk to the studio's Azure model (new API style), keeps no copy of prompts on Azure, and CI now refuses an AI budget priced above $6.10 a month. Reviewed and merged.
- [_starter] Two earlier starter fixes (cleaner web page serving, pinned base images) were reviewed and passed.
- [_starter] Safer Azure sign-in for the starter's AI calls: a slow Azure login endpoint can no longer stall every user past the page's time limit. Reviewed twice and merged.
- [_starter] Starter AI calls hardened: cut-off answers are no longer saved as if complete, and odd replies from Azure still count against the spending caps. Reviewed and merged.
- [ideas] Scouting round 6 tried "only ideas we can prove from public data": 4 ideas written, all 4 killed (51-57). Still 0 of 39 ideas at the bar. Q-6 now defaults to B (build the restaurant margin copilot as a cheaper entrant) if you don't answer; C (tell us your friend's sector) is still the recommendation.
- [_starter] Small starter tidy-ups merged (missing-asset 404s, all page routes tested, grouped GitHub Actions update PRs, Node 22 end-of-life note). Reviewed and merged.
- [_starter] Sign-in now holds up under bursts: junk or rate-limited requests can no longer queue for the password-check slots and block real users. Reviewed twice and merged.
- [_starter] Test runs no longer trip over each other when several agents test at once (each run gets its own throwaway database). Reviewed twice and merged.
- [_starter] Starter can now share sign-in rate limits across several app copies through Redis (optional; nothing new on Azure), and two test-tooling fixes landed. Both reviewed twice and merged.
- [restaurant-margin-copilot] Prep for Q-6 option B: a draft spec and a 15-tool competitor price check are written and passed the validator. Honest position: less product for much less money (about £39-£69 a site vs Jelly's £129) plus a weekly 'here are the fixes' message; Jelly already does price alerts. Building waits for your Q-6 answer (default B tonight), and live invoice reading needs the cheaper model in Q-7.
- [_starter] Starter: a slow Redis can no longer tie up the threads that serve other pages (its own small thread pool), and the web app now states the exact Node version it needs. Reviewed and merged.
- [_starter] Starter: if Redis gets slow, sign-in checks now wait at most 1 second and then fall back to the built-in limiter, instead of queueing forever. Reviewed and merged.
- [_starter] Passwordless database sign-in: design approved by the security check, and the app side is built, reviewed and merged (the app uses an Azure identity token instead of a stored database password). Infrastructure changes are next. One new question (Q-8): let deploys sign in to Azure only from main.
