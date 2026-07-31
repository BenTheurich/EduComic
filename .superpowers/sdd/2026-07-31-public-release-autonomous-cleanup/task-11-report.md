# Task 11 report

Implemented validated request bodies and safe backend failures for the active demo workflows.

## Scope and inventory

- Moved active classroom creation, student creation, chapter start, and story choice values from query strings to bounded JSON bodies; the existing chapter commit body now validates its UUID and idea ID.
- Added the active thumbnail JSON model because `StoryGenerator` still calls it until Task 12 removes that workflow.
- Validated every registered UUID path before handler execution. Kept active multipart upload fields as bounded form inputs because Tasks 13/16A own their replacement/removal.
- Left `/story/generate-options`, `/chapters/ideas`, and `/story/create/{classroom_id}` without new request models: they have no active page caller and Task 16 deletes them. No current client-submitted status or list-valued POST input exists, so no speculative status/list request field was added.
- Updated every changed active request in `frontend/src/lib/api.ts`; added a boundary test covering the emitted JSON payloads.
- Replaced credentialed wildcard CORS with comma-parsed `ALLOWED_ORIGINS`, safe localhost defaults, and explicit wildcard rejection.
- Sanitized all 5xx responses with a stable message and server-generated `error_reference`. Server logs contain only the reference, method, path, and status—not exception/provider text or request payloads.

## TDD evidence

- RED backend: `uv run --frozen --extra dev pytest -q tests/test_request_validation.py` produced 7 failures / 2 passes. JSON student creation returned 422, malformed UUIDs reached handlers, commit UUIDs reached the database, provider failures were not correlated, and wildcard CORS reflected the unlisted origin.
- RED frontend: `npm.cmd test -- --run src/lib/api.request-bodies.test.ts` failed all 4 cases because active values were still in query strings.
- RED wildcard rejection: focused test failed with `DID NOT RAISE RuntimeError` before restoring the rejection branch.
- Mutation check: removing the style allowlist and lesson maximum made both focused tests fail with 500 instead of 422, proving the assertions catch the intended regressions.
- GREEN backend focused: 10/10 passed.
- GREEN frontend request contracts: 4/4 passed.

## Final verification

- Backend full suite: `uv run --frozen --extra dev pytest -q` — 16 passed.
- Ruff touched Python files: all checks passed.
- Frontend full suite: `npm.cmd test -- --run` — 8 files, 23 tests passed. Existing application `console` output remains in unrelated workflow tests.
- Frontend typecheck: `npm.cmd run typecheck` — passed.
- Touched frontend ESLint: passed.
- Frontend production build with `VITE_API_URL=https://api.example.invalid`: passed. Existing stale Browserslist-data and large-chunk warnings remain.
- `gitleaks dir . --redact --no-banner --no-color --verbose` reported only preserved ignored/generated paths under `backend/.venv` and `output/playwright/task7-10`; Task 11 did not modify or delete them.
- Staged Task 11 scan: `gitleaks git . --staged --redact --no-banner --no-color` — no leaks found (Git emitted the environment's existing inaccessible global-ignore warning).

## Files changed

- `.superpowers/sdd/2026-07-31-public-release-autonomous-cleanup/task-11-report.md`
- `backend/.env.example`
- `backend/src/api_models.py`
- `backend/src/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_request_validation.py`
- `backend/tests/test_student_signup_flow.py`
- `frontend/src/lib/api.request-bodies.test.ts`
- `frontend/src/lib/api.ts`

Self-review found no unresolved Task 11 defect. The deliberately excluded stale endpoints are scheduled for deletion in Tasks 12/16/16A as noted above.
