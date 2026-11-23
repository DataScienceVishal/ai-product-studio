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

