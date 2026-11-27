# T-163 NEXT (hand-off from run 20261126T231926Z-run-6fea, 2026-11-27T00:05Z)

State: branch p/_starter/T-163 = T-162 (merged to main) + bf7d109 (M1 persisted trip, L1 explicit price) + reviewer CHANGES (reviews/T-163-review.md). Not merged.

Next run:
1. Merge origin/main into this branch first (main has T-162 merge + T-162-review.md; no conflicts expected).
2. Fix Blocking 1: the route-level trip check (routes/notes.py:113 -> TripStore.tripped, ai.py:105) opens a second pooled connection while the request session holds one; >=10 concurrent AI requests starve the pool and fail closed with a false 503. Preferred fix: pass the request's db session into ensure_ai_enabled (read the trip on the caller's session); keep the check in complete(). Add a regression test with db_pool_size=1, db_max_overflow=0 and a healthy model -> 200.
3. Non-blocking, do in the same round: N1 config-change test must change only the deployment between two priced names; N2 read-error message should not blame configuration; N4 BRIEF.md migrations up to 0008; N5 align tripped_at default model vs migration.
4. Full backend suite on the merged tree (`cd products/_starter/backend && /path/venv/bin/python -m pytest -o addopts="" -q`), then reviewer re-check, then merge to main.
