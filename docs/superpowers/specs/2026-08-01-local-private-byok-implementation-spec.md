# EduComic Local Private BYOK Application Implementation Specification

Date: 2026-08-01  
Status: approved architecture direction; implementation has not started

## Goal

The first complete EduComic release must run on one developer-controlled computer without a hosted database, object-storage account, user-authentication service, or container stack. A developer clones the repository, installs the documented dependencies, adds OpenAI and Black Forest Labs keys, starts the application, and can complete the teacher and student workflows with real local persistence and real provider calls.

The public fictional demo comes later. It will reuse the private application's screens, components, workflow states, and visual system after a UI/UX audit and remediation phase.

## Approved decisions

1. The private/BYOK application is the primary implementation target.
2. The private application is single-machine and localhost-only in its first release.
3. SQLite is the default database.
4. Uploaded and generated files are stored in a local data directory.
5. Supabase is not required to install or run the private application.
6. SQLAlchemy and Alembic provide the database boundary and migrations so the same schema can later target PostgreSQL.
7. Provider keys remain backend-only and come from a local ignored environment file in the first release.
8. Multi-user authentication, Internet hosting, object storage, tenant isolation, and school operations belong to a later hosted track.
9. A UI/UX critique, technical audit, remediation pass, and visual-system freeze occur after the private application is functionally complete and before work begins on the fictional demo.
10. The fictional demo uses the polished private application as its visual and interaction source.

## Scope

The local application includes these real workflows:

- create, view, edit, and delete classrooms;
- create, view, edit, enroll, unenroll, and delete student profiles;
- optional synthetic or user-supplied photo guidance for avatar creation;
- create and regenerate an existing avatar;
- upload, extract, select, and delete lesson PDFs;
- generate story options with OpenAI;
- choose an option and generate comic panels with OpenAI and Black Forest Labs;
- monitor truthful generation states;
- read stories in teacher and student views;
- regenerate selected panels without replacing unrelated panels;
- export completed stories as PDFs;
- configure settings that have a real effect;
- remove related database rows and local files when content is deleted.

## Deferred hosted scope

The first private release does not implement:

- public Internet hosting;
- remote student access;
- teacher or student passwords;
- email verification or account recovery;
- school or tenant administration;
- hosted PostgreSQL or Supabase provisioning;
- Supabase Auth, RLS, or Storage policies;
- distributed workers;
- remote object storage or a CDN;
- billing, subscriptions, or managed provider keys;
- production monitoring or incident response.

The local design must not block these capabilities. It does not build partial versions of them.

## Local user experience

### Setup

The documented setup requires OpenAI and BFL keys. Supabase variables are absent from the local environment contract.

On first start, the application:

1. resolves the configured local data directory;
2. creates it if it does not exist;
3. applies checked-in Alembic migrations to the SQLite database;
4. creates the required asset subdirectories;
5. starts FastAPI on `127.0.0.1`;
6. reports provider readiness without calling either paid provider;
7. starts the frontend with the local API URL.

A startup failure names the missing key, failed migration, inaccessible data directory, or unsupported database version. It does not print provider keys, prompts, file contents, or raw exceptions.

### Local identity

Local mode is not authentication. The interface must call it `Local mode` and must not use account or login language for a profile selector.

The application creates one local teacher profile. The teacher can switch to a student preview by selecting a student in one of the teacher's classrooms. The selected student ID is local UI state, not proof of identity.

The API binds to `127.0.0.1` by default. Documentation must warn that changing the bind address exposes an unauthenticated private application and is unsupported in the first release.

### Persistence

Every local mutation is real. A success message means the SQLite transaction and required local file operation completed. Provider-looking fixture results are not used in private mode.

The local application may include fictional seed content, but seed content must be identified as an example. Users can delete it. User-created data survives browser refreshes and application restarts.

## Runtime architecture

The private release keeps the current React and FastAPI split:

```text
React frontend
    -> FastAPI JSON and multipart endpoints on localhost
        -> SQLAlchemy repositories -> SQLite file
        -> local storage functions -> data directory
        -> OpenAI SDK -> story ideas and scripts
        -> BFL HTTP API -> avatars and comic images
```

The frontend never reads the database file, filesystem paths, or provider keys. FastAPI returns application URLs for local media rather than absolute filesystem paths.

## Database design

### Technology

- SQLAlchemy 2 provides database sessions, transactions, models, and queries.
- Alembic provides checked-in migrations.
- SQLite uses Python's built-in driver. An async database dependency is not required for the first release.
- `DATABASE_URL` defaults to the SQLite database inside the local data directory. The local/private runtime accepts SQLite URLs only and rejects hosted or other non-SQLite URLs before creating storage or an engine.
- The database layer avoids SQLite-only query syntax where SQLAlchemy provides a dialect-neutral equivalent.

SQLAlchemy is preferred over raw `sqlite3` because the application needs foreign keys, transactional replacement of panels, schema migrations, and a later PostgreSQL path. A local PostgreSQL or Supabase stack was rejected because it adds account, CLI, container, and schema-provisioning work to the first-run path.

### Initial entities

The local schema contains:

- `local_profiles`: the single local teacher profile and local display settings;
- `classrooms`: classroom settings and a stable owner UUID;
- `students`: teacher-managed student profile data and local avatar/photo paths;
- `student_classrooms`: many-to-many classroom enrollment;
- `materials`: source filename, local object path, extraction state, content hash, page-aware extracted text, and timestamps;
- `chapter_materials`: the exact materials selected for a chapter;
- `chapters`: prompt, chosen idea, title, status, revision, and timestamps;
- `panels`: chapter revision, panel number, dialogue, description, speakers, and local image path;
- `generation_runs`: idempotency key, chapter, target revision, job state, error reference, and timestamps;
- `settings`: generation defaults, retention choices, model selections, and non-secret application preferences.

UUIDs are stored in a PostgreSQL-compatible representation. Timestamps are UTC. Foreign keys are enabled in every SQLite connection. Required uniqueness, status checks, panel sequence rules, and cascades are migrations, not comments in application code.

Provider keys are not stored in any table.

### Transaction rules

- Classroom and student edits use one transaction.
- Enrollment changes use a unique `(student_id, classroom_id)` constraint.
- Story replacement keeps the current revision until every new panel and image is valid.
- The panel-row swap is one database transaction.
- A failed replacement leaves the previous revision readable.
- File deletion occurs through recorded local object paths. Failed cleanup remains retryable and does not produce a false success message.
- Deletion operations are idempotent so an interrupted cleanup can be run again.

## Local file storage

### Data directory

`EDUCOMIC_DATA_DIR` overrides the data location. The development default is an ignored `backend/data/` directory containing:

```text
backend/data/
  educomic.db
  materials/
  student-photos/
  avatars/
  story-images/
  staging/
```

The repository never tracks this directory. Setup and diagnostic commands print its resolved path, not its contents.

### Storage functions

A small concrete local-storage module owns these operations:

- create a random owner-scoped object path;
- write validated bytes to staging;
- atomically move a completed file to its final path;
- open a file for an authorized local response;
- delete a recorded object path;
- remove abandoned staging files;
- report free-space and writability readiness.

Routes and generation services do not call `Path.write_bytes`, Supabase Storage, or provider delivery URLs directly. They call the local-storage functions. A future hosted storage module can implement the same operations without changing teacher or student workflows.

The module must reject absolute paths, parent traversal, unrecognized object classes, and paths outside the configured data directory.

### Media delivery

FastAPI serves local media through bounded application routes. Responses use known MIME types, safe filenames, cache policy appropriate to revisioned assets, and no directory listing. Database responses contain media URLs and object identifiers, not Windows or POSIX filesystem paths.

When BFL needs an input image, the backend sends supported encoded image data or a provider upload. A localhost URL is not sent to BFL because the provider cannot access it. BFL output is downloaded, decoded, validated, and saved locally before the related row becomes ready.

## Provider configuration

The local ignored environment file contains:

- `OPENAI_API_KEY`;
- the selected OpenAI model IDs;
- `BFL_API_KEY`;
- the selected BFL endpoint;
- bounded review and generation settings;
- optional `EDUCOMIC_DATA_DIR` and SQLite-only `DATABASE_URL` overrides.

The frontend receives only provider readiness states and selected non-secret model labels. It never receives key values.

Settings may change model selections and generation defaults stored in SQLite. Changing a key still requires editing the backend environment file and restarting the backend in the first release.

Provider calls use fictional fixtures in automated tests. Live provider verification is an explicit opt-in command that states it can incur cost.

## Materials workflow

The first implementation supports PDFs with extractable text. OCR is outside the first scope.

Upload processing:

1. enforce configured byte and page limits;
2. verify the PDF signature and parser result instead of trusting the browser MIME type;
3. reject encrypted, malformed, or textless files with a named extraction state;
4. store the source under a random local object path;
5. extract bounded page-aware text and a content hash;
6. let the teacher select one or more ready materials for a story;
7. record the exact selected material IDs and hashes on the chapter;
8. place bounded excerpts in a clearly delimited prompt section;
9. treat document instructions as source text, not system instructions.

Paired fictional tests must prove that selected source text changes the structured story and that unselected material does not enter the prompt.

## Photo-guided avatar workflow

Photo guidance is optional. The local UI explains that the configured BFL account receives the image for avatar creation.

The backend:

1. decodes the actual image bytes;
2. enforces byte and pixel limits;
3. strips metadata and normalizes the image;
4. writes a private local source object;
5. sends supported encoded input to BFL;
6. downloads and validates the BFL result;
7. writes a new durable avatar locally;
8. swaps the student avatar row only after the file is ready;
9. retains the previous avatar after any failure;
10. deletes the source photo according to the approved retention setting;
11. deletes the replaced avatar after a successful swap.

Tests and prompt evaluation use synthetic portraits only.

## Generation and regeneration

Story and panel generation use strict provider-output contracts. Invalid OpenAI output cannot create a generation run, delete panels, or call BFL.

A generation run has one idempotency key and target chapter revision. Images first enter staging. The application validates every panel and moves every image to final local storage before swapping the chapter revision in one database transaction.

If the process stops during generation, startup marks the unfinished run failed or resumes only a step that is safe to repeat. It never deletes the previous readable revision.

Selective panel regeneration uses the same rule for one panel: generate and validate the replacement, swap one panel row, then delete the old image. Other panel rows and files do not change.

## Edit, deletion, and settings behavior

### Editing

Classroom and student edits validate the same field bounds as creation. The UI preserves unsaved form values after a recoverable API error. A successful classroom edit affects later stories; it does not rewrite completed stories.

Avatar regeneration is available when an avatar already exists. The old avatar stays visible until replacement succeeds.

### Deletion

The UI distinguishes:

- remove a student from one classroom;
- delete the local student profile and its private source/avatar files;
- delete a chapter and its panel images;
- delete a classroom and its owned materials and chapters;
- reset all local application data.

Each confirmation names the affected data. A deletion reports success only after the required database transaction and file cleanup complete. Shared-story treatment follows the founder-approved deletion policy recorded in the reconciliation document.

### Settings

The first settings page contains only values with an implemented effect:

- story length/default panel count;
- default design style;
- OpenAI model selection;
- BFL endpoint selection;
- automatic panel review enabled/disabled and attempt cap;
- original-photo retention;
- local data directory display and backup guidance;
- provider readiness;
- reduced-motion and reader preferences already supported by the UI.

It does not include decorative toggles, fake account controls, deployment settings, or browser-visible provider keys.

## Private application acceptance gate

The private application is functionally complete before UI redesign or demo work begins. Acceptance requires:

- a clean checkout can start without Supabase variables or a Supabase account;
- the first run creates and migrates SQLite automatically;
- setup needs only the documented OpenAI and BFL keys beyond normal language/package tooling;
- teacher and student local-mode workflows work after restart;
- generated files survive provider delivery URL expiry;
- failed generation preserves the previous story;
- editing and deletion change both SQLite and local files correctly;
- materials demonstrably influence a story generated from fictional fixtures;
- optional photo guidance works with a synthetic portrait;
- selective panel regeneration changes only the selected panel;
- PDF export fails closed and exports a complete story;
- backend tests, frontend tests, typecheck, lint, build, and browser workflows pass without live providers by default;
- the app binds to `127.0.0.1` unless the operator makes an unsupported override.

## UI/UX audit and remediation gate

UI/UX work starts after private application acceptance so the audit observes complete, truthful workflows rather than placeholders.

### Product context

Create `PRODUCT.md` with the approved audience, teacher and student goals, tone, privacy constraints, and product vocabulary. Document the incumbent visual system before deciding whether to refine or replace it.

### UX critique

Review the complete teacher and student journeys using independent design and implementation assessments. Score Nielsen's usability heuristics, cognitive load, error recovery, user control, terminology, product specificity, and the emotional effect of high-stakes actions such as generation, photo sharing, and deletion.

The critique covers:

- first local start and provider readiness;
- classroom creation and editing;
- material upload, extraction state, and selection;
- student creation, profile editing, and avatar generation;
- story prompt, option selection, generation progress, review, regeneration, and export;
- student profile, classroom selection, and story reading;
- settings, failures, empty states, confirmations, and deletion.

### Technical UI audit

Measure and verify:

- WCAG AA contrast and semantics;
- keyboard-only completion of each primary workflow;
- screen-reader names, roles, states, and error announcements;
- reduced-motion behavior that preserves useful feedback;
- 44 by 44 pixel touch targets;
- layouts at desktop and representative mobile widths;
- text zoom, long content, empty data, slow loading, and failed requests;
- image loading and route bundle cost;
- design-token use, theming consistency, and implementation drift.

### Remediation and visual-system freeze

Fix all blocking and major findings before demo work. Fix minor issues that affect a repeated component or primary workflow. Run one desktop/mobile inspection batch, apply one grouped fix pass, and run one confirmation batch.

After the fixes, document the shared visual tokens, components, interaction patterns, status language, and responsive rules. The fictional demo must import and reuse these components. It must not maintain a parallel visual implementation.

## Public fictional demo boundary

The demo is a later deployment profile built from the audited application shell.

It contains bundled fictional classrooms, students, portraits, materials, avatars, stories, and panels. It may keep changes in browser session state. A persistent banner states that the data is fictional, actions reset, no provider call occurs, and no server persistence is claimed.

The demo does not register paid-generation, arbitrary-upload, or destructive persistence endpoints. Teacher and student role paths reuse the private application's components and state vocabulary. PDF export from bundled panels remains a real client operation.

## Hosted migration path

The future hosted version replaces infrastructure, not product workflows:

- point SQLAlchemy at PostgreSQL and add hosted migration verification;
- replace local storage functions with private object storage;
- add real teacher/student authentication and account recovery;
- enforce ownership and membership in the API and database;
- add RLS if Supabase exposes the database API;
- replace local in-process jobs with durable workers;
- add tenant controls, quotas, monitoring, retention, and incident procedures;
- bind the API through a production proxy instead of localhost.

Supabase is one valid hosted implementation. It is not a requirement of the product contract.

## Verification strategy

### Offline automated checks

- SQLAlchemy repository tests use a temporary SQLite database.
- Migration tests upgrade a blank database to head and verify constraints.
- Storage tests use a temporary directory and assert traversal rejection, staging cleanup, atomic replacement, and deletion.
- Provider tests replace OpenAI and BFL at their HTTP/SDK boundaries.
- API tests cover validation, local-mode capability gates, failure references, and exact response state.
- Frontend tests cover each primary teacher and student workflow plus error states.
- Demo tests fail if an outbound OpenAI, BFL, Supabase, or mutation request occurs.

### Browser checks

Run complete teacher and student paths at desktop and mobile sizes. Include keyboard navigation, reduced motion, slow/failing requests, generation failure, deletion confirmation, local restart persistence, PDF export, and demo simulation labels.

### Optional live checks

Live provider checks use fictional prompts, synthetic portraits, and bundled PDFs. They require an explicit command and cost acknowledgement. They never run in ordinary CI.

## Documentation requirements

The repository must include:

- one local quick start with no Supabase steps;
- exact required and optional environment variables;
- local data location, backup, reset, and deletion instructions;
- provider cost and data-sharing warnings;
- private mode's localhost-only security boundary;
- public demo simulation and data disclosures;
- the separate future hosted architecture;
- commands that exist and have been verified from a clean checkout.

## Implementation plan decomposition

This specification covers several dependent subsystems. It must not become one oversized implementation plan. After the founder reviews this file, write and execute separate plans in this order:

1. recovery branch and provider-output contract preservation;
2. SQLAlchemy, Alembic, SQLite, and local file storage;
3. local-mode API and frontend persistence conversion;
4. atomic story generation and local asset lifecycle;
5. classroom, student, deletion, and settings workflows;
6. PDF extraction and story grounding;
7. photo-guided avatar creation and regeneration;
8. provider modernization and fictional evaluation;
9. selective panel regeneration and private-app acceptance;
10. UI/UX audit and remediation;
11. public fictional demo;
12. documentation and release verification.

Hosted PostgreSQL, authentication, object storage, and school operations require a later specification and plan.

## Design approval record

The founder approved the following sequence on 2026-08-01:

1. complete the local/private/BYOK application;
2. run and remediate the UI/UX critique and technical audit;
3. freeze the shared visual and interaction system;
4. derive the public fictional demo;
5. pursue hosted database, object storage, and multi-user authentication later.
