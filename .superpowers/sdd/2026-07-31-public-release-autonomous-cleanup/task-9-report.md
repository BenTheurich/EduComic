# Task 9 report

Implemented centralized frontend API base resolution.

- Production builds now require a non-empty `VITE_API_URL` supplied through the build environment.
- Development and Vitest retain the localhost fallback; photo uploads and thumbnails use `apiFetch`.
- `.env.example` provides the non-secret local development URL.

Verification:

- RED: with `VITE_API_URL` removed, the original production build passed.
- GREEN: with `VITE_API_URL` removed, production build fails with `VITE_API_URL must be set for production builds.`
- `VITE_API_URL=https://api.example.invalid npm.cmd run build` passes; `rg` finds no localhost URL in `frontend/dist`.
- `npm.cmd run typecheck`, `npm.cmd run test -- --run`, and touched-file ESLint pass.

Deferred: Task 5 CI must set a non-secret invalid `VITE_API_URL` for production frontend builds; CI was intentionally not changed here.
