# Task 5 Report - Secret-Free CI

## Changes

- Deleted `.github/workflows/deploy.yml`.
- Added `.github/workflows/ci.yml` with read-only repository permissions and independent backend/frontend verification jobs.
- Rewrote `.github/SECRETS_CHECKLIST.md` as a future-deployment checklist with no configuration claims.
- Preserved the pre-existing Task 17 completion note in `progress.md`.

## Verification

Backend environment variables `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`, and `BFL_API_KEY` were removed from the local process before running:

```powershell
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q
uv run --frozen --extra dev python -m compileall -q src tests
```

Result: install succeeded; 33 tests passed; compileall exited 0.

Frontend commands mirrored from CI:

```powershell
npm ci
npm run typecheck
npm run lint
npm test -- --run
$env:VITE_API_URL='https://api.invalid'; npm run build
```

Result: all commands exited 0; 11 test files and 29 tests passed; production build succeeded. `npm ci` reported 47 total advisories including development dependencies; dependency remediation remains outside this configuration-only task.

The already-installed transitive `yaml` CLI validated the workflow without installing another parser:

```powershell
Get-Content -Raw '..\.github\workflows\ci.yml' | cmd /c node_modules\.bin\yaml.cmd valid
```

Result: exit 0.

Static checks asserted `.github/workflows/ci.yml` contains none of `continue-on-error`, shell `||`, secret expressions, deployment wording, generated `.env` files, provider URLs, or `curl`; asserted it is the only workflow; and ran `git diff --check`.

Result: all checks passed.

Staged source scan:

```powershell
gitleaks git --staged --redact --no-banner --no-color
```

Result: exit 0; no leaks found. Gitleaks emitted the known contributor-local global Git ignore permission warning but scanned the staged content successfully.
