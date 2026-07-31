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

## Review fix round 1

Addressed all three Important review findings:

- Added a shared 2048-character constraint to active `photo_url` and `thumbnail_url` HTTP references.
- Made active photo filename and material title form fields reject whitespace-only values while retaining their 255/200-character limits at the FastAPI boundary.
- Audited `avatar.py`, `thumbnail.py`, and `comic_creation.py`; removed raw exceptions, tracebacks, identifiers, classroom/story/prompt content, provider bodies, and generated URLs from output. Remaining messages contain only generic events, numeric progress, counts, scores, elapsed time, or HTTP status codes. Provider/body-bearing exception messages encountered during the audit were also made generic.
- Added real ASGI boundary coverage and representative avatar/thumbnail/comic failure-path output capture.

TDD and verification:

- RED: the focused backend command reported 7 failures / 12 passes: both 5,000-character URLs reached handlers, both whitespace-only multipart fields reached handlers, and all three representative service failures printed sensitive values.
- GREEN: `uv run --frozen --extra dev pytest -q tests/test_request_validation.py tests/test_safe_service_logging.py` — 19 passed.
- Backend full suite — 25 passed.
- Ruff on all touched Python files — passed.
- Frontend request-contract suite — 4 passed; full suite — 9 files / 25 tests passed.
- Frontend typecheck and production build with `VITE_API_URL=https://api.example.invalid` — passed; existing Browserslist and chunk-size warnings remain.

- Staged Round 1 scan: `gitleaks git . --staged --redact --no-banner --no-color` — no leaks found (Git emitted the environment's existing inaccessible global-ignore warning).

Round 1 files: `backend/src/api_models.py`, `backend/src/main.py`, `backend/src/services/avatar.py`, `backend/src/services/thumbnail.py`, `backend/src/services/comic_creation.py`, `backend/tests/test_request_validation.py`, `backend/tests/test_safe_service_logging.py`, and this report.

## Review fix round 2

- Audited the reachable `panel_review.py` path. Quality-review output no longer includes provider image URLs, featured-student names, configured model names, prompt content, raw provider exceptions, or invalid response bodies. Provider-call and JSON-parse failures now expose generic errors only; retained output is generic events and safe numeric counts/scores.
- Extended representative success, provider-failure, and invalid-response output capture around the real `review_panel_image` behavior. The thumbnail regression now inspects combined stdout and stderr for traceback and sensitive values.
- Normalized `avatar.py`, `thumbnail.py`, `comic_creation.py`, and `panel_review.py` to LF without semantic changes. All four were verified as `i/lf w/lf`, and `git diff --check` passed.

TDD and verification:

- RED: the focused safe-logging suite reported 3 failures / 3 passes for the exposed panel URL/student name, raw provider exception, and raw invalid response.
- GREEN: `uv run --frozen --extra dev pytest -q tests/test_safe_service_logging.py` — 6 passed.
- Backend full suite — 28 passed.
- Ruff on all touched Python files — passed.
- Frontend request-contract regression — 4 passed; frontend typecheck — passed. No API or frontend file changed in this round, so the immediately prior successful production-build evidence remains applicable.
- Staged Round 2 scan: `gitleaks git . --staged --redact --no-banner --no-color` — no leaks found (Git emitted the environment's existing inaccessible global-ignore warning).

Round 2 files: `backend/src/panel_review.py`, `backend/src/services/avatar.py`, `backend/src/services/thumbnail.py`, `backend/src/services/comic_creation.py`, `backend/tests/test_safe_service_logging.py`, and this report.
