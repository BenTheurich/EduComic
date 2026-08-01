# EduComic backend

The backend's Phase 1 foundation uses FastAPI, SQLite, Alembic migrations, and local files. No hosted database or object-storage setup is required. Legacy CRUD and generation callers remain deliberately unavailable behind a fail-closed compatibility sentinel until Phase 2 converts them.

```bash
uv sync --extra dev --locked
copy .env.example .env
uv run uvicorn --app-dir src main:app --reload --host 127.0.0.1 --port 8000
```

On first startup the backend creates `data/educomic.db`, applies migrations, and creates the asset directories. This foundation does not yet make the legacy application workflows persistence-ready. Set `EDUCOMIC_DATA_DIR` to keep local data elsewhere, or `DATABASE_URL` for an explicitly configured SQLAlchemy database.

Provider keys stay in the ignored backend `.env` file. Do not expose the backend beyond localhost: the private profile has no authentication.

Run offline tests with:

```bash
uv run pytest -q
```
