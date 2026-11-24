# Meta-review: why nothing passes G1, and how to still ship (strategist, 2026-11-24)

Sources: RANKING.md, round summaries 8-17, QUESTIONS.md. No new web research; all facts are from those files.

```
 Desk-found gap --> kill test --> incumbent ships it (or no price / no data) --> dead
   ~250 candidates       53 scored       0 reached 70       best: 68, 66, 64, 63
```

## 1. The pattern: theses tried and why each closed

| Round | Thesis | Why it closed |
|---|---|---|
| 6 | Public-data proof tests | Competition and Pay failed before any proof test ran |
| 7 | Public enforcement costs | Small single-purpose UK rivals appear within weeks of a new rule |
| 8 | Start from a priced job (docs into ledger/ERP) | System vendors and add-ons (RemitClear, LUCKINSlive) already ship it |
| 9 | Judgement outputs | New statutory markets draw 4 launches fast; yearly jobs cannot carry a subscription |
| 10 | Marketplace add-ons | Host vendor, rival or MCP connector covers it; no public price |
| 11 | Wedge check on 5 near-misses | Price and channel wedges do not beat a cheaper incumbent |
| 12 | Down-market from enterprise | SMB tools already exist; one-off consultant demand |
| 13 | Per-unit bureau prices | Prices collapse (£1-£5 a unit); software owns the regulated output |
| 14 | Small-operator pricing | Booking platforms ship dynamic pricing; uplift unprovable without real data |
| 15 | Review mining | Complaints are about price or reliability; point tools ship the job within months |
| 16 | 2027 rules | Dates slip; regulators issue free tools within weeks |
| 17 | Geographic arbitrage | Same incumbents abroad, plus stronger free regulator tools |

Common cause: every thesis was desk-only and public, so it saw what every other builder sees. None used a private signal (a real buyer conversation, a real data export).

## 2. Options for ~11 weeks left

| Option | What it is | Trade-off |
|---|---|---|
| a. New thesis: buyer-first discovery | Vishal's own finance and tax network (Q-4 option B, never tried): 5-8 short problem interviews to find a job someone already pays for, and to get a real data export | Only thesis that adds private evidence. Contacting people is ask-first, so it needs Vishal; slow if he is busy. Partly cuts across Q-6 A ("studio collects evidence itself") |
| b. Cheaper entrant, with a wedge | **pEPR packaging data (68)** vs Repackd: Starter £299 has no document extraction, Growth £799 has it. Entrant offers extraction at about £299-£399 on a deadline-driven, recurring job in Vishal's data-engineering edge. Beats the restaurant copilot (66), which has no wedge against Jelly at £129 | Round 11 found no confirmed wedge and Competition stays 3. Value shown only if extraction beats Repackd on messy spec sheets (needs the Q-9 trial and the T-14 benchmark). Needs an explicit G1 exception |
| c. Horizontal AI product via the friend | RAG receptionist or AI interviewer | Weak. Receptionist is a feature of vertical CRMs (round 5) and of Meta's own WhatsApp agent. AI interviewer for hiring is high-risk under the rubric. Win-loss interviewing scored 59. Without knowing the friend's sector there is no Reach advantage |
| d. Service-wrapped | Run the AI as a done-for-you service for one niche, with human checking | Gets paid evidence fast, but it is a different business and does not meet the "subscription product" bar |

## 3. Recommendation

Run b and a together. First, finish the Q-9 Repackd trial (a week at most). If extraction on messy documents is clearly weak, spec and build pEPR as the entrant, with the G1 bar waived for this one idea and a written kill test: if the benchmark is below 90% field accuracy or Repackd Growth handles the same documents, kill it and switch to a. In parallel, ask for 5 warm introductions from Vishal's network, to give the next idea real Pay and Reach evidence. Option c only if Vishal names the friend's sector.

Timeline: 1 week trial and benchmark, 2 weeks spec and MVP, 4 weeks to Sellable. That leaves about 4 weeks of slack for the fallback.

### Q-10 (draft, status: open)
- Decision: How should the studio reach a first Sellable product, given 0 of 53 ideas passed G1?
- Context: Seventeen desk-only scouting rounds all closed on incumbents or missing data. The closest are pEPR (68) and the restaurant copilot (66).
- Options: A) Build pEPR as a cheaper entrant to Repackd, with a one-off G1 exception, a kill test, and the Q-9 trial first; also ask for 5 introductions from your network B) Keep desk-only scouting with a new thesis, no exception C) Tell us your friend's business sector, so ideas start from a real channel D) Build the restaurant copilot against Jelly (£129 a site)
- Recommended: A, because it is the only route with a named wedge, a deadline, and a cheap early kill test, and the studio's 11 weeks cannot afford another 17 rounds
- If no answer: the studio starts pEPR desk work and spec only (reversible), and keeps scouting; no code is built and the G1 exception waits for you
