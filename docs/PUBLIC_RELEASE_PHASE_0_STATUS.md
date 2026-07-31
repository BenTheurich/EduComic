# Public Release Phase 0 Status

Date: 2026-06-09

Phase 0 goal: make the repository safe to share without leaking secrets, private data, or immediately dangerous configuration.

## Completed Or Staged Locally

- Staged `backend/.env` and `frontend/.env` for removal from git tracking while leaving local copies on disk. The files and their leaked values remain in `HEAD`, `origin/main`, and repository history until the sanitized publication strategy is completed.
- Replaced `backend/.env.example` and `frontend/.env.example` with placeholder-only templates.
- Replaced a current `SUPABASE_SETUP.md` credential snippet with placeholder-only values.
- Installed Gitleaks locally through `winget`.
- Ran a redacted all-history secret scan:

```powershell
gitleaks detect --source . --log-opts="--all" --redact --no-banner --no-color --verbose
```

Result: failed as expected. Gitleaks scanned 56 commits and found 8 redacted leaks in repository history.

- Ran a redacted current-source scan against a temporary checkout of the staged git index:

```powershell
gitleaks dir <temporary-staged-index-checkout> --redact --no-banner --no-color --verbose
```

Result: passed. Gitleaks scanned the staged source tree and reported no leaks.

## History Findings

The scanner reported redacted findings in historical commits for:

- `backend/.env`
- `SUPABASE_SETUP.md`

Rules included:

- `openai-api-key`
- `jwt`
- `generic-api-key`

No raw secret values were printed or copied into this status file.

## Required Owner Actions

These actions require access to provider dashboards or project data and cannot be completed from the local repo alone:

- Rotate the exposed OpenAI API key.
- Rotate the exposed Black Forest Labs API key.
- Inspect the exposed Supabase key type.
- Rotate any exposed Supabase service-role key immediately.
- Review whether the current Supabase project contains real student names, photos, interests, classroom materials, or generated content.
- Create a separate demo Supabase project with fictional data before public hosting.

## Publication Strategy

Recommendation: create a fresh public repository from a sanitized source tree after rotating exposed keys.

Reason: all-history scanning confirmed secrets in old commits. A fresh public repository is simpler and safer than relying on history rewriting for an external handoff.

If the current repository must be reused, clean history with a purpose-built tool such as `git filter-repo` or BFG, then rerun:

```powershell
gitleaks detect --source . --log-opts="--all" --redact --no-banner --no-color --verbose
```

Do not make the current repository public until the all-history scan passes.

## Non-Code Artifact Review Result

The July 31, 2026 follow-up visually inspected the tracked PDFs and image and reviewed the local assistant files, fix notes, and manual test artifacts:

- The three PDFs are obsolete internal hackathon artifacts. Two contain personal author metadata, and their technical guidance is stale. Remove them from the public source.
- The image is a stale technical flowchart, not a personal photo. Remove it or replace it with current architecture documentation.
- `.claude/settings.local.json` contains a contributor-specific local path. Remove `.claude/` from the public source.
- Root fix notes include unsafe public-storage and RLS-disabling guidance. Remove the historical notes after current setup documentation is written.
- Root manual test files call prototype or live-service paths and are not a release test suite. Remove them after isolated tests replace any useful coverage.
- Replace the Lovable frontend README and social metadata with current EduComic documentation.

The full result and exact autonomous cleanup plan are recorded in:

- `docs/PUBLIC_RELEASE_READINESS_REVIEW.md`
- `docs/superpowers/plans/2026-07-31-public-release-autonomous-cleanup.md`

## Phase 0 Acceptance State

- No `.env` files should be tracked in the sanitized/public source.
- Env examples should contain placeholders only.
- All exposed keys must be rotated.
- Gitleaks must pass on the chosen public source/history.
- Public artifacts must be reviewed and sanitized.
- The fresh-public-repository publication strategy should be confirmed before external sharing.
