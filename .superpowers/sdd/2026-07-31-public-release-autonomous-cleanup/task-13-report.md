# Task 13 report: delete the unauthenticated student-photo flow

## Result

The optional child-photo feature was removed rather than hardened. The public source now creates students from bounded text only, generates avatars without a reference image, and displays either the generated avatar or initials.

## Changes

- Deleted `POST /students/upload-photo`, its multipart imports, public `StudentPhotos` upload, and caller-controlled filename handling.
- Removed `photo_url` from `StudentCreateRequest`, database inserts, frontend requests, response types, fixtures, and presentation fallbacks. Unknown request fields are forbidden.
- Removed the signup file input, preview, upload-first orchestration, and photo logging.
- Removed the avatar service's photo lookup, `input_image` payload, and face/body-preservation claim. The prompt now uses interests plus the enrolled classroom style only.
- Removed Pillow and python-multipart from `backend/pyproject.toml` and `backend/uv.lock`.
- Updated the implementation plan with the deletion decision and reintroduction gate.
- Preserved the already-pending Task 5 and Task 13 preflight ledger notes.

## TDD evidence

- RED backend: `4 failed, 14 passed`. Failures proved the old insert still wrote `photo_url`, the request still accepted that field, the upload route remained registered, and avatar generation still passed a third photo argument.
- RED frontend: `2 failed, 3 passed`. Failures proved the API still serialized `photo_url` and the real signup form still rendered a file input.
- GREEN focused backend: `18 passed` across request validation, active routes, and signup/avatar flow.
- GREEN focused frontend: `5 passed` across request-body and real StudentSignup coverage. The component test fills first name, last name, and interests; asserts there is no photo control; asserts `create("Ada Lovelace", "robots")`; and reaches the dashboard.

## Verification

- `uv lock --offline`: pass; removed Pillow 12.0.0 and python-multipart 0.0.20.
- `uv lock --check`: pass; 61 packages resolved.
- `uv sync --frozen --extra dev`: pass; both removed packages were uninstalled.
- `uv run --frozen --extra dev pytest -q`: `32 passed`.
- `python -m compileall -q src tests`: pass.
- `uvx ruff check src tests`: pass.
- `npm test -- --run`: `12` files and `30` tests passed.
- `npm run typecheck`: pass.
- `npm run lint`: pass.
- `VITE_API_URL=https://api.invalid npm run build`: pass; largest application entry chunk `403.69 kB`.
- Production absence scan across `backend/src` and non-test `frontend/src`: zero matches for photo fields/client/route/bucket/reference-photo symbols, multipart handlers, Pillow, or python-multipart.
- `git diff --check`: pass.
- `gitleaks git --staged --redact --no-banner --no-color .`: pass; approximately 10.75 kB scanned and no leaks found. Gitleaks also printed the known contributor-global ignore permission warning.

The full frontend suite still prints two pre-existing debug messages, and Browserslist reports stale browser data during build. Neither comes from this task; later cleanup already owns frontend logging/documentation and dependency maintenance.

## Founder reintroduction gate

Do not restore child-photo intake until authentication, explicit guardian/student consent, retention and deletion rules, private object storage, authorized signed access, and abandoned-upload cleanup are designed and implemented. This task intentionally did not delete any historical deployed buckets, objects, or columns and did not change generated-avatar storage; Tasks 15 and 19 own the durable-image and migration contracts.
