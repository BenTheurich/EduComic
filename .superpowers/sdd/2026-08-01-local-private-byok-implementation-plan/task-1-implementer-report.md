# Task 1 implementer report

## Status

COMPLETE

Phase 1 now has a checked-in SQLite/Alembic data contract, concrete validated local storage, first-run initialization, and bounded FastAPI media delivery. The default dependency and environment paths do not require the Supabase package, variables, project, database, or Storage.

## Architecture and boundaries

- `backend/src/database/models.py` defines SQLAlchemy 2 models for local profiles, classrooms, students, enrollments, materials, chapter-material provenance, chapters/revisions, panels/recorded object paths, generation runs, and settings.
- `backend/alembic/versions/0001_local_foundation.py` is the authoritative initial migration. It creates foreign keys, cascades, uniqueness rules, status/revision/positive-sequence checks, indexes, and UTC `CURRENT_TIMESTAMP` defaults. There is deliberately no final or upper panel-count constraint while the founder decision remains pending.
- `backend/src/database/session.py` creates engines/sessions and enables SQLite foreign keys on every connection. `backend/src/database/migrations.py` applies checked-in migrations to head.
- `backend/src/local_runtime.py` resolves `EDUCOMIC_DATA_DIR`, defaults to ignored `backend/data/`, creates required directories, resolves the SQLite `DATABASE_URL`, and migrates at FastAPI lifespan startup.
- `backend/src/local_storage.py` is one concrete local implementation: UUID owner-scoped object names, nonempty/size-bounded staging, `os.replace` atomic finalization/replacement, bounded reads, idempotent deletion, abandoned-staging cleanup, traversal/absolute/unknown-class rejection, and known MIME handling. Staging objects cannot be read through the ready-object boundary.
- `GET /media/{object_path}` returns bounded bytes and application headers only; it does not expose a local filesystem path or directory listing.
- The legacy `database.database.supabase` name is an import-compatibility sentinel only. It imports no Supabase package and fails closed if a remaining direct query-builder path executes.

## Files and commits

Implementation commit:

- `3a73e25 feat: add local sqlite and file foundation`

Key added files:

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_local_foundation.py`
- `backend/src/database/models.py`
- `backend/src/database/session.py`
- `backend/src/database/migrations.py`
- `backend/src/local_runtime.py`
- `backend/src/local_storage.py`
- `backend/tests/test_local_database.py`
- `backend/tests/test_local_storage.py`
- `backend/tests/test_local_startup.py`

Environment/setup documentation was changed to the local private contract. `SUPABASE_SETUP.md` now contains future-hosted, deny-by-default boundaries only.

## RED / GREEN / refactor evidence

Baseline before implementation:

```text
uv --cache-dir C:\tmp\EduComic-uv-cache run pytest -q
54 passed in 5.38s
```

Initial RED:

```text
uv --cache-dir C:\tmp\EduComic-uv-cache run pytest -q tests\test_local_database.py tests\test_local_storage.py tests\test_local_startup.py tests\test_health.py
ERROR tests/test_local_database.py - ModuleNotFoundError: database.migrations
ERROR tests/test_local_storage.py - ModuleNotFoundError: local_storage
ERROR tests/test_local_startup.py - ModuleNotFoundError: local_runtime
```

The first implementation run reached real behavioral failures: Alembic created tables but rolled back its version-row transaction after SQLite `PRAGMA`, and two tests bypassed SQLAlchemy UUID conversion with raw SQL. The migration transaction was fixed; the tests were corrected to exercise real ORM behavior. Focused GREEN then reported `15 passed in 1.78s`.

Self-review found that `read_bytes()` still admitted `staging/...`. A regression test was added and observed RED:

```text
FAILED test_staging_files_cannot_be_read_as_ready_objects
Failed: DID NOT RAISE StorageValidationError
```

Changing the ready-object resolver default to deny staging produced storage GREEN: `5 passed in 0.17s`. Tests were then split so each new test names one break.

Final focused result before the implementation commit:

```text
uv --cache-dir C:\tmp\EduComic-uv-cache run pytest -q tests\test_local_database.py tests\test_local_storage.py tests\test_local_startup.py tests\test_health.py
19 passed in 1.54s
```

Final full backend result before the implementation commit:

```text
uv --cache-dir C:\tmp\EduComic-uv-cache run pytest -q
70 passed in 2.25s
```

Fresh post-report verification repeated the same full command: `70 passed in 1.69s`.

## Offline and reproducibility results

```text
uv --cache-dir C:\tmp\EduComic-uv-cache lock --check --offline
Resolved 48 packages in 1ms

uv --cache-dir C:\tmp\EduComic-uv-cache sync --extra dev --locked --offline
Resolved 48 packages in 1ms
Checked 44 packages in 2ms

uv --cache-dir C:\tmp\EduComic-uv-cache run python -m compileall -q src alembic
exit 0

npm ci --offline --ignore-scripts
added 431 packages; audited 432 packages; found 0 vulnerabilities

npm test -- --run
18 test files passed; 43 tests passed; duration 6.30s

npm run typecheck
exit 0

npm run lint
exit 0

VITE_API_URL=http://127.0.0.1:8000 npm run build
2487 modules transformed; built in 4.16s
```

The first production build attempt correctly failed because the existing Vite configuration requires `VITE_API_URL`; rerunning with the documented local API URL passed. The successful build retained the existing stale `caniuse-lite` advisory and had no build error.

## Dependency and lockfile changes

- Removed the direct `supabase` dependency and its transitive client stack from `backend/pyproject.toml` / `backend/uv.lock`.
- Added exact direct pins `sqlalchemy==2.0.51` and `alembic==1.18.5` through `uv add`.
- `uv.lock` records exact resolved packages and passes both offline lock checking and locked offline sync.
- The initial sandbox run could not access `C:\Users\benth\AppData\Local\uv\cache`; the successful approved workflow used isolated `C:\tmp\EduComic-uv-cache` without bypassing uv or hand-editing the lockfile.

## Source-worktree preservation

The two dirty source worktrees were inspected read-only before and after implementation. Their final status matched the initial evidence:

```text
main...origin/main
M  SUPABASE_SETUP.md
D  backend/.env
M  backend/.env.example
AM docs/PUBLIC_RELEASE_PHASE_0_STATUS.md
D  frontend/.env
M  frontend/.env.example
?? AGENTS.md
?? docs/PRODUCT_INTENT_RECONCILIATION_AUDIT.md
?? docs/PUBLIC_RELEASE_READINESS_REVIEW.md
?? docs/superpowers/

codex/public-release-cleanup
 M backend/.env.example
 M backend/src/panel_review.py
 M backend/src/services/comic_creation.py
 M backend/src/services/story_idea.py
 M backend/tests/test_safe_service_logging.py
?? backend/src/story_contracts.py
?? backend/tests/test_story_contracts.py
```

No reset, stash, clean, checkout, provider call, Supabase project access, deployment, push, or merge was performed.

## Self-review and Phase 2 handoff

Self-review confirmed traversal checks, staging isolation, no API filesystem-path response, SQLite foreign-key activation, migration head tracking, restart persistence, cascades, and the absence of a new final panel-count rule. The local implementation uses standard library file operations and one SQLAlchemy boundary; no storage/persistence plugin framework was added.

Exact Phase 2 handoff:

- convert all legacy functions in `backend/src/database/database.py` from the fail-closed sentinel to SQLAlchemy session/repository operations while preserving response dictionaries;
- replace direct query-builder calls in `backend/src/main.py` for student create/list and chapter insert/status/update;
- replace the direct enrollment lookup and Supabase avatar upload in `backend/src/services/avatar.py` with local queries and `LocalStorage`;
- replace direct panel deletion and image upload in `backend/src/services/comic_creation.py` with transactional local persistence/storage;
- return `media_url(recorded_object_path)` rather than object paths from the converted API serializers;
- expand readiness to database/data-directory checks during Phase 2, and complete durable provider-output revision swaps in Phase 3.

Those paths are intentionally not reported as working local CRUD/generation in Phase 1; they are import-compatible and fail closed rather than silently using hosted infrastructure or temporary provider URLs.
