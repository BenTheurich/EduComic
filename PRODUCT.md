# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Teachers running EduComic locally or privately with their own OpenAI and Black Forest Labs keys. They create classrooms, add materials and students, choose story ideas, generate comics, review results, and export them.
- Students represented through a local profile-selection flow. They create or edit a profile and avatar, join fictional or teacher-created classrooms, and read completed stories.
- Repository evaluators who need a clean, zero-hosted-database setup and a separate fictional public demonstration.

## Product Purpose

EduComic turns lesson material and a fictionalized classroom cast into personalized educational comics. The primary product is the complete local/private/BYOK application; the public demo is derived later from the same workflows and visual system using bundled fictional data and explicit simulation.

Success means a teacher can start from a clean checkout, add provider keys, complete the teacher and student workflows, generate and review a comic, and export it without provisioning Supabase or another hosted service.

## Positioning

EduComic combines teacher-selected lesson grounding, student-character personalization, and a reviewable comic-generation workflow. The lesson, selected story idea, cast, avatar references, images, and export remain one traceable product flow rather than disconnected AI-generation utilities.

## Operating Context

- The first release runs on one machine, binds to localhost, and stores application data in SQLite plus local files.
- The application has teacher and student experiences, but local profile switching is not authentication.
- OpenAI provides structured story ideas, scripts, and optional panel review. Black Forest Labs provides avatar, idea-preview, and comic-panel images.
- The later public demo accepts no arbitrary personal files, makes no paid provider calls, and never claims durable persistence when behavior is simulated.

## Capabilities and Constraints

- Preserve complete teacher and student workflows, including classroom editing, materials grounding, avatar creation/editing, deletion, settings, story generation, panel correction, reading, and PDF export.
- Exactly three story ideas are generated. Each has a title, complete summary, theme, and server-owned local preview image when preview generation succeeds.
- Once selected, the idea title, summary, and preview image become the story's canonical title, description, and thumbnail. The teacher's lesson prompt remains secondary provenance, not public-facing story copy.
- Every teacher and student surface that presents story description content reads the canonical selected-idea summary rather than independently falling back to the lesson prompt.
- Paid generation is available only in local/private/BYOK mode. Provider output and delivery URLs are untrusted and must be copied into durable local media before use.
- Caller-controlled URLs are never fetched by the backend.
- Generated-looking public-demo actions are visibly labeled as fictional or simulated.
- Hosted database, school authentication, authorization, and multi-user operations are future work, not hidden requirements of the local release.

## Brand Commitments

- The product name is **EduComic**. Do not introduce alternate product names such as StoryClass.
- Preserve the recognizable hackathon product and teammate contributions. Refinement is preferred over wholesale rebranding or information-architecture replacement.
- Use direct, teacher-friendly language and honest status copy. Avoid generic AI hype, fake success, invented persistence, or unsupported curriculum claims.
- Let actual comic art demonstrate the product. Avoid decorative stock imagery or generic SaaS illustration as a substitute.

## Evidence on Hand

- The repository contains runnable teacher and student workflows, local persistence, provider integrations, fictional fixtures, and automated browser/unit coverage.
- Existing generated evaluation images may be used for private verification only unless their public asset provenance is explicitly documented.
- No testimonials, school customers, outcome metrics, press claims, or public-demo asset licenses are established; future UI and documentation must not fabricate them.

## Product Principles

1. Preserve the complete private application; derive the public demo afterward.
2. Unsafe to expose publicly means gate or simulate it, not delete product intent.
3. Every state is truthful about provider work, persistence, failure, and cost.
4. Lesson grounding and student personalization must visibly influence the resulting story.
5. Prefer a zero-setup local path and a straightforward future migration to hosted PostgreSQL and private object storage.

## Accessibility & Inclusion

Primary workflows must be keyboard-completable, work at representative mobile widths and text zoom, preserve useful reduced-motion status feedback, and meet WCAG AA semantics and contrast. Image-based comics require meaningful text alternatives or a transcript/read-text mode; `Panel N` alone is not sufficient.
