# Task 6 Report: Invite, Navigation, And Broken Routes

## Scope

- Direct student invite no longer renders the classroom preview before its classroom data exists.
- Mobile sidebars receive the same children as desktop sidebars.
- Mobile navigation controls are labelled buttons; Escape closes the menu and focus returns to its trigger.
- Empty-classroom story link now uses `/story/new`; the unavailable Settings item was removed.

## RED evidence

Added these behavioral regression tests before the production change:

- `frontend/src/pages/student/JoinClassroom.test.tsx`
  - Renders `/student/join/classroom-123` with a pending real API fetch and expects an accessible loading state.
- `frontend/src/components/ui/animated-sidebar.test.tsx`
  - Opens the real mobile sidebar, verifies mobile and desktop navigation links both render, checks named button controls, Escape close, and trigger focus restoration.

Command:

```powershell
Set-Location frontend
npm.cmd test -- --run JoinClassroom animated-sidebar
```

Result before implementation: 2 failed tests. `JoinClassroom` threw `TypeError: Cannot read properties of null (reading 'name')` at `JoinClassroom.tsx:217`. The sidebar test could not find a `button` named `Open navigation`; the rendered control was a clickable SVG.

## GREEN evidence

After the minimal changes, the same focused command passed: 2 test files / 2 tests.

Final verification:

```powershell
Set-Location frontend
npm.cmd test -- --run
npm.cmd run typecheck
npx.cmd eslint src/pages/student/JoinClassroom.tsx src/pages/student/JoinClassroom.test.tsx src/components/ui/animated-sidebar.tsx src/components/ui/animated-sidebar.test.tsx src/pages/teacher/ClassroomDetail.tsx src/components/teacher/TeacherSidebar.tsx
npm.cmd run build
```

- Tests: 3 files / 3 tests passed.
- Typecheck: passed.
- Touched-file lint: exit 0; one existing `react-refresh/only-export-components` warning in `animated-sidebar.tsx` (no lint errors).
- Production build: passed. Vite reported existing stale Browserslist data and a 623.50 kB chunk warning.

## Review

- `git diff --check` passed.
- No JSX `href` remains for `/story/generate` or `/teacher/settings`.
- Reviewed the full task diff: the loading guard covers both direct-invite load and failed direct-invite fallback; mobile content is passed through the shared `SidebarBody` path; focus restoration is only applied after the menu had been open.
- Pre-existing `README.md` and `backend/src/educomic.egg-info/*` changes are excluded.

## Review fix 1

- Removed the unrelated `UploadedMaterial` type and restored the pre-existing `uploadedMaterials` state declaration; the `/story/new` route fix remains unchanged.
- Focused Task 6 tests: 2 files / 2 tests passed. Typecheck: passed.
- `npx.cmd eslint src/pages/teacher/ClassroomDetail.tsx` reports the restored, pre-existing `@typescript-eslint/no-explicit-any` error at line 65. It is intentionally left unchanged to keep this review fix scoped to removing the unrelated change.

## Browser fix round 2

Headed Chromium at 390x844 exposed a shared layout failure: both app roots kept their desktop row direction while the mobile sidebar occupied `w-full`, collapsing the content sibling to zero width.

Added `frontend/src/components/layouts.test.tsx` before the production change. It renders the real teacher and student layouts and independently requires their mobile-column/desktop-row container contract.

RED command:

```powershell
Set-Location frontend
npm.cmd test -- --run layouts animated-sidebar
```

RED result: both layout cases failed because their roots had `flex` but lacked `flex-col md:flex-row`; the existing mobile menu/focus test passed.

The minimal fix adds `flex-col md:flex-row` to `TeacherLayout` and `StudentLayout` only.

GREEN and verification:

- Focused layout/sidebar tests: 2 files / 3 tests passed.
- Full frontend tests: 9 files / 25 tests passed.
- Typecheck: passed.
- Touched-file lint for the two layouts and new test: passed with no findings.
- Production build: passed with `VITE_API_URL=http://localhost:8000`. The first build without that required variable stopped at the production configuration guard as designed. Vite retained the existing stale Browserslist data and large-chunk warnings.
