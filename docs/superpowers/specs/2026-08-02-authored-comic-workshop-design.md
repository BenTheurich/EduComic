# EduComic Authored Comic Workshop Design Specification

**Date:** 2026-08-02

**Status:** Founder-selected direction; written specification awaiting final review

**Scope:** UI/UX remediation for the complete local/private/BYOK application, before the fictional public demo

## Goal

Refine the recognizable hackathon interface into an intentional **Authored Comic Workshop** without replacing its routes, role structure, core palette, or working interaction patterns. Fix the functional and content contracts that the interface depends on, then make real comic imagery—not generic SaaS decoration—the product's visual authority.

The private application remains the source product. The later fictional demo imports its finished components, tokens, status language, and responsive behavior.

## Sources of truth

- `PRODUCT.md` defines users, product language, operating modes, and truthful behavior.
- `DESIGN.md` defines the visual world, tokens, component character, and design guardrails.
- `.impeccable/design.json` provides Impeccable-compatible token metadata and representative components.
- `docs/PRODUCT_INTENT_RECONCILIATION_AUDIT.md` defines which cleanup decisions remain valid and which capabilities return.
- This specification defines the approved UI/UX remediation scope and acceptance behavior.

If implementation details conflict with these documents, product truth and truthful state take priority over decoration.

## Approved direction

The founder selected **Option 1: Authored Comic Workshop**.

This is a refinement:

- preserve existing information architecture, routes, role workflows, recognizable palette family, and accessible shared controls;
- preserve valuable cleanup work around truthful state, validation, error handling, responsive behavior, keyboard use, and reduced motion;
- unify the product name as EduComic;
- use existing Lora, Inter, and Space Mono roles deliberately rather than importing another typography system;
- reduce generic template signals such as identical feature cards, gratuitous gradients, hover-scale cards, unlabeled floating actions, and excessive rounded containers;
- use local comic previews, avatars, and completed panels as the dominant visual evidence.

## Non-goals

- No route rewrite, design-framework replacement, wholesale component-library rewrite, or separate student theme.
- No public-demo implementation during this phase.
- No hosted authentication, Supabase restoration, school administration, or production deployment work.
- No caller-controlled URL fetching, browser-held provider keys, or persistence of expiring provider delivery URLs.
- No speculative animation system, elaborate onboarding, or parallel design system.

## Foundational functional fixes

These are prerequisites for trustworthy visual remediation because the affected screens cannot be designed honestly around missing or misleading data.

### 1. Reliable BFL job handling

- Continue submitting to an approved BFL endpoint and polling only the provider-owned URL returned by that submission.
- Replace the fixed short abandonment window with bounded, observable handling appropriate to real provider latency.
- Distinguish pending, provider failure, timeout, download failure, validation failure, and local-finalization failure without exposing provider secrets or raw sensitive output.
- Preserve existing atomic story publication and cleanup guarantees.
- Do not repeat paid jobs automatically without an explicit bounded policy.

### 2. Three server-owned story-idea previews

Exactly three OpenAI story ideas remain the contract. After their structured text is stored, the backend owns preview generation for each idea:

1. Build the BFL request from the stored idea title, complete summary, classroom style, and other server-owned context.
2. Submit the three independent preview jobs with bounded concurrency so one slow job does not force serial latency.
3. Poll the returned provider URLs; never accept a polling or image URL from the browser.
4. Download, validate, and save each successful image beneath the local application data directory.
5. Expose only same-origin local media URLs to the frontend.

Text ideas become usable as soon as OpenAI succeeds. Each preview has a truthful pending, ready, or failed state. A failed preview does not erase valid text ideas or block selection; it exposes a bounded retry that regenerates only that preview. Successful acceptance verifies all three previews and their local persistence.

Preview media belongs to the chapter and is deleted with that chapter or a full local reset. The first implementation may retain all three previews while the chapter exists; no extra retention subsystem is needed.

The preview workflow reuses the configured BFL model and existing image-validation/storage boundaries unless a later fictional evaluation approves a dedicated preview model.

### 3. Canonical selected-idea presentation

Once an idea is selected, its content becomes the canonical story presentation:

- selected idea title → story title;
- selected idea summary → story description;
- selected idea preview → story-card thumbnail.

The API should expose these as stable derived story fields so teacher and student clients do not independently rediscover them from raw idea arrays.

Every teacher or student surface that presents a story description—including lists, cards, detail/review metadata, reader context, and accessible descriptive text—uses the canonical selected-idea summary. It may shorten layout around the description responsively, but it does not replace the content with the lesson prompt.

The teacher's original lesson prompt remains available as labelled secondary provenance, such as **Lesson prompt**, on appropriate teacher detail/review surfaces. It is not a fallback story description and is not promoted on student story cards.

Existing chapters derive the canonical fields from their stored selected idea where possible. If no selected summary exists, the UI shows an honest absence rather than substituting the lesson prompt.

### 4. Complete idea comparison

- Show each idea's full summary; remove line clamping and fixed-height summary boxes.
- Allow choice cards to grow naturally while keeping image treatment and selection actions aligned.
- Make the entire choice semantically clear without relying on a pointer-only card click.
- Preserve visible preview loading/failure states and keyboard selection.

### 5. Progressive comic previews during generation

Keep the current generation-loading composition. As each panel image becomes a validated local temporary artifact, expose it through a read-only preview contract and reveal it in the existing panel grid.

- Temporary previews do not make a chapter readable or `ready`.
- Final story publication remains atomic.
- Failure removes the current attempt's temporary previews and retains any prior completed revision.
- Status copy identifies the current stage and whether the user may safely leave the page.
- Reduced-motion mode replaces animation with useful static progress and status text.

## Visual system

### Brand and hierarchy

- Use **EduComic** everywhere; remove StoryClass naming.
- Use Lora for rare narrative and story-defining headlines, Inter for operational UI, and Space Mono sparingly for status/codes/metadata.
- Keep the existing blue-and-paper palette. Convert the incumbent yellow glow into the restrained Story Spark accent documented in `DESIGN.md`.
- Let preview images and finished panels establish personality before adding decorative elements.

### Surfaces and components

- Prefer flat paper surfaces, borders, and spacing over universal card shadows.
- Remove hover scaling from story and classroom cards.
- Reserve pills for statuses and compact filters.
- Give navigation a visible active state and accessible names.
- Replace the unlabeled floating create-classroom action with an accessible, contextually understandable action without moving the workflow unnecessarily.
- Reuse existing Radix/shadcn primitives where they already solve behavior and accessibility.

### Landing and dashboards

- Keep the existing role entry and dashboard structure.
- Replace generic feature-card emphasis with a real fictional comic preview and concise explanation of the teacher-to-story workflow.
- Correct pluralization, subject-color normalization, grade labels, and other visible content seams.
- Avoid invented claims, testimonials, schools, metrics, or curriculum guarantees.

#### Landing proof panel: The Condensation Jar

The landing artwork should demonstrate a real teaching beat rather than merely showing students taking a measurement. Use one uncluttered comic panel with exactly three fictional classmates behind a classroom lab table. Maya stands at the center and points directly to visible water droplets forming beneath a cold tray holding several ice cubes above a wide transparent jar with a shallow layer of warm water. The other students watch the same phenomenon.

Keep the generated dialogue short and exact: **“COOLING MAKES DROPLETS!”** Pair the artwork with an HTML caption that supplies the precise lesson: **“Water vapor cools and condenses into droplets—the same process that helps form clouds and rain.”** The image should contain no rain gauge, umbrella, sign, test tube, secondary experiment, loose water outside the jar, extra characters, labels, or additional text. Preserve Maya's established avatar appearance and the existing BFL comic style.

### Teacher story workflow

- Make the lesson input, optional material grounding, three complete story choices, preview generation, selection, comic generation, review, correction, and export feel like one authored production sequence.
- Show grounded materials and teacher prompt as provenance, not as the public story description.
- On completion, offer a direct **Read story** action rather than redirecting before the teacher can inspect the result.

### Student experience and reader

- Keep student surfaces recognizably part of EduComic while allowing the artwork more space and reducing operational chrome.
- Default narrow readers to fit-to-width and prevent desktop scale preferences from shrinking mobile panels.
- Provide meaningful panel text alternatives through transcript, narration, or a read-text mode. `Panel N` alone is insufficient.
- Maintain keyboard, touch, text-zoom, and reduced-motion support.

## Status and error language

Status language must reflect durable backend truth:

- distinguish generating text ideas from generating their three previews;
- identify per-preview pending, ready, failed, and retry states;
- distinguish temporary panel previews from a completed story;
- state when prior story/avatar media is preserved after failure;
- explain when an action may take longer or spend additional credits;
- never claim persistence, provider completion, authentication, or deletion before it is true.

Public-demo versions later reuse the same components but label fixture transitions as simulated and make no provider call.

## Responsive and accessibility requirements

- Primary actions and unfamiliar icon controls meet a 44-by-44-pixel target and have accessible names.
- Pages expose appropriate `main`, `nav`, `header`, heading, tab, dialog, and status semantics.
- All primary teacher and student workflows complete by keyboard.
- Story choices, loading media, retry controls, destructive confirmations, and validation errors announce meaningful state.
- Representative desktop and narrow layouts have no horizontal overflow.
- Comic text remains readable on narrow screens and at text zoom.
- Reduced motion preserves useful progress without near-zero animations being the only feedback.
- Color is never the only carrier of state.

## Performance boundaries

- Preview and story-card images load lazily outside the initial viewport.
- Do not block the entire page on decorative media.
- Avoid adding a frontend dependency for behavior already covered by the platform or installed component primitives.
- Keep provider work on the backend and avoid duplicate preview requests across rerenders or page refreshes.

## Dependency-ordered implementation phases

### A. Story media and metadata contract

Stabilize BFL job handling, local preview storage, per-idea preview state, canonical title/description/thumbnail fields, cleanup ownership, and temporary panel-preview reads. Verify the complete contract with fictional mocks before changing visual presentation.

### B. Shared visual and semantic foundations

Align tokens and component patterns with `DESIGN.md`; unify EduComic naming; fix landmarks, accessible names, reduced-motion feedback, repeated copy/metadata defects, navigation state, and mobile reader defaults.

### C. Teacher production workflow

Apply the authored-workshop hierarchy to lesson input, materials, full idea choices, progressive preview states, comic generation, completion, review, correction, and export.

### D. Student and reader refinement

Apply canonical story metadata and thumbnails across student lists and dashboards, reduce reader chrome, add readable mobile defaults and story text alternatives, and preserve existing role workflows.

### E. Landing/dashboard refinement and system freeze

Bring real fictional comic evidence into the landing/dashboard, remove remaining template signals, complete one desktop/mobile inspection batch, apply at most one grouped fix round, and freeze the shared system for the public demo.

## Verification

Focused automated checks cover:

- three idea previews generated from server-owned inputs and returned only as local media URLs;
- no browser request body accepts thumbnail or polling URLs and no selection handler fetches a caller URL;
- preview failure/retry does not regenerate or erase valid text ideas;
- preview files survive restart and are removed with their chapter/reset;
- selected title, full summary, and preview appear consistently across teacher and student story cards;
- lesson prompt is secondary teacher provenance and never substitutes for story description;
- progressive panel previews appear during generation while final readiness remains atomic;
- mobile reader sizing, transcript/text alternative, semantics, reduced motion, keyboard use, and representative loading/error states.

Run focused checks during implementation. Run the complete backend/frontend/static/build suite once at the end of the phase. Browser verification covers representative teacher and student workflows at desktop and narrow widths, followed by at most one scoped fix/re-review round under the approved cadence.

No live paid provider call is required for normal verification. An opt-in bounded fictional smoke check may be run only with explicit founder authorization.

## Acceptance gate

- All blocking findings from the UI/UX audit are fixed or presented as an actual founder blocker.
- All three idea cards can show durable local BFL previews, complete summaries, and accessible selection states.
- Every story card uses the selected idea's title, summary, and preview image.
- Progressive generation reveals truthful temporary images without weakening atomic final publication.
- Teacher and student primary workflows pass keyboard and representative mobile verification.
- The interface remains recognizably EduComic and does not introduce a parallel demo theme.
- `PRODUCT.md`, `DESIGN.md`, and `.impeccable/design.json` match the implemented shared system before the fictional demo begins.

## Approval record

On 2026-08-02 the founder selected **Authored Comic Workshop** and explicitly requested:

1. restoration of three server-owned, locally stored BFL idea-preview images without caller-controlled URL fetching;
2. full unclamped idea descriptions;
3. selected idea summary as the canonical story description, with the lesson prompt secondary;
4. selected idea preview as the story-card thumbnail;
5. progressive display of generated panel images during the existing loading experience.
