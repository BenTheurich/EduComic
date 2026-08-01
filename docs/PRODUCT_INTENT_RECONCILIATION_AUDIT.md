# EduComic Product-Intent Reconciliation and Recovery Audit

Date: 2026-08-01  
Audit target: `main` at `a84e728` and `codex/public-release-cleanup` at `c3ee935`  
Status: audit and recovery plan only; no product code, Git refs, deployments, provider accounts, or Supabase resources were changed

## 1. Executive summary

The public-release cleanup should remain the technical foundation. It fixed real security, reliability, truthfulness, accessibility, and maintainability defects. In particular, it removed tracked secrets and private artifacts from the candidate tree, replaced a fake deployment workflow with secret-free CI, added offline tests and explicit type/lint/build gates, bounded request inputs, sanitized errors and logs, removed an arbitrary-URL fetch, made generation states and PDF export truthful, repaired mobile and keyboard behavior, and removed genuinely duplicate or unreachable code.

The cleanup diverged from the clarified product goal when it equated “unsafe or unfinished in a public anonymous deployment” with “not part of the product.” That affected four explicit product capabilities:

- photo-guided student avatars;
- teacher materials whose extracted content grounds story generation;
- real classroom/profile/avatar edit and student/account deletion workflows;
- a real settings destination.

It also left historically intended selective panel regeneration unimplemented. The old UI for several of these capabilities was fake or incomplete, and the old photo/material implementations were unsafe. Those exact implementations should stay deleted. The capabilities should be reimplemented on the cleanup branch’s safer request, error, testing, and accessibility foundations.

The repository must now target three deliberately separate products:

1. a complete local/private/BYOK application with real OpenAI and Black Forest Labs calls;
2. a public fictional demo with no arbitrary personal uploads, paid anonymous generation, or claims of durable persistence;
3. a future school deployment with institutional identity, authorization, privacy, retention, deletion, abuse controls, durable jobs, and operational monitoring.

`c3ee935` is not yet any of those finished targets. It has no reproducible local database migration, durable file-storage contract, or hosted authorization boundary. It stores or falls back to unsafe image URLs and can lose an existing story or remain stuck during failed generation. Its README and setup material are stale. Cleanup Tasks 14, 15, 19, 20, and 21 remain relevant, but Task 19 now starts with a local SQLite schema and moves Supabase-specific RLS and Storage work to the future hosted track.

### Approved local-first direction

The founder approved these decisions on 2026-08-01:

- The first complete release is a single-machine, localhost-only private/BYOK application.
- SQLite replaces Supabase as the default private database.
- Uploaded and generated files use an ignored local data directory.
- SQLAlchemy and Alembic keep the schema portable to hosted PostgreSQL without requiring a database account for local setup.
- The private application uses real local persistence and real OpenAI/BFL calls. It does not pretend that local profile selection is authentication.
- Hosted teacher/student authentication, object storage, RLS, remote access, and school operations are deferred.
- A UI/UX critique, technical audit, remediation pass, and visual-system freeze occur after private application acceptance and before the fictional demo.
- The fictional demo reuses the polished private application components and workflow states.
- Story generation defaults to exactly 12 panels and offers an explicit 20-panel `Full comic` setting.
- Classroom removal and full student erasure are distinct. Full erasure removes the profile, source photo, avatar, provider-input provenance, and every completed story revision/file generated from that student's identity or likeness while preserving the selected idea in a regenerable chapter shell.

The implementation specification is `docs/superpowers/specs/2026-08-01-local-private-byok-implementation-spec.md`.

The approved high-level execution roadmap is `docs/superpowers/plans/2026-08-01-local-private-byok-implementation-plan.md`.

### Capabilities that should return

| Capability | Reconciliation |
|---|---|
| Photo-guided avatars | Reimplement for local/private use with consent, private temporary source storage, image validation/re-encoding, BFL reference input, durable avatar storage, and deletion. Hosted use adds authentication later. Demonstrate publicly with bundled synthetic portraits only. |
| Teacher materials | Reimplement as verified PDF ingestion, text extraction, explicit per-story selection, bounded prompt grounding, provenance, and deletion. Demonstrate with bundled fictional PDFs and pre-extracted text. |
| Edit classroom | Add a real local update contract and UI. Hosted mode adds ownership authorization later. Demo can edit session-local fictional state with a reset label, or remain read-only. |
| Edit/regenerate avatar | Keep the fake page deleted; add a real regeneration flow that preserves the prior avatar until success and cleans the replaced object. Demo uses fixed synthetic before/after assets. |
| Delete student/account | Add explicit leave-classroom versus delete-profile semantics and complete local database/file cleanup. Hosted account and session cleanup comes later. Public demo must not imply durable deletion when none exists. |
| Settings | Add only settings with real persistence and effect: generation defaults, classroom defaults, privacy/retention choices, and provider readiness/model selection. Provider secrets remain server-side. |
| Selective panel regeneration | Implement after durable, atomic generation exists. Preserve the old panel until the replacement image and row are valid. Keep absent from the first public demo unless represented by a fixed fictional fixture. |

## 2. Audit evidence and repository preservation

### Worktrees and branches

| Worktree | Branch / HEAD | State at audit start | Preservation ruling |
|---|---|---|---|
| `C:/Users/benth/Documents/Coding/EduComic` | `main` / `a84e728`; equal to `origin/main` | Founder-owned staged edits/deletions to `SUPABASE_SETUP.md`, `backend/.env`, `backend/.env.example`, `frontend/.env`, `frontend/.env.example`, and `docs/PUBLIC_RELEASE_PHASE_0_STATUS.md`; the status document also has an unstaged change; `AGENTS.md`, the readiness review, and `docs/superpowers/` are untracked. | Do not reset, restore, stash, merge, or overwrite. This audit adds only this clearly named new document. |
| `C:/tmp/EduComic-worktrees/public-release-cleanup` | `codex/public-release-cleanup` / `c3ee935`; no upstream | No staged changes. Five tracked files have unstaged Task 14 work and two Task 14 files are untracked: `backend/src/story_contracts.py` and `backend/tests/test_story_contracts.py`. | Treat all seven paths as founder-owned work. Do not partially commit the modified imports without the two untracked contract files. |

`git merge-base main codex/public-release-cleanup` is `a84e728`. The cleanup range contains 43 commits, changes 212 paths, and totals approximately `+8,258/-20,696`; 111 files were deleted. The first cleanup planning commit is `ae15bc6`, directly after the product-code baseline `a84e728`.

The audit read the readiness review, Phase 0 status, cleanup plan and task reports, `AGENTS.md`, the deleted `.kiro` requirements/design/tasks at the baseline commit, README/setup documents, historical feature notes, active frontend/backend flows, and the committed and dirty cleanup diffs. Historical specifications are used as intent evidence, not as a current implementation contract.

### Important baseline caveat

The baseline was not a verified complete application. The cleanup’s recorded baseline had 23 ESLint errors and 9 warnings; backend test collection failed because a live/manual script was discovered as a test; the frontend build passed with a 623.86 kB main bundle. Several workflows were real but unsafe, while others were no-op or fake-success UI. No cleanup test called a live database or paid provider.

The cleanup task records report 33 backend tests and 43 frontend tests, plus typecheck, lint, and build, passing at `c3ee935`. During this audit, the backend/security review also ran the dirty Task 14 work offline with provider/database secrets blank and bytecode/cache output disabled: 52 tests passed and no live service was contacted. These checks do not verify a real Supabase schema/RLS policy, real provider behavior, durable job recovery, or deployment.

## 3. Reconciliation categories

- **Keep**: retain the cleanup improvement.
- **Keep deleted**: do not restore the deleted implementation.
- **Restore and implement**: restore the product capability by building a correct current implementation, not by reverting old code.
- **Full-app only**: keep the capability in public source and enable it only in private/BYOK or authorized school modes.
- **Demo implementation**: represent the intent with fictional fixtures, bundled assets, or explicitly labeled session-local simulation.
- **Founder decision required**: a genuine choice that changes cost, privacy, data semantics, or product scope.

## 4. Complete cleanup change ledger

The ledger groups all material effects of the 43 cleanup commits; documentation-only sequencing/fix-round commits are grouped with the capability they verified.

| Capability/change | Before cleanup | Cleanup action | Cleanup rationale | Reconciliation verdict | Recommended recovery | Full app behavior | Public demo behavior | Risk/dependencies |
|---|---|---|---|---|---|---|---|---|
| Source secrets and env files (`ef28ff6`) | Tracked backend/frontend env files and secret-bearing history existed. | Removed env files from the candidate tree; added placeholder examples/ignore rules. | Prevent tip-of-tree disclosure. | **Keep** / env files **Keep deleted**. | Rotate exposed OpenAI, BFL, and Supabase keys; publish fresh sanitized history or explicitly rewrite and rescan. | Keys loaded only by backend from local env/secret manager. | No keys and no provider calls. | Tip deletion does not sanitize ancestry; determine whether exposed Supabase key was service-role. |
| Private/generated artifacts (`9240824`) | Contributor settings, PDFs, a photo, generated metadata, manual testers, and many stale fix notes were tracked. | Deleted 4 binaries, generated metadata, local settings, testers, and stale notes. | Remove private, generated, misleading, or contributor-specific artifacts. | Mostly **Keep deleted**. | Recover product intent into maintained docs, not by restoring artifact sprawl. | Current docs only. | Fictional assets must be deliberately licensed/bundled. | Verify asset provenance and all-history secrets before publication. |
| Historical `.kiro` specs (`ef28ff6`) | Requirements documented photo avatars, 20 panels, and selective regeneration but also stale architecture/security assumptions. | Deleted the three specs as obsolete planning artifacts. | Reduce stale/misleading public documentation. | Exact specs **Keep deleted**; intent **Restore and implement** in a current contract. | The current contract uses 12 panels by default and an explicit 20-panel `Full comic` option. | Same full contract. | Demo limitations documented separately. | The approved current contract, not stale specs, governs runtime. |
| Package identity, locks, and unused backend dependencies (`6d088c1`) | Generic Vite identity, npm and Bun locks, generated Python package identity, broken/unused dependencies. | Kept npm lock, removed Bun lock/generated metadata and verified unused dependencies. | Reproducible installs and smaller dependency surface. | **Keep** / redundant files **Keep deleted**. | Add dependencies only when recovered features need them and with tests. | Same lock; no provider-only dependencies in browser. | PDF extraction may require one maintained parser; run audits after additions. |
| Offline backend harness/readiness (`65e941e`, `86fd084`) | Imports required live config; pytest collected a broken live script; health conflated liveness/readiness. | Isolated tests, lazy config failure, separate `/health` and `/ready`, canonical BFL key. | Make checks secret-free and honest. | **Keep**. | Extend private readiness for the SQLite migration, local data-directory writability, model config, and generation capability. Add hosted checks later. | Demo readiness asserts provider calls and mutations are disabled. | Readiness currently checks only strings, not database/storage/job capability. |
| Frontend test/type gates (`9c0189d`) | Permissive checks missed real shared-type errors; no workflow tests. | Added explicit typecheck, Vitest/Testing Library, and initial smoke tests. | Make frontend regressions observable. | **Keep**. | Extend tests for recovered workflows. | Add mode-boundary and fixture tests. | Avoid paid/network tests in CI. |
| Placeholder deployment versus CI (`e6ab427`) | Workflow tolerated failures, wrote env files, and printed deployment success without deploying. | Deleted it and added read-only, secret-free CI. | Remove fake-success and secret dependence. | CI **Keep**; old workflow **Keep deleted**. | Add deployment only after a target and access model are approved. | Build static/read-only demo with no secrets. | `.github/DEPLOYMENT.md` is stale; three high React Router v6 advisories remain. |
| Invite/mobile navigation (`d624aec`, `ef5aa81`) | Direct invites could null-crash; mobile nav omitted content and used inaccessible controls; layout collapsed on mobile. | Added loading guards, shared nav children, real buttons, Escape/focus return, responsive roots. | Correctness and accessibility. | **Keep**. | Authorized invite flow. | Fictional persona/classroom selection using the same accessible shell. | Current join trusts a localStorage student ID and is not identity. |
| Fake story options and fake actions (`c05e519`, `eac0bfd`) | Provider failure produced mock choices; Edit Classroom/Delete Account/Edit Avatar were no-op or fake; a fake avatar page invented an ID. | Removed fake fallbacks/actions/page; kept truthful retry; corrected signup/enrollment/avatar ordering. | Do not claim provider success or persistence. | Fake implementations **Keep deleted**; capabilities **Restore and implement**. | Real local mutations and provider results only. Hosted mode adds authorization later. | Fixed fixture choices and session-only actions visibly labeled `Demo`; never claim durable save/provider success. | Signup remains non-transactional and can orphan a student on enrollment failure. |
| Truthful chapter state/readers (`c3b126d`, `4dc93dd`) | UI invented progress/“Completed,” mixed poll errors with elapsed time, and allowed non-ready reading. | Shared status vocabulary, terminal failure UI, indeterminate progress, ready-only lists/readers/navigation. | State must reflect backend truth. | **Keep**. | Drive from durable job state. | Deterministic fixture state machine labeled simulated. | Backend can still remain stuck in `generating`; zero-panel ready text has a minor truth bug. |
| Production API URL (`56462b2`, `8fb0d4f`) | Production silently fell back to localhost; callers constructed URLs separately. | Centralized URL resolution and failed builds without production URL. | Avoid misconfigured deployments. | **Keep**. | Separate private and school backend URLs. | Demo build points to read-only fixture service or contains local fixtures. | Client configuration is not an authorization boundary. |
| PDF export (`c6fc9e8`, `626ad1b`) | Duplicated callers could save blank/partial PDFs after failed image fetch/embed. | One fail-closed exporter with timeouts, full image validation/decode, aspect preservation, and success only after save. | Reliability, integrity, advisory remediation. | **Keep**. | Private app exports through local media routes. Hosted mode later uses authorized signed assets. | Export bundled same-origin fictional panels; this is real client work, not simulation. | Every required image must remain available through the export; no silent partial output. |
| Request validation, safe errors/logs, and CORS (`da122f5`, `8a9b294`, `59a9776`) | Scalar query mutations, weak bounds, raw exception/provider data, wildcard credentialed CORS, sensitive logging. | Bounded JSON/Pydantic models, UUID/style checks, origin allowlist, error references, redacted logs/review output. | Trust-boundary hardening. | **Keep**. | Extend to every recovered upload/edit/delete endpoint. | Server rejects disabled routes regardless of UI. | CORS is not authentication; file contents and model outputs remain untrusted. |
| Story-option thumbnails and arbitrary URL fetch (`8ec8452`, `b9642c2`) | Optional BFL thumbnails worked, but used legacy provider configuration and sent a caller-controlled URL to a backend fetch that could reach private networks. | Deleted thumbnail generation, fetch, second key name, and request field. | Remove SSRF, excess paid calls, and duplicate provider path. | Old fetch/implementation **Keep deleted**; thumbnail capability **Founder decision required**. | Defer by default. If retained, create previews server-side from an owned provider job/result, or reuse a final panel/cover. | Use bundled covers only. | Never restore caller-supplied server fetch; this optional feature adds provider cost and story-choice latency. |
| Parallel story APIs/helpers (`635317b`, `6f20437`) | One endpoint returned success while saying unimplemented; two generation paths duplicated the active chapter path; relationship helpers were duplicated. | Kept one start→choose→commit→read chain and rejected stale routes under all methods. | One truthful implementation. | **Keep deleted**. | Extend the canonical chapter API only. | Demo mirrors canonical response shapes with fixtures. | Avoid compatibility routes until an actual external consumer exists. |
| Materials CRUD removal (`350392c`, `91ab256`) | Upload/list/delete UI and Supabase CRUD/storage could operate if remotely provisioned, but no extraction or generation service read the material. Caller MIME was trusted. | Removed all material UI/routes/helpers/storage claims. | The feature misrepresented grounding and enlarged an unsafe surface. | Old CRUD **Keep deleted**; capability **Restore and implement** + **Full-app only**; **Demo implementation**. | Verified local PDF upload, extraction, selected sources, prompt grounding/provenance, retention, and file deletion. | Bundled fictional PDF(s), visible extracted snippets, deterministic grounded output; no public upload. | Local path safety, parser limits, prompt-injection treatment, extraction failure UX, and migrations. Hosted auth/storage comes later. |
| Dead frontend modules/dependencies (`4a53b1f`) | Large scaffold contained 38 unreachable modules and 28 unused dependencies. | Removed them, kept all active routes, lazy-loaded pages; main bundle fell to about 403.87 kB. | Reduce unowned code and attack/update surface. | **Keep deleted**. | Re-add a primitive only when a recovered feature uses it. | Same. | Do not restore whole UI scaffold to build forms; use native/existing components first. |
| Unauthenticated student-photo flow (`9185bfc`) | A real photo upload wrote public `StudentPhotos` objects; signup passed the public URL to BFL. It lacked auth, strong decoding, consent, retention, and abandoned-upload cleanup. | Removed upload route/field/UI/fallbacks and unused image/multipart dependencies. | Child-photo handling was unsafe for anonymous public hosting. | Old implementation **Keep deleted**; capability **Restore and implement** + **Full-app only**; **Demo implementation**. | Local optional upload, consent, byte/pixel validation, metadata stripping/re-encode, private local source, supported encoded BFL input, durable local avatar, retention policy, and cleanup. Hosted use adds authenticated ownership later. | Select only bundled synthetic portraits and bundled generated results; visibly state no upload/provider/persistence occurs. | Minor-data policy, BFL input contract, local path safety, deletion, and quotas. |
| Accessibility/responsive/reduced motion (`6eed33f`, `bf4ba58`, `d9ab5ed`, `b1a0f71`, `84ae8f9`) | Pointer-only choices, weak labels/focus/touch targets/contrast, hidden load failures, poor narrow reader layout. | Native/labelled controls, focus behavior, 44 px targets, contrast, reduced motion, responsive readers, visible retryable errors, headed browser checks. | **Keep**. | Recovered flows must meet the same standard. | Same shell and controls. | Remaining gaps: story option control semantics, some icon labels, and retry buttons/tests on several pages. |
| Public identity/config cleanup (`c3ee935`) | Lovable metadata/tagger and mismatched local origin remained. | Removed template identity and aligned local CORS/Vite port. | Accurate product identity and configuration. | **Keep**. | Finish docs and metadata. | Demo must disclose fixture/simulation behavior. | README/frontend/backend setup still contain stale routes, scripts, schema, and license placeholder. |
| Strict provider-output contracts (dirty Task 14) | Story ideas/scripts used permissive JSON, padding/default normalization, oversized prompt context, and review-on defaults. | Pydantic contracts require exactly 3 ideas and sequential bounded panels/speakers; services use structured parsing/token caps; narrative context drops IDs/avatar URLs; review defaults off and attempts are capped. | Reject invalid model output before persistence/provider fan-out and minimize personal context/cost. | **Keep direction** with the approved exact selected count. | Require exactly the snapshotted 12 or 20 panels before image-provider fan-out or publication. | Reuse the same response schema with fixtures. | Generation snapshots its contract so later settings changes do not alter an active or historical run. |
| Generation atomicity/failure state (planned Task 15) | In-process background work deletes panels early, inserts incrementally, may persist expiring BFL URLs, may race, and can stay `generating`. | Planned but not completed. | Prevent data loss, partial stories, stuck state, and false readiness. | **Restore and implement**; still-relevant cleanup work. | Generate and durably upload complete replacement, atomic DB swap, idempotency/concurrency guard, top-level `failed`, cleanup obsolete objects; durable worker before school deployment. | No live job; deterministic labelled simulation only. | Required before avatar/panel regeneration and public live generation. |
| Data contract and hosted Supabase work (planned Task 19) | Historical schemas conflict with current many-to-many chapters runtime; no checked-in migration proves cascades/statuses or file lifecycle. Setup references nonexistent SQL and public storage. | Planned but not completed. | Reproducibility and deny-by-default data access. | **Restore and implement**, split into local-first and hosted tracks. | Private app: SQLAlchemy models, Alembic migrations, SQLite, fictional seed, constraints/indexes, and local object paths. Hosted track: PostgreSQL/Supabase, authentication, RLS, private buckets, and signed URLs. | Separate fixture store or demo-only seed; provider/mutation routes disabled. | Never restore either historical schema verbatim. Keep hosted RLS and service-role risks out of the zero-setup local path without forgetting them. |
| Authentication/authorization/privacy | Baseline and cleanup treat localStorage UUID selection as login and expose all reads/mutations anonymously. | Not addressed beyond CORS/input hardening. | Deferred as founder/public-host gate. | Local profile language **Restore and implement** now; hosted authentication/authorization **Full-app only** later. | Private release binds to `127.0.0.1`, labels profile switching as local mode, minimizes provider data, and implements retention/deletion. Hosted release adds validated identity, ownership/membership checks, and matching RLS. | Fictional personas with no claim of authentication and no sensitive/persistent data. | The local API must not be advertised as network-safe. OpenAI under-18 guidance adds a ZDR gate for under-13/applicable-age personal data. |
| Classroom editing | Baseline button had no handler; cleanup removed it. No update API exists. | Removed fake control. | Avoid claiming a mutation. | Fake control **Keep deleted**; capability **Restore and implement**. | Authorized PATCH with validation, optimistic concurrency, real success/error UI. | Read-only, or clearly session-local fictional edit that resets. | Ownership, audit of prompt-impacting fields, concurrent generation behavior. |
| Student/profile and existing-avatar editing | Baseline fake page invented an ID; cleanup retains only missing-avatar retry. | Removed fake edit route/page. | Avoid fake persistence/provider action. | Fake page **Keep deleted**; capability **Restore and implement** + **Full-app only**; **Demo implementation**. | Authorized profile update and avatar regenerate; keep old avatar until new durable object/row succeeds; remove replaced object. | Synthetic portrait/avatar pairs; “preview only” or session-local selection. | Consent, quotas, object cleanup, story consistency when avatar changes. |
| Student/account deletion and leave | Database had simple row deletes and an unauthenticated leave route; UI Delete Account only logged/navigated. No complete file cleanup contract existed. | Removed fake Delete Account. | Avoid false deletion. | Fake UI **Keep deleted**; real distinct operations **Restore and implement**. | Private release separates unenrollment from full erasure. Full erasure removes personal files, provider-input records, and affected revisions/assets, then publishes the latest unaffected revision or preserves a regenerable chapter shell. | No durable delete claim; reset session-local persona state only. | Cleanup is manifest-backed and retryable; success is withheld while required files or rows remain. |
| Settings | Sidebar linked a nonexistent route; cleanup removed link. | Removed broken destination. | Avoid dead navigation. | Broken link **Keep deleted**; capability **Restore and implement**. | Persist generation/classroom defaults, retention choices, and provider readiness/model selection. Keep keys server-side. | Read-only explanation of demo limits and accessibility preferences that truly persist locally. | Scope and BYOK secret placement are founder decisions. |
| Selective panel regeneration | Old requirements promised it, but neither baseline nor cleanup had an active endpoint/UI; automatic initial-generation review is not the feature. | No direct deletion; intent disappeared with stale specs. | It never worked. | **Restore and implement** + **Full-app only** after Task 15. | Authorized per-panel correction prompt; generate/upload replacement, atomically swap one panel, keep old on failure, clean old object, record revision. | Optional fixed before/after example explicitly labelled simulated. | Provider cost, story/avatar consistency, object revisions, safety/review. |
| OpenAI/BFL model and prompt modernization | Baseline/history used older model assumptions, permissive output, legacy BFL paths/keys, and sometimes provider delivery URLs as final assets. Current committed defaults include `gpt-5.1`, `gpt-4o`, and `flux-2-pro`. | BFL base/key consolidated; dirty Task 14 adds strict parsing and prompt minimization. Full modernization not completed. | Reliability, privacy, cost, and current API compatibility. | **Keep** current hardening; **Restore and implement** evaluation-led modernization. | Evaluate current OpenAI Sol/Terra roles on fictional fixtures; keep model IDs configurable/pinned; use BFL `api.bfl.ai`, returned `polling_url`, pinned production endpoint, private reference inputs, and immediate durable copy. | No paid calls; replay schema-valid fixtures and bundled images. | Never auto-upgrade production models without eval; provider terms/data controls for minors; current BFL `safety_tolerance=4` needs child-safety review. |
| README/setup/architecture/provider handoff (planned Task 20) | Docs advertise deleted endpoints, nonexistent scripts/SQL/routes, public buckets, obsolete schema, Lovable template text, and a license placeholder. | Task 20A fixed only identity/port metadata; full rewrite unfinished. | Public truthfulness and reproducibility. | **Keep plan**, broaden for three modes and restored features. | Verified commands, migration setup, BYOK/provider data flow, limitations. | Exact fixture/simulation disclosures and zero-secret setup. | Do not invent license, deployment, privacy, or production claims. |
| Final verification/public release gate (planned Task 21) | No coherent release candidate existed. | Unit/browser checks were added during cleanup; final source export/signoff not run. | Prevent unsafe publication. | **Keep plan**, run separately for each mode. | Offline suite plus opt-in fictional provider integration, migration reset, auth/ownership, job-failure, deletion, browser/PDF checks. | Build with no secrets; assert disabled routes, fictional data, labels, no external provider requests, and deterministic reset. | Fresh-history Gitleaks and key rotation are owner gates; no public push/deploy during recovery audit. |

### Commit coverage

The ledger covers the cleanup range through these groups: planning/records (`ae15bc6`, `f5ab6ac`, `c87bab5`, `fea50fd`, `b8e5e7b`, `f02261e`, `bdf4980`, `01769bf`); package/test foundations (`6d088c1`, `65e941e`, `86fd084`, `9c0189d`); workflow and state fixes (`d624aec`, `a7a8352`, `c05e519`, `eac0bfd`, `c3b126d`, `4dc93dd`, `56462b2`, `8fb0d4f`, `ef5aa81`); sanitation (`ef28ff6`, `9240824`); PDF/API/security (`c6fc9e8`, `626ad1b`, `da122f5`, `8a9b294`, `59a9776`, `8ec8452`, `b9642c2`); consolidation/deletion (`635317b`, `6f20437`, `350392c`, `91ab256`, `4a53b1f`); CI/photo/accessibility/identity (`e6ab427`, `9185bfc`, `6eed33f`, `bf4ba58`, `d9ab5ed`, `b1a0f71`, `84ae8f9`, `c3ee935`).

## 5. Product-mode matrix

These are separate deployment profiles, not one environment with a few hidden buttons. The server must enforce capabilities; a frontend flag alone is insufficient.

| Boundary | Full local/private/BYOK application | Public fictional demo | Future production/school deployment |
|---|---|---|---|
| Purpose | Primary complete product for one founder/developer-controlled computer and founder-supplied provider accounts. | Show both roles and product intent without personal data, anonymous spend, or false persistence. | Multi-user hosted website for teachers and students on separate devices. |
| Data | SQLite in an ignored local data directory. SQLAlchemy models and Alembic migrations define the contract. | Bundled fictional classrooms, students, materials, portraits, avatars, stories, and panels. Session changes reset and are labelled. | Hosted PostgreSQL, including Supabase or an equivalent provider, with tenant and school boundaries. |
| Files | Local materials, source photos, avatars, and story images under `EDUCOMIC_DATA_DIR`; FastAPI returns media URLs rather than filesystem paths. | Bundled synthetic assets only. | Private object storage, signed delivery, lifecycle rules, and deletion jobs. |
| Identity/access | One local teacher profile and explicit student preview/profile selection. This is not authentication. FastAPI binds to `127.0.0.1`. | Persona selection, not authentication. No endpoint can enumerate or mutate a real database. | Teacher, student, and administrator authentication, lifecycle/recovery, ownership/membership authorization, optional SSO, and RLS where applicable. |
| OpenAI/BFL | Real backend calls using BYOK keys from an ignored environment file; model/cost controls and opt-in fictional integration tests. | Provider routes are absent or disabled; fixture responses only. UI states that the example is simulated. | Managed organization/project keys, quotas, budgets, durable queues, monitoring, provider data controls, and incident response. |
| Story generation | Real start, choose, generation run, ready/failed state, local durable images, and atomic revision replacement. | Deterministic fixture transition with an honest simulated status. It does not claim a provider or database succeeded. | Durable workers, idempotency, concurrency control, retries, cost accounting, audit, and service objectives. |
| Materials | Local PDF upload, verified extraction, explicit selection, provenance/grounding, retention, and file deletion. | Bundled fictional material and pre-extracted text; no uploads. | Malware/content controls, institutional policy, limits, audit, retention, and optional OCR after evaluation. |
| Student photos/avatars | Optional local photo input with explicit consent, normalized private source, supported encoded BFL input, durable local avatar, retention, and deletion. | Choose a bundled synthetic portrait and show a bundled avatar result. No arbitrary upload. | Guardian/school consent as applicable, strict purpose/retention, access audit, deletion, and provider data controls. |
| Edit/delete/settings | Real SQLite and local-file changes; settings have documented effects. | Session-local preview/reset only, or read-only. Settings explain demo limits and persist only real browser preferences. | Role-scoped administration/self-service, retention/legal holds, auditable deletion, and policy settings. |
| Abuse/cost | Localhost binding, provider concurrency limits, and explicit paid-test commands; no browser-visible keys. | No paid endpoints. | Per-user/IP/tenant limits, deduplication, provider spending caps, billing alerts, and audit. |
| Release criterion | Clean checkout, automatic SQLite migration, local backup/reset instructions, offline tests, explicit paid fictional smoke test, complete browser workflows, and correct file/database deletion. | Zero secrets, zero provider requests, no durable writes, fictional-data scan, simulation labels, accessible teacher/student paths, and fresh sanitized history. | Security/privacy/legal review, production migration rehearsal, load/failure recovery, monitoring, incident procedures, and verified erasure. |

Recommended profile names are `local_private`, `public_demo`, and `school_hosted`. Each has its own environment contract and startup assertions. `local_private` must bind to localhost by default. `public_demo` must fail closed if provider keys or mutation routes are enabled. `school_hosted` must fail closed if authentication, authorization, private storage, or durable jobs are absent.

## 6. Official provider/platform findings

### OpenAI

- The official model resolver used for this audit identifies the current flagship as `gpt-5.6-sol`. OpenAI’s current guidance also presents Terra as the balanced intelligence/cost option. The application should not blindly replace every call with the most expensive model; it should evaluate Sol and Terra by role on fictional fixtures and pin the chosen production IDs/configuration. See [latest model guidance](https://developers.openai.com/api/docs/guides/latest-model).
- The dirty cleanup work’s `chat.completions.parse` plus Pydantic contracts is current and supported. OpenAI recommends the Responses API for new work, but Chat Completions remains supported. Migrate one flow only if evals, privacy controls, or operational simplicity improve; structured-output shape differs in Responses. See [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [migrating to Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses).
- Keep narrative calls data-minimal: fictional/pseudonymous character text, no database IDs, no avatar URLs, and only selected material excerpts. If Responses is adopted, review storage behavior and use `store: false` where appropriate.
- Add stable privacy-preserving `safety_identifier` values and use the free Moderation API where it helps. See [safety best practices](https://developers.openai.com/api/docs/guides/safety-best-practices).
- Most importantly, OpenAI’s [under-18 API guidance](https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance) states that personal data of children under 13 or the applicable age of digital consent must not be processed without first implementing Zero Data Retention. A private/BYOK deployment does not remove that provider requirement. Real-minor use therefore remains gated by data minimization, consent/legal review, age-appropriate safeguards, and the necessary OpenAI data controls.

### Black Forest Labs

- Keep the current global `https://api.bfl.ai` integration pattern and provider-returned `polling_url`; remove all legacy `api.bfl.ml` assumptions. BFL says sample delivery URLs are not intended for direct serving and expire quickly, so every accepted result must be downloaded, validated, and stored durably before a job is ready. See [integration guidelines](https://docs.bfl.ai/api_integration/integration_guidelines).
- `flux-2-pro` is the sensible pinned reproducible default for production-quality generation; preview endpoints are useful for explicit evaluation, not silent upgrades. See [image generation quick start](https://docs.bfl.ai/quick_start/generating_images) and [release notes](https://docs.bfl.ai/release-notes).
- FLUX.2 supports `input_image`/multi-reference editing and is suitable for consistent fictional/student character references. Source photos should be supplied as short-lived authorized inputs or supported encoded data, never as permanently public child-photo URLs. See [FLUX.2 image editing](https://docs.bfl.ai/flux_2/flux2_image_editing) and [prompting guidance](https://docs.bfl.ai/guides/prompting_guide_flux2).
- Use project-scoped BFL keys/spending controls, bounded polling/retry behavior, and provider concurrency limits. Review the current `safety_tolerance=4`; BFL documents lower values as stricter and a child-facing default should not silently be more permissive than the provider default.

### Supabase for future hosted deployments

Supabase is no longer part of the private application's setup or runtime contract. These findings remain requirements if the future hosted website uses Supabase for PostgreSQL, authentication, or object storage.

- RLS must be enabled on exposed tables and policies must enforce the same teacher ownership/student membership rules as the API. See [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).
- Storage buckets are private by default; private assets should use authorized downloads or short signed URLs. Public demo assets should be bundled separately, not placed in the sensitive application buckets. See [Storage buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals).
- Delete objects through the Storage API, not direct SQL metadata deletion, to avoid orphaned provider objects. See [deleting objects](https://supabase.com/docs/guides/storage/management/delete-objects).
- Service-key uploads do not automatically receive end-user ownership. Object paths and ownership must be deliberate. See [Storage ownership](https://supabase.com/docs/guides/storage/security/ownership).
- Auth/profile deletion needs ordered cleanup: a profile can cascade from `auth.users`, but storage objects may block user deletion and sessions can survive until JWT expiry. See [managing user data](https://supabase.com/docs/guides/auth/managing-user-data).
- Check in versioned migrations and fictional seeds and prove them with a local/disposable reset before remote application. See [local development and migrations](https://supabase.com/docs/guides/local-development/cli-workflows).

## 7. Dependency-ordered recovery plan

No phase below authorizes a public push, deployment, provider call, key rotation, or remote migration. Use fictional fixtures throughout automated verification. Product code changes begin only after this audit and the material founder decisions are approved.

### Phase 0: Preserve and establish the recovery branch

1. Founder reviews this reconciliation and resolves the blocking decisions below, especially panel count, identity model, deletion semantics, and photo retention.
2. Snapshot the existing main Phase 0 changes and the complete seven-path Task 14 dirty set separately; do not mix them or omit the untracked schema/test files.
3. Create a new `codex/product-intent-recovery` worktree from the preserved cleanup tip. Leave both current worktrees untouched.
4. Add an authoritative current product/mode contract. Keep stale `.kiro` files and historical fix-note sprawl deleted.

Exit criterion: every founder-owned dirty path is committed or otherwise explicitly preserved by the founder, the recovery worktree is clean, and the current contract states the three profiles and story-length decision.

### Phase 1: Finish still-relevant cleanup foundations

1. Complete Task 14’s strict Pydantic output contracts after adapting the panel bounds to the approved product contract.
2. Keep exactly three nonblank ideas, sequential panels, known speakers, bounded dialogue/description, explicit token ceilings, data-minimal narrative prompts, review disabled by default, and capped attempts.
3. Add/update offline tests for schema rejection, speaker membership, sequential panels, prompt data minimization, and no database/BFL work after invalid OpenAI output.
4. Finish the small residual accessibility/error items: one native uniquely named story-choice control per option, accessible names for remaining icon buttons, and retry controls/tests where an error currently has none.

Exit criterion: offline backend/frontend gates pass; invalid provider output cannot reach persistence or image generation; no capability is removed to make tests pass.

### Phase 2: Replace Supabase with local persistence and files

1. Implement the relevant part of Task 19 as SQLAlchemy 2 models and Alembic migrations for SQLite. Keep UUIDs, UTC timestamps, constraints, indexes, cascades, many-to-many enrollment, chapter revisions, material provenance, generation runs, and recorded local object paths portable to PostgreSQL.
2. Set `DATABASE_URL` to the SQLite file under `EDUCOMIC_DATA_DIR` by default. Apply checked-in migrations during the documented local startup path.
3. Add a concrete local-storage module for validated staging writes, atomic finalization, bounded media reads, deletion, traversal rejection, and abandoned staging cleanup.
4. Remove Supabase client and Storage requirements from the default private dependency and environment contract.
5. Add fictional seed data, temporary-SQLite repository tests, migration tests, and temporary-directory storage tests.
6. Rewrite setup around the automatic local database and data directory. Remove nonexistent SQL, bucket, and Supabase-account steps from the private quick start.

Exit criterion: a clean checkout with only OpenAI and BFL keys creates and migrates SQLite, starts on `127.0.0.1`, persists data across restarts, and stores no user data in the repository.

### Phase 3: Local mode, privacy, and capability profiles

1. Create one local teacher profile and explicit student preview/profile selection. Remove login/account claims from local mode because no remote identity is verified.
2. Bind FastAPI to `127.0.0.1` by default and document that changing the bind address exposes an unauthenticated application.
3. Add server-side profiles for `local_private`, `public_demo`, and `school_hosted`. The demo and future hosted profiles fail closed when their required controls are absent.
4. Add provider concurrency limits, job deduplication, precise CORS, safe audit events, and readiness for the SQLite migration and local data-directory writability.
5. Document provider sharing, consent, photo retention, deletion, and the OpenAI under-18/ZDR gate before using real minors' data.

Exit criterion: local mode is truthful, persistent, and localhost-only; the public demo cannot reach upload, mutation, or provider handlers; hosted authentication remains a separate later workstream.

### Phase 4: Make generation durable and non-destructive

1. Complete Task 15 before adding panel/avatar regeneration: validate chapter and chosen idea; create a generation revision/idempotency key; keep current panels intact.
2. Generate and validate all replacement panels and copy every BFL result into local staging and final storage. A missing or unwritable data directory is terminal, never a reason to persist a provider delivery URL.
3. Atomically swap panel rows only after the replacement files are complete; mark every top-level failure `failed`; clean new partial files on failure and old files after success.
4. Prevent concurrent commit/provider-spend races. Persist generation-run state in SQLite. Use a durable worker/queue only in the later hosted deployment.
5. Extend readiness to the migration head, data-directory writability, provider config, and recoverable generation-run state.

Exit criterion: fault-injection tests at OpenAI, BFL submit/poll/download, storage, database insert/swap, and process restart preserve the previous story and end in a truthful recoverable state.

### Phase 5: Restore real edit, delete, and settings workflows

1. Add real local classroom/profile update contracts and UI with bounded fields and honest error/success states. Reserve hosted ownership checks for the hosted track.
2. Add existing-avatar regeneration using the durable replacement pattern; preserve the previous avatar on failure and delete it only after a successful row swap.
3. Define and implement separate leave-classroom, delete student profile, delete classroom, delete chapter, and reset-local-data operations. Enumerate recorded local object paths, delete files and database rows with explicit failure handling, and make retries idempotent. Hosted auth-account deletion comes later.
4. Implement the approved shared-story policy when a student is removed and expose its consequences before confirmation.
5. Add a real settings route for settings with effect. Store provider keys only in backend env/secret management for the first BYOK release; the UI may show configured/missing status and approved model/default choices without returning secrets.

Exit criterion: browser and API tests prove local-mode truthfulness, validation, cancel/confirm, failure recovery, and SQLite/file cleanup; no simulated or no-op success remains.

### Phase 6: Restore material grounding

1. Start with native-text PDFs only unless OCR is explicitly approved. Validate extension, MIME, file signature/structure, byte size, page count, and extracted text bounds; reject encrypted/scanned/unreadable files with a clear status.
2. Store the source under a random local object path, extract text in an isolated bounded job, record a content hash/page provenance/status, and allow local deletion/retry.
3. Require teachers to select materials for a story. Include bounded, clearly delimited excerpts in the narrative prompt with instructions to treat document text as source material, not system instructions.
4. Record selected material IDs/content hashes on the chapter and expose a simple “Grounded in …” summary. Prove influence with paired fictional tests where a unique source fact must appear and unsupported facts must not.
5. Avoid a vector database until fixture size/retrieval quality demonstrates it is needed; bounded direct extraction is the smaller reliable first implementation.

Exit criterion: an uploaded fictional text PDF changes generated structured output in the expected grounded way; an unselected material does not; deletion removes the local file and database data; the demo uses the same schema with bundled pre-extracted fixtures only.

### Phase 7: Restore optional photo-guided avatars

1. Add a local optional upload with explicit consent copy and the approved retention default. Hosted use adds authenticated ownership later.
2. Decode by content, enforce byte/dimension limits, strip metadata, normalize/re-encode, assign a random local object path, and clean abandoned uploads.
3. Give BFL supported encoded input or a provider upload. A localhost URL is not a valid provider reference and a permanent public child-photo URL is forbidden.
4. Validate/download the BFL result immediately, write a durable local avatar, atomically update the student, and remove old/source files according to policy. Keep the prior avatar on failure.
5. Test only with synthetic portraits. Add quotas and provider-safe failure messages.

Exit criterion: synthetic fixture tests cover upload validation, consent requirement, provider input, provider failure, durable local copy, replacement cleanup, and profile deletion; public demo accepts only bundled synthetic selections.

### Phase 8: Modernize providers and evaluate prompts

1. Keep model IDs/configuration explicit by role: idea generation, script generation, optional vision review, avatar image editing, and comic panels.
2. Evaluate current OpenAI Sol versus Terra on a checked-in fictional corpus for schema conformance, educational grounding, age-appropriate language, cast distribution, prompt-injection resistance, latency, and recorded token/cost estimates. Keep tests offline by default and require an explicit cost acknowledgement for live fixture runs.
3. Keep `chat.completions.parse` if it wins on simplicity/reliability; trial Responses on one flow with `store: false` where appropriate rather than performing a broad API churn.
4. Use BFL `flux-2-pro` as the pinned baseline, compare preview models only in explicit evaluation, use structured multi-reference prompts, and set a reviewed child-appropriate safety tolerance.
5. Retain cached fictional evaluation artifacts and human visual rubrics; never use real student data in prompt/image evaluation.

Exit criterion: model/default choices are backed by recorded fictional eval results, not “latest” branding; provider delivery URLs never reach persisted ready records; prompt/model changes require eval comparison.

Non-blocking carry-forward ledger from the Phase 4 review:

- Clear the erased student profile from frontend memory immediately after successful full erasure, before navigation completes.
- Add the same destructive actions to the compact student/classroom list views as the detail views.
- Install and run the configured Ruff gate in the checked-in backend development environment before final release.
- Refresh the frontend Browserslist database during the final dependency-maintenance pass.

### Phase 9: Complete story correction and export workflows

1. Add local selective panel regeneration using the same revision, atomic swap, and file-cleanup rules as full generation. Hosted authorization comes later.
2. Show correction status and previous panel until success; keep full-story status readable and truthful.
3. Ensure PDF export can read local media routes for the full export and still fails closed.
4. Decide whether changing a student avatar affects only future stories or enables explicit historical panel regeneration.

Exit criterion: selective regeneration updates only requested panels, preserves all others, preserves the old target on failure, and exports the resulting story successfully.

### Phase 10: Accept the complete local/private/BYOK application

1. Verify a clean checkout starts without Supabase variables, an external database, Docker, or object-storage setup.
2. Verify first start creates and migrates SQLite, prepares the local data directory, and reports OpenAI/BFL readiness without a paid call.
3. Run every teacher and student workflow through browser restart and backend restart boundaries using fictional records.
4. Verify materials influence story output, photo guidance uses a synthetic portrait, generated assets remain available after provider URLs expire, deletion removes local files and rows, and failed regeneration preserves the previous result.
5. Document local backup, reset, data location, provider data sharing, cost, and the unsupported risk of binding beyond `127.0.0.1`.

Exit criterion: the local application is functionally complete, persistent, truthful, and usable from a clean checkout with only the documented OpenAI and BFL keys.

### Phase 11: Run the UI/UX audit and remediation gate

1. Create `PRODUCT.md` with the approved audience, teacher/student goals, product vocabulary, tone, and privacy constraints. Document the incumbent visual system before choosing refinement or redesign.
2. Run an independent UX critique across both full role journeys. Score Nielsen heuristics, cognitive load, error recovery, user control, terminology, product specificity, and high-stakes moments such as photo sharing, generation, and deletion.
3. Run a technical audit for accessibility, keyboard completion, contrast, reduced motion, responsive behavior, text zoom, long content, empty/error/loading states, image and route performance, theming, and implementation drift.
4. Fix all blocking and major findings plus repeated-component minor findings. Preserve the cleanup pass's verified accessibility improvements.
5. Inspect desktop and mobile once as a batch, apply one grouped fix pass, then run one confirmation batch.
6. Document and freeze shared tokens, components, interaction patterns, responsive rules, and truthful status language.

Exit criterion: teacher and student primary flows pass the approved usability and technical quality thresholds, and the shared UI system is the sole visual source for the demo.

### Phase 12: Derive the public fictional demo

1. Build both role paths from the audited product shell: fictional teacher classroom/material selection/story review/export and fictional student join/profile/avatar/story reader.
2. Bundle synthetic portraits, avatars, PDFs, extracted snippets, story choices, panels, and expected state transitions with documented provenance.
3. Use read-only fixtures or browser session state. Label every generated-looking transition `Simulated demo`; state that changes reset and no provider/database call occurred.
4. Assert at the server/build boundary that upload, mutation, deletion, and provider routes are unavailable. Capture outbound requests in browser tests and fail on unexpected OpenAI, BFL, Supabase, or mutation traffic.
5. Import the private application's shared components and tokens. Do not create a parallel demo visual system.

Exit criterion: a secret-free build demonstrates both roles, accepts no arbitrary files or personal data, makes no paid call, writes no durable data, exports a real PDF from bundled panels, and never reports fake persistence.

### Phase 13: Finish documentation and release verification

1. Complete reframed Tasks 20 and 21: rewrite README, backend/frontend setup, architecture, provider handoff, deployment notes, and mode limitations from verified commands, routes, and migrations.
2. Make the private quick start local-first. Supabase appears only in the future hosted architecture.
3. Remove internal SDD reports from the final public export after their relevant decisions/results are captured in maintained docs.
4. Re-run backend tests/compile/lint, frontend tests/typecheck/lint/build, dependency audits, redacted Gitleaks on the exact source export and chosen history, and headed desktop/mobile keyboard/reduced-motion/overflow/console/network workflows for each released profile.
5. Resolve or explicitly gate the React Router advisory through a tested supported major upgrade before hosted school use; do not perform a blind dependency bump.
6. Rotate exposed keys and create a fresh sanitized public repository only as explicit founder actions after source acceptance.

Exit criterion: separate signed-off checklists exist for the local/private app and public demo; documentation contains no nonexistent path, mandatory hosted service, unsafe storage advice, fake deployment, or unstated simulation.

### Phase 14: Preserve the future hosted track

After the private app and public demo are complete, use the same SQLAlchemy schema with hosted PostgreSQL, replace local files with private object storage, add teacher/student authentication and authorization, add RLS if Supabase exposes the database API, and move generation to durable workers. This is a separate implementation plan, not a hidden requirement of the local release.

## 8. Founder decisions

### Decisions resolved on 2026-08-01

- The first private release is single-machine and localhost-only.
- SQLite and local files replace Supabase in the default private setup.
- SQLAlchemy and Alembic preserve a PostgreSQL migration path.
- Local profile selection is not authentication.
- OpenAI and BFL keys come from an ignored backend environment file in the first release.
- Hosted authentication, Supabase/PostgreSQL, object storage, and school operations are deferred.
- The UI/UX audit and remediation gate occurs before the fictional demo.
- The fictional demo reuses the audited private application's components and visual system.
- Stories default to 12 panels with an explicit 20-panel `Full comic` option.
- Full student erasure removes all profile/likeness inputs and affected revisions/assets while preserving chapter shells and selected ideas for regeneration.

### Decisions still required

Only choices that change implementation or data risk remain here.

1. **Photo retention after successful avatar creation?**
   Recommendation: delete the original normalized photo immediately by default. Retention requires an explicit consent choice and a defined duration.

2. **Material scope: native-text PDFs only or OCR/scanned documents too?**
   Recommendation: native-text PDFs first, with an honest `No extractable text` state. Add OCR only after fictional fixtures demonstrate a need.

3. **Public-demo state model: fully read-only or session-local edits/simulation?**
   Recommendation: allow session-local teacher and student interactions, display a persistent `Fictional demo: resets on refresh; no provider or server persistence` banner, and provide a reset action. Durable backend writes stay disabled.

4. **Real-minor provider boundary?**
   Recommendation: use pseudonyms and the minimum selected material text for OpenAI. Do not send raw student photos to OpenAI. Send a photo to BFL only for explicit avatar creation. Do not enable under-13 or applicable-age personal data until the required provider data controls, including OpenAI ZDR, and consent/legal basis are in place.

5. **Public repository history and license?**
   Recommendation: preserve this repository privately as the historical archive, publish a fresh-history sanitized source repository, and choose an explicit license before release. Do not expose the current secret-bearing ancestry or invent a license in docs.

8. **Should story-option choices regain generated thumbnail previews?**  
   Recommendation: defer them. Text choices are sufficient for the first complete app, and three extra BFL calls add cost and latency before selection. If previews return, create them from server-owned jobs/results or use a low-cost approved model. Never restore the caller-supplied URL fetch.

## 9. Risk-controlled Git recovery strategy

1. **Freeze the evidence.** Before any integration, record `git worktree list`, both statuses, both HEADs, and the seven Task 14 paths. No reset, checkout-overwrite, stash, merge, or broad restore in the current worktrees.
2. **Preserve founder work separately.** The main Phase 0 changes and cleanup Task 14 changes have different intent and should be separate commits/snapshots after founder review. Task 14’s modified imports and untracked contract/test files are one indivisible set.
3. **Branch from cleanup, not main.** Create a new worktree/branch from the preserved cleanup tip because its safety, truthfulness, tests, accessibility, and consolidation work should remain. Do not merge the old main runtime over it.
4. **Do not revert feature-deletion commits wholesale.** In particular, do not revert `9185bfc` (photos), `350392c` (materials), `8ec8452` (thumbnail/URL fetch), or `c05e519` (fake actions). Those reversions would restore unsafe request/storage contracts and collide with later validation/security changes.
5. **Use history as reference.** Inspect old behavior with `git show a84e728:<path>`, focused commit diffs, and historical docs. Copy only validated domain intent; implement new endpoints/services/UI on current contracts.
6. **One recoverable capability per reviewable change.** Suggested dependency branches/commits are: contract/modes; SQLite and local files; local-mode profile language; atomic generation; edit/delete/settings; materials; photo avatars; provider evals; panel regeneration; private acceptance; UI/UX remediation; public demo; docs/release gate. Hosted database/authentication work gets a later plan. Each change includes its smallest meaningful offline check.
7. **Keep remote/external actions separate.** Applying migrations, rotating keys, running paid provider tests, deploying, publishing, rewriting history, and pushing are founder-controlled steps after local review.
8. **Publish sanitized history.** The preferred final public path is a new repository populated from an exact, verified source-only export. Retain the current repository as private historical evidence. If the existing repository must become public, an explicitly approved history rewrite plus all-history Gitleaks and credential rotation is mandatory.

## 10. Final audit verdict

Adopt the cleanup branch as the recovery base and preserve its quality and security work. Keep fake, duplicate, arbitrary-fetch, generated, private, and unreachable implementations deleted. Restore the intended capabilities on SQLite and local file storage, with durable generation and explicit product-mode boundaries. Accept the complete localhost/private/BYOK application first. Run the UI/UX audit and remediation gate next. Derive the public fictional demo from the audited components afterward. Treat hosted PostgreSQL/Supabase, object storage, authentication, and school operations as a later track. The cleanup branch is not public-ready until generation, local migrations, documentation, release verification, and the demo's server-enforced no-personal-data/no-paid-call boundary are complete.
