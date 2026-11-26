# Meta-review 2: what replaces scouting (strategist, T-152, 2026-11-26)

Desk reading only. Sources: CLAUDE.md, RANKING.md, META-REVIEW.md, META-REVIEW-strategist.md, Q-16 in QUESTIONS.md. No new research. I did not open the T-141 to T-151 scout files, so the pattern below rests on the ranking notes and round 18-20 headings.

## 1. Why rounds 18-24 failed

The decision to stop was logged, but nothing replaced the habit, so the scheduler kept picking the cheapest unclaimed task, which was another scout round. Each round used the same method that failed in rounds 1-17: public desk search, then the cheap kill test. That method finds only what every vendor also sees, so the survivors had an incumbent or free tool, no public price, or a deterministic core. The kill tests worked as designed. The inputs were wrong. The ranking shows the cost: retailer-deduction scored 51, leasehold scored 41 (the SI was already made). Rounds 18-20 wrote 0 files at all. More rounds will not change the result. The studio has no private signal (a buyer, a real data export) and its gate asks for proof that the desk cannot produce. A second cause is that the board had no better task. Fix that, and scouting stops.

## 2. Options for the next 1-2 weeks

```
 Now: 0 products in G2-G5, 22 parked, 1 idea at 64, 8 weeks to the target
 A build holiday-pay   B horizontal product   C Vishal-as-informant intake
```

### Option A (recommended): take holiday-pay-payroll-lookback-audit to G3 under the proof-test route
- Why this idea: it is the only one with a confirmed gap on incumbents' own pages (BrightPay, Moneysoft, Sage 50, Xero), part A of its kill test already passed, and the part B sorter is built and reviewed. It sits on Vishal's finance and payroll edge. Nothing else in the queue is within 6 points of it.
- Cost: about 2 weeks of runs. Azure OpenAI spend is pennies (Q-16 cap $2, worst case about $0.31).
- Evidence produced: a working demo on synthetic payroll exports, a measured mapping accuracy (95% needed), and a real answer to "does the demo make a payroll bureau say yes". The demo is also what Vishal's friend would see later.
- Risk: the 64 score is below the 70 bar and Pay is unproven. The government consultation response and the enforcement date are still unknown, so the market may arrive late. Mitigation: set the kill line now (below).
- First 3 board tasks:
  1. T-A1: run part B (needs Q-16 yes). Without a yes, build on part A only and freeze B.
  2. T-A2: architect and builder start from `products/_starter`. Slice: upload a payroll export (CSV), map pay items, recompute 52-week holiday pay under the 2024 rules, list exceptions with the working shown, export a sign-off pack. Synthetic data only.
  3. T-A3: qa end-to-end test of that flow, plus security and reviewer gates on the branch `p/holiday-pay-payroll-lookback-audit/...`.
- Done looks like: part B at 95% or better, the 6-step demo runs end to end in under 5 minutes on 3 synthetic payrolls, reviewer, qa and security write PASS, a demo script exists. That is G3.
- Kill line: part B under 95% after one redesign, or the government response removes the look-back duty, or nobody in Vishal's network says the job is paid for once selling unlocks. Then stop and go to C.

### Option B: horizontal product on Vishal's edges (RAG answer desk for accountancy practices)
- Idea: a practice-knowledge RAG that answers staff and client queries from the firm's own engagement letters, HMRC manuals and working papers, with citations. Competition exists (Karbon and TaxDome AI, ChatGPT with pasted text), so the wedge would be price (about £49 a month, one practice) and a tax-manual grounding.
- Cost: about 2 weeks. Evidence: a demo with a retrieval benchmark. The ranking notes say a chatbot with the terms is the cheapest substitute, so Pay evidence would be weak.
- Risk: high. It is the pattern that killed 30 ideas (AI over documents is now a free feature). Not recommended before A.

### Option C: Vishal-as-informant intake (no outside contact)
- Idea: a 30-minute structured intake. Vishal lists jobs he has seen businesses pay people, bureaus or consultants for in finance, tax and data, with the price, how often, and what data exists. The studio then runs the existing kill tests on those.
- Cost: about 30 minutes of Vishal time and 1 run. It is a private signal and involves no contact, so it is allowed.
- Evidence: real Pay and frequency numbers, which is the weakest score in every idea so far.
- Risk: it is one person's experience, and it may confirm nothing. Cheap, so run it alongside A.

## 3. What the Lead can decide, and what needs Vishal

The Lead can decide alone and log it (reversible, no money, no contact):
- Run A's build tasks on part A (free), and adopt C as a request.
- Cancel scheduled scout rounds in the board (remove the scouting tasks, or mark them "blocked by META-REVIEW-2"). Add a rule: no scout task unless a new private input exists (an intake answer, a trial, a data export).
- Re-run the holiday-pay check monthly for the government response.

Needs Vishal (draft question):

### Q-17 (draft)
- Decision: May the studio build the top parked idea (holiday-pay look-back, 64) to G3 although it has not passed G1 (70)?
- Context: 0 of 55 ideas passed. Part A of the proof test passed. The build uses synthetic data, nothing public, no contact. G3 only proves the demo, and the product can still be killed at G4.
- Options: A) Yes, as a one-off exception with the kill line above (recommended) B) No, keep waiting for 70 and scout only with new private input C) Yes, but only after the government publishes its response
- Recommended: A. Waiting leaves the studio with no product for the target.
- If no answer: after 12 hours it defaults to A, as it is reversible. This is a gate change, so the Lead logs it in DECISIONS.md.

Q-16 (the $2 spend for part B) stays open. Mention it in the same message, since part B is the first task of option A. It is ask-first, so it waits for a yes.
