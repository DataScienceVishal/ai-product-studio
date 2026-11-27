# Review: T-186 (slice S2, ingest and retrieval)

- Branch: `p/sme-council-tender-drafting/T-186` at `1cceaba`, diff against `origin/main` (20 files, +1917/-15)
- Reviewer: reviewer agent, 2026-11-27
- **Verdict: CHANGES** (one must-fix, F1. Everything else is small and can ship with the fix or go to the board.)

## Evidence (run by the reviewer on this exact tree)

| Check | Result |
|---|---|
| Fresh Python 3.12 venv, `uv pip install --require-hashes -r requirements-dev.txt` | installs, exit 0 |
| Fresh venv, `uv pip install --require-hashes -r requirements.txt` (prod) | installs, exit 0 (lxml 6.2.0, pypdf 6.21.4, python-docx 1.2.0, python-multipart 0.0.34) |
| `python -m pytest -q -o addopts=""` against a new Postgres 16 DB | **892 passed, 1 skipped**, 1 warning, 178.85 s (matches the builder) |
| `alembic upgrade head`, `check`, `downgrade -1`, `upgrade head`, `check` on an empty DB | all OK, "No new upgrade operations detected" twice |
| E-n concurrency probe: 16 threads at a barrier, `next_numbers(db, tenant, 5)` each, every 4th rolls back | 0 errors, 60 committed numbers, 60 unique, max 60 (no gaps from rollbacks, no duplicates) |
| tsquery fuzz (`&`, `|`, `!`, `<->`, `:*`, quotes, backslashes, URLs, emails, only punctuation) through the exact `replace(plainto_tsquery(...)::text,'&','|')::tsquery` expression | no syntax error on any input; operators in user text never survive `plainto_tsquery`; lexemes stay quoted; empty queries go to NULL |
| XXE probe: DOCX whose `word/document.xml` has `<!DOCTYPE ... SYSTEM "file:///...secret">`, UTF-8 and UTF-16 | UTF-8 refused `xml_entities`; UTF-16 passes the pre-check (F2) but lxml does not expand the entity (text cut at `&x;`, secret not present) |

## What is good

- The untrusted-file path matches DESIGN 4.1: magic bytes only (`ingest.py:58-75`), content type never used, extension never used, the stored filename stripped of path parts and control characters, and the bytes in a `TemporaryDirectory` that is removed in every path.
- The worker is started by absolute path with `-I`, `env={}`, `stdin=DEVNULL`, `cwd` the temp dir, and a 45 s wall timeout. `RLIMIT_AS` and `RLIMIT_CPU` are set in `main()` before `pypdf` or `docx` is imported (`parse_worker.py:158`, the imports sit inside the parse functions). A crash, signal (SIGXCPU), non-zero exit, oversize output or bad JSON all become `parse_failed`. Unknown codes from the child are mapped to `parse_failed` (`ingest.py:107`), so the child can't choose the HTTP message.
- The zip check runs before `docx.Document()` (`parse_worker.py:117`). Lying `file_size` headers are capped by `zipfile` itself (it stops at the declared size and fails the CRC), and `RLIMIT_AS` stops anything else.
- Tenant isolation: every new route goes through `get_scoped`/`scoped`. The raw retrieval SQL filters `tenant_id` on both `evidence_items` and `source_documents`, and the join is on `(tenant_id, id)`. The question is a bound parameter, so there is no SQL injection. Tests cover cross-tenant search, cross-tenant delete (404) and duplicate sha per tenant.
- Delete: `delete_row` turns the `fk_requirements_document` NO ACTION failure into 409 `document_in_use`. Other integrity errors are re-raised, not swallowed. There are no ORM relationships, so the database cascade order decides, and the pack-delete-with-own-citations case works (tested).
- The E-n counter is an advisory transaction lock plus an upsert. My probe confirms no duplicates under contention.
- The tests test behaviour: real generated PDF and DOCX fixtures for every refusal, "the server is still up" after each one, and "nothing stored" after a refusal.

## Critical issues

### F1 (High, must fix): no global cap on concurrent parse workers, so one tenant can take the 1 GiB container down
`app/routes/tender.py:119` and `:134`, `app/tender/ingest.py:85`.

- The only throttle is `limiter.check(upload:{tenant}, 10, 3600)`. It counts requests, not concurrency. One signed-in user can send 10 uploads at the same moment and every one starts a worker.
- Each worker may grow to `RLIMIT_AS` 512 MiB and burn 30 s of CPU. The app runs as one container with 0.5 vCPU and 1 GiB (`infra/main.bicep:97-98`, which already budgets memory for the 2 password-hashing slots). Two or three crafted PDFs (for example a FlateDecode stream that inflates in memory) push the cgroup into the OOM killer, and it can kill uvicorn, not the child. Section 7 promises "the server stays up". Several tenants make it worse, because the cap is per tenant.
- The routes are sync `def`, so each upload also holds an AnyIO threadpool thread (40 by default, shared with every other sync route) and a pooled DB connection for up to 45 s. `get_db` has already run SELECTs, so the connection sits idle in a transaction. Ten parallel uploads can therefore starve sign-in and every other route too.
- **Fix:** add a process-wide `threading.BoundedSemaphore(settings.parse_workers)`, default 1 (2 at most on 1 GiB), around `run_worker`. Acquire it with a short timeout, and if it isn't free, refuse with 503 or 429 `busy` ("Another file is being read; try again in a minute"). This mirrors the starter's hashing-slot capacity (`test_async_hash_capacity`). Better still, end the read transaction (`db.commit()` or `db.rollback()`) before the worker runs, so no connection is held while parsing. Add a test that starts N+1 parses at once with a slow fake worker and checks that the extra one gets the busy refusal.

## Suggestions (not blocking)

- **F2 (Low): the XXE/DTD pre-check can be bypassed** (`parse_worker.py:107-111`). It only looks at parts whose names end in `.xml` or `.rels` (case-sensitive), and it searches for ASCII `<!DOCTYPE`/`<!ENTITY`. A UTF-16 part, an upper-case `.XML`, or a main part with another extension (python-docx follows `_rels/.rels`, not the name `word/document.xml`) is not checked. I confirmed the UTF-16 case. The real defence holds, because python-docx's parser uses `resolve_entities=False` (and lxml's `no_network` default), so nothing leaks. Still, the refusal promised in DESIGN 4.1 isn't reliable. Fix: check every entry, and also look for the UTF-16 forms (or decode via the BOM or XML declaration before searching).
- **F3 (Low): the macro refusal goes by name only** (`parse_worker.py:103`). A renamed VBA part slips through. Also refuse when `[Content_Types].xml` holds `macroEnabled` or `vbaProject`. This is cosmetic, because macros never run.
- **F4 (Low): cap races.** The pack-size cap (`:127-132`) and the pages-per-day cap (`:138-142`) are checked and then written without a lock, so parallel uploads can overshoot them. Deleting a document also refunds its pages for the day. F1's semaphore removes most of this. Alternatively, take the tenant advisory lock before the checks.
- **F5 (Low): worker hardening.** Also set `RLIMIT_FSIZE` (0 or small), `RLIMIT_NPROC` and `RLIMIT_NOFILE` in `set_limits`. The child has the same uid, filesystem and network as the app. That's acceptable for pure-Python parsers, but these limits are free.
- **F6 (Product, Low): the tender image-only rule will refuse many real council PDFs.** Any PDF page under 30 characters fails the whole tender file (`tender.py:143`), and blank separator pages and logo-only covers are common. This follows DESIGN 4.1, so it is not a code defect, but the Lead should know before the demo packs are chosen. One option is to refuse only when most pages are image-only, and warn otherwise.
- **F7 (Low): retrieval candidates are capped at 100 before the boost** (`evidence.py` `CANDIDATES`). A passage holding the exact code but with a low ts_rank can miss the boost in a large library. This is fine at demo scale. Note it for the S-tuning slice.
- **F8 (Nit): `'&'` inside URL or path lexemes is rewritten to `'|'`**, so such lexemes can never match. That is harmless. A more exact fix is a regex that replaces only ` & ` between quoted lexemes.
- **F9 (Nit): the delete route differs from DESIGN section 5.** DESIGN lists `DELETE /evidence/documents/{id}`, but the code has `DELETE /api/documents/{id}`, which serves both kinds. Update DESIGN section 5, or the frontend slice will guess wrong. Any member, not only the owner, can delete packs and documents. That needs a one-line decision in DECISIONS.md.
- **F10 (Design, for S6): evidence document delete is a hard delete** (the evidence_items rows cascade), while DESIGN 4.2 and R4 speak of `deleted_at`. The gate still blocks because the numbers are never reused, but the cited passage text is gone for the appendix and audit. Decide on soft delete versus hard delete before S6.
- **F11 (Nit): `clean_filename` keeps bidi control characters** (U+202E and friends). Strip the Unicode `Cf` category to stop filename spoofing in the UI.

## Top issue
F1: there is no process-wide limit on concurrent parse workers. Ten parallel uploads from one tenant, each allowed 512 MiB, can OOM the 1 GiB container and starve the threadpool and DB pool. Add a bounded semaphore (1 to 2) with a busy refusal, and release the DB transaction before parsing.
