# Cost-Safe Generation and Review Implementation Plan

> **For inline execution:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`; do not dispatch subagents. Track the three tasks below in order.

**Goal:** Preserve paid story work across failures, make corrected panels teacher-approved candidates, and select more relevant PDF grounding excerpts.

**Architecture:** Extend the existing `GenerationRun` record with structured checkpoint, provider-job, cost, and candidate fields. Reuse the current workers, revision swap, managed storage, and chapter polling contracts. Keep PDF grounding deterministic and local by selecting the most lesson-relevant extracted page per source.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, SQLite, React 18, TypeScript, Pytest, Vitest.

## Global Constraints

- No live OpenAI or BFL calls during implementation or verification.
- No automatic paid retry, parallel panel generation, OCR, embeddings, or correction history.
- Preserve readable revisions until a full story completes or a correction candidate is accepted.
- Work inline on one feature branch; no subagents or additional worktrees.

---

### Task 1: Resume full-story generation without duplicate paid work

**Files:**
- Create: `backend/alembic/versions/0010_generation_checkpoints.py`
- Modify: `backend/src/database/models.py`
- Modify: `backend/src/database/migrations.py`
- Modify: `backend/src/database/database.py`
- Modify: `backend/src/services/generation.py`
- Modify: `backend/src/main.py`
- Modify: `backend/src/api_models.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/types/story.ts`
- Modify: `frontend/src/pages/teacher/StoryGenerator.tsx`
- Test: `backend/tests/test_generation_durability.py`
- Test: `backend/tests/test_local_database.py`
- Test: `backend/tests/test_local_startup.py`
- Test: `frontend/src/pages/teacher/StoryGenerator.test.tsx`

**Interfaces:**
- `submit_bfl_generation(...) -> BFLJob(job_id, polling_url, reported_cost)`.
- `record_generation_provider_job(run_id, panel_number, job)` persists before polling.
- `record_generation_checkpoint(run_id, panel_number, object_path)` moves one finalized image from cleanup bookkeeping into ordered checkpoints and clears the active job.
- `resume_generation_run(run_id)` atomically requeues one failed, current story run.
- `POST /generation-runs/{run_id}/resume` and `POST /generation-runs/{run_id}/discard?confirm=true` are idempotent local operations.

- [x] Add failing migration and durability tests for checkpoint fields, same-job polling after interruption, resume from the first missing panel, explicit moderation resubmission, and checkpoint cleanup.
- [x] Run focused backend tests and confirm failures are caused by the missing contract.
- [x] Implement the minimal schema, database transitions, worker resume path, and API endpoints.
- [x] Add failing frontend tests for preserved panel count, reported cost, `Resume from panel N`, and confirmed discard.
- [x] Implement the frontend API/types and generation failure actions, then run focused backend/frontend tests green.
- [x] Commit Task 1.

### Task 2: Hold panel corrections for teacher approval

**Files:**
- Modify: `backend/src/database/database.py`
- Modify: `backend/src/services/panel_regeneration.py`
- Modify: `backend/src/main.py`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/teacher/StoryViewer.tsx`
- Test: `backend/tests/test_panel_regeneration.py`
- Test: `frontend/src/pages/teacher/StoryViewer.test.tsx`

**Interfaces:**
- A successful panel worker stores `candidate_object_path`, sets stage `candidate_ready`, and leaves the chapter revision unchanged.
- `POST /panel-regenerations/{run_id}/accept` publishes through the existing atomic revision swap.
- `POST /panel-regenerations/{run_id}/reject` clears and deletes the candidate without changing the chapter.
- Status returns `candidate_ready`, `candidate_url`, moderation error details, and provider-reported cost.

- [x] Add failing backend tests proving generation does not publish, accept changes only the target, reject preserves the original, and stale/duplicate actions are safe.
- [x] Run the focused backend test and confirm the expected failures.
- [x] Implement candidate persistence plus accept/reject database and API behavior.
- [x] Add failing frontend tests for the focused correction dialog, original/candidate comparison, accept, reject, and moderation copy.
- [x] Replace the inline editor with the dialog and run focused backend/frontend tests green.
- [x] Commit Task 2.

### Task 3: Select and show representative PDF grounding

**Files:**
- Modify: `backend/src/materials.py`
- Modify: `backend/src/database/database.py`
- Modify: `frontend/src/pages/teacher/StoryViewer.tsx`
- Test: `backend/tests/test_materials_grounding.py`
- Test: `frontend/src/pages/teacher/StoryViewer.test.tsx`

**Interfaces:**
- `snapshot_sources(sources, lesson_prompt)` selects one page per source by deterministic normalized-term overlap, ties by page number, and falls back to the first non-empty page.
- The completed teacher story view renders source filename and snapshotted page number from `chapter.grounded_sources`.

- [x] Add failing tests for later-page relevance, deterministic tie/fallback behavior, and visible story provenance.
- [x] Run focused tests and confirm the expected failures.
- [x] Implement the smallest page scorer and provenance treatment.
- [x] Run focused tests, all backend/frontend tests, TypeScript checks, production build, migration check, and Impeccable detector.
- [x] Review the final diff against the approved design and commit Task 3.
