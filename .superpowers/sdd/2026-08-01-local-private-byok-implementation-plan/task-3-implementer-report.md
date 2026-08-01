# Task 3 Implementer Report: Durable Local Story Generation

Status: **COMPLETE**

Task base: `a4870e9`

Implementation commit: `3bf3542 feat: make local story generation durable`

## Architecture and boundaries

- The existing `chapters.revision` pointer and `(chapter_id, revision, panel_number)` panel key remain the readable-revision boundary.
- `generation_runs` is the persisted job boundary. A run owns one chapter, selected idea, scoped idempotency key, target revision, stage, terminal state, safe error code/reference, and new-file manifest.
- FastAPI keeps the single existing `POST /chapters/commit` path and dispatches one local `BackgroundTasks` worker only when the database creates a new run. No queue, Redis, Celery, plugin framework, or second API path was added.
- `services/generation.py` is the one-machine coordinator. It validates the stored chapter/classroom/idea, obtains a strict OpenAI script through the existing provider contract, then performs BFL submit, poll, download, PNG validation/decompression, staging, durable finalization, and one SQLite swap.
- Provider delivery and polling URLs remain transient in memory. Only `story-images/...` object paths are eligible for ready panel rows.
- All new images are finalized locally before the database transaction. The transaction deletes prior panel rows, inserts the complete sequential target revision, advances the chapter revision, and succeeds the run atomically. Old files are deleted only after that commit.
- A failed run deletes its staging/finalized new artifacts and restores `ready` when an older revision exists; an initial failed chapter becomes `failed`.
- Startup deliberately fails `queued`/`running` runs as `interrupted`, restores the previous readable revision, deletes each run's finalized new-file manifest, and clears staging. It does not attempt provider resume.

## Schema and API changes

Migration `0002_generation_durability` adds only the missing durable run contract:

- `selected_idea_id`
- `stage`
- `error_code`
- `artifact_paths`
- a partial unique index allowing at most one `queued`/`running` run per chapter

The existing globally unique stored idempotency column is retained. Client keys are SHA-256 scoped with the chapter ID before storage, giving chapter-local retry semantics without exposing the client key.

`POST /chapters/commit` accepts additive optional `idempotency_key` input and returns additive `run_id`. Legacy callers receive a deterministic chapter/revision key. An identical retry returns the existing run without scheduling work; a different key while work is active returns `409`.

The frontend creates one UUID per deliberate commit attempt. Re-sending that request is idempotent. A new deliberate attempt after a terminal failure gets a new key. Existing active chapter/run claims prevent response-loss retries from starting another provider job.

`GET /ready` remains provider-call-free and now reports:

- persistence availability;
- migration-head state;
- data-directory writability;
- storage availability;
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
7. Final backend suite: 117/117.

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
.\.venv\Scripts\python.exe -m pytest -q --basetemp=C:\Users\benth\.codex\visualizations\2026\08\01\019fbcc7-9c58-7db2-8430-b2bd52255000\phase3-backend-final
# 117 passed in 8.30s

.\.venv\Scripts\python.exe -m compileall -q src alembic
# exit 0

cd C:\tmp\EduComic-worktrees\product-intent-recovery\frontend
npm.cmd test -- --run
# 18 files passed; 46 tests passed

npm.cmd run lint
# exit 0

$env:VITE_API_URL='http://127.0.0.1:8000'; npm.cmd run build
# 2487 modules transformed; built successfully
```

The production build correctly refused to run without `VITE_API_URL`; the successful gate used the supported loopback URL. Ruff is configured but is not installed in the checked-in backend development environment (`python -m ruff` reported `No module named ruff`), so Python compilation plus the full pytest suite were the available backend static/runtime gates. No dependency was added merely to run that optional command.

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

## Preservation evidence

- No Supabase, hosted database, deployment, provider, or real student-data operation was run.
- OpenAI and BFL stages were replaced with deterministic test doubles; readiness tests explicitly fail if provider clients/transports are constructed.
- The current OpenAI model, strict parse request, BFL endpoint/request dimensions/output shape, and existing provisional 8-12 script contract were not modernized or narrowed.
- The `main` source worktree and `public-release-cleanup` worktree were inspected read-only. Their pre-existing dirty tracked/untracked states were not staged, reset, stashed, or modified. A sandbox-owned test-only temp directory briefly created in the main source workspace was removed completely before final verification.
- No push, merge, reset, stash, deployment, or live-service call was performed.

## Self-review and Phase 7 handoff

Self-review found and fixed two durability gaps before completion: the post-`os.replace` manifest crash window and database-swap bypass of the storage traversal/existence boundary. It also found the startup recovery database-path bug during the full suite; recovery now uses the exact database URL initialized by startup.

Deliberate simplifications:

- The worker is in-process and startup fails interrupted work instead of resuming it. This is sufficient for one machine and preserves the old revision.
- Old-file retirement after a successful database commit is idempotent best effort; failure can leave harmless unreferenced old media, never a broken ready revision.
- No progress/event framework was added; the persisted run stage is the truthful operational state.

Phase 7 should review provider modernization and consolidate/remove the now-inactive destructive legacy `commit_story_choice`/combined BFL helper path after deciding how optional panel review fits the durable coordinator. It may also decide whether to expose a dedicated run-status read model, persist provider job IDs for resume, revise the provisional panel-count contract, or change current models/endpoints. None of those founder/provider decisions were made here.

## Result

**COMPLETE** — Phase 3's local/private durability, idempotency, safe failure, atomic swap, startup recovery, readiness, offline verification, and preservation requirements are satisfied.
