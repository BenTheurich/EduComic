# EduComic repository guide

## Product

EduComic turns teacher-provided lesson material into illustrated classroom stories whose recurring cast is built from student-created avatars.

The repository supports two deliberately separate experiences:

- **Local/private application:** the complete teacher and student workflows, local persistence, provider-backed generation, review, correction, reading, and PDF export.
- **Public demo:** a static, read-only GitHub Pages build with bundled fictional data and no uploads, writes, secrets, provider calls, or authentication claims.

The local profile chooser is a preview mechanism, not authentication. Never expose the local backend or its classroom data to the Internet.

## Current stack

- Frontend: React 18, TypeScript, Vite, Vitest, Tailwind CSS.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite, pytest.
- Local media: validated files under `backend/data/`, served by the backend.
- Providers: OpenAI for structured narrative work and Black Forest Labs for generated artwork.
- Public hosting: a static demo built by `.github/workflows/pages.yml`.

Supabase, Railway, Vercel, hosted authentication, and multi-tenant authorization are not part of the current implementation.

## Run locally

Backend:

```powershell
cd backend
uv sync --extra dev --locked
Copy-Item .env.example .env
uv run python src/run_local.py --reload
```

Frontend, in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:8080/`. The backend binds to `127.0.0.1:8000` by default.

Provider keys belong only in the ignored `backend/.env` file. Never put them in frontend variables, fixtures, documentation, logs, or commits.

## Verify changes

Backend:

```powershell
cd backend
uv run pytest -q
```

Frontend:

```powershell
cd frontend
npm test -- --run
npm run lint
npm run typecheck
npm run build:demo
```

CI must stay secret-free and deterministic. Do not add live provider calls to tests or pull-request workflows.

## Repository map

- `backend/src/`: API, local runtime, persistence, provider services, and generation workflows.
- `backend/alembic/`: checked-in SQLite migrations.
- `backend/tests/`: offline backend tests.
- `frontend/src/`: application and public-demo UI.
- `frontend/src/demo/`: fictional public-demo data and adapters.
- `frontend/public/demo/`: fictional artwork and story fixtures used by the public demo.
- `README.md`: public overview, setup, verification, architecture, and limitations.
- `PRODUCT.md`: current product contract and safety boundaries.
- `DESIGN.md`: current visual design contract.

The implementation and tests are the source of truth for endpoints and schema. Do not maintain duplicate endpoint inventories or historical task reports.

## Product and safety constraints

- Preserve complete teacher and student workflows in the local application.
- Public-demo behavior must remain fictional, read-only, visibly labeled, and free of paid API calls.
- Uploaded PDFs are untrusted input. Keep validation, bounded extraction, immutable source snapshots, and safe prompt delimiters.
- Caller-controlled URLs must never be fetched by the backend.
- Provider output and delivery URLs are untrusted until copied into managed local media.
- Paid generation must be explicit and recoverable. Preserve checkpoints and avoid duplicate provider submission on retries.
- Panel corrections remain candidates until the teacher accepts them; do not overwrite the accepted panel on failed regeneration.
- Keep copy truthful about cost, persistence, failure, simulation, and authentication.
- Use only fictional students and classrooms in committed demo fixtures. Do not commit real student data.
- Do not reintroduce hosted storage or databases without real authentication, authorization, tenant isolation, and a separate approved design.

## Working style

- Prefer deletion and consolidation over new wrappers, scripts, or duplicate documents.
- Reuse existing types, services, UI components, and test patterns before adding abstractions.
- Make the smallest root-cause change that preserves validation, error handling, security, and accessibility.
- Keep generated planning artifacts out of the repository; Git history already records completed implementation work.
