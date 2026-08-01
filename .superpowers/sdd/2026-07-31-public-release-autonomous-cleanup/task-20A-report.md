# Task 20A report: release identity and local development alignment

## Result

The backend now permits Vite's actual local development origins by default, the frontend build no longer includes Lovable's component tagger, and the document metadata identifies the project factually as EduComic.

## Changes

- Aligned the backend default and environment example with Vite on ports `8080` for both loopback hostnames.
- Removed `lovable-tagger` from Vite, the frontend manifest, and the npm lockfile.
- Replaced template title and social metadata with an `EduComic` title and one factual description; no public URL or social image was invented.

## TDD evidence

- RED: the focused backend test failed on the old `5173` origins.
- GREEN: the focused test passes with the two `8080` origins.

## Verification

- Backend: `33` tests pass; `compileall` passes.
- Frontend: typecheck and lint pass; `43` tests pass; production build passes.
- Scoped stale-identity search: no `Lovable`, `lovable-tagger`, or `localhost:5173` matches.
- Production dependency audit: `3` high React Router advisories, no fix available in the current major, and `0` critical.
- `git diff --check`: pass.
- Staged source-tree Gitleaks scan: no leaks found.

The build still prints the pre-existing stale Browserslist database advisory.
