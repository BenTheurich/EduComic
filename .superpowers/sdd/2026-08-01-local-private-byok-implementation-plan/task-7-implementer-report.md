# Phase 7 implementer report

## Status

DONE

## Scope and diff

- Centralized the fixed provider defaults in `provider_config.py`: OpenAI defaults to `gpt-5.6-terra`; BFL remains `flux-2-pro`.
- New settings accept Terra, Sol, and Luna. Historical `gpt-5.1` remains accepted only by the internal provider replay allowlist.
- Kept the existing OpenAI Chat Completions `chat.completions.parse` flow and Pydantic response contracts. No Responses migration or provider abstraction was added.
- Set avatar, active panel-generation, and legacy comic BFL submissions to `safety_tolerance: 2`; retained canonical `api.bfl.ai` submission, provider polling URLs, base64 local references, and immediate local durable media handling.
- Added migration `0007_provider_defaults`, which changes only local `settings.openai_model = 'gpt-5.1'` rows to `gpt-5.6-terra`; it does not update chapter or generation-run provenance snapshots.
- Added the three-model Settings selector with short Terra/Sol/Luna tradeoffs and updated the API type.
- Removed ignored model variables from `backend/.env.example`; downloaders only paste `OPENAI_API_KEY` and `BFL_API_KEY` for provider use.
- Updated the OpenAI dependency and lockfile from 2.8.1 to 2.52.0.

## RED evidence

- Backend focused RED: current Settings literals rejected `gpt-5.6-*`; story idea/script/review mocks sent `gpt-5.1`; avatar omitted safety tolerance; comic BFL used safety 4. Result: 6 expected assertion failures after correcting test setup.
- Frontend focused RED: `npm.cmd test -- --run src/pages/teacher/Settings.test.tsx` produced 1 failure because no current-model tradeoff selector existed.
- Active panel contract RED: `python -m pytest ... test_panel_bfl_contract_encodes_local_reference_and_returns_provider_poll_url` failed specifically because the body used safety tolerance 4 rather than 2.
- The first complete backend run exposed a migration-head readiness regression: 4 failures and 173 passes. Updating `MIGRATION_HEAD` to `0007_provider_defaults` made those four focused tests pass.

## GREEN evidence

- Focused provider/schema/migration contracts: 7 passed.
- Focused Settings UI: 3 passed.
- Focused readiness regression: 4 passed.
- Complete Phase 7 provider contract file after the active panel RED/GREEN cycle: 4 passed.

## Dependency and lock result

- Command: `uv lock --upgrade-package openai`
- Result: `Resolved 50 packages`; `Updated openai v2.8.1 -> v2.52.0`.
- Command: `uv sync --extra dev --locked` followed by importing `openai.__version__`.
- Result: environment synchronized and reported `2.52.0`.
- Lock evidence: `openai==2.52.0`; sdist SHA-256 `7c736d592f81471ce1f734838390983c4d8c8aecff23dcd36e600a58e5032d9c`; wheel SHA-256 `f97e231d9a8fa69ab55897df1080f02d99913fb0a30e3ee56ea16a1eb6c2d434`.

## Migration, defaults, and provenance

- Fresh teacher settings, fallback settings, reset settings, option snapshots, and new generation snapshots use `gpt-5.6-terra` and `flux-2-pro`.
- `0007_provider_defaults` migrates only the mutable local settings row from `gpt-5.1` to Terra.
- Historical generation snapshots remain `gpt-5.1`; the internal supported-model set retains it so durable replay/resume remains readable.
- Automatic panel review remains off by default.

## Mocked provider contracts

- OpenAI story ideas, full comic scripts, and panel reviews assert `model='gpt-5.6-terra'`, the exact Pydantic `response_format`, and existing completion-token bounds. Existing fictional grounding and redaction assertions remain in place.
- Avatar BFL mock asserts `https://api.bfl.ai/v1/flux-2-pro`, provider-returned polling URL use, base64 input image, and safety 2.
- Active panel BFL mock asserts the pinned endpoint, dimensions/output fields, provider-returned polling URL, locally read/base64-encoded reference bytes, and safety 2.
- Legacy comic BFL boundary still asserts canonical submit/poll/delivery URLs, local encoded references, and now safety 2.
- No live OpenAI, BFL, Supabase, deployment, or real-data operation was performed.

## Complete suite

- Backend: `.venv\\Scripts\\python.exe -m pytest -q --basetemp=..\\output\\pytest-phase7-final-rerun` -> **177 passed in 21.67s**.
- Backend static: `.venv\\Scripts\\python.exe -m compileall -q src tests` -> exit 0.
- Frontend typecheck: `npm.cmd run typecheck` -> exit 0.
- Frontend lint: `npm.cmd run lint` -> exit 0.
- Frontend tests: `npm.cmd test -- --run` -> **20 files, 60 tests passed**.
- Frontend production build: `VITE_API_URL=https://api.invalid npm.cmd run build` -> **2488 modules transformed, exit 0**.
- Existing non-failing warnings: React Router v7 future flags and stale Browserslist metadata.

## Browser result

- Verified `npx.cmd` before invoking the bundled Playwright CLI wrapper.
- Started the app against isolated fictional local data with no provider keys.
- Opened `/teacher/settings`, selected `gpt-5.6-sol`, clicked **Save settings**, observed **Settings saved.**, reloaded once, and confirmed **Sol — highest quality** remained selected.
- UI truthfully displayed both provider keys as not configured. No provider call was made.
- Browser and exact local test servers were closed after the check.

## Self-review

- No material findings after reviewing the final diff and running `git diff --check`.
- The change reuses existing settings, structured parse, durable snapshot, polling, local-storage, and error-handling paths.
- Deliberately skipped Responses API work, evaluation infrastructure, pricing/telemetry, automatic upgrades, deployment, Supabase, and live-key smoke testing per scope.

## Commit

Implementation and initial report: `d169914` (`feat: modernize local provider defaults`).

## Concerns

- The real fictional provider smoke test remains deliberately deferred until the founder supplies keys.
