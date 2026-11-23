# Questions for Vishal

Add new questions at the bottom. The Desk sends up to 3 per digest, most important first.

Format:

    ## Q-<n> (status: open)
    - Decision: one sentence
    - Context: two lines at most
    - Options: A) ... B) ... C) ...
    - Recommended: A, because ...
    - If no answer: A after 12 hours (reversible) | waits (ask-first list)

Status moves through: open → sent <UTC> → answered | defaulted.

## Q-1 (status: open)
- Decision: How should this session's work reach `main`, where the scheduled runs start?
- Context: Today's work (kit moved to the repo root, 15 ideas, T-2 spend report, T-6 starter) is on branch `vishal/blissful-cray-v1s3ys`. `main` still has the old nested `files/ai-product-studio/` layout, so scheduled runs would fail at step 1.
- Options: A) You merge the branch into `main` on GitHub (a PR or a fast-forward), and switch on "Allow unrestricted branch pushes" for the scheduled tasks B) Ask this session to open a PR for you to review and merge C) Keep the branch separate for now, and don't start the scheduled tasks yet
- Recommended: A, because the branch only adds to main (no conflicts) and the scheduled runs need it to work at all
- If no answer: waits (needs you on GitHub)

## Q-2 (status: open)
- Decision: Does the studio have any way to sell outside the UK (India, Indonesia or elsewhere)?
- Context: The validator scored every India and Indonesia idea 2 or 3 out of 10 on reach, because selling goes through your friend's UK business. Without a channel there, those ideas can't reach the 70-point bar however good the evidence gets.
- Options: A) No: prioritise UK and English-speaking ideas, and keep non-UK ideas parked B) Yes: I (Vishal) can sell in India myself, so score Indian ideas with that channel C) Yes, through a partner I'll name
- Recommended: A, because it matches the plan in CLAUDE.md, and B or C can be switched on later
- If no answer: A after 12 hours (reversible)

## Q-3 (status: open)
- Decision: 25 ideas have been scored and none has reached the 70-point G1 bar (best: pEPR packaging data at 68). What should the studio do while pEPR's evidence comes in?
- Context: pEPR is 2 points short. The validator thinks it reaches about 73 if competitor pages confirm the spec-sheet gap (T-13, desk research, can start now) and an extraction benchmark hits 90% (T-14, needs your Azure OpenAI setup). The shared product starter is nearly through its review gates.
- Options: A) Start specification work on pEPR now (customer profile, core flow, MVP scope, architecture and cost), with no product code until G1 passes B) Keep the rules as they are: only desk research and new scouting until an idea passes C) Lower the G1 bar to 65 for the first product, so pEPR (68) and the restaurant margin copilot (66) can go ahead now
- Recommended: A, because the spec work is cheap and reversible, it makes the product buildable the day the benchmark passes, and it keeps the 70-point bar intact
- If no answer: A after 12 hours (reversible)

