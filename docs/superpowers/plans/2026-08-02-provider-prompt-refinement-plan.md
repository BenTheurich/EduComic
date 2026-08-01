# Provider and Prompt Refinement Implementation Plan

> Implement the approved provider refinement as one focused phase. Choose code-level details after tracing the current callers; keep the diff narrow and test-first.

**Design source:** `docs/superpowers/specs/2026-08-01-provider-prompt-refinement-design.md`

## Task 1: Refine scoring, settings, references, and prompts

### Outcome

The local/private application can explicitly enable trustworthy paid panel review, understands its time-and-credit implications, and uses lean current-model prompts for every active OpenAI call.

### Work

- Repair panel evaluation so exact visible text, unexpected lettering, bubble ownership, reference identity/continuity, requested action, and layout are judged separately. Derive retry eligibility from the validated review contract rather than trusting an unconstrained overall score.
- Keep review off by default. Reuse the existing settings persistence and UI controls; make the enablement and attempt cap understandable, including that every attempt can add one OpenAI review and another BFL image generation, increasing latency and spend.
- Pass coherent, explicitly ordered previous-panel and featured-avatar references through generation and evaluation. Preserve sequential continuity and local-media validation.
- Refine the story-idea, full-script, and panel-review OpenAI prompts using current GPT-5.6 guidance: lean instructions stated once, clear outcome and success criteria, grade-specific language, selected-material grounding, strict existing structured outputs, and no duplicated hand-written JSON schema.
- Keep Terra and Pro as defaults. Offer Flex only as the approved optional higher-cost BFL choice; do not add Max.
- Update public setup/settings documentation only where needed to explain the paid optional behavior.

### Boundaries

- No live provider calls, Supabase calls, deployments, or real student data.
- No automatic review or paid retry in ordinary tests, the public demo, or default settings.
- Preserve durable generation state, sanitized provider errors, file validation, previous successful panels, manual correction, and the attempt cap of three.
- Do not migrate API surfaces or add optional GPT-5.6 features without measured need.

### Acceptance gate

- Focused tests fail before the implementation and cover scorer caps, invented text, bubble attribution, coherent reference ordering, settings persistence, UI warnings, and every active OpenAI prompt boundary.
- Enabling review affects only new generation snapshots; disabling it produces one BFL attempt and no OpenAI review.
- The user-visible warning clearly explains additional time and credits before enablement.
- Backend, frontend, static checks, and builds pass; the settings workflow is browser-verified without live providers.
