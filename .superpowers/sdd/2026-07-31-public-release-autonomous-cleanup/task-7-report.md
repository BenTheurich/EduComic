# Task 7 Report: Remove Fake Production Flows

## Scope

- Story-option API failures remain on the prompt step, show an inline retryable error, and never expose fabricated choices.
- Student creation only persists the student. Signup enrolls the student before calling the existing avatar endpoint, so avatar generation sees the classroom design style.
- Avatar failure leaves the student and enrollment intact; a missing avatar can be retried from the real profile.
- Removed the fake avatar route/page, fake Edit Avatar entry point, no-op Delete Account and Edit Classroom actions, fabricated student fallback, and classroom-creation material upload.
- Backend material routes and the existing Classroom Detail materials UI remain for Task 16A.

## RED evidence

Added both regression tests before production changes.

Frontend command:

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/teacher/StoryGenerator.test.tsx
```

Result before implementation: 1 failed test. The component had no `role="alert"`, moved to “Choose Your Story,” and rendered the three `mockStoryOptions`, including “Newton's Space Race,” after `startChapter` rejected with `Service unavailable`.

Backend command:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest tests/test_student_signup_flow.py -q
```

Result before implementation: 2 failed tests. `generate_avatar` was awaited once during `create_student`, and the end-to-end create/enroll/explicit-avatar sequence produced two provider prompts: the first used the unenrolled default style and the second used the enrolled classroom style.

## GREEN evidence

Focused commands after the minimal implementation:

```powershell
Set-Location frontend
npm.cmd test -- --run src/pages/teacher/StoryGenerator.test.tsx

Set-Location ..\backend
.\.venv\Scripts\python.exe -m pytest tests/test_student_signup_flow.py -q
```

- Frontend: 1 file / 1 test passed.
- Backend: 2 tests passed.
- No network or live provider call occurred; the provider and storage boundaries were replaced with offline test doubles.

## Full verification

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q

Set-Location ..\frontend
npm.cmd test -- --run
npm.cmd run typecheck
npx.cmd eslint src/App.tsx src/pages/shared/StudentSignup.tsx src/pages/student/StudentAllStories.tsx src/pages/student/StudentDashboard.tsx src/pages/student/StudentProfile.tsx src/pages/teacher/ClassroomDetail.tsx src/pages/teacher/CreateClassroom.tsx src/pages/teacher/StoryGenerator.tsx src/pages/teacher/StoryGenerator.test.tsx src/pages/teacher/TeacherDashboard.tsx
npm.cmd run build
```

- Backend: 6 tests passed after review fix round 1.
- Frontend: 4 files / 4 tests passed.
- Typecheck: passed.
- Frontend touched-file lint: all Task 7 changes are clean; the command reports the restored pre-existing `@typescript-eslint/no-explicit-any` error in `ClassroomDetail.tsx:65`, previously documented by Task 6 and outside this task's one-line removal.
- Backend focused Ruff (`avatar.py` and the new signup test): passed.
- Full `main.py` Ruff still reports 11 pre-existing findings outside the student-creation change (8 import-order findings, one unused assignment, one whitespace finding, and one unused import).
- Production build: passed. Vite reported existing stale Browserslist data and a 615.77 kB chunk advisory.

## Review

- `git diff --check` passed.
- `rg -n "student-new-|mockStoryOptions|Delete Account|Edit Classroom|Student / Learning" frontend/src` found no matches.
- No `CreateAvatar`, `create-avatar`, `Learning Materials`, or `uploadMaterial` match remains in the app routes, student pages, or classroom-creation page.
- The explicit avatar endpoint observes enrollment through `student_classrooms`; the regression test asserts exactly one provider prompt containing `style of a cartoon classroom comic strip`.
- Full-suite test-order isolation was verified after the existing health test reloads `database`, `services`, and `main`; the new tests import the current modules inside each test.
- Reviewed the complete diff for preserved student/enrollment state, valid empty-data handling, route reachability, and accidental material-route deletion.
- Pre-existing `README.md`, `backend/src/educomic.egg-info/*`, and `output/` changes are excluded from staging.

## Review fix round 1

- Removed the classroom lookup exception handler in `generate_avatar`. A failed `student_classrooms` query now propagates before prompt construction or any provider/storage call; only a successful empty lookup retains the manga default.
- Added `test_avatar_lookup_failure_propagates_before_provider_call` before the production fix. RED: the lookup error was logged and swallowed, provider/storage ran, and the test received a later database configuration error instead of `classroom lookup failed`.
- GREEN: `tests/test_student_signup_flow.py` passes 3 tests, including the existing enrolled-cartoon style assertion and the new no-provider-on-lookup-failure assertion.
- Updated the readiness/avatar smoke to supply an explicit successful empty enrollment result. This preserves its API-key compatibility purpose under the stricter lookup contract.
- Full backend: 6 tests passed. Ruff passed for `src/services/avatar.py`, `tests/test_student_signup_flow.py`, and `tests/test_health.py`.
