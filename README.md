# EduComic

EduComic is a local/private educational comic application built with React and FastAPI. Classroom, student-profile, enrollment, chapter, reader, avatar, and export data use SQLite and validated local media rather than a hosted database or object-storage account.

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
   uv run python src/run_local.py --reload
   ```

   First startup creates `backend/data/`, applies the checked-in Alembic migrations, and serves local media through `/media/...` URLs. An optional `DATABASE_URL` override must still be SQLite; the local application refuses hosted database URLs.

4. Start the frontend:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

The supported launcher binds to `127.0.0.1`. A wider bind is refused unless both `--host` and `--allow-unsupported-exposure` are supplied; that override is unsupported because local profile selection is not authentication.

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
