# Task 12 report

Removed the separate story-option thumbnail feature and its arbitrary URL fetch.

## Implementation

- Deleted the backend thumbnail endpoint/service and frontend thumbnail helper, imports, state, and calls. Story options now render their existing theme fallback and remain selectable.
- Removed `thumbnail_url` from the public choose-idea request model and frontend client. Caller-supplied extra fields are rejected with 422 before handler execution.
- Removed the `Thumbnails` bucket path while preserving existing stored `chapter.thumbnail_url` reads for compatibility.
- Consolidated active avatar, comic, readiness, tests, examples, and setup text on `BFL_API_KEY`.
- Fixed comic submission to `https://api.bfl.ai`; avatar and comic generation continue polling only the provider-returned URL.

## TDD evidence

- RED backend: `test_thumbnail_boundary.py` reported 4 failures because the thumbnail route returned 200 and loopback, private-network, and non-provider URLs each attempted an HTTP client. The canonical-host regression separately failed because the legacy base override redirected submission.
- RED frontend: the focused suites reported 2 failures because choose-idea still emitted `thumbnail_url: null` and `StoryGenerator` still passed a third thumbnail argument.
- GREEN focused backend: 28 passed across thumbnail boundary, request validation, safe logging, and health.
- GREEN focused frontend: 9 passed across the active request-body and StoryGenerator suites.

## Final verification

- Backend full suite: `uv run --frozen --extra dev pytest -q` - 31 passed.
- Ruff on touched Python files: all checks passed.
- Frontend full suite: 9 files / 26 tests passed.
- Frontend typecheck and touched-file ESLint: passed.
- Frontend production build with `VITE_API_URL=https://api.example.invalid`: passed; existing stale Browserslist-data and large-chunk warnings remain.
- Expected-zero scans found no legacy BFL key/base, old provider host, thumbnail bucket/helper, or public thumbnail request path in active source/config.
- `git diff --check`: passed; only the repository's existing LF-to-CRLF checkout warnings were emitted.

## Files changed

- `.superpowers/sdd/2026-07-31-public-release-autonomous-cleanup/task-12-report.md`
- `AGENTS.md`
- `README.md`
- `SUPABASE_SETUP.md`
- `backend/.env.example`
- `backend/src/api_models.py`
- `backend/src/main.py`
- `backend/src/services/avatar.py`
- `backend/src/services/comic_creation.py`
- `backend/src/services/thumbnail.py` (deleted)
- `backend/tests/conftest.py`
- `backend/tests/test_request_validation.py`
- `backend/tests/test_safe_service_logging.py`
- `backend/tests/test_thumbnail_boundary.py`
- `frontend/src/lib/api.request-bodies.test.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/teacher/StoryGenerator.test.tsx`
- `frontend/src/pages/teacher/StoryGenerator.tsx`
- `frontend/src/services/thumbnailGenerator.ts` (deleted)

Self-review found no unresolved Task 12 defect. No live provider, database, deployment, or external application endpoint was contacted.

## Review fix round 1

Addressed both Important findings and the Minor cleanup:

- Set `extra="forbid"` only on `StoryChoiceRequest`. Loopback, private-network, and non-provider `thumbnail_url` extras now return stable 422 responses before database or network code; the supported `{idea_id}` body remains successful.
- Renamed the obsolete deployment workflow, deployment guide, and secrets checklist references to the canonical `BFL_API_KEY` without redesigning the placeholder workflow.
- Deleted the three `console.log` calls from `StoryGenerator`; no logging abstraction was added.

TDD and verification:

- RED backend: the focused boundary suite reported 3 failures / 3 passes because every malicious extra reached `get_chapter`.
- RED frontend: the focused StoryGenerator suite reported 1 failure / 4 passes and identified all three console calls.
- GREEN focused: backend 6/6 and StoryGenerator 5/5 passed.
- Backend full suite: 32 passed; Ruff passed on touched Python files.
- Frontend full suite: 9 files / 26 tests passed; typecheck, touched-file ESLint, and the production build passed. Existing Browserslist and chunk-size warnings remain.
- Active configuration/documentation scans, excluding dated release-review and SDD history, found zero `BLACK_FOREST_API_KEY` or `FLUX_API_KEY` references. `StoryGenerator` has zero `console.log` calls.
- Staged Round 1 Gitleaks scan: no leaks found; Git emitted only the environment's existing inaccessible global-ignore warning.
- `git diff --check` passed with only the repository's existing LF-to-CRLF checkout warnings.

Round 1 files: `.github/workflows/deploy.yml`, `.github/DEPLOYMENT.md`, `.github/SECRETS_CHECKLIST.md`, `backend/src/api_models.py`, `backend/tests/test_thumbnail_boundary.py`, `frontend/src/pages/teacher/StoryGenerator.tsx`, `frontend/src/pages/teacher/StoryGenerator.test.tsx`, and this report.
