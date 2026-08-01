# Provider and Prompt Refinement Design

**Status:** Founder-approved direction, updated with the 2026-08-01 fictional model bake-off for final review.

## Goal

Improve story and comic quality after the private/local application works end to end. Preserve continuity, exact educational text, predictable BYOK cost, and truthful failure states. This is a focused refinement pass, not a new generation architecture.

## Provider decisions

- Keep `gpt-5.6-terra` as the default OpenAI narrative model. Retain the existing supported OpenAI choices for users who prefer lower cost or higher quality.
- Keep pinned `flux-2-pro` as the default BFL panel model. It remains the best continuity/cost balance in the current evidence.
- Permit `flux-2-flex` as an opt-in, clearly higher-cost typography alternative in the full local application. Do not make it the default from this single fixture.
- Do not expose `flux-2-max` as a normal choice yet. It cost more than Pro and did not improve text reliability in this evaluation.
- Keep automatic image review and paid retry loops off by default.

## Fictional BFL evaluation

The approved comparison generated the same fictional continuity-sensitive panel four times with matched seeds for Pro, Flex, and Max. Every request used the same 960x640 output, previous-panel reference, synthetic avatar reference, exact text, and disabled prompt upsampling. Each image was graded by the existing Terra panel rubric and inspected manually.

| Model | Mean automated score | Mean text dimension | BFL cost for four | Observed result |
|---|---:|---:|---:|---|
| FLUX.2 Pro | 8.00 | 8.25 | about $0.24 | Best reference/character stability; one narration misspelling and one bubble-attribution failure. |
| FLUX.2 Flex | 7.88 | 8.25 | $0.60 | Strongest literal typography signal, but one extra background word and more identity drift; 2.5x Pro's cost. |
| FLUX.2 Max | 7.13 | 6.25 | $0.52 | Attractive peak output, but one narration misspelling, one bubble-attribution failure, and repeated avatar traits across characters. |

The returned BFL costs totaled about $1.36. Eleven submissions recorded $1.30; the first identical Pro request completed before its returned cost was persisted, so its approximately $0.06 cost is included in the total. Twelve Terra reviews were also run; the temporary scorer did not persist their billing amount.

This fixture exposed one evaluation limitation: its previously generated panel and standalone avatar gave conflicting signals about which visual character represented Ada. The text, layout, latency, and cost comparisons remain useful, but identity conclusions are directional. Future checked-in fixtures must use coherent, explicitly role-labeled references.

## Prompt design

OpenAI prompts should be concise, grade-specific, and grounded only in selected fictional or teacher-provided material. Structured output contracts continue to enforce idea and panel counts, short dialogue, known speakers, and required fields; prompts should not duplicate the entire schema when the SDK already enforces it.

BFL panel prompts should follow this order:

1. subject and featured characters;
2. action and speaker ownership;
3. visual style;
4. setting and story context;
5. explicit role of each ordered reference image;
6. exact narration and bubble layout.

Use positive descriptions, exact quoted text, and explicit placement/tail instructions. Disable prompt upsampling for exact-text panels. Pass the previous successful panel first and only the featured students' current avatars afterward. Keep generation sequential so each successful panel becomes the next continuity reference. Do not add parallel panel generation until evidence shows a continuity-preserving grouping strategy.

## Evaluation design

The current strict reviewer remains useful, but its `text_accuracy` dimension mixes literal transcription with speaker attribution. The bake-off produced both a false high score for a visible misspelling and low text scores for correctly spelled words attached to the wrong subject.

Prompt/model evaluation should therefore report separate dimensions for:

- exact visible text, including invented background lettering;
- speech-bubble ownership and tail placement;
- reference identity and cross-panel continuity;
- requested action and educational scene accuracy;
- layout and child readability;
- latency and reported provider cost.

A failed exact-text or bubble-ownership check may cap the evaluation score, but evaluation findings must not automatically trigger paid retries. Use a small checked-in fictional fixture corpus plus cached outputs for repeatable human comparison.

## Acceptance gate

- Terra and Pro remain stable defaults, with Flex clearly labeled as optional and higher cost.
- Featured avatar references reach BFL in an explicit, deterministic order after the previous panel.
- Prompt tests prove grade context, material grounding, exact text placement, and reference-role wording.
- Fictional provider evaluation records model, prompt version, seed, latency, provider-reported cost, automated dimensions, and human verdict.
- No normal test, public demo action, or application retry loop calls a paid provider.
- Existing structured validation, durable media handling, truthful generation state, and manual panel correction behavior remain intact.

## Deferred

- Parallel panel generation.
- Automatic paid review/regeneration loops.
- Max as a user-selectable model.
- A larger statistical benchmark; add it only if the first diverse fictional fixture set leaves Pro and Flex materially tied.
