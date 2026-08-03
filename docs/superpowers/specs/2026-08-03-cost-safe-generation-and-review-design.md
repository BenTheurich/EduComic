# Cost-Safe Generation, Review, and Grounding

**Status:** Founder-approved design direction.

## Goal

Make paid story creation recoverable and reviewable without weakening lesson grounding. A teacher must never lose completed paid panels because a later panel is moderated or interrupted, and a generated panel correction must remain a candidate until the teacher explicitly accepts it.

The work is split into three implementation plans because generation durability, panel-correction review, and PDF grounding are independently testable subsystems. They ship in that order so the correction workflow can reuse the durable provider-job and candidate-media behavior established for full-story generation.

## Verified Baseline

- Full story generation validates and stores the complete OpenAI script before BFL panel work begins, but any later exception currently deletes every temporary panel image.
- BFL moderation is persisted as `bfl_request_moderated` or `bfl_content_moderated`, including the blocked panel number. No automatic moderation retry occurs.
- One-panel correction is wired from `StoryViewer` through the API and background worker. It preserves the readable story on failure and atomically replaces only the selected panel on success.
- Correction currently publishes the replacement immediately. It has no candidate approval or undo state.
- Checked, ready PDFs are real provider inputs. Bounded excerpts are sent to both OpenAI story-idea and full-script generation; BFL receives their effect through the validated script and panel prompts rather than raw PDF text.
- PDF grounding currently snapshots only the first non-empty page from each selected PDF. Scanned PDFs are rejected because OCR is not included.

## Global Product Rules

- Paid work is never retried automatically.
- A transport failure with an already-submitted BFL job resumes polling that job instead of submitting another request.
- A terminal moderation result requires an explicit teacher action before another paid request.
- Existing ready stories and panels remain readable until a complete replacement is accepted.
- Provider delivery URLs are temporary transport data; accepted and checkpointed images use managed local storage.
- Provider-reported cost is stored and labelled as provider-reported rather than presented as an independently calculated bill.
- Default automatic panel review remains off. This design does not add parallel generation, automatic correction loops, OCR, embeddings, or a version-history browser.

## 1. Resumable Full-Story Generation

### Durable run state

Extend the existing `GenerationRun` record rather than introducing a second job system. A story run persists:

- the validated `script_snapshot` already stored today;
- ordered completed-panel checkpoints containing panel number and managed local image path;
- the current BFL job identifier, polling URL, panel number, and provider-reported cost immediately after submission;
- the accumulated provider-reported BFL cost for the run.

`artifact_paths` remains cleanup bookkeeping. Completed checkpoints are intentional durable work and therefore do not make local readiness fail or get deleted during normal startup cleanup.

### Worker behavior

The worker loads an existing validated script snapshot when present instead of making another OpenAI script request. It validates every saved checkpoint against the expected sequence and local file before resuming from the first missing panel.

For the current panel:

1. If an unfinished BFL job is persisted, poll that same job.
2. Otherwise submit exactly one new request and persist its job metadata before polling.
3. Download and validate the returned PNG.
4. Move it into managed local storage and append the completed checkpoint transactionally.
5. Clear the active provider-job snapshot only after the checkpoint is durable.

The chapter becomes `ready` only after all expected panel checkpoints form the exact 12- or 20-panel sequence and the existing atomic revision publication succeeds.

### Failure and recovery

A failed or interrupted run retains its script, completed checkpoints, and active provider job. The chapter response exposes whether the run is resumable, the failed/current panel, completed count, expected count, error category, and accumulated reported BFL cost.

The generation screen replaces the current generic failure card with two deliberate actions:

- **Resume from panel N:** requeues the same run and preserves all completed work. For a terminal moderation result this explicitly authorizes one new BFL request for the blocked panel; it never starts itself.
- **Discard this attempt:** removes checkpoint media through the existing durable cleanup mechanism before returning to story choice.

Connection loss remains an unknown state until the persisted run is checked. The client never creates a second run merely because polling timed out.

## 2. Panel Correction as a Reviewable Candidate

### Selected interaction

Replace the inline form under each comic panel with one focused correction dialog. The original panel remains the visual anchor while the teacher writes one visual correction and sees the truthful cost note: generating a replacement makes one BFL image request, while automatic review remains off.

The interaction has four states:

1. **Editing:** original panel, correction field, and `Generate replacement`.
2. **Working:** original remains visible; status names the current stage and may be closed safely.
3. **Candidate ready:** original and candidate appear side by side on wide screens and stacked on narrow screens.
4. **Failure:** original remains active; moderation and unknown transport outcomes have distinct copy and actions.

When a candidate is ready, the only publication actions are:

- **Use replacement:** atomically advances the chapter revision and deletes the superseded original after publication.
- **Keep original:** discards the candidate through durable cleanup and leaves the chapter revision unchanged.

`Generate another` first requires confirmation that the current paid candidate will be discarded, then starts a new explicit paid request. Accepted originals are not retained as a version history; adding undo would require a separate retention policy and is intentionally deferred.

### Backend state

The existing panel `GenerationRun` gains an `awaiting_review` state. A successful BFL result is stored as managed candidate media and survives navigation or application restart, but `finalize_panel_regeneration` is not called until the accept endpoint succeeds.

The panel-regeneration status response includes the candidate URL only for its owning local run. Separate accept and reject endpoints are idempotent, validate the original chapter revision, and cannot publish a stale candidate. Starting another story generation or panel correction for the chapter remains blocked while a candidate awaits review.

Moderation uses the same exact persisted error codes as full-story generation. The UI preserves the teacher's correction text and never labels an unconfirmed request as failed.

## 3. More Representative PDF Grounding

### Keep the existing real pipeline

PDF storage, native-text extraction, immutable chapter source snapshots, prompt-delimiting, and selected-only behavior remain unchanged. Raw source text continues to be treated as untrusted facts rather than instructions.

### Improve excerpt selection without another provider call

Pass the teacher's lesson prompt into source snapshotting. For each selected PDF, score its extracted pages by deterministic overlap with normalized lesson-prompt terms and snapshot the highest-scoring page. Ties prefer the earlier page; a document with no matching terms falls back to its first non-empty page.

This deliberately selects one page per source so all ten allowed sources can remain represented inside the existing 16,000-character grounding budget. It adds no embedding service, summarization call, or new dependency.

### Make grounding visible

The story-option screen continues to show selected source labels. The completed teacher story view additionally shows compact provenance containing each source label and snapshotted page number. It does not expose full source excerpts by default.

The product must describe this precisely as selected PDF excerpts grounding the story. It must not claim whole-document comprehension, OCR, or curriculum verification.

## API and State Boundaries

- Full-story resume and discard operate on the existing generation-run identity, not a newly generated chapter or idempotency key.
- Correction generate, status, accept, and reject operations all remain scoped to the panel run and expected chapter revision.
- Material selection remains part of chapter start; source snapshots stay immutable even if the uploaded material is later deleted.
- Deleting a chapter, classroom, student, or all local data includes checkpoint and candidate media in the existing deletion-manifest process.
- Local readiness distinguishes intentional resumable/candidate media from failed cleanup residue.

## Error and Cost Behavior

- `Request Moderated` and `Content Moderated` remain distinct persisted BFL outcomes.
- Submit, poll, download, validation, finalization, publication, and cleanup failures remain separate internal error categories with safe references.
- A persisted polling URL is resumed after network or process interruption. No replacement BFL job is submitted while that job may still complete.
- The UI reports completed panels and provider-reported BFL cost when the provider supplied it. Missing cost data is shown as unavailable, never inferred.
- Tests, public-demo behavior, and browser verification use mocks or bundled fictional media. A paid canary happens only after all fault-injection tests pass and requires a separate explicit decision.

## Verification

Generation durability tests prove:

- failure after panel N preserves panels 1 through N-1 and the script snapshot;
- restart resumes the persisted BFL polling job without another submit;
- moderation resume submits only the blocked panel after an explicit action;
- repeated resume clicks are idempotent;
- publication still requires the exact panel sequence;
- discard and deletion clean all checkpoint files safely.

Correction tests prove:

- a generated candidate does not change the readable chapter;
- candidate state survives reload;
- accept changes only the chosen panel and is idempotent;
- reject preserves the chapter and removes candidate media;
- stale accept/reject requests fail without publishing;
- moderation, unknown polling, and cleanup failures preserve the original.

Grounding tests prove:

- a fact on a later relevant PDF page enters both OpenAI prompts;
- unselected source text never enters either prompt;
- no-overlap documents use the first non-empty page;
- every selected source keeps a labelled, bounded excerpt;
- story provenance displays the exact snapshotted source and page.

Final verification runs the focused backend and frontend suites, the complete regression suites, TypeScript checks, the production build, and one bounded desktop/mobile browser pass. No paid provider call is part of completion.

## Explicitly Deferred

- Automatic paid retries or retry-on-moderation loops.
- Full panel version history or post-accept undo.
- OCR for scanned PDFs.
- Embedding-based retrieval, provider summarization, or whole-document claims.
- Parallel panel generation.
- Public hosting and fictional-demo deployment.
