# Task 2 implementer report

Status: **COMPLETE**

Base: `32cb4d3951520845b89dfc16af738924affde60f`

Implementation commits:

The post-review persistence, provider-boundary, lifecycle, and claim fixes are included in the current review-fix commit in addition to the commits listed below.

- `af277ca` — `feat: use local persistence for application workflows`
- `cf595de` — `feat: make local profile flows truthful`

## Boundaries changed

### Persistence and services

- Replaced the Phase 1 fail-closed Supabase compatibility object in `backend/src/database/database.py` with direct SQLAlchemy operations over the existing Phase 1 models and session factory. Classroom, student, enrollment, chapter, panel, list, reader, and deletion helpers now use local persistence.
- Kept the implementation concrete: one cached SQLAlchemy session factory, direct queries, existing models, and existing `LocalStorage`; no repository/provider plugin framework or new dependency was added.
- Seeded exactly one fixed local teacher profile after migration. Startup remains idempotent.
- Extended the existing student-create route, rather than adding a second route, with optional client UUID and classroom UUID. Student creation plus enrollment is one transaction. Exact retries return the existing result; conflicting retries fail; a missing classroom rolls the whole transaction back.
- Converted avatar classroom lookup and final avatar persistence to local queries and validated `/media/...` storage. Provider responses are downloaded with a content-type and size boundary before atomic local finalization.
- Converted generated panel images to durable local media. A generated revision is written separately, and the chapter switches to that revision only after all panels succeed. Readers expose only the current ready revision; provider or cleanup failure is marked `failed` by the background wrapper.
- Removed raw `avatar_object_path` updates from the public persistence helper during Ponytail full self-review. Only validated local-media URLs may cross that boundary.
- Local startup and readiness now accept SQLite URLs only. A configured PostgreSQL, Supabase, or other non-SQLite `DATABASE_URL` is rejected before a storage directory or database engine is opened.
- Simultaneous identical student create/enroll requests now reload and compare the committed winner after an integrity race; conflicting profile or enrollment payloads still fail truthfully.
- BFL reference images are resolved only from validated `/media/...` local objects, restricted to supported image types, read with a 20 MiB bound, and base64-encoded into the existing `input_image` through `input_image_8` fields. Localhost and relative application URLs never cross the provider boundary.
- Avatar replacement compensates a failed database update by deleting the new file, and removes the superseded avatar only after the new row commits. Panel insert failures delete their new image; retries clear interrupted target-revision rows/files; successful revision changes remove superseded rows/files; chapter deletion removes all recorded panel files after the database commit. Cleanup failures are sanitized and logged without rolling back an already-correct database state.
- Provider clients are constructed lazily on the first provider operation. Import, liveness, and readiness do not construct OpenAI, HTTPX, or Requests transports.
- Chapter commit now uses one conditional SQL update to claim only `idea_chosen` or `failed` chapters with the selected idea. A repeated/in-flight commit receives HTTP 409 rather than starting a second generation.
- Idea selection now uses its own conditional SQL update and is permitted only from `options_generated`, `idea_chosen`, or `failed`. It cannot reset `generating` (or another non-editable state) to `idea_chosen`; both a directly active chapter and a commit claim that wins after the route's read return HTTP 409 without changing the claimed state.
- Preserved UUID validation, extra-field rejection, UTC serialization, database cascades, traversal/redirect protection, bounded media reads/writes, generic API errors, ready-only readers, and fail-closed PDF behavior. The pending panel-count decision was not changed.

### Readiness and startup

- `/ready` now checks the migrated local-profile table and an actual bounded stage/unlink operation in local storage. It returns 503 with `local_persistence_unavailable` and/or `local_storage_unavailable` only when those local dependencies fail.
- Provider capability is configuration inspection only. No network call is made. Missing or copied placeholder values are reported as unconfigured without blocking otherwise-usable local data.
- Added `backend/src/run_local.py`. Its default and documented command is:

  ```text
  cd backend
  uv run python src/run_local.py --reload
  ```

- The launcher defaults to `127.0.0.1`. Any other bind is refused unless `--allow-unsupported-exposure` accompanies an explicit `--host`; the override logs an unmistakable no-authentication warning.
- Updated both READMEs, the frontend example URL, Vite dev host/proxies, and `start-dev-linux.sh` to use `127.0.0.1`. `/media` is proxied to the local backend as well as `/api`.

### Frontend

- Replaced `/student/login` with `/student/select` and changed visible actions from login/account language to truthful local preview/profile selection.
- Changed teacher/student sidebar `Logout` actions to `Exit Teacher View` / `Exit Student View` after the real-browser audit exposed the remaining misleading label.
- Student signup now creates a stable client UUID and sends optional classroom enrollment in the same existing create request. It no longer performs a second join request for direct-invite signup.
- Existing loading, empty, failure, retry, accessibility, ready-only reader, avatar retry, and PDF states remain in place.

## Principal files

Backend implementation:

- `backend/src/database/database.py`
- `backend/src/local_runtime.py`
- `backend/src/run_local.py`
- `backend/src/main.py`
- `backend/src/api_models.py`
- `backend/src/services/avatar.py`
- `backend/src/services/comic_creation.py`

Frontend and launch surface:

- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/shared/Landing.tsx`
- `frontend/src/pages/shared/StudentLogin.tsx`
- `frontend/src/pages/shared/StudentSignup.tsx`
- `frontend/src/components/teacher/TeacherSidebar.tsx`
- `frontend/src/components/student/StudentSidebar.tsx`
- `frontend/vite.config.ts`
- `frontend/.env.example`
- `README.md`
- `backend/README.md`
- `start-dev-linux.sh`

Behavioral coverage was added or converted in `backend/tests/test_local_application.py`, the existing backend route/service tests, the student selection/signup tests, API request-body tests, landing tests, and sidebar/layout tests.

## TDD evidence

The initial Phase 2 backend behavior run failed six new tests for the intended reasons: active CRUD still reached the Phase 1 sentinel, student create/enroll fields were rejected, readiness remained blocked, avatar/panels still used Supabase paths, the safe local launcher did not exist, and generation failures lacked the new wrapper behavior. The startup seed test independently failed until the explicit test database URL was passed through. The converted focused set then passed 7/7.

The initial frontend focused run failed four assertions for the old `/student/login` route, account wording, and two-request create/join behavior. Those tests passed after the single local profile flow was implemented.

Additional small RED/GREEN cycles caught:

- copied placeholder provider keys incorrectly reported as configured: 1 RED, then the readiness regression set passed;
- the browser-discovered `Logout` labels: 2 RED, then 5/5 focused sidebar/layout tests passed;
- raw avatar object paths bypassing the local-media URL boundary: 1 RED, then 2/2 focused media tests passed.
- a non-SQLite local configuration reaching migration/storage and a simultaneous client-UUID insert raising `IntegrityError`: 2 RED, then the 15-test focused persistence set passed;
- `/media/...` references being sent verbatim to BFL, invalid references reaching the provider, missing-key/avatar error conflation, orphaned avatar replacement files, and repeated chapter commit: focused tests failed first and then passed;
- eager OpenAI construction during application import: the constructor-level sentinel failed first, then passed after lazy construction;
- panel-insert compensation, successful avatar replacement cleanup, and chapter-delete cleanup passed with the concrete local filesystem and database.
- the first choose-idea state regression failed with HTTP 200 and a mutated `generating` chapter; after the conditional transition it passed together with a stale-read/claim-wins boundary test (2/2), and the fresh backend suite passed 105/105.

## Fresh verification

All successful commands ran in the isolated recovery worktree. No provider network call was used.

```text
backend\.venv\Scripts\python.exe -m pytest -q
105 passed in 5.47s

npm.cmd test -- --run
18 test files passed; 45 tests passed; duration 5.85s

npm.cmd run typecheck
exit 0

npm.cmd run lint
exit 0

VITE_API_URL=http://127.0.0.1:8000 npm.cmd run build
2487 modules transformed; built in 3.65s

backend\.venv\Scripts\python.exe -m compileall -q src tests
exit 0

uv --cache-dir C:\tmp\EduComic-uv-cache lock --check --offline
Resolved 48 packages in 1ms

git diff --check
exit 0
```

The production build retained only the existing stale `caniuse-lite` advisory.

Source scans found no `supabase`, `create_client`, `.table(`, `.storage`, `/student/login`, `Logout`, `Sign In`, or `Create Account` match in active backend/frontend source. The only remaining `localhost` scan match is an allowed CORS origin alongside the supported `127.0.0.1` origin; neither server binds to it by default.

## Readiness and bind verification

With an isolated `EDUCOMIC_DATA_DIR`, the supported launcher logged:

```text
Uvicorn running on http://127.0.0.1:8000
```

`GET /ready` returned HTTP 200 with:

```json
{
  "status": "ready",
  "local_data": {"persistence": true, "storage": true},
  "provider_capabilities": {"openai": false, "bfl": false},
  "missing_configuration": ["OPENAI_API_KEY", "BFL_API_KEY"]
}
```

The readiness network sentinel patches the actual OpenAI constructor plus HTTPX and Requests transports before application import. It proves this inspection neither constructs a provider client nor makes a paid call. Unit coverage proves placeholder keys remain false and local persistence/storage failures return precise 503 reasons. `validate_bind("0.0.0.0", false)` is rejected; only the explicit unsupported override permits it.

## Provider request verification

The BFL request shape was checked against the official current FLUX.2 `[pro]` API reference: `POST /v1/flux-2-pro` accepts `input_image`, `input_image_2`, through `input_image_8`, with reference content supplied as a URL or base64 data. The existing endpoint, model, polling URL handling, and field names were retained; only validated local files are converted to bounded base64 before submission. Source: [FLUX.2 `[pro]` API reference](https://docs.bfl.ai/api-reference/models/generate-or-edit-an-image-with-flux2-%5Bpro%5D).

## Real-browser journey and restart

`npx` was present at `C:\Program Files\nodejs\npx.ps1`. The required bundled wrapper was used through Git Bash:

```text
C:\Users\benth\.codex\skills\playwright\scripts\playwright_cli.sh
```

The WSL `bash.exe` shim has no distribution, but Git Bash successfully ran the wrapper. No Playwright test scaffolding was added. All snapshots, logs, the SQLite database, screenshots, and download are under ignored `output/playwright/`.

The fictional journey used classroom **Aurora Science Lab** and student **Mira North**:

1. Opened the landing page and teacher dashboard.
2. Created the classroom through both accessible form steps.
3. Exited the teacher view, opened `/student/select`, and verified the explicit “does not authenticate anyone” copy.
4. Created the local student profile. Missing BFL configuration produced the truthful saved-profile/avatar-retry message; browser requests showed only the local avatar endpoint and no BFL/OpenAI request.
5. Followed the classroom invite, accepted the terms, and joined. The dashboard showed the persisted classroom.
6. Stopped the exact backend listener and launcher, restarted the supported command against the same directory, reloaded through Playwright, and saw the same student, classroom, and enrollment. `/ready` remained 200.
7. Seeded one fictional ready chapter through the application’s own database/storage APIs, with no provider. Student and teacher readers displayed **Mira and the Aurora** and `Panel 1`; the browser recorded HTTP 200 for `/media/story-images/...png` through the local proxy.
8. A deliberately tiny invalid fixture first demonstrated the generic fail-closed PDF error with no partial file. Replacing only that isolated fixture with a valid Playwright-produced PNG made the same PDF flow succeed. Playwright captured `PDF downloaded successfully!` and a non-empty `output/playwright/.playwright-cli/Mira-and-the-Aurora.pdf` (2,768,148 bytes).

The browser console had zero errors after the restart journey. The browser sessions and all listeners on ports 8000/8080 were stopped after verification.

## Source-worktree and live-service preservation

The source worktrees were inspected read-only after implementation and match the Phase 1 preservation evidence.

```text
main...origin/main
M  SUPABASE_SETUP.md
D  backend/.env
M  backend/.env.example
AM docs/PUBLIC_RELEASE_PHASE_0_STATUS.md
D  frontend/.env
M  frontend/.env.example
?? AGENTS.md
?? docs/PRODUCT_INTENT_RECONCILIATION_AUDIT.md
?? docs/PUBLIC_RELEASE_READINESS_REVIEW.md
?? docs/superpowers/

codex/public-release-cleanup
 M backend/.env.example
 M backend/src/panel_review.py
 M backend/src/services/comic_creation.py
 M backend/src/services/story_idea.py
 M backend/tests/test_safe_service_logging.py
?? backend/src/story_contracts.py
?? backend/tests/test_story_contracts.py
```

No reset, stash, clean, checkout, live Supabase project access, OpenAI/BFL call, deployment, push, merge, or modification of either source worktree was performed. Supabase guidance was checked only against official changelog/documentation; no Supabase service or project was contacted.

## Self-review and Phase 3 handoff

Ponytail full review confirmed that the conversion reuses the existing models, session factory, `LocalStorage`, FastAPI routes, and browser pages. It adds no abstraction layer and no dependency. It also removed the one raw storage-field bypass described above. Validation, data-loss prevention, accessibility, and explicit security boundaries were not simplified.

No Task 2 acceptance blocker remains. This review follow-up adds atomic status claiming, target-revision isolation, and concrete compensation/post-commit file cleanup. It does **not** claim the full Phase 3 generation protocol: durable `generation_runs`, all-images staging followed by one database replacement transaction, restart-time detection/resume of crashed work, and retryable durable cleanup records remain Phase 3 work. Controlled real-provider acceptance, provider-key lifecycle/log hardening, and any future hosted/remote security design also remain later work. The panel-count policy remains explicitly unresolved and unchanged.
