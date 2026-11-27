# T-163 build round 2

Changes: route trip check now reads on the request session (`ensure_ai_enabled(provider, db)`, `check_persisted_trip(db)`, `TripStore.tripped(fp, db)`), no second pooled connection; `complete()` still checks (own session, after reserve committed). N1 config-change test now changes only the deployment (chat -> chat2, same explicit 2.0) and asserts checked_price is not None. N2 neutral read-error message (code unchanged). N4 BRIEF.md says 0008. N5 model tripped_at gets server_default=func.now(), matching migration 0008.
New test: test_route_trip_check_uses_the_request_session_not_a_second_connection (pool 1, overflow 0: healthy 200 under 8 s, tripped 503).
Full backend suite (Postgres 16 local): 720 passed, 1 skipped, 0 failed (alembic check clean).
Mutation: route reverted to no db -> new test fails (10.5 s timeout); deployment dropped from fingerprint -> config test fails. Both restored.
