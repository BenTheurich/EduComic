# EduComic Local Private BYOK Implementation Plan

> **For implementation agents:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when executing this roadmap. Treat each phase as an outcome boundary, inspect the current code before choosing implementation details, and stop at the acceptance gate before continuing.

**Goal:** Deliver a complete localhost/private/BYOK EduComic application, audit and improve its UI/UX, then derive a safe fictional public demo from the same interface and workflow system.

**Architecture:** The private application uses React, FastAPI, SQLite through SQLAlchemy and Alembic, and an ignored local file store. OpenAI and Black Forest Labs calls remain backend-only. Hosted PostgreSQL/Supabase, object storage, authentication, and school operations are a later track.

**Primary specification:** `docs/superpowers/specs/2026-08-01-local-private-byok-implementation-spec.md`

## Planning level

This roadmap intentionally does not prescribe line numbers, internal function names, complete schemas, or code snippets. The agents implementing each phase are expected to inspect the current repository, trace the affected workflow, reuse sound cleanup work, and choose the smallest design that satisfies the specification.

Agents may decide:

- exact file boundaries within the existing backend and frontend structure;
- concrete repository and storage function names;
- test organization and fixtures;
- whether a current module should be split when its responsibilities require it;
- small dependency choices supported by the approved architecture;
- UI component composition within the audited visual system.

Agents must not decide without founder approval:

- product behavior listed in the remaining founder-decision section of the reconciliation audit;
- new hosted services or a return to mandatory Supabase setup;
- public acceptance of personal student data or paid anonymous generation;
- deletion semantics for historical identifiable stories;
- a materially different provider, framework, or deployment target;
- removal of an intended product capability.

## Global constraints

- Preserve the founder-owned dirty changes in both existing worktrees.
- Recover from `codex/public-release-cleanup`; do not merge the old runtime over it or revert deletion commits wholesale.
- Keep the cleanup's validation, safe errors/logging, truthful state, PDF, accessibility, responsive, CI, and dependency improvements.
- The private release must run without Supabase, Docker, a hosted database, or object-storage setup.
- FastAPI binds to `127.0.0.1` by default in local mode.
- Provider keys stay backend-only and out of Git, logs, API responses, and browser state.
- Automated checks use fictional records, bundled PDFs, and synthetic portraits.
- Live provider checks are explicit, optional, and never part of ordinary CI.
- BFL delivery URLs are temporary inputs. Ready records point only to durable local files.
- Invalid provider output cannot mutate story data or trigger image generation.
- A failed generation or regeneration preserves the last readable result.
- The public demo accepts no arbitrary personal upload, performs no paid provider call, and does not claim durable persistence.
- Do not weaken input validation, security boundaries, accessibility, or error handling to restore an old workflow.

## Phase dependencies

```text
Repository preservation and contract baseline
    -> Local database and file foundation
        -> Core local workflow conversion
            -> Durable story generation
                -> Edit, delete, and settings workflows
                    -> Material grounding
                        -> Photo-guided avatars
                            -> Provider evaluation and modernization
                                -> Panel regeneration and private acceptance
                                    -> UI/UX audit and remediation
                                        -> Public fictional demo
                                            -> Documentation and release verification
```

## Phase 0: Preserve the cleanup base and current provider-contract work

### Outcome

A clean recovery worktree starts from the cleanup branch while both existing dirty worktrees remain intact. The seven-file Task 14 provider-contract set is preserved as one coherent change.

### Work

- Record both worktrees, branches, HEADs, staged paths, unstaged paths, and untracked paths.
- Preserve the main Phase 0 documentation/env sanitation and cleanup Task 14 work separately.
- Create a recovery branch/worktree from the preserved cleanup tip.
- Carry forward the strict Pydantic provider-output direction, prompt data minimization, bounded outputs, and review-off default.
- Resolve the panel-count choice before finalizing the strict script contract.
- Establish a green offline baseline in the recovery worktree and record known warnings separately from failures.

### Boundaries

- Do not restore the old photo, materials, thumbnail, fake avatar, fake settings, or duplicate story paths.
- Do not modify, stash, reset, or clean either source worktree.
- Do not call live providers or Supabase.

### Acceptance gate

- Recovery worktree is clean before feature work.
- The Task 14 contract files and their service imports/tests are complete as a set.
- Invalid story ideas, scripts, and panel-review results fail before persistence or BFL work.
- Existing offline backend/frontend gates pass or have a documented, reproducible baseline failure.

## Phase 1: Build the SQLite and local file foundation

### Outcome

The backend has a reproducible local data contract and file lifecycle with no Supabase runtime dependency in the private profile.

### Work

- Add SQLAlchemy and Alembic using the approved SQLite-first, PostgreSQL-portable design.
- Model the current core entities and the approved additions for materials, settings, generation revisions/runs, and recorded file paths.
- Add constraints, indexes, foreign keys, cascades, uniqueness rules, and UTC timestamps in migrations.
- Make the local startup path create the data directory and apply migrations.
- Add local storage operations for validated staging, atomic finalization, bounded reads, deletion, and abandoned staging cleanup.
- Serve local media through FastAPI URLs without exposing filesystem paths.
- Remove Supabase from the private environment contract and default dependency path.
- Keep hosted Supabase guidance only in the future-hosted documentation.

### Implementation discretion

The agent chooses the SQLAlchemy model layout, session pattern, migration organization, and storage module API after tracing current database and service callers. Avoid a generic plugin framework. One concrete local implementation with a narrow boundary is sufficient.

### Acceptance gate

- A blank temporary database upgrades to migration head.
- Foreign keys and constraints fail invalid data.
- Data survives backend restart.
- Storage tests prove traversal rejection, staging cleanup, atomic replacement, and deletion.
- The private backend imports and starts with all Supabase variables absent.
- No API response contains a local filesystem path.

## Phase 2: Convert the current application to truthful local mode

### Outcome

Existing classroom, student, enrollment, chapter, reader, avatar-retry, and PDF flows operate against SQLite and local media without authentication claims.

### Work

- Replace direct Supabase query-builder use in routes and services with the local persistence boundary.
- Create one local teacher profile and a student preview/profile-selection flow.
- Remove `login`, `account`, or security language from actions that only select a local profile.
- Bind local startup to `127.0.0.1` and make any wider bind an explicit unsupported override.
- Make signup/enrollment changes transactional so retries do not create orphan records.
- Preserve truthful loading, empty, failure, ready-only reader, and PDF behavior from the cleanup branch.
- Provide provider and local-data readiness without making paid calls.
- Supply one verified local start command and clear errors for missing keys, migration failure, or unwritable storage.

### Boundaries

- Do not add email/password authentication, remote access, account recovery, or RLS.
- Do not describe local profile selection as secure identity.
- Do not add a second API path for any existing workflow.

### Acceptance gate

- Teacher and student local flows survive browser and backend restarts.
- Student creation and enrollment either both succeed or remain safely retryable.
- Direct invite/selection, chapter lists, readers, and PDF export use local persisted data.
- The app refuses or clearly warns about unsupported network exposure.
- Frontend and backend regression suites pass offline.

## Phase 3: Make story generation durable and non-destructive

### Outcome

Story generation produces complete local revisions, reports every terminal failure, and never destroys a readable story before its replacement succeeds.

### Work

- Complete the still-relevant cleanup Task 15 behavior on SQLite and local files.
- Validate the classroom, chapter, selected idea, and strict OpenAI script before creating BFL work.
- Give each run an idempotency key, target revision, and truthful persisted state.
- Stage and validate every generated image before finalization.
- Swap panel rows as one transaction after all final local files exist.
- Remove failed staging files and retire old revision files only after a successful swap.
- Prevent duplicate/concurrent generation spend for the same chapter.
- Recover or fail interrupted local runs safely at startup.
- Expand readiness for database migration, data-directory writability, and generation configuration.

### Implementation discretion

The agent may use an in-process local worker or persisted job loop suitable for one machine. Do not introduce distributed queue infrastructure. The state must still survive a process interruption without losing the prior story.

### Acceptance gate

- Fault injection at OpenAI, BFL submission/polling/download, decoding, file finalization, and database swap preserves the previous revision.
- Every failed run reaches `failed` with a safe error reference.
- Ready panels use local media, not BFL delivery URLs.
- Duplicate requests do not duplicate provider spend or panel rows.
- Successful stories remain readable after provider URLs expire and after application restart.

## Phase 4: Restore classroom, student, deletion, and settings workflows

### Outcome

Removed fake controls return as real local mutations with complete SQLite and file effects.

### Work

- Implement classroom editing with the same validation rules used at creation.
- Implement student profile editing and existing-avatar regeneration entry points.
- Distinguish classroom removal, student-profile deletion, chapter deletion, classroom deletion, and full local reset.
- Preserve completed stories and panel media unchanged when deleting a student; remove only the profile, memberships, source photo, avatar, and other student-owned local files.
- Make destructive actions explicit, confirmable, idempotent, and honest about partial cleanup failures.
- Add settings only for implemented behavior: story length, design defaults, provider models, review controls, photo retention, local data information, and existing reader/accessibility preferences.
- Keep provider key values in the backend environment file. Settings may show readiness but never return a key.

### Boundaries

- Do not add decorative settings or fake account/deployment controls.
- Do not rewrite completed stories after an ordinary classroom or student edit.
- Do not delete or rewrite completed stories when a student profile is erased.
- Do not report deletion success while required files remain due to an error.

### Acceptance gate

- Edit forms preserve user input after recoverable failures.
- Each delete operation has database and local-file verification.
- Student-profile deletion preserves completed story rows and panel media.
- Retrying an interrupted deletion is safe.
- Existing avatar remains visible until replacement succeeds.
- Settings persist and change the documented behavior.
- Browser checks cover cancellation, confirmation, success, and failure states.

## Phase 5: Restore PDF material extraction and story grounding

### Outcome

Teacher materials are real story inputs rather than unrelated file attachments.

### Work

- Restore material upload around verified, bounded, text-bearing PDFs.
- Store sources locally and record extraction state, content hash, page provenance, and deletion state.
- Give teachers an explicit material-selection step for each story.
- Include bounded selected excerpts in a clearly delimited prompt section that treats document instructions as source text.
- Record the exact material IDs and hashes used by each chapter.
- Show extraction failures and grounded-source metadata in the UI.
- Delete the local source and database records through the shared deletion rules.

### Boundaries

- Native-text PDFs are the first scope. Do not add OCR without founder approval.
- Do not add a vector database until fixture size and retrieval tests prove direct bounded excerpts are insufficient.
- Do not claim a material influenced a story unless its selected content entered the prompt.

### Acceptance gate

- A fictional PDF with a unique fact changes the generated structured story when selected.
- The same file does not enter the prompt when unselected.
- Malformed, encrypted, oversized, textless, and parser-failing PDFs produce truthful states.
- Material deletion removes its file and records without breaking chapters that retain recorded provenance.
- No prompt contains unbounded document content.

## Phase 6: Restore photo-guided avatar generation and editing

### Outcome

The private application supports optional photo-guided avatars with local source handling, explicit provider disclosure, safe replacement, and deletion.

### Work

- Restore optional photo selection in the local student workflow.
- Explain that BFL receives the image for avatar generation.
- Decode and normalize image content, enforce byte/pixel limits, strip metadata, and store a random local source path.
- Send BFL supported encoded input or a provider upload rather than a localhost/public source URL.
- Download, decode, validate, and store the new avatar locally before changing the student row.
- Preserve the prior avatar on failure and clean the replaced avatar after success.
- Apply the founder-approved original-photo retention setting.
- Reuse the same path for first avatar generation and regeneration of an existing avatar.

### Boundaries

- Automated and evaluation inputs use synthetic portraits only.
- Do not send the source photo to OpenAI.
- Do not restore public child-photo URLs, unauthenticated network upload, or permanent provider delivery URLs.

### Acceptance gate

- File validation catches false MIME types, corrupt images, excessive dimensions, and metadata.
- Synthetic photo guidance reaches the expected BFL input field through a mocked provider test.
- Provider/file/database failures retain the prior avatar and clean new partial files.
- Retention and profile deletion remove the required local source/avatar files.
- The UI distinguishes no avatar, generation in progress, failure/retry, and replacement success.

## Phase 7: Modernize providers and evaluate prompt quality

### Outcome

OpenAI and BFL defaults are current, configurable, cost-aware, and selected using fictional evaluation evidence.

### Work

- Keep strict structured output and explicit model roles for ideas, scripts, optional vision review, avatars, and panels.
- Compare the approved current OpenAI candidates on a checked-in fictional prompt/material corpus.
- Evaluate schema conformance, grounding, age-appropriate language, cast use, safety, latency, and recorded token/cost estimates.
- Keep Chat Completions structured parsing unless a bounded Responses trial produces a measured benefit.
- Use current `api.bfl.ai` submission and provider-returned polling URLs.
- Compare pinned BFL production and preview endpoints only through explicit evaluation.
- Restore exactly three story-idea previews through server-owned BFL jobs with bounded concurrency, validated local storage, local media URLs, and per-preview retry that preserves valid text ideas.
- Replace the fixed short BFL abandonment window with bounded, observable status handling; do not repeat paid requests automatically without an explicit cap.
- Set child-appropriate safety defaults and keep automatic panel review disabled unless its measured quality gain justifies its cost.
- Retain synthetic cached artifacts and a human visual rubric for prompt/model changes.

### Boundaries

- No production model silently tracks a latest alias without evaluation.
- No live provider checks in ordinary CI.
- No real student data in provider evaluation.
- Provider modernization must not expand prompt data beyond the minimum required for the task.

### Acceptance gate

- Model selections have recorded fictional evaluation results.
- Structured-contract failure rates and cost/latency observations are documented.
- Provider errors remain sanitized and correlated.
- Story-idea previews and final panel results are durable local media before ready state, and no caller-controlled URL reaches a backend fetch.
- A future model change can rerun the same fixture corpus for comparison.

## Phase 8: Add selective panel regeneration and accept the private app

### Outcome

The complete local application passes its product acceptance gate, including safe correction of individual panels.

### Work

- Implement selected-panel correction prompts and regeneration through the durable revision/file rules.
- Keep the current panel visible until its replacement succeeds.
- Replace only selected panels and clean only replaced files.
- Decide and document how changing a student avatar affects completed stories.
- Verify PDF export after selective regeneration.
- Run a clean-checkout local setup and all teacher/student workflows using fictional data.
- Verify backup, reset, restart persistence, provider readiness, failure recovery, and local data deletion.
- Verify all three idea previews survive restart, selected idea metadata remains canonical across story cards, and preview files follow chapter/reset cleanup.
- Record any remaining issue as a release blocker or a later hosted concern.

### Acceptance gate

- Selective regeneration changes only requested panels.
- Failed correction keeps the old panel and story readable.
- Clean setup requires no Supabase account, Docker, hosted database, or object-storage configuration.
- SQLite, materials, photos, avatars, stories, settings, and local files survive restart and delete correctly.
- Exactly three successful idea previews return as local media URLs; idea summaries are complete and the selected summary/preview become the story description/thumbnail.
- PDF export produces a complete file and fails closed when a required image is unavailable.
- The private application is accepted before visual redesign or demo implementation begins.

## Phase 9: Run the UI/UX audit and remediation gate

### Outcome

Both role journeys have a documented product context, measured UX and technical audit, completed high-priority fixes, and one shared visual system ready for the demo.

### Work

- Use `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`, and the Authored Comic Workshop specification as the shared product and visual context.
- Apply the founder-selected **Authored Comic Workshop** direction as a restrained refinement; preserve routes, role workflows, palette family, shared controls, and verified accessibility behavior.
- Run an independent UX critique and implementation assessment across every primary teacher and student flow.
- Score usability heuristics, cognitive load, error prevention/recovery, user control, terminology, product specificity, and high-stakes moments.
- Run the technical audit for accessibility, keyboard completion, contrast, reduced motion, responsive layouts, zoom/long content, loading/error/empty states, performance, theming, and implementation integrity.
- Preserve the cleanup's verified accessibility and responsive improvements.
- Show three server-owned local story-idea previews, complete unclamped summaries, and accessible per-preview loading/failure/retry states.
- Use the selected idea title, summary, and preview as canonical story-card content; keep the teacher lesson prompt as labelled secondary provenance.
- Keep the current generation loading composition and reveal validated local temporary panel previews progressively without weakening atomic final publication.
- Fix EduComic naming, mobile reader fit-to-width, meaningful comic text alternatives, landmarks/accessibility names, useful reduced-motion status, and repeated copy/metadata defects.
- Fix blocking and major findings, plus repeated minor defects in shared components.
- Inspect desktop and mobile in one batch, make one grouped correction pass, and run one confirmation batch.
- Document the final shared tokens, components, interaction patterns, status language, and responsive rules.

### Implementation discretion

The refinement direction is fixed; implementing agents retain code-level discretion within `DESIGN.md` and the approved specification. They should not replace the information architecture, introduce a new component framework, or expand the phase beyond named audit findings and shared repeated patterns.

### Acceptance gate

- The audit report includes evidence, severity, positive findings, and prioritized remediation.
- Teacher and student primary flows complete with keyboard and representative mobile layouts.
- Blocking and major audit findings are fixed and confirmed.
- Story idea comparison, canonical story metadata, local thumbnails, and progressive generation previews satisfy the approved content/status contracts.
- Error, loading, empty, destructive, and simulated states use consistent language and components.
- The public demo can reuse the same components without a parallel theme or page implementation.

## Phase 10: Derive the public fictional demo

### Outcome

A secret-free public profile demonstrates the teacher and student product without personal-data collection, paid provider access, or false persistence.

### Work

- Bundle fictional classrooms, students, portraits, avatars, materials, extracted snippets, story choices, panels, and expected transitions with documented provenance.
- Reuse the audited private application's components, tokens, layouts, state vocabulary, and PDF exporter.
- Implement teacher material selection, simulated generation, review, and export against fixtures/session state.
- Implement student persona selection, profile/avatar preview, classroom view, and story reader against fixtures/session state.
- Display a persistent demo disclosure and reset action.
- Disable or omit arbitrary uploads, paid provider routes, durable mutations, and destructive backend actions at the server/build boundary.
- Test outbound traffic and fail on unexpected OpenAI, BFL, Supabase, or mutation requests.

### Boundaries

- Do not fork the UI into a separate visual implementation.
- Do not show a real-looking success message for a provider or persistence action that did not occur.
- Do not accept arbitrary public photos or PDFs.
- Do not require provider or database secrets to build or host the demo.

### Acceptance gate

- Both roles can be clicked through at desktop and mobile sizes.
- Every simulated state is labeled and resettable.
- No paid provider request, personal upload, or durable write is possible.
- Bundled assets and data are fictional and reviewed for provenance.
- PDF export from bundled panels is real and complete.
- Browser network inspection shows only expected demo assets and services.

## Phase 11: Finish documentation and release verification

### Outcome

The repository accurately documents the local application, public demo, and later hosted track, and the exact source export passes the release gates.

### Work

- Complete the still-relevant cleanup Tasks 20 and 21 against the new architecture.
- Replace stale routes, nonexistent scripts/SQL, public-bucket advice, Lovable/template copy, and placeholder claims.
- Write a local quick start that requires no Supabase steps.
- Document provider setup, costs, data sharing, local storage, backup/reset/deletion, localhost boundary, and optional live checks.
- Document demo fixtures, simulation, disabled capabilities, and asset provenance.
- Describe hosted PostgreSQL/Supabase, authentication, object storage, and workers as future architecture only.
- Run backend and frontend tests, lint/type/build checks, dependency audits, browser workflows, and redacted secret scans on the exact candidate.
- Resolve or explicitly gate known dependency advisories before any applicable hosted release.
- Produce the sanitized source export and final private/demo acceptance records.

### Acceptance gate

- Every documented command and path exists and has been checked from a clean source tree.
- The private quick start does not mention mandatory Supabase, Docker, hosted database, or object storage.
- The demo build contains no secrets and makes no provider/database requests.
- Gitleaks passes on the chosen public source/history after founder-owned rotation/publication actions.
- No documentation claims authentication, persistence, deployment, privacy compliance, or provider success that the target profile does not provide.

## Deferred hosted plan

After the private app and fictional demo are released, create a separate hosted-school specification and plan. That work may point SQLAlchemy at PostgreSQL, use Supabase or another hosted database, replace local files with private object storage, add teacher/student authentication and account recovery, enforce ownership and tenant isolation, add durable workers, and introduce school operations.

It is not an acceptance dependency for this roadmap.

## Execution and review cadence

- Execute one phase at a time in dependency order.
- Use one fresh implementation agent and one fresh independent reviewer per phase.
- Let the implementation agent choose concrete code details within this plan and specification after tracing only the affected callers and tests.
- Use focused tests during implementation and any fix round, then run the complete backend/frontend/static/build gate once at phase end.
- Repeat the full gate only when a fix changes shared architecture, migrations, dependencies, or cross-cutting runtime behavior.
- Run browser verification for user-visible workflow changes, not routine backend-only fixes without a named browser risk.
- Allow at most one normal fix round and one scoped re-review. If a Critical or Important finding remains, stop and present the load-bearing blocker to the founder.
- Treat Critical and Important findings as blocking. Record Minor findings for the UI/UX or final release phase instead of extending the phase loop.
- Keep review risk-focused: data loss, privacy, deletion, migrations, provider spend/output, storage, authentication claims, and truthful persistence/status receive strict scrutiny; ordinary UI wiring, wording, and low-risk refactoring receive lighter review.
- Do not reopen an approved phase unless a later diff directly regresses it.
- Keep internal briefs, reports, and review packages ignored and uncommitted; commit only actual public project documentation.
- Preserve each phase as one reviewable outcome or a small sequence of coherent commits.
- Ask the founder only when a genuine product decision blocks the phase or the proposed work changes scope.
- Do not expand a phase with speculative hosted infrastructure.

## Plan completion condition

This roadmap is complete when:

1. the local/private/BYOK application passes Phase 8 acceptance;
2. the UI/UX audit and remediation gate passes;
3. the public fictional demo passes Phase 10 acceptance;
4. documentation and release verification pass on the exact source candidate;
5. hosted-school work remains documented as a separate future plan.
