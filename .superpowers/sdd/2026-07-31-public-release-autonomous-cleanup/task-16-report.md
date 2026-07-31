# Task 16 report

Kept the active chapter workflow and removed the parallel story-start surface.

## Implementation

- Preserved the frontend's only active chain: `POST /classrooms/{id}/chapters/start`, `POST /chapters/{id}/choose-idea`, `POST /chapters/commit`, then `GET /chapters/{id}` for status/read polling.
- Deleted the success-returning `/story/create/{classroom_id}` no-op and stale `/story/generate-options` and `/chapters/ideas` routes. No compatibility aliases were added.
- Deleted the unused frontend `generateOptions` client and zero-caller legacy `Story`, `StoryWithPanels`, and `StoryPreview` types.
- Deleted the stale `story_idea.start_chapter` path and CLI, its sole-use `create_chapter` database helper, the exact duplicate relationship-helper block, empty `services/chapter.py`, and the zero-caller `get_panel`, `delete_classroom`, `delete_student`, `delete_panel`, and `get_classroom_full_story` helpers. The caller inventory proved each deletion was unreachable after removing the stale route.
- Kept Task 12's strict `StoryChoiceRequest` boundary unchanged; caller-supplied thumbnail fields remain rejected.

## TDD evidence

- RED: the new active-route suite had one passing start/choose/commit/read flow and three expected failures because the stale routes returned 200/500/500 instead of being absent.
- GREEN: `tests/test_active_routes.py` passed all 4 cases after the route deletions.

## Verification

- Backend focused route suite: 4 passed.
- Backend full suite: 36 passed.
- Ruff on touched Python files and the new test: passed.
- Frontend full suite: 9 files / 26 tests passed.
- Frontend typecheck, touched-file ESLint, and production build with `VITE_API_URL=https://api.example.invalid`: passed. The existing Browserslist-data and large-chunk warnings remain.
- Full frontend ESLint still reports the repository's existing 8 errors and 8 warnings in untouched files; Task 17 owns dead-code/lint cleanup.
- Expected-zero active-source scans found no removed route strings, old client call, stale start helper, deleted database helper, or legacy story type. Each relationship helper has exactly one definition.
- Staged Gitleaks scan: no leaks found; Git emitted only the environment's existing inaccessible global-ignore warning.
- `git diff --check`: passed with only the existing LF-to-CRLF checkout warnings.

No live provider, database, deployment, or external application endpoint was contacted.

## Review fix round 1

- Replaced the permissive stale-route POST assertions with an exact FastAPI route-registry assertion. Reintroducing any stale path under any HTTP method now fails the regression.
- Mutation RED: temporarily registered `GET /chapters/ideas`; the focused suite failed 1 of 2 tests at the new route-registry assertion.
- GREEN: removed the temporary mutation; the focused route suite passed 2 tests, the full backend passed 34 tests, and Ruff passed on the changed test.
- No backend or frontend application source changed, so the prior frontend suite, typecheck, touched-file ESLint, and production-build evidence remains applicable.
- The staged Gitleaks scan and cached diff check passed; Git emitted only the existing inaccessible global-ignore warning.
- Internal SDD reports are deliberately retained for ongoing coordination and will be removed together during Task 21 final-candidate cleanup; deleting only this report now would leave the coordination ledger incomplete.
