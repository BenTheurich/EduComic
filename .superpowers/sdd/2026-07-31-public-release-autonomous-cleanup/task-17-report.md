# Task 17 report

Implementation commit: `4a53b1fe7150fa847c826e5fa1c6948c586f474f`

## Import and dependency inventory

- Bundled `src/main.tsx` with esbuild metadata after the cleanup. It found 46 reachable runtime source inputs (including `index.css`); the two omitted TypeScript files are type-only imports used by `api.ts` and PDF/story callers. No production source module remains unreachable.
- Included `index.css`, Vite, Tailwind, PostCSS, ESLint, TypeScript, and package scripts in dependency classification.
- Deleted 38 unreachable source modules: scaffold UI primitives, the unused `NavLink`, reader/sidebar variant, legacy Radix toast stack/hooks, mobile hook, and classroom type variant.
- Removed 27 unused production dependencies and the unused Typography dev plugin. Moved build-only `tailwindcss-animate` to dev dependencies and retained it because active dialogs, selects, and tooltips use its animation utilities.
- Removed React Query after confirming there were no query/mutation hooks. Kept the directly used Sonner toaster and deleted its unused themed wrapper plus the second toaster.
- Kept every active route and lazy-loaded all 15 route pages behind the existing `ClassicLoader` treatment.

## TDD and checks

- RED: the new app-route test could not find the loading status while `Landing` was still statically imported.
- GREEN: the deterministic test now renders the fallback, explicitly resolves the mocked lazy module inside `act`, and observes the route page.
- `npm.cmd ci`: passed after downloading the one package absent from the local cache. The prior offline attempt failed only because `jspdf-4.2.1.tgz` was not cached.
- `npm.cmd run typecheck`: passed.
- `npm.cmd run lint`: passed with zero errors and zero warnings.
- `npm.cmd test -- --run`: 11 files, 29 tests passed.
- `npm.cmd run build` with `VITE_API_URL=https://invalid.example`: passed. The main entry chunk is 403.87 kB, down 219.99 kB (35.3%) from the 623.86 kB baseline; route pages are separate chunks.
- `npm.cmd audit --omit=dev`: 3 high, 0 critical, 0 moderate, 0 low. All three are the same React Router open-redirect/XSS advisory; npm reports no fix available for the installed React Router 6 line. No forced major upgrade was attempted.
- Import/dependency absence scans, `git diff --check`, and staged redacted Gitleaks passed. Gitleaks emitted only the environment's existing inaccessible global-ignore warning.

No route, browser behavior, or file with uncertain reachability was removed.
