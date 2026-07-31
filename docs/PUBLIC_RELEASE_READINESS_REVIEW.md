# EduComic Public Release Readiness Review

Date: July 31, 2026

Purpose: Re-audit the complete repository, reconcile the June 9 review with the current tree, and define what must happen before EduComic is made public, hosted as a demo, or handed to Black Forest Labs.

This was a review pass. No application code, live database, provider account, or deployment was changed. Existing Phase 0 changes in the working tree were preserved.

## Verdict

EduComic is a compelling hackathon project, but the current repository is not safe to publish or open-host.

The fastest credible release is a read-only demo with fictional, pre-generated data. A live multi-user demo that accepts student data and exposes AI generation needs authentication, authorization, private storage, quotas, reliable background work, and a documented privacy model first.

Current release status:

| Area | Status | Release consequence |
| --- | --- | --- |
| Git and secrets | Blocked | Eight historical secret findings remain in the current history. Keys must be rotated and public history must be replaced or cleaned. |
| Public access | Blocked | All 28 backend routes are anonymous, including data listing, uploads, deletes, and paid AI operations. |
| Student privacy | Blocked | Student data and files are publicly addressable and sent to providers without a release-ready consent or retention model. |
| Core demo flow | Blocked | Invite links can crash, mobile navigation is empty, generation states are misleading, and PDF export is unreliable. |
| Data setup | Blocked | No migrations, storage policies, or reproducible seed path exist. |
| Generation reliability | Blocked for live use | In-process jobs can erase working panels, remain stuck, or save expiring provider URLs as final images. |
| Quality gates | Failing | Lint and type checks fail; backend tests and CI are not trustworthy. |
| Dependencies | Failing | The production frontend tree has 25 known vulnerabilities, including one critical finding. |
| Public presentation | Incomplete | License, current README, deployment config, privacy text, and handoff instructions are missing or stale. |

## What Changed Since The June Review

The earlier review correctly identified most of the major themes. This audit confirms those themes and adds exact evidence, several new blockers, and a smaller release strategy.

Corrections to the old snapshot:

- `backend/.env` and `frontend/.env` are now staged for removal, not removed from the remote repository or its history.
- Both `.env.example` files contain placeholders, but some optional backend placeholders are not safe to copy because production code parses them as numbers during import.
- Gitleaks is available and was run. The all-history scan found eight redacted findings across 56 commits. A staged-source scan found zero.
- The current ignored `backend/.env` still contains three detected secrets. It must remain local and must not be copied into a public repository.
- `pytest-asyncio` is declared in the backend development extra. CI does not install that extra, and the repository has no valid backend test suite.
- The frontend bundle still builds, but `tsc --noEmit` now provides a clearer result: eight type errors.
- The production dependency audit has worsened from 12 to 25 findings: 13 moderate, 11 high, and 1 critical.
- The runtime uses 8 to 12 panels per chapter. Old 20-panel documentation is stale.
- Current code consistently checks for `ready` in the active generation flow. The real defect is that lists label every chapter “Completed,” including failed, generating, and abandoned chapters.
- Source files are valid UTF-8. Apparent mojibake in earlier terminal output was a shell-rendering issue, not a repository encoding defect.
- The three PDFs and the image under `docs/` were visually reviewed. They are obsolete hackathon artifacts, not required release documentation.

## Review Scope And Method

The review covered:

- Git state, tracked artifacts, full-history secret exposure, and staged-source safety.
- All backend Python source, routes, provider integrations, data access, uploads, generation, and error handling.
- Frontend routes, navigation, API use, teacher and student workflows, export, loading/error states, accessibility basics, responsiveness, and dependency reachability.
- Supabase schema assumptions, storage buckets, privacy boundaries, and reproducibility.
- CI, deployment files, documentation, licenses, package metadata, tests, lint, type checks, build output, and dependency advisories.
- Historical hackathon documents, PDFs, images, local settings, manual scripts, generated metadata, and dead source candidates.

Safe verification performed:

| Check | Result |
| --- | --- |
| Gitleaks 8.30.1, all history | 8 redacted findings in 56 commits |
| Gitleaks, staged public source | 0 findings |
| Gitleaks, current working tree | 3 findings, all in ignored local `backend/.env` |
| Frontend production build | Passed |
| Frontend bundle | Main JS 623.86 kB, 190.09 kB gzip; jsPDF chunk 413.70 kB |
| ESLint | Failed: 23 errors and 9 warnings |
| TypeScript no-emit | Failed: 8 errors |
| Production dependency audit | 25 findings: 13 moderate, 11 high, 1 critical |
| Backend syntax | All relevant Python files parsed and compiled |
| Backend tests | Not run against local secrets or live services; current test structure is invalid |

No Supabase, OpenAI, Black Forest Labs, deployment platform, or other live service was contacted.

## Findings

### P0. Secret History And Public Repository Safety

The index contains a good start:

- `backend/.env` and `frontend/.env` are staged for removal.
- example files use placeholder values.
- a concrete credential snippet in `SUPABASE_SETUP.md` is staged for replacement.
- `docs/PUBLIC_RELEASE_PHASE_0_STATUS.md` records the redacted scans.

That does not make the existing repository history safe to publish. Gitleaks found:

- three JWT findings in historical `backend/.env`;
- two generic API-key findings in historical `backend/.env`;
- two OpenAI key findings in historical `backend/.env`;
- one generic API-key finding in historical `SUPABASE_SETUP.md`.

Required before any public push:

1. Rotate the exposed OpenAI key.
2. Rotate the exposed Black Forest Labs key.
3. Classify and rotate the exposed Supabase key.
4. Create a fresh public repository from the sanitized tree, or deliberately rewrite and rescan all history.
5. Run a final Gitleaks scan on the exact public source and its history.

Recommended choice: create a fresh public repository. It is easier to verify and avoids publishing unrelated hackathon history.

### P0. Anonymous Data, Destructive Actions, And Paid APIs

The backend has 28 routes and no authentication or authorization middleware. A single global Supabase client performs every request without a user security context.

Anonymous callers can:

- list all students and classrooms;
- choose any student identity in the frontend;
- read ID-addressed student and classroom routes;
- upload student photos and classroom material;
- trigger OpenAI and Black Forest Labs work;
- join or leave classrooms;
- delete materials and chapters.

The frontend reinforces this model:

- `frontend/src/pages/shared/StudentLogin.tsx` fetches all students and stores any selected student ID in `localStorage`;
- `frontend/src/pages/student/JoinClassroom.tsx` trusts that ID;
- teacher routes have no login at all;
- “logout” only navigates to the landing page.

`backend/src/main.py` also enables wildcard CORS while allowing credentials.

Release consequence: do not deploy the current backend to a public URL. A hidden URL is not access control.

Minimum live-demo boundary:

- one server-validated access mechanism;
- server-side teacher ownership and student membership checks;
- restricted origins;
- quotas and concurrency limits for generation, uploads, and deletes;
- no global all-students picker.

### P0. Student Privacy And Provider Data Flow

The application handles names, interests, photos, avatars, classroom membership, and stories involving students. The current data flow is broader than necessary:

- student name, interests, and `photo_url` can be sent as query parameters and therefore appear in access logs;
- names, interests, and avatar URLs are sent to OpenAI prompts;
- student photo or avatar reference URLs are sent to Black Forest Labs;
- generated panel images may be sent to OpenAI for visual review;
- photos, avatars, materials, thumbnails, and panels are designed around public storage URLs;
- the join screen presents an agreement without an actual privacy, consent, retention, or deletion policy.

An avatar URL is not needed to write the story script and should be removed from that prompt context. Query parameters should be replaced with validated request bodies. Storage should be private unless an asset is deliberately published.

Release consequence: use fictional demo identities and generated assets until the founder has decided what real student data may be processed, by which providers, for how long, and under what consent model.

### P0. Direct Invite Links Crash

`frontend/src/pages/student/JoinClassroom.tsx` initializes the classroom to `null` but enables the classroom preview immediately for a direct `/student/join/:classroomCode` route. The first render dereferences `classroom.name` before the fetch finishes.

This breaks the primary shared-invite workflow with a white-screen runtime error.

Minimal fix: render a loading state until a classroom exists, then render either the preview or the existing error state.

### P1. Generation Can Destroy Good Data Or Never Finish

`backend/src/services/comic_creation.py` deletes all existing panels before it validates and generates the replacement chapter. Only the success path marks a chapter `ready`.

Provider errors, invalid ideas, malformed model output, process restarts, storage failures, or database failures can therefore leave:

- a previously working chapter erased;
- partial panels;
- a permanent `generating` state;
- no actionable user error.

The work runs through FastAPI `BackgroundTasks`, which is tied to the web process and is not a durable job system.

Minimum fix before any live generation:

- validate the chapter and chosen idea before mutation;
- keep current panels until a full replacement is ready;
- atomically replace panel rows after success;
- set `failed` for every top-level job exception;
- expose truthful failure status to the frontend.

A durable queue and worker are still required for a reliable public service. They are not required for a read-only demo.

### P1. Completed Stories Can Lose Their Images

Panel storage is optional. If the image bucket is not configured or upload fails, comic generation stores the temporary Black Forest Labs delivery URL and still marks the chapter `ready`.

The current CI environment does not configure `SUPABASE_IMAGES_BUCKET`.

Minimum fix:

- require durable image storage when generation is enabled;
- fail the chapter when durable upload fails;
- never persist a temporary provider delivery URL as final story data.

### P1. Server-Side Request Forgery In Thumbnail Selection

`POST /chapters/{chapter_id}/choose-idea` accepts an arbitrary `thumbnail_url`. The backend fetches it without a trusted-host check, private-network rejection, content validation, or response-size limit, then uploads the response as an image.

An anonymous caller can make the server request internal or attacker-controlled resources.

Minimal fix: do not accept arbitrary URLs. Store a provider-owned result identifier or accept only a previously issued thumbnail record. If a URL fetch remains, enforce HTTPS, a strict provider-host allowlist, private-address rejection, content verification, and a bounded body.

### P1. Uploads Trust Caller Metadata

Photo and material endpoints:

- trust client-supplied MIME values;
- buffer the full request before enforcing limits;
- derive extensions from caller filenames;
- publish storage URLs;
- do not consistently compensate for partial database or storage failures.

Material deletion ignores storage deletion failure, removes the database row, and reports success. This can leave orphaned public files.

Minimum fix:

- enforce bounded reads;
- validate file signatures;
- re-encode accepted images;
- verify PDFs before storage;
- generate server-owned filenames;
- keep database and storage mutations consistent;
- make sensitive buckets private.

### P1. AI Output Is Not A Validated Contract

Story idea parsing pads short responses with blank placeholders. Comic script parsing does not enforce:

- exactly three nonblank story choices;
- 8 to 12 panels;
- sequential, unique panel indices;
- bounded narration and dialogue;
- known speakers;
- valid field types.

A zero-panel model response can still reach `ready`. Prompts also contain conflicting dialogue length limits.

Minimum fix: use one validated structured-output contract and reject the whole operation before persistence when it does not match.

[GPT-5.1 remains a supported API model](https://developers.openai.com/api/docs/models/gpt-5.1). The issue is not immediate model removal; it is unvalidated output, missing cost bounds, and no explicit evaluation or upgrade policy.

### P1. Story Generation UI Produces Impossible States

`frontend/src/pages/teacher/StoryGenerator.tsx` has several coupled defects:

- an API failure substitutes mock story options;
- mock options have no persisted `chapterId`, so they cannot be selected;
- successful polls and failed polls share one counter, so a later transient error can incorrectly trigger the error threshold;
- `failed` is not handled as a terminal status;
- progress divides by 12 although chapters may have 8 to 12 panels;
- the polling comment describes five minutes, while the actual interval allows about ten.

Minimal fix: remove the production mock fallback, track consecutive failures separately, handle `failed`, and use indeterminate progress until the backend returns an expected panel count.

### P1. Chapter Lists Misrepresent State

Teacher and student story lists hard-code every chapter as “Completed.” Chapters are created before a story option is chosen, so abandoned, generating, and failed rows appear complete and often open an empty reader.

Minimal fix: include the backend status in frontend types, filter unreadable chapters, and render every visible state honestly.

### P1. PDF Export Is Unreliable

Both frontend exporters pass remote URL strings directly to `jsPDF.addImage`, catch per-panel errors, then save the document and show a success toast. A local check with an HTTP image URL failed with a PNG signature error.

The likely user result is a blank or partial PDF labeled successful.

Minimum fix: fetch and verify each image, convert it to data accepted by jsPDF, and abort with an exact failed-panel message when any required panel cannot be embedded.

The current `jspdf` version also carries the direct critical dependency finding. Export must be fixed or disabled before release.

### P1. Mobile Navigation Is Empty And Inaccessible

`frontend/src/components/ui/animated-sidebar.tsx` passes navigation children to the desktop sidebar but not the mobile sidebar. Opening the menu on mobile therefore produces an empty panel.

The open control is a clickable SVG and the close control is a clickable `div`, without proper button semantics, labels, focus handling, or Escape behavior.

Minimal fix: pass the existing children through and use labeled buttons with basic focus and keyboard handling.

### P1. Core Keyboard And Contrast Failures

Examples:

- student selection uses clickable cards without keyboard behavior;
- classroom style selection uses clickable cards instead of a radio-group interaction;
- layout controls and sliders lack accessible names;
- the main foreground/background color pair measures about 3.85:1, below the 4.5:1 target for normal text;
- several white-on-bright status colors measure roughly 2.15 to 2.54:1;
- pervasive motion has no reduced-motion path.

Minimum fix: use native buttons and radio controls, provide names and pressed state, adjust the token pairs, and respect reduced-motion preferences.

### P1. Prototype Actions Make False Promises

The current UI includes:

- “Delete Account,” which only logs and navigates home despite permanent-deletion copy;
- “Edit Avatar,” which navigates to a page that fabricates a `student-new-<timestamp>` ID;
- “Edit Classroom,” which has no handler;
- a teacher settings link with no route;
- an empty-story CTA to nonexistent `/story/generate` instead of `/story/new`.

Minimal release fix: remove actions that do not work. Restore them only with a real, server-authorized operation.

### P1. Errors Are Disguised As Empty Or Demo Data

Several frontend pages convert request failures into “no data” screens. The student dashboard fabricates a generic student record after failure. Classroom creation can persist a classroom, fail during material upload, report that creation failed, and create a duplicate on retry.

Minimum fix:

- keep explicit error state and retry;
- never fabricate production identities or data;
- report partial success accurately;
- make multi-step mutations idempotent or compensating.

### P1. Supabase Setup Is Not Reproducible

There are no SQL migrations or schema files. Runtime code assumes:

- `classrooms`;
- `students`;
- `student_classrooms`;
- `chapters`;
- `panels`;
- `materials`;
- multiple storage buckets with inconsistent names and visibility.

Documentation references nonexistent SQL files and disagrees with runtime bucket capitalization. No checked-in constraints, indexes, row-level policies, or seed data define the actual system.

Several root fix notes are actively unsafe as public setup guidance. `FIX_STORAGE_PERMISSIONS.md` recommends broad public storage operations and disabling storage RLS, while `FIX_MATERIALS_UPLOAD_ERROR.md` proposes world-applicable material policies. These files are not proof of the live Supabase configuration, but they should not ship as instructions.

Minimum fix: create one migration sequence for current tables, constraints, indexes, private buckets, and access policies. Add fictional seed data for the demo.

### P1. Materials Are A No-Op Product Feature

The UI and setup guide imply that uploaded PDFs influence story generation. The generation prompts contain classroom details, students, and the teacher outline, but no material content. No PDF extraction path exists.

Minimal release fix: remove the claim and hide material upload. Building a retrieval or extraction pipeline is speculative until the feature is deliberately chosen.

### P1. Production Configuration Can Silently Target Localhost

Three frontend paths fall back to `http://localhost:8000` when `VITE_API_URL` is missing. A misconfigured production bundle therefore calls each visitor’s own computer.

Minimum fix: require a production API URL at build time and keep the localhost default only for development.

### P2. Tests And CI Do Not Protect The Release

Backend:

- Pytest points to a missing `tests` directory.
- `backend/src/services/test_story_idea.py` imports nonexistent symbols.
- `backend/src/database/test_connection.py` is a live credential-check script that can print a key fragment.
- manual shell scripts call live or paid services and can leave data behind.
- development test dependencies are optional, but CI installs only runtime dependencies.

Frontend:

- no test or type-check script exists;
- there are no frontend test files;
- TypeScript strictness and unused-variable checks are disabled;
- `tsc --noEmit` reports eight errors;
- ESLint reports 23 errors and 9 warnings.

CI:

- test and lint failures are masked with `continue-on-error` behavior;
- provider and database secrets are scoped to the whole job, exposing them to dependency installation, build, and lint steps;
- the deployment section is a placeholder.

Minimum fix: replace the placeholder deployment workflow with a secret-free CI workflow that fails on build, type, lint, and isolated mocked tests. Keep live smoke tests outside pull-request CI.

### P2. Dependency And Bundle Health

The July 31 production audit found 25 vulnerabilities:

- 13 moderate;
- 11 high;
- 1 critical.

The critical direct dependency is `jspdf@3.0.4`. React Router and transitive PostCSS, Lodash, Recharts, and related packages also appear in the advisory tree.

The build passes but eagerly loads all route pages. The main JavaScript bundle is 623.86 kB and the jsPDF chunk is 413.70 kB.

Minimal fix:

- resolve or replace the PDF export dependency;
- upgrade supported direct dependencies and regenerate one chosen lockfile;
- lazy-load route pages;
- rerun the production audit and build;
- do not chase bundle micro-optimizations before deleting unused modules.

### P2. Dead And Duplicate Code

Verified high-confidence deletion candidates include:

Backend:

- the duplicate classroom/student relationship helper block in `backend/src/database/database.py`;
- the success-returning no-op `/story/create/{classroom_id}` route;
- stale parallel story-option entry points not used by the active frontend;
- empty `backend/src/services/chapter.py`;
- tracked `backend/src/educomic.egg-info/`;
- unused runtime dependencies `pydantic-settings`, `reportlab`, and `Pillow`.

Frontend:

- 35 source modules are unreachable from the application entry graph, excluding `vite-env.d.ts`;
- this includes roughly 30 unused shadcn UI modules, unused navigation/reader components, and unused types;
- React Query wraps the app, but the code uses no query or mutation hooks;
- two toaster systems are mounted while application code uses one;
- 25 declared runtime dependencies are not reachable from the application entry, subject to a final config/script usage check.

Repository:

- 40 root-level historical fix-note Markdown files, about 7,754 lines;
- 7 manual root test files, about 762 lines;
- stale `.kiro` and `.claude` specifications, about 1,849 lines;
- three obsolete PDFs and one stale architecture image;
- `.claude/settings.local.json`, which includes a contributor-specific local path;
- both npm and Bun lockfiles.

Conservative deletion target: more than 13,000 lines and at least 3 backend runtime dependencies, before frontend dependency pruning.

### P2. Provider Integration Drift

The main comic generation path follows the current Black Forest Labs guidance by using `api.bfl.ai` and the provider-returned polling URL. See the official [integration guidelines](https://docs.bfl.ai/api_integration/integration_guidelines) and [result endpoint documentation](https://docs.bfl.ai/api-reference/utility/get-result).

`backend/src/services/thumbnail.py` is inconsistent:

- it uses `api.bfl.ml` rather than the configured `api.bfl.ai` base;
- it hard-codes a result endpoint instead of using the returned polling URL;
- it recognizes only one of the two Black Forest Labs environment variable names;
- it converts all failures to `None`, while the API reports success.

Minimal fix: delete the duplicate thumbnail implementation if thumbnails are removed from release. Otherwise route it through the same provider client and failure contract as comic generation.

### P2. Backend API And Runtime Drift

The backend exposes several ways to start stories, with different persistence and status behavior. One route returns success while explicitly unimplemented. Synchronous Supabase and OpenAI calls also run inside many `async def` handlers and can block the event loop.

The health route cannot report missing Supabase configuration because module import fails first. With any nonempty strings it reports healthy without checking service readiness.

Minimum fix:

- keep the one active chapter-start flow;
- delete success-returning no-ops and stale routes;
- use plain synchronous FastAPI handlers for synchronous work or isolate blocking calls;
- separate liveness from real dependency readiness.

### P2. Public Presentation And Deployment Are Incomplete

Repository presentation:

- no license;
- root README contains a license placeholder;
- frontend README is the default Lovable template;
- package metadata remains `vite_react_shadcn_ts@0.0.0`;
- `frontend/index.html` still includes Lovable social metadata;
- setup guides reference missing files and the old 20-panel model.

Deployment:

- no Dockerfile, Railway, Nixpacks, Vercel, or equivalent configuration;
- BrowserRouter deep links have no committed SPA rewrite;
- the existing GitHub workflow does not deploy anything;
- no production environment contract, readiness check, demo seed, backup, or rollback procedure exists.

Deployment configuration should follow the founder’s chosen release mode and host. Adding several speculative platform files would create more stale code.

### P3. Historical Artifacts

The following artifacts were visually inspected:

- `docs/assignments_summary.pdf`: a three-page hackathon team-assignment summary with event branding;
- `docs/Claude.pdf`: a 14-page initial team contract/specification with obsolete 20-panel, no-auth, and mock-data guidance; its metadata contains an individual author name;
- `docs/Workload.pdf`: a 10-page hackathon work split with stale cost estimates and unsafe backup-key advice; its metadata contains an individual author name;
- `docs/PHOTO-2025-11-29-15-03-26.jpg`: a tall generation architecture flowchart, not a personal photograph.

None is required for the public source. Remove the PDFs. Replace the flowchart with a current architecture diagram only if the README needs one.

## Smallest Credible Release

The release should be split by risk, not by feature count.

### Release A: Public Source

Can be prepared without a live deployment:

- fresh sanitized repository;
- no secrets or contributor-local artifacts;
- current setup and architecture documentation;
- a real license;
- reproducible database migrations;
- passing secret scan, build, type, lint, and isolated tests;
- no false product claims or fake actions.

### Release B: Read-Only Demo

Recommended first hosted version:

- fictional classrooms and students;
- pre-generated stories and locally controlled assets;
- no user uploads;
- no AI generation endpoints exposed;
- no real student data;
- no destructive actions;
- explicit demo limitations.

This is sufficient to show the product to Black Forest Labs and public visitors without putting provider keys, children’s data, or an unfinished job system on the public internet.

### Release C: Gated Live Generation

Only after:

- authenticated users and server-side authorization;
- private storage and signed delivery;
- quotas, cost limits, and abuse controls;
- durable jobs and failure recovery;
- validated AI output;
- documented privacy, consent, retention, and deletion;
- provider and deployment configuration verified in a non-production environment.

## Founder Checklist

These decisions or account actions cannot be completed safely without the founder.

### Urgent Account Actions

- [ ] Rotate the exposed OpenAI key.
- [ ] Rotate the exposed Black Forest Labs key.
- [ ] Identify whether the exposed Supabase key is anon or service-role, then rotate it.
- [ ] Confirm that no deployed service still depends on an old key before revocation.

The local ignored `backend/.env` still contains detected credentials. No value was copied into this report.

### Public Repository

- [ ] Approve the recommended fresh public repository strategy, or explicitly choose full history rewriting.
- [ ] Choose the open-source license.
- [ ] Confirm which contributor names, acknowledgements, and hackathon credits should appear publicly.
- [ ] Decide whether the old private repository remains the internal archive.

### Demo Scope

- [ ] Choose the first release mode: read-only fictional demo, gated live demo, or full multi-user service.
- [ ] Approve fictional demo content and any screenshots or generated assets that may be public.
- [ ] Choose the frontend and backend hosts. Current project notes mention Vercel and Railway, but no deploy contract exists.
- [ ] Decide whether public visitors may generate any paid content, and set a hard budget if yes.

### Student Data And Privacy

- [ ] Decide whether real student names, interests, photos, or avatars will ever be accepted.
- [ ] Decide what may be sent to OpenAI and Black Forest Labs.
- [ ] Set retention and deletion expectations for original photos, avatars, materials, prompts, and generated stories.
- [ ] Provide or approve privacy, consent, acceptable-use, and contact text before real users are invited.
- [ ] Confirm the intended countries, schools, and age groups before legal or policy review.

### Supabase And Provider Configuration

- [ ] Provide access to a disposable non-production Supabase project when migration and policy verification begins.
- [ ] Confirm the intended storage visibility and retention for each asset type.
- [ ] Confirm the OpenAI model and account budget after a small quality/cost evaluation.
- [ ] Confirm the Black Forest Labs model, account limits, and preferred integration for the handoff demo.

### Final Release Approval

- [ ] Review the public README, screenshots, credits, license, privacy text, and demo limitations.
- [ ] Run a short founder acceptance pass through teacher and student demo workflows.
- [ ] Approve the exact sanitized commit that will become the public repository root.

## Autonomous Work Boundary

The companion implementation plan contains the work that can proceed without founder input:

- remove obsolete and generated artifacts;
- replace placeholder CI with secret-free quality checks;
- isolate tests from live services;
- fix deterministic frontend crashes, navigation, routing, state, export, and accessibility defects;
- delete fake actions, duplicate routes, dead modules, and unused dependencies;
- add input and provider-output validation;
- harden uploads and the server-side URL boundary;
- preserve chapters on generation failure and expose truthful states;
- create current migrations and documentation from the code’s actual data contract;
- update package metadata, environment examples, README, and handoff notes;
- verify the sanitized source with Gitleaks, builds, types, lint, tests, and dependency audit.

No founder action is required to begin that cleanup. Public deployment and real-user activation remain gated by the checklist above.
