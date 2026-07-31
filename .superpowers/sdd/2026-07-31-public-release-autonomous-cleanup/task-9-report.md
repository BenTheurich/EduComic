# Task 9 report

Implemented centralized frontend API base resolution.

- Production builds now require a non-empty `VITE_API_URL` from either the explicit build environment or Vite's mode-specific env files.
- Development and Vitest retain the localhost fallback; photo uploads and thumbnails use `apiFetch`.
- `.env.example` provides the non-secret local development URL.

Verification:

- RED: with `VITE_API_URL` removed, the original production build passed.
- GREEN: with `VITE_API_URL` removed, production build fails with `VITE_API_URL must be set for production builds.`
- `VITE_API_URL=https://api.example.invalid npm.cmd run build` passes; `rg` finds no localhost URL in `frontend/dist`.
- `npm.cmd run typecheck`, `npm.cmd run test -- --run`, and touched-file ESLint pass.

Deferred: Task 5 CI must set a non-secret invalid `VITE_API_URL` for production frontend builds; CI was intentionally not changed here.

## Review fix round 1

The build guard now uses Vite `loadEnv` and runs for every `vite build` mode. Explicit `process.env.VITE_API_URL` values take precedence.

- RED: with a valid, temporary non-secret `.env.production` and no process variable, the prior guard failed the build.
- GREEN: that `.env.production` builds successfully; an explicit `https://override.example.invalid` is embedded instead when supplied.
- With controlled temporary env files removed, both default and `--mode staging` builds fail clearly with no URL.
- Final `https://api.example.invalid` build contains that URL and no localhost URL; typecheck, all 10 frontend tests, and touched-file ESLint pass.
