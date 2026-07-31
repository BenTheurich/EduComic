# Task 16A report

Deleted the unused classroom materials feature end to end. No compatibility routes remain.

## Consumer proof

- Inspected the generation services, panel review, teacher generator/viewer, and student reader paths. A focused search reported `GENERATION_READER_MATERIAL_CONSUMERS=0`; story prompts use classroom details, students, and the teacher outline only.
- Inspected all material callers, setup/product documentation, active tests, `CreateClassroom`, `ClassroomDetail`, `TeacherSidebar`, the frontend API client, FastAPI routes, and database helpers before editing.
- `CreateClassroom` already had no material state, upload, or API call, so it was left unchanged.

## Changes

- Removed the material list, upload, and delete FastAPI routes without 404 compatibility handlers.
- Removed all material database helpers and the `Materials` storage-bucket calls.
- Deleted `backend/src/database/MATERIALS_SETUP.md`, including its false PDF/story-generation claims and unsafe public-bucket guidance.
- Removed material fetching, state, handlers, tab, upload/list/delete UI, API methods/types, and the teacher-sidebar link.
- Removed only the deleted material-title cases from Task 11 request-validation coverage; both photo filename boundary cases remain.
- Added a backend route-template absence regression and real-component regressions for `ClassroomDetail` and `TeacherSidebar`.

## TDD evidence

- RED backend: `uv run --frozen --extra dev pytest -q tests/test_active_routes.py -k material` failed because all three material templates were registered.
- RED frontend: `npm.cmd test -- --run src/pages/teacher/ClassroomDetail.test.tsx` failed both tests because the real detail rendered the Materials tab and the real sidebar rendered its desktop/mobile Materials links.
- GREEN backend focused: 1 passed / 2 deselected.
- GREEN frontend focused: 2 passed.

## Verification

- Active production/setup reference scan: `ACTIVE_MATERIAL_REFERENCES=0` (regression tests and the dated historical readiness review intentionally retain removal context).
- Backend full suite: 33 passed.
- Frontend full suite: 10 files / 28 tests passed.
- Frontend typecheck: passed.
- Ruff on touched backend files: passed.
- ESLint on touched frontend files: passed.
- Production build with `VITE_API_URL=https://api.example.invalid`: passed. Existing stale Browserslist-data and large-chunk warnings remain.
- `git diff --check`: passed.
- Full-tree Gitleaks remains noisy only in pre-existing ignored/generated `backend/.venv`, `output/playwright/task7-10`, and `tmp/task16-gitleaks` content.
- Staged Gitleaks: no leaks found; Git emitted only the environment's existing inaccessible global-ignore warning.

Self-review found no unresolved Task 16A defect or unrelated change.
