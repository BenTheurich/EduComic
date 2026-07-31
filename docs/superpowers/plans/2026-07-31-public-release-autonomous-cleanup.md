# EduComic Public Release Autonomous Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a sanitized, testable, honest public-source candidate and repair the deterministic application defects that do not require provider-dashboard or policy decisions from the founder.

**Architecture:** Keep the existing React, FastAPI, Supabase, OpenAI, and Black Forest Labs structure. Delete prototype branches and duplicate integrations before adding code. Put validation at existing HTTP/provider boundaries, preserve current chapter data until replacements succeed, and keep public demo restrictions separate from full user authentication.

**Tech Stack:** React 18, TypeScript, Vite, FastAPI, Pydantic, Supabase Python client, OpenAI Python SDK, HTTPX/Requests, Pytest, ESLint, npm, uv, Gitleaks.

## Global Constraints

- Do not contact live Supabase, OpenAI, Black Forest Labs, or deployment services during local checks.
- Do not read or print secret values. Tests must clear provider/database variables and inject fakes.
- Preserve the founder’s staged Phase 0 changes. Do not stage, commit, rewrite history, rotate keys, or push without separate authorization.
- Do not claim the app is safe for real student data. Full authentication, policy approval, and live deployment remain founder gates.
- Prefer deletion. Do not preserve old endpoints, mock fallbacks, false controls, or historical notes for compatibility when the active application does not use them.
- Run Gitleaks after every task that changes configuration, documentation, fixtures, or history-facing content.
- A task is complete only when its stated checks pass. Record blocked checks with the exact command and failure, without relaxing the check.

---

## Phase 1: Sanitize The Source Tree

### Task 1: Remove Non-Product Artifacts And Unsafe Historical Advice

**Files:**

- Delete: `.claude/claude.md`
- Delete: `.claude/settings.local.json`
- Delete: `.kiro/specs/classroom-story-platform/design.md`
- Delete: `.kiro/specs/classroom-story-platform/requirements.md`
- Delete: `.kiro/specs/classroom-story-platform/tasks.md`
- Delete: `backend/src/educomic.egg-info/`
- Delete: `docs/Claude.pdf`
- Delete: `docs/Workload.pdf`
- Delete: `docs/assignments_summary.pdf`
- Delete: `docs/PHOTO-2025-11-29-15-03-26.jpg`
- Delete: every tracked root-level `*.md` except `README.md`, `AGENTS.md`, and `SUPABASE_SETUP.md`
- Delete: `test-api.html`
- Delete: `test-classroom-join.html`
- Delete: `test-connection.sh`
- Delete: `test-many-to-many.sh`
- Delete: `test-materials-bucket.py`
- Delete: `test-story-generation.html`
- Delete: `test-url-extraction.html`
- Modify: `.gitignore`
- Modify: `docs/PUBLIC_RELEASE_PHASE_0_STATUS.md`

- [ ] Confirm every target is tracked and none is referenced by active source:

```powershell
git ls-files .claude .kiro backend/src/educomic.egg-info docs *.md test-*
rg -n "Claude\.pdf|Workload\.pdf|assignments_summary\.pdf|PHOTO-2025|test-api|test-classroom-join|test-connection|test-many-to-many|test-materials-bucket|test-story-generation|test-url-extraction" README.md backend frontend .github
```

Expected: targets are repository artifacts, not runtime dependencies.

- [ ] Delete the listed artifacts. Keep `README.md`, `AGENTS.md`, `SUPABASE_SETUP.md`, `docs/PUBLIC_RELEASE_PHASE_0_STATUS.md`, `docs/PUBLIC_RELEASE_READINESS_REVIEW.md`, and this plan.
- [ ] Add `/tmp/`, Python caches, test caches, build output, and generated package metadata to `.gitignore` if an equivalent rule does not already exist.
- [ ] Update the Phase 0 status to say env deletion is staged in the local index, not completed in the remote history.
- [ ] Replace the artifact-review gate with the completed inspection result and public-tree removal decision.
- [ ] Verify no unsafe public-bucket or RLS-disabling advice remains:

```powershell
rg -n -i "disable.*rls|public read|public write|public delete|backup api keys|share.*\.env" .
```

Expected: no release documentation recommends disabling access controls or sharing secrets.

- [ ] Verify the sanitized source:

```powershell
gitleaks dir . --redact --no-banner --no-color
git status --short
```

Expected: any Gitleaks finding is limited to the ignored local env and is absent from tracked/staged public source.

### Task 2: Choose One JavaScript Lockfile And Remove Generated Package Identity

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Delete: `frontend/bun.lockb`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`

- [ ] Confirm npm is the documented and CI package manager.
- [ ] Rename the frontend package from `vite_react_shadcn_ts` to `educomic-frontend`. Keep `"private": true`.
- [ ] Remove unused backend runtime dependencies only after import verification:

```powershell
rg -n "pydantic_settings|reportlab|from PIL|import PIL" backend/src backend/tests
```

Expected: no active source imports `pydantic-settings`, `reportlab`, or `Pillow`.

- [ ] Remove those three backend dependencies and regenerate `backend/uv.lock`.
- [ ] Delete `frontend/bun.lockb`; retain npm and `package-lock.json` as the single source of truth.
- [ ] Reinstall from locks:

```powershell
Set-Location frontend
npm ci
Set-Location ../backend
uv sync --frozen --extra dev
```

Expected: both installs succeed without lock drift.

---

## Phase 2: Make Quality Checks Real And Offline

### Task 3: Replace Live “Tests” With An Isolated Backend Smoke Suite

**Files:**

- Delete: `backend/src/services/test_story_idea.py`
- Delete: `backend/src/database/test_connection.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Modify: `backend/src/database/database.py`
- Modify: `backend/src/main.py`
- Modify: `backend/pyproject.toml`

- [ ] Write `conftest.py` so tests clear all Supabase/OpenAI/BFL variables before importing application modules and inject fake clients.
- [ ] Write a health test that proves liveness can load without live service access and readiness reports missing configuration. Run it first and confirm it fails because the current database client is initialized during import.
- [ ] Change database client initialization only enough to let the application import without credentials and make real database operations fail with a clear configuration error.
- [ ] Separate `/health` liveness from `/ready` configuration readiness.
- [ ] Run the new tests and confirm they pass without any network request:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q
```

Expected: the isolated health suite passes and no network request occurs.

- [ ] Move any useful manual connection diagnostics to a non-test `scripts/` path only if they can avoid printing credential fragments. Otherwise delete them.
- [ ] Keep Pytest discovery limited to `backend/tests`.

### Task 4: Add Frontend Type And Workflow Gates

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/tsconfig.app.json`
- Modify: `frontend/eslint.config.js`
- Create: `frontend/src/pages/student/JoinClassroom.test.tsx`
- Create: `frontend/src/pages/teacher/StoryGenerator.test.tsx`
- Create: `frontend/src/components/ui/animated-sidebar.test.tsx`

- [ ] Add a `typecheck` script that runs `tsc --noEmit`.
- [ ] Add Vitest, Testing Library for React, jest-dom matchers, and jsdom as development dependencies. Reuse Vite configuration; do not add an end-to-end framework.
- [ ] Write a direct-invite test that renders `/student/join/:classroomCode` with a pending fetch and asserts a loading state instead of a crash.
- [ ] Write a generation test that asserts an API failure produces an error state, not selectable mock options.
- [ ] Write a mobile-sidebar test that asserts the same navigation children are present in mobile and desktop render paths.
- [ ] Run the tests and record the expected current failures:

```powershell
Set-Location frontend
npm run typecheck
npm test -- --run
```

- [ ] Enable unused-variable checking after dead code is removed. Increase strictness only where the current source can pass in the same task.

### Task 5: Replace Placeholder Deployment With Secret-Free CI

**Files:**

- Delete: `.github/workflows/deploy.yml`
- Create: `.github/workflows/ci.yml`
- Modify: `.github/SECRETS_CHECKLIST.md`

- [ ] Create one CI workflow with read-only repository permissions.
- [ ] Do not expose Supabase, OpenAI, or BFL secrets to install, lint, type, build, or unit-test steps.
- [ ] Run backend tests with cleared provider/database variables and the development extra installed.
- [ ] Run frontend install, type check, lint, tests, and production build.
- [ ] Remove every failure-masking flag and the fake deployment-success step.
- [ ] Rewrite the secrets checklist as a list of secrets needed only by an eventual deploy target. Remove claims that keys are already configured.
- [ ] Validate YAML and mirror every CI command locally.

Expected: CI has no deploy job, no provider secrets, and no allowed quality-gate failures.

---

## Phase 3: Repair The Core Demo Workflow

### Task 6: Fix Invite, Navigation, And Broken Route Failures

**Files:**

- Modify: `frontend/src/pages/student/JoinClassroom.tsx`
- Modify: `frontend/src/components/ui/animated-sidebar.tsx`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/components/teacher/TeacherSidebar.tsx`

- [ ] Make direct invite rendering wait for a non-null classroom or show the existing error state.
- [ ] Pass the existing navigation children into `MobileSidebar`.
- [ ] Replace clickable SVG/div menu controls with labeled buttons. Restore focus on close and handle Escape.
- [ ] Change the empty-story link from `/story/generate` to the registered `/story/new` route.
- [ ] Delete the settings navigation item until a settings page exists.
- [ ] Run:

```powershell
Set-Location frontend
npm test -- --run JoinClassroom animated-sidebar
npm run typecheck
npm run build
```

Expected: direct invite and mobile navigation tests pass; no route points to `/story/generate` or `/teacher/settings`.

### Task 7: Delete Fake Actions And Fake Production Data

**Files:**

- Delete: `frontend/src/pages/student/CreateAvatar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/student/StudentProfile.tsx`
- Modify: `frontend/src/pages/student/StudentDashboard.tsx`
- Modify: `frontend/src/pages/shared/StudentSignup.tsx`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/pages/teacher/StoryGenerator.tsx`
- Modify: `frontend/src/pages/teacher/TeacherDashboard.tsx`
- Modify: `frontend/src/pages/student/StudentAllStories.tsx`
- Modify: `backend/src/main.py`
- Modify: `backend/src/services/avatar.py`

- [ ] Delete the fake avatar route and its “Edit Avatar” entry point. Existing signup avatar generation remains the only avatar flow.
- [ ] Remove “Delete Account” until an authorized backend deletion contract exists.
- [ ] Remove “Edit Classroom” until it performs a real mutation.
- [ ] Delete `mockStoryOptions` and show an explicit retryable error when story-option generation fails.
- [ ] Remove fallback student records and keep fetch errors distinct from valid empty data.
- [ ] Remove material upload from classroom creation because uploaded materials do not influence generation.
- [ ] Stop avatar generation inside student creation. Create the student, enroll the student in the intended classroom, then call the existing avatar endpoint so classroom design style is available.
- [ ] Treat avatar failure as a retryable profile state without undoing the student or enrollment.
- [ ] Verify:

```powershell
rg -n "student-new-|mockStoryOptions|Delete Account|Edit Classroom|Student / Learning" frontend/src
Set-Location frontend
npm test -- --run
npm run typecheck
npm run build
```

Expected: the search finds no fake IDs, mock production choices, no-op deletion, or fabricated student fallback.

### Task 8: Make Generation And Chapter State Truthful

**Files:**

- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/teacher/StoryGenerator.tsx`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/pages/student/StudentClassroom.tsx`
- Modify: `frontend/src/pages/student/StudentAllStories.tsx`
- Modify: `frontend/src/pages/student/StudentStoryReader.tsx`

- [ ] Add the backend chapter status vocabulary to the one shared frontend chapter type.
- [ ] Track consecutive polling errors separately from total successful polls.
- [ ] Treat `failed` as terminal and render its actionable error.
- [ ] Replace fixed 12-panel progress with indeterminate progress unless the API provides an expected count.
- [ ] Correct the polling duration comment to match the interval and attempt count.
- [ ] Filter unreadable chapters and render visible statuses from data instead of hard-coding “Completed.”
- [ ] Remove duplicate local chapter interfaces after all callers use the shared type.
- [ ] Run:

```powershell
Set-Location frontend
npm test -- --run StoryGenerator
npm run typecheck
npm run lint
```

Expected: no fixed `/ 12` progress calculation and no hard-coded completion label for all chapters.

### Task 9: Make Production API Configuration Fail Clearly

**Files:**

- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/services/thumbnailGenerator.ts` or delete it in Task 12
- Modify: `frontend/.env.example`
- Modify: `frontend/vite.config.ts`

- [ ] Centralize API URL resolution in `frontend/src/lib/api.ts`.
- [ ] Permit the localhost default only in development.
- [ ] Fail the production build with a clear message when `VITE_API_URL` is missing.
- [ ] Route photo and thumbnail requests through the same configured client.
- [ ] Run one build without the variable and one with a non-secret test URL:

```powershell
Set-Location frontend
Remove-Item Env:\VITE_API_URL -ErrorAction SilentlyContinue
npm run build
$env:VITE_API_URL='https://api.example.invalid'
npm run build
```

Expected: the first production build fails clearly; the second passes and contains no localhost API fallback.

### Task 10: Repair Or Disable PDF Export

**Files:**

- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/pages/teacher/StoryViewer.tsx`
- Create: `frontend/src/lib/exportStoryPdf.ts`
- Create: `frontend/src/lib/exportStoryPdf.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] Write one test using a fake remote panel response that proves the exporter embeds verified image bytes and rejects a failed panel.
- [ ] Move the duplicated export logic into one function only because two active callers need the same correction.
- [ ] Fetch each remote image with a bounded timeout, validate its response type, convert it to accepted image data, and stop on a required-panel failure.
- [ ] Show success only after every required panel is embedded and the file is saved.
- [ ] Resolve the critical `jspdf` advisory. If no supported safe version exists, remove the export controls and the dependency for the public release.
- [ ] Run:

```powershell
Set-Location frontend
npm test -- --run exportStoryPdf
npm audit --omit=dev
npm run build
```

Expected: no critical production advisory and no successful blank/partial export.

---

## Phase 4: Harden Existing Backend Boundaries

### Task 11: Add Request Models, Bounds, And Safe Errors

**Files:**

- Create: `backend/src/api_models.py`
- Modify: `backend/src/main.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_request_validation.py`

- [ ] Inventory every scalar POST parameter and define only the shared request models that have at least one active route.
- [ ] Put student name, interests, photo reference, teacher outline, and story choice into JSON request bodies.
- [ ] Enforce UUIDs, nonblank strings, bounded lengths, allowed styles/statuses, and bounded list sizes.
- [ ] Remove raw exception strings and provider responses from client-facing errors. Keep a server-side correlation identifier without logging secret-bearing payloads.
- [ ] Replace wildcard credentialed CORS with a parsed `ALLOWED_ORIGINS` allowlist. Reject `*` when credentials are enabled and give the example file a valid local default.
- [ ] Add tests for oversized text, invalid UUIDs, invalid styles, and a provider exception that must not appear in the response.
- [ ] Add a test that an unlisted origin receives no credentialed CORS permission.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_request_validation.py
```

Expected: invalid trust-boundary input returns a stable 4xx response and internal provider text is absent.

### Task 12: Remove Arbitrary URL Fetching And Consolidate Black Forest Labs Calls

**Files:**

- Modify: `backend/src/main.py`
- Modify: `backend/src/services/comic_creation.py`
- Modify or delete: `backend/src/services/thumbnail.py`
- Modify or delete: `frontend/src/services/thumbnailGenerator.ts`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_thumbnail_boundary.py`

- [ ] Write a test proving caller-supplied loopback, private-network, and non-provider URLs are rejected without any request.
- [ ] Remove `thumbnail_url` from the public choose-idea contract. Resolve the chosen thumbnail from a server-owned chapter/story record.
- [ ] If thumbnails remain, reuse the configured `api.bfl.ai` base, the provider-returned polling URL, and the existing comic-generation client behavior.
- [ ] If the active UI can work without generated thumbnails, delete the thumbnail endpoint, service, frontend helper, bucket, and second BFL key name.
- [ ] Keep one canonical `BFL_API_KEY` setting and one provider base.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_thumbnail_boundary.py
rg -n "api\.bfl\.ml|BLACK_FOREST_API_KEY|thumbnail_url" backend frontend
```

Expected: no arbitrary server-side URL fetch, no stale provider base, and one BFL key name.

### Task 13: Validate Upload Bytes And Make Storage Mutations Consistent

**Files:**

- Modify: `backend/src/main.py`
- Create: `backend/src/upload_validation.py`
- Create: `backend/tests/test_upload_validation.py`

- [ ] Write tests for a mislabeled executable, an oversized stream, a fake PDF, a valid small image, and a storage-success/database-failure compensation path.
- [ ] Use a bounded read and verify signatures before upload.
- [ ] Re-encode accepted images with the already-installed image support only if image upload remains enabled; otherwise reject photo upload in the read-only release.
- [ ] Generate server-owned object names and ignore caller filename extensions.
- [ ] Remove an uploaded object when its database insert fails.
- [ ] Do not remove the database record when storage deletion fails. Return a truthful retryable error.
- [ ] Keep photos, avatars, and materials private in the migration contract.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_upload_validation.py
```

Expected: invalid bytes never reach storage and partial failures do not create invisible orphan state.

### Task 14: Validate Provider Output Before Persistence

**Files:**

- Modify: `backend/src/services/story_idea.py`
- Modify: `backend/src/services/comic_creation.py`
- Modify: `backend/src/services/panel_review.py`
- Create: `backend/src/story_contracts.py`
- Modify: `backend/tests/test_story_contracts.py`

- [ ] Define one Pydantic contract for three nonblank ideas and one for 8 to 12 sequential panels with bounded text and known speakers.
- [ ] Ask OpenAI for structured output matching those contracts.
- [ ] Delete blank-option padding and permissive panel normalization.
- [ ] Reject invalid output before any database or image-generation work begins.
- [ ] Remove student avatar URLs from narrative prompt context. Include only the minimum character text needed for the story.
- [ ] Set explicit output-token bounds and fix the contradictory dialogue-length instructions.
- [ ] Default panel review to disabled, keep numeric settings parseable when copied from `.env.example`, and enforce a hard attempt ceiling.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_story_contracts.py
```

Expected: malformed, short, duplicate-index, unknown-speaker, and zero-panel responses fail before persistence.

### Task 15: Preserve Chapters And Report Every Generation Failure

**Files:**

- Modify: `backend/src/services/comic_creation.py`
- Modify: `backend/src/database/database.py`
- Modify: `backend/src/main.py`
- Modify: `backend/tests/test_generation_failure.py`

- [ ] Validate the chapter and selected idea before mutation.
- [ ] Generate replacement panel data without deleting current rows.
- [ ] Upload every final image to durable storage. Treat missing bucket configuration or upload failure as job failure.
- [ ] Replace current panel rows only after the complete replacement is valid and durable.
- [ ] Wrap the top-level job so every exception sets chapter status to `failed`.
- [ ] Never store a provider delivery URL as final panel data.
- [ ] Add a startup/readiness check that generation is unavailable when its durable image bucket is missing.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_generation_failure.py
```

Expected: current panels survive every injected failure, status becomes `failed`, and no temporary provider URL is persisted.

BackgroundTasks remain suitable only for local or gated demonstration after this task. A durable worker is a founder-gated deployment task.

---

## Phase 5: Delete Parallel Implementations And Restore Clarity

### Task 16: Keep One Story-Start API And One Relationship Helper Set

**Files:**

- Modify: `backend/src/main.py`
- Modify: `backend/src/database/database.py`
- Modify: `frontend/src/lib/api.ts`
- Delete: `backend/src/services/chapter.py`
- Create: `backend/tests/test_active_routes.py`

- [ ] Confirm active frontend callers use `/classrooms/{id}/chapters/start`.
- [ ] Write a route test for the one supported start/choose/status/read path.
- [ ] Delete the success-returning `/story/create/{classroom_id}` no-op.
- [ ] Delete stale `/story/generate-options` and `/chapters/ideas` routes and their unused frontend client functions.
- [ ] Delete the second exact copy of relationship helpers in `database.py`.
- [ ] Delete unused database helpers only after `rg` confirms zero callers.
- [ ] Delete empty `chapter.py`.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_active_routes.py
Set-Location ../frontend
npm run typecheck
npm run build
```

Expected: one story-start contract and no success response from unimplemented work.

### Task 16A: Delete The Unused Materials Feature

**Files:**

- Modify: `backend/src/main.py`
- Modify: `backend/src/database/database.py`
- Delete: `backend/src/database/MATERIALS_SETUP.md`
- Modify: `frontend/src/pages/teacher/CreateClassroom.tsx`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] Confirm no generation prompt, service, or active reader consumes stored material content.
- [ ] Delete material upload, list, and delete UI.
- [ ] Delete the matching API routes, database helpers, response types, and storage-bucket references.
- [ ] Remove material claims from setup and product text.
- [ ] Run backend tests, frontend tests, type check, lint, and build.

Expected: the public source makes no claim that PDFs affect stories, and no unused public material-storage endpoint remains.

### Task 17: Remove Unreachable Frontend Modules And Dependencies

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Delete: frontend source modules proven unreachable from `frontend/src/main.tsx`

- [ ] Recompute the import graph after Tasks 6 through 10. Include CSS/config/script use before classifying a dependency as unused.
- [ ] Delete unreachable UI modules, unused `NavLink`, unused reader/sidebar variants, and unused type files.
- [ ] Remove React Query if no query or mutation hooks remain.
- [ ] Keep only the toaster used by application pages.
- [ ] Lazy-load route pages with `React.lazy` and one existing loading treatment.
- [ ] Remove direct dependencies with no source, config, or script use. Do not delete `tailwindcss-animate` while Tailwind config uses it.
- [ ] Run:

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run lint
npm test -- --run
npm run build
npm audit --omit=dev
```

Expected: all checks pass, route behavior is unchanged, and main-bundle size is lower than the July 31 baseline.

### Task 18: Fix Basic Accessibility And Responsive Reader Controls

**Files:**

- Modify: `frontend/src/index.css`
- Modify: `frontend/src/pages/shared/StudentLogin.tsx`
- Modify: `frontend/src/pages/teacher/CreateClassroom.tsx`
- Modify: `frontend/src/pages/student/StudentStoryReader.tsx`
- Modify: `frontend/src/pages/teacher/StoryViewer.tsx`
- Modify: shared button/badge components only if the token fix belongs there

- [ ] Replace clickable choice cards with native button or radio-group behavior.
- [ ] Give layout toggles and sliders accessible names and pressed/value state.
- [ ] Adjust primary and status color tokens to at least 4.5:1 for normal text.
- [ ] Make reader controls wrap or collapse at narrow widths and keep primary touch targets at least 44 px.
- [ ] Add reduced-motion behavior for nonessential animation.
- [ ] Choose one honest theme: wire the existing dark tokens completely, or remove unused dark-mode claims and unreachable code. Do not leave a half-theme.
- [ ] Run the existing component tests, type check, lint, and build. Perform one keyboard-only pass at desktop and mobile viewport widths.

Expected: login, classroom style choice, navigation, and reader controls work without a pointer.

---

## Phase 6: Reproduce The Data Contract And Rewrite Public Documentation

### Task 19: Create A Current, Deny-By-Default Supabase Migration

**Files:**

- Create: `supabase/migrations/202607310001_initial_public_release.sql`
- Create: `supabase/seed.sql`
- Create: `backend/tests/test_schema_contract.py`
- Modify: `SUPABASE_SETUP.md`
- Delete: `backend/src/database/MATERIALS_SETUP.md` if materials remain removed

- [ ] Extract the actual table, column, status, relationship, and bucket contract from current database helpers and API response types.
- [ ] Write a migration for `classrooms`, `students`, `student_classrooms`, `chapters`, `panels`, and only features still present after deletion.
- [ ] Add foreign keys, unique constraints, status checks, panel sequence constraints, and indexes used by active queries.
- [ ] Enable RLS and define no public write/delete policy. Keep sensitive storage private.
- [ ] Add fictional, non-personal seed rows without remote asset URLs.
- [ ] Add a static schema-contract test that asserts runtime table/status/bucket names match the migration.
- [ ] Rewrite setup instructions around the checked-in migration and remove references to nonexistent SQL files.
- [ ] Run:

```powershell
Set-Location backend
uv run --frozen --extra dev pytest -q tests/test_schema_contract.py
rg -n "database\.sql|add_materials_table\.sql|setup_materials_bucket\.sql|public read|public write|disable.*rls" ..
```

Expected: runtime names match one migration and no setup guide weakens RLS.

Applying the migration to a disposable Supabase project remains a founder action.

### Task 20: Rewrite README, Environment Contract, And Black Forest Labs Handoff

**Files:**

- Modify: `README.md`
- Modify: `backend/README.md`
- Replace: `frontend/README.md`
- Modify: `frontend/index.html`
- Modify: `backend/.env.example`
- Modify: `frontend/.env.example`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/BLACK_FOREST_LABS_HANDOFF.md`

- [ ] Document the current chapter workflow and 8 to 12 panel contract.
- [ ] Document only commands and paths that exist: npm for frontend, uv for backend, checked-in migrations for data.
- [ ] Give optional backend settings valid parseable defaults. Keep one BFL key name.
- [ ] Remove Lovable metadata, private project URLs, template package language, and the license placeholder.
- [ ] State the exact public-demo limitations: fictional data, no real students, no public live generation until founder gates are complete.
- [ ] Write a concise architecture document from actual routes, storage, and provider boundaries.
- [ ] Write the Black Forest Labs handoff with setup, the one BFL integration path, demo workflow, known limitations, and where their feedback is useful.
- [ ] Do not invent a license, privacy policy, deployment URL, provider budget, or production claim.
- [ ] Verify every documented path and command locally.

Expected: a new contributor can understand and run the sanitized project without consulting hackathon notes.

---

## Phase 7: Final Public-Source Verification

### Task 21: Run The Release Candidate Gate

**Files:**

- Modify only files needed to fix failures found by these checks
- Update: `docs/PUBLIC_RELEASE_PHASE_0_STATUS.md`
- Update: `docs/PUBLIC_RELEASE_READINESS_REVIEW.md`

- [ ] Run backend checks:

```powershell
Set-Location backend
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q
python -m compileall -q src tests
```

- [ ] Run frontend checks:

```powershell
Set-Location ../frontend
npm ci
npm run typecheck
npm run lint
npm test -- --run
npm run build
npm audit --omit=dev
```

- [ ] Run repository checks:

```powershell
Set-Location ..
gitleaks dir . --redact --no-banner --no-color
rg -n -i "disable.*rls|backup api keys|student-new-|mockStoryOptions|localhost:8000|@Lovable|vite_react_shadcn_ts|Add your license"
git status --short
```

- [ ] Build a temporary source-only export from the exact candidate tree and run Gitleaks against that export.
- [ ] Confirm the export excludes local env files, `tmp/`, build output, caches, internal PDFs, contributor-local settings, and generated metadata.
- [ ] Start the release-candidate frontend and an offline stub API, then use the Playwright CLI in a headed browser to verify:
  - landing page at desktop and mobile widths;
  - teacher dashboard and classroom navigation;
  - direct student invite loading, success, and invalid-code states;
  - student and teacher mobile navigation;
  - story option, generation progress, failed generation, reader, and PDF-export states;
  - keyboard access for login, classroom style choice, menus, and reader controls.
- [ ] Capture final screenshots under `output/playwright/` and inspect browser console and failed network requests. Fix any application error before release-candidate signoff.
- [ ] Update the review with resolved items, remaining founder gates, commands, dates, and exact results.
- [ ] Stop before public push, deployment, key rotation, migration application, paid API testing, or real-user data.

Expected release-candidate state:

- staged/public source secret scan passes;
- build, type, lint, tests, and syntax checks pass;
- zero critical production dependency advisories;
- no fake actions or broken core routes;
- no live API is available without the founder-approved access model;
- the founder checklist is the only remaining release gate.
