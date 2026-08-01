# EduComic

EduComic is an educational comic application built with React and FastAPI. Phase 1 provides the SQLite and local-file foundation without a hosted database or object-storage account. Existing classroom, student, and generation paths still fail closed at a compatibility boundary until Phase 2 converts them; this is not yet the complete private application.

## Local setup

1. Install backend dependencies:

   ```bash
   cd backend
   uv sync --extra dev --locked
   ```

2. Copy `backend/.env.example` to `backend/.env` and add the backend-only OpenAI and Black Forest Labs keys.

3. Start the backend on localhost:

   ```bash
   cd backend
   uv run uvicorn --app-dir src main:app --reload --host 127.0.0.1 --port 8000
   ```

   First startup creates `backend/data/`, applies the checked-in Alembic migrations, and serves local media through `/media/...` URLs.

4. Start the frontend:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

Changing the backend bind address exposes an unauthenticated local application and is unsupported for the private release.

## Tests

```bash
cd backend
uv run pytest -q

cd ../frontend
npm test
```

## Architecture

- React 18, TypeScript, and Vite provide the browser UI.
- FastAPI provides the local JSON and media API.
- SQLAlchemy 2 and Alembic manage the SQLite data contract.
- Validated local storage under `backend/data/` owns uploaded and generated files.
- OpenAI and Black Forest Labs are optional paid provider integrations configured only on the backend.

Future hosted PostgreSQL or Supabase work is separate from the private profile. PostgreSQL migration execution remains a future hosted acceptance gate; Phase 1 verifies portability by schema inspection and tests only. See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for the deny-by-default hosted boundary, not local setup instructions.
