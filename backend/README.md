# EduComic backend

The backend uses FastAPI, SQLite, Alembic migrations, and validated local files. No hosted database or object-storage setup is required.

```bash
uv sync --extra dev --locked
copy .env.example .env
uv run python src/run_local.py --reload
```

On first startup the backend creates `data/educomic.db`, applies migrations, creates one local teacher profile, and creates the asset directories. Set `EDUCOMIC_DATA_DIR` to keep local data elsewhere. `DATABASE_URL` is an optional SQLite override only; local mode rejects PostgreSQL, Supabase, and every other non-SQLite URL before opening storage or a database engine.

Provider keys stay in the ignored backend `.env` file. Do not expose the backend beyond localhost: the private profile has no authentication.

Run offline tests with:

```bash
uv run pytest -q
```

## Lesson PDF materials

Teachers can upload bounded native-text PDFs and explicitly select ready sources when starting a story. The backend verifies the raw PDF, stores it under a random local object path, and snapshots bounded page excerpts plus the SHA-256 hash on the chapter before provider work. Both option and full-script prompts use that immutable snapshot inside an untrusted-source delimiter; deleting the source PDF does not erase chapter provenance.

Scanned/textless and encrypted PDFs are rejected with safe named states. OCR, semantic search, and hosted storage remain outside this release.
