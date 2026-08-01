# Task 3 Implementer Report: Durable Local Story Generation

Status: **COMPLETE**

Task base: `a4870e9`

Implementation commit: `3bf3542 feat: make local story generation durable`

Review-hardening commit: `1c4b526 fix: harden durable generation recovery`

Migration timestamp commit: `89be00a fix: type legacy migration timestamp`

Frontend retry-stage commit: `57be661 fix: retry ambiguous story commit directly`

## Architecture and boundaries

- The existing `chapters.revision` pointer and `(chapter_id, revision, panel_number)` panel key remain the readable-revision boundary.
- `generation_runs` is the persisted job boundary. A run owns one chapter, selected idea, scoped idempotency key, target revision, stage, terminal state, safe error code/reference, and new-file manifest.
- FastAPI keeps the single existing `POST /chapters/commit` path and dispatches one local `BackgroundTasks` worker only when the database creates a new run. No queue, Redis, Celery, plugin framework, or second API path was added.
- `services/generation.py` is the one-machine coordinator. It validates the stored chapter/classroom/idea, obtains a strict OpenAI script through the existing provider contract, then performs BFL submit, poll, download, PNG validation/decompression, staging, durable finalization, and one SQLite swap.
- Provider delivery and polling URLs remain transient in memory. Only `story-images/...` object paths are eligible for ready panel rows.
- All new images are finalized locally before the database transaction. The transaction deletes prior panel rows, inserts the complete sequential target revision, advances the chapter revision, and succeeds the run atomically. Old files are deleted only after that commit.
- Failed-run cleanup and successful old-media retirement use the persisted run artifact manifest. Only paths actually deleted are cleared. Unresolved paths survive restart, block readiness, and are retried during startup without changing the readable revision.
- Startup deliberately fails `queued`/`running` runs as `interrupted`, restores the previous readable revision, retries every pending artifact manifest, and clears staging. It does not attempt provider resume.

## Schema and API changes

Migration `0002_generation_durability` adds only the missing durable run contract:

- `selected_idea_id`
- `stage`
- `error_code`
- `artifact_paths`
- a partial unique index allowing at most one `queued`/`running` run per chapter

The existing globally unique stored idempotency column is retained. Client keys are SHA-256 scoped with the chapter ID before storage, giving chapter-local retry semantics without exposing the client key.

`POST /chapters/commit` accepts additive optional `idempotency_key` input and returns additive `run_id`. Legacy callers receive a deterministic chapter/revision key. An identical retry returns the existing run without scheduling work; a different key while work is active returns `409`.

The frontend creates one UUID per chapter/idea attempt and retains both its key and confirmed stage across ambiguous failures. A failed choose remains at `choose`; once choose resolves, a lost commit response remains at `commit` and retries commit directly without repeating choose. It rotates the key only after observing a terminal result or creating a new chapter. Existing active chapter/run claims prevent response-loss retries from starting another provider job.

`GET /ready` remains provider-call-free and now reports:

- persistence availability;
- migration-head state;
- data-directory writability;
- storage availability;
- generation-artifact cleanup state;
- configured OpenAI/BFL capabilities; and
- combined generation capability.

Application readiness continues to mean the local/private app can start; missing paid-provider keys truthfully disable generation without disabling local reading.

## RED/GREEN evidence

All provider behavior was mocked; no live request was made.

1. Initial durability RED: 10 failures because `begin_generation_run` and `services.generation` did not exist.
2. Initial durability GREEN: 10/10 covering duplicate/conflicting claims, strict script failure, BFL submit/poll/download failures, image validation/decode failure, finalization failure, database swap failure, successful publication, and startup recovery.
3. API RED/GREEN: 2 failures on missing idempotent run responses, then 2/2 after the existing commit route used persisted runs.
4. Readiness RED/GREEN: 3 expected failures on missing migration/writability/generation reporting, then 4/4 including migration-head inspection.
5. Self-review RED/GREEN: a simulated crash after `os.replace` exposed an orphan-file window; recording the intended path before replace made the focused suite 11/11.
6. Storage-boundary RED/GREEN: the database swap initially accepted a traversing/missing media path; validating it through `LocalStorage.absolute_path()` and file existence made the focused suite 12/12.
7. Bounded-download RED/GREEN: the old response buffered `.content`; the focused test then proved streamed reading stops at 20 MiB + 1 byte, closes the response, and never consumes the remaining oversized stream.
8. PNG RED/GREEN: malformed dimensions, bit depth, color type, interlace, row filters, decoded length, and trailing bytes were initially accepted. Strict chunk-order/CRC/header validation and bounded incremental decompression made the input suite 9/9.
9. Persistent-cleanup RED/GREEN: one filesystem failure initially discarded both failed-run and successful-retirement cleanup state. Pending manifests now survive, readiness reports `cleanup: false`, startup fails safely, and a later startup clears the manifest after deletion succeeds. Durability suite: 14/14.
10. Populated-migration RED/GREEN: a real 0001 database with colliding active rows failed the new partial unique index. The migration now terminalizes legacy work first, preserves a readable current revision, fails an initial generation, and declares matching SQLite/PostgreSQL predicates. Its timestamp bind is explicitly typed; the focused migration test passes with `DeprecationWarning` promoted to an error.
11. Frontend ambiguity RED/GREEN: a lost commit response initially produced two different keys. The retry now reuses the first key, while an observed terminal failure rotates it.
12. Frontend re-review RED/GREEN: with key retention in place, the focused call-order test still observed two choose calls after the first choose succeeded and the commit response was lost. The attempt now records `choose`/`commit`; retry observes one choose followed by two commits with the identical key. Focused StoryGenerator suite: 8/8.
13. Final backend suite: 129/129. Final frontend suite: 48/48 across 18 files.

The fault assertions verify that the old chapter stays `ready`, its revision remains unchanged, its panel remains readable, its media file remains present, the run becomes `failed`, the safe code/reference is persisted, sensitive exception text is absent, and staging/new files are removed.

## Idempotency, transaction, and restart evidence

- Same chapter/key returns the same run ID and target revision with `created=False`.
- A second active key raises `GenerationConflict`; the partial unique index is the concurrent database backstop.
- Only `created=True` schedules the background worker, and `start_generation_run` atomically changes only `queued` to `running`; a duplicate worker invocation therefore does no work.
- Ready publication requires exact panel sequence `1..N`, with no new database panel-count decision.
- The swap rejects staging, missing, traversing, or non-`story-images` media before opening the revision transaction.
- Database swap injection rolls back all row changes; no partial panel replacement is observable.
- Startup recovery test finalizes an abandoned new file, records an active run, reinitializes the backend, and verifies `interrupted`, old revision/media readability, and abandoned-file deletion.
- Successful mocked provider delivery URLs are absent from ready rows; local media remains readable independently of their expiry and database/session restart.

## Exact offline verification

Run from the recovery worktree; all commands exited 0 unless noted:

```powershell
cd C:\tmp\EduComic-worktrees\product-intent-recovery\backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp=C:\Users\benth\.codex\visualizations\2026\08\01\019fbcc7-9c58-7db2-8430-b2bd52255000\phase3-review-backend-clean-final
# 129 passed in 10.98s

.\.venv\Scripts\python.exe -m pytest tests/test_local_database.py::test_populated_0001_database_reconciles_active_runs_before_unique_index -q -W error::DeprecationWarning --basetemp=C:\Users\benth\.codex\visualizations\2026\08\01\019fbcc7-9c58-7db2-8430-b2bd52255000\phase3-review-migration-no-warnings
# 1 passed in 0.63s

.\.venv\Scripts\python.exe -m compileall -q src alembic
# exit 0

cd C:\tmp\EduComic-worktrees\product-intent-recovery\frontend
npm.cmd test -- --run src/pages/teacher/StoryGenerator.test.tsx
# 1 file passed; 8 tests passed

npm.cmd test -- --run
# 18 files passed; 48 tests passed

npm.cmd run typecheck
# exit 0

npm.cmd run lint
# exit 0

$env:VITE_API_URL='http://127.0.0.1:8000'; npm.cmd run build
# 2487 modules transformed; built successfully
```

The production build correctly refused to run without `VITE_API_URL`; the successful gate used the supported loopback URL. Ruff is configured but is not installed in the checked-in backend development environment (`python -m ruff` reported `No module named ruff`), so Python compilation plus the full pytest suite were the available backend static/runtime gates. No dependency was added merely to run that optional command.

The frontend-only retry-stage follow-up changed no backend file, so its final gate repeated the focused and complete frontend suites, TypeScript no-emit typecheck, ESLint, and production build. The build emitted only the pre-existing stale Browserslist database advisory; refreshing frontend dependency metadata was outside this narrow fix.

## Files and commits

Main implementation files:

- `backend/alembic/versions/0002_generation_durability.py`
- `backend/src/database/models.py`
- `backend/src/database/database.py`
- `backend/src/services/generation.py`
- `backend/src/local_runtime.py`
- `backend/src/local_storage.py`
- `backend/src/main.py`
- `backend/src/api_models.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/teacher/StoryGenerator.tsx`
- focused and regression tests under `backend/tests` and `frontend/src/lib`

Implementation commit: `3bf3542 feat: make local story generation durable`.

Review-hardening commit: `1c4b526 fix: harden durable generation recovery`.

Migration timestamp commit: `89be00a fix: type legacy migration timestamp`.

Frontend retry-stage commit: `57be661 fix: retry ambiguous story commit directly`.

## Preservation evidence

- No Supabase, hosted database, deployment, provider, or real student-data operation was run.
- OpenAI and BFL stages were replaced with deterministic test doubles; readiness tests explicitly fail if provider clients/transports are constructed.
- The current OpenAI model, strict parse request, BFL endpoint/request dimensions/output shape, and existing provisional 8-12 script contract were not modernized or narrowed.
- The `main` source worktree and `public-release-cleanup` worktree were inspected read-only. Their pre-existing dirty tracked/untracked states were not staged, reset, stashed, or modified. A sandbox-owned test-only temp directory briefly created in the main source workspace was removed completely before final verification.
- No push, merge, reset, stash, deployment, or live-service call was performed.

## Self-review and Phase 7 handoff

Self-review found and fixed the post-`os.replace` manifest crash window, database-swap bypass of the storage traversal/existence boundary, unbounded delivery buffering, permissive PNG decompression, non-persistent cleanup failures, populated migration collision, ambiguous-response key rotation, and repeated choose call before a same-key commit retry. It also found the startup recovery database-path bug during the full suite; recovery now uses the exact database URL initialized by startup.

Deliberate simplifications:

- The worker is in-process and startup fails interrupted work instead of resuming it. This is sufficient for one machine and preserves the old revision.
- Artifact cleanup remains intentionally local and startup-driven; no separate janitor service or distributed queue was added.
- No progress/event framework was added; the persisted run stage is the truthful operational state.

Phase 7 should review provider modernization and consolidate/remove the now-inactive destructive legacy `commit_story_choice`/combined BFL helper path after deciding how optional panel review fits the durable coordinator. It may also decide whether to expose a dedicated run-status read model, persist provider job IDs for resume, revise the provisional panel-count contract, or change current models/endpoints. None of those founder/provider decisions were made here.

## Result

**COMPLETE** — Phase 3's local/private durability, idempotency, safe failure, atomic swap, startup recovery, readiness, offline verification, and preservation requirements are satisfied.
