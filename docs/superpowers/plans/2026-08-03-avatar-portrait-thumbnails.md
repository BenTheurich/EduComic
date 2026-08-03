# Avatar Portrait Thumbnails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show locally derived head-and-shoulders avatar thumbnails in compact student UI while preserving full-body avatars for profiles and comics, and remove the student chooser's yellow page glow.

**Architecture:** Keep the existing full-body avatar as the canonical asset. During avatar storage, derive one 256×256 PNG thumbnail with Pillow, persist its object path beside the avatar path, and expose a nullable thumbnail URL through the existing student API serializer. Compact React surfaces prefer the thumbnail and fall back to the full avatar; the main profile and comic pipeline remain unchanged.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Pillow, React 18, TypeScript, Vitest, Pytest.

## Global Constraints

- Do not call BFL/FLUX or OpenAI for this work.
- Reuse the existing avatar storage and media URL pipeline.
- Preserve full-body avatars as the story-generation and main-profile source.
- Keep the thumbnail optional so older rows and failed derivations continue to render.
- Use test-first red/green cycles for backend behavior and frontend rendering.

---

### Task 1: Add the thumbnail data contract and lifecycle

**Files:**
- Create: `backend/alembic/versions/0009_avatar_thumbnails.py`
- Modify: `backend/src/database/models.py`
- Modify: `backend/src/database/migrations.py`
- Modify: `backend/src/database/database.py`
- Test: `backend/tests/test_local_database.py`
- Test: `backend/tests/test_local_mutations.py`

- [x] Add failing migration/serialization tests for the nullable thumbnail path and `avatar_thumbnail_url`.
- [x] Run the focused backend tests and confirm they fail because the field/migration do not exist.
- [x] Add the nullable model column, migration, migration head, and API serialization fallback field.
- [x] Extend avatar replacement and personal-data deletion so current/superseded thumbnails are cleaned with full avatars.
- [x] Re-run the focused tests until green.

### Task 2: Derive and store portrait thumbnails locally

**Files:**
- Modify: `backend/src/services/avatar.py`
- Test: `backend/tests/test_student_signup_flow.py`
- Test: `backend/tests/test_health.py`
- Test: `backend/tests/test_phase4_review_fixes.py`
- Test: `backend/tests/test_panel_regeneration.py`

- [x] Add a failing Pillow-based test proving the output is a 256×256 PNG framed from the top/foreground.
- [x] Add failing lifecycle tests proving avatar replacement publishes the thumbnail and failure cleanup removes both new files.
- [x] Run the focused tests and confirm expected failures.
- [x] Implement the minimum local crop/resize helper and store the thumbnail alongside the original avatar.
- [x] Update existing avatar-service test doubles for the new return/signature contract.
- [x] Re-run focused avatar and database tests until green.

### Task 3: Prefer portraits in compact UI and remove the yellow glow

**Files:**
- Modify: `frontend/src/types/student.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/shared/StudentLogin.tsx`
- Modify: `frontend/src/pages/student/StudentDashboard.tsx`
- Modify: `frontend/src/components/student/ClassPictureBanner.tsx`
- Modify: `frontend/src/pages/student/StudentClassroom.tsx`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/components/ui/background-components.tsx`
- Test: affected component tests under `frontend/src/**/*.test.tsx`

- [x] Add failing component tests that compact avatars prefer `avatar_thumbnail_url` and the shared background has no yellow gradient.
- [x] Run the focused frontend tests and confirm expected failures.
- [x] Add the nullable field to frontend contracts and use thumbnail → full avatar → initials in compact surfaces.
- [x] Replace the radial yellow overlay with the normal `bg-background` surface.
- [x] Run focused tests, TypeScript build, and the Impeccable detector until green.

### Task 4: Backfill local review data and verify end to end

**Files:**
- Modify data only: `C:/tmp/EduComic-worktrees/product-intent-recovery/backend/data`

- [ ] Run the migration against the active local recovery data.
- [ ] Generate Ben and James thumbnails locally from their stored avatars and update their rows without API generation calls.
- [ ] Sync the running recovery worktree to the implemented main commit if it is clean.
- [ ] Run backend and frontend regression suites.
- [ ] Inspect the student chooser and compact avatar surfaces at desktop/mobile sizes, then perform at most one correction pass.
- [ ] Confirm the full-body student profile and story paths still use `avatar_url`.
