# Public Demo GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Do not dispatch subagents.

**Goal:** Publish a permanent, public, read-only EduComic product tour from the `redesign` branch without hosting FastAPI or making paid API calls.

**Architecture:** Keep the existing React application and route every demo-build read through the existing `apiFetch` boundary to bundled fictional fixtures. Normal development builds continue calling FastAPI unchanged. A GitHub Actions workflow builds the Vite demo with hash routing and deploys only `frontend/dist` to GitHub Pages.

**Tech Stack:** React 18, TypeScript, Vite 5, Vitest, GitHub Actions, GitHub Pages

## Global Constraints

- The public demo is read-only and contains only fictional classroom data.
- The public demo must never call FastAPI, OpenAI, Black Forest Labs, or Supabase.
- Never put provider keys or backend environment values into `VITE_*` variables.
- The normal local application and its bring-your-own-key backend behavior must remain unchanged.
- Publish from `redesign`; do not modify or deploy `main`, and do not open a pull request.
- Use the existing twelve-panel Misty Jar fixture and existing avatar artwork; generate no new paid assets.
- GitHub Pages for this private repository requires GitHub Pro or higher; the deployed site itself will be public.

---

## File Map

- Create `frontend/src/lib/runtime.ts`: one source of truth for demo mode and Vite base-path-safe asset URLs.
- Create `frontend/src/demo/data.ts`: fictional classroom, material, student, chapter, and panel records.
- Create `frontend/src/demo/api.ts`: read-only endpoint adapter used by `apiFetch` during demo builds.
- Create `frontend/src/demo/api.test.ts`: verifies representative reads and rejects every mutation.
- Create `frontend/src/components/shared/DemoBanner.tsx`: compact public-demo disclosure.
- Modify `frontend/src/lib/api.ts`: select the bundled adapter in demo mode.
- Modify `frontend/src/App.tsx`: use hash routing for Pages and prevent entry into mutation-only routes.
- Modify `frontend/src/pages/shared/Landing.tsx`: make public asset URLs work below `/EduComic/`.
- Modify the existing teacher/student pages listed below: hide mutation controls in demo mode while preserving browse/read/export behavior.
- Modify `frontend/vite.config.ts` and `frontend/package.json`: add a deterministic demo build.
- Create `frontend/.env.demo`: enable demo mode without an API URL.
- Create `.github/workflows/pages.yml`: build and deploy the demo artifact from `redesign`.

---

### Task 1: Add the bundled fictional API

**Files:**
- Create: `frontend/src/lib/runtime.ts`
- Create: `frontend/src/demo/data.ts`
- Create: `frontend/src/demo/api.ts`
- Create: `frontend/src/demo/api.test.ts`
- Modify: `frontend/src/lib/api.ts:28-65`

**Interfaces:**
- Produces: `isDemoMode: boolean`
- Produces: `assetUrl(path: string): string`
- Produces: `demoApiFetch<T>(endpoint: string, options?: RequestInit): Promise<T>`
- Consumes: existing `ChapterWithPanels`, `ChapterPreview`, and `Student` types

- [ ] **Step 1: Write the failing demo adapter tests**

Create `frontend/src/demo/api.test.ts` with focused checks for the actual browse path:

```ts
import { describe, expect, it } from "vitest";
import { demoApiFetch } from "./api";

describe("public demo API", () => {
  it("returns the fictional classroom roster", async () => {
    const response = await demoApiFetch<{ classroom: { students: unknown[] } }>(
      "/classrooms/class-5b-science",
    );
    expect(response.classroom.students).toHaveLength(8);
  });

  it("returns the complete twelve-panel story", async () => {
    const response = await demoApiFetch<{ chapter: { panels: unknown[] } }>(
      "/chapters/misty-jar",
    );
    expect(response.chapter.panels).toHaveLength(12);
  });

  it("never permits writes", async () => {
    await expect(demoApiFetch("/classrooms", { method: "POST" })).rejects.toThrow(
      "The public demo is read-only.",
    );
  });
});
```

- [ ] **Step 2: Run the new test and confirm it fails because the adapter does not exist**

Run:

```powershell
cd frontend
npm test -- --run src/demo/api.test.ts
```

Expected: FAIL because `./api` cannot be resolved.

- [ ] **Step 3: Add the runtime helpers**

Create `frontend/src/lib/runtime.ts`:

```ts
export const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";

export const assetUrl = (path: string) =>
  `${import.meta.env.BASE_URL}${path.replace(/^\/+/, "")}`;
```

- [ ] **Step 4: Define one complete fictional classroom fixture**

Create `frontend/src/demo/data.ts` with these stable IDs and values:

```ts
import type { ChapterPreview, ChapterWithPanels } from "@/types/story";
import type { Student } from "@/types/student";
import { assetUrl } from "@/lib/runtime";

export const DEMO_CLASSROOM_ID = "class-5b-science";
export const DEMO_CHAPTER_ID = "misty-jar";
const createdAt = "2026-08-02T10:00:00Z";

const studentDetails = [
  ["maya-rivers", "Maya Rivers", "Weather mysteries, drawing, and soccer"],
  ["leo-martinez", "Leo Martinez", "Robotics, basketball, and science experiments"],
  ["amara-johnson", "Amara Johnson", "Dance, animals, and nature journals"],
  ["noah-chen", "Noah Chen", "Space, puzzles, and coding"],
  ["sophie-miller", "Sophie Miller", "Clouds, painting, and gymnastics"],
  ["eli-williams", "Eli Williams", "Building, football, and inventions"],
  ["priya-shah", "Priya Shah", "Books, chemistry, and music"],
  ["finn-murphy", "Finn Murphy", "Sketching, hiking, and weather"],
] as const;

export const demoStudents: Student[] = studentDetails.map(([id, name, interests], index) => ({
  id,
  name,
  interests,
  avatar_url: assetUrl(`demo/how-it-works/avatar-${String(index + 1).padStart(2, "0")}.png`),
  avatar_thumbnail_url: assetUrl(`demo/how-it-works/avatar-${String(index + 1).padStart(2, "0")}.png`),
  created_at: createdAt,
}));

export const demoClassroom = {
  id: DEMO_CLASSROOM_ID,
  name: "Class 5B Science",
  subject: "Science",
  grade_level: "Grade 5",
  story_theme: "Weather mysteries",
  design_style: "comic",
  student_count: 8,
  story_count: 1,
  created_at: createdAt,
};

export const demoMaterial = {
  id: "clouds-and-rain-material",
  classroom_id: DEMO_CLASSROOM_ID,
  source_filename: "How clouds make rain.pdf",
  extraction_state: "ready" as const,
  content_hash: "fictional-demo-clouds-and-rain",
  page_count: 3,
  text_char_count: 1842,
};

export const demoChapter: ChapterWithPanels = {
  id: DEMO_CHAPTER_ID,
  classroom_id: DEMO_CLASSROOM_ID,
  index: 1,
  revision: 1,
  chapter_outline: "Eight classmates solve the mystery of condensation on a cold jar.",
  original_prompt: "Teach how cooling water vapor forms droplets, clouds, and rain.",
  thumbnail_url: assetUrl("demo/stories/misty-jar/panels/panel-01.png"),
  story_title: "The Mystery of the Misty Jar",
  story_description: "Eight classmates connect condensation on a cold jar to clouds and rain.",
  status: "ready",
  created_at: createdAt,
  grounded_sources: [{
    material_id: demoMaterial.id,
    content_hash: demoMaterial.content_hash,
    source_label: demoMaterial.source_filename,
    excerpts: [{ page: 1, text: "Water vapor cools and condenses into liquid droplets." }],
  }],
  panels: Array.from({ length: 12 }, (_, offset) => {
    const index = offset + 1;
    return {
      id: `misty-jar-panel-${index}`,
      chapter_id: DEMO_CHAPTER_ID,
      index,
      image: assetUrl(`demo/stories/misty-jar/panels/panel-${String(index).padStart(2, "0")}.png`),
      created_at: createdAt,
    };
  }),
};

export const demoChapterPreview: ChapterPreview = {
  ...demoChapter,
  classroom_name: demoClassroom.name,
  classroom_subject: demoClassroom.subject,
};
```

- [ ] **Step 5: Route only the GET endpoints needed by existing screens**

Create `frontend/src/demo/api.ts`. Reject non-GET methods first, then return fixture-shaped responses for:

```ts
GET /classrooms
GET /classrooms/class-5b-science
GET /classrooms/class-5b-science/chapters
GET /classrooms/class-5b-science/materials
GET /students
GET /students/:studentId
GET /students/:studentId/classrooms
GET /students/:studentId/chapters
GET /chapters/misty-jar
GET /settings
```

Use exact endpoint matching and throw `Unknown public demo endpoint: ${endpoint}` for every unlisted request. `GET /students/:studentId` must reject an unknown ID instead of silently returning Maya. `/settings` returns story length `12`, design style `comic`, models `gpt-5.6-sol` and `flux-2-pro`, automatic review `true`, attempt cap `2`, empty reader preferences, both provider readiness values `false`, and `local_data: "Fictional public demo"`.

- [ ] **Step 6: Select the adapter at the existing API boundary**

Modify `frontend/src/lib/api.ts` so production API configuration is required only outside demo mode:

```ts
import { demoApiFetch } from "@/demo/api";
import { isDemoMode } from "@/lib/runtime";

const API_BASE_URL = isDemoMode ? "" : import.meta.env.VITE_API_URL || (
  import.meta.env.DEV || import.meta.env.MODE === "test"
    ? "http://127.0.0.1:8000"
    : (() => { throw new Error("VITE_API_URL must be set for production builds."); })()
);

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  if (isDemoMode) return demoApiFetch<T>(endpoint, options);
  // Preserve the existing fetch implementation below this guard.
}
```

- [ ] **Step 7: Run the adapter and existing API tests**

Run:

```powershell
cd frontend
npm test -- --run src/demo/api.test.ts src/lib/api.request-bodies.test.ts
```

Expected: both files PASS and no HTTP request occurs in `demo/api.test.ts`.

- [ ] **Step 8: Commit the fixture boundary**

```powershell
git add frontend/src/lib/runtime.ts frontend/src/demo frontend/src/lib/api.ts
git commit -m "feat: add read-only public demo data"
```

---

### Task 2: Make existing screens safe and Pages-compatible

**Files:**
- Create: `frontend/src/components/shared/DemoBanner.tsx`
- Modify: `frontend/src/App.tsx:1-64`
- Modify: `frontend/src/pages/shared/Landing.tsx:36-275`
- Modify: `frontend/src/pages/shared/StudentLogin.tsx:83-132`
- Modify: `frontend/src/pages/teacher/TeacherDashboard.tsx:60-87`
- Modify: `frontend/src/pages/teacher/ClassroomDetail.tsx:320-713`
- Modify: `frontend/src/pages/teacher/StoryViewer.tsx:270-390`
- Modify: `frontend/src/pages/student/StudentProfile.tsx:140-213`
- Modify: `frontend/src/components/teacher/TeacherSidebar.tsx:23-38`
- Test: `frontend/src/App.test.tsx`
- Test: `frontend/src/pages/shared/Landing.test.tsx`

**Interfaces:**
- Consumes: `isDemoMode` and `assetUrl` from Task 1
- Produces: a browseable UI with no reachable write controls in demo mode

- [ ] **Step 1: Add failing assertions for the disclosure and base-safe landing assets**

Extend existing tests to require the text `Public demo · Fictional data · Read-only` and to verify the landing artwork uses the configured Vite base path through `assetUrl` rather than hard-coded root URLs.

- [ ] **Step 2: Add the compact disclosure**

Create `frontend/src/components/shared/DemoBanner.tsx`:

```tsx
import { isDemoMode } from "@/lib/runtime";

export function DemoBanner() {
  if (!isDemoMode) return null;
  return (
    <div className="border-b bg-primary px-4 py-2 text-center text-xs font-semibold text-primary-foreground" role="status">
      Public demo · Fictional data · Read-only
    </div>
  );
}
```

Render it once near the top of `App.tsx`, above the routed content.

- [ ] **Step 3: Use hash routing only for the Pages build**

In `frontend/src/App.tsx`, import `HashRouter`, `Navigate`, and `isDemoMode`, then select the router without duplicating routes:

```tsx
const Router = isDemoMode ? HashRouter : BrowserRouter;
```

Keep normal builds on `BrowserRouter`. In demo mode, redirect these mutation-only routes instead of mounting their forms:

```text
/teacher/settings                         -> /teacher/dashboard
/teacher/classroom/new                    -> /teacher/dashboard
/teacher/classroom/:classroomId/story/new -> /teacher/dashboard
/student/signup                           -> /student/select
/student/join and /student/join/:code      -> /student/select
```

- [ ] **Step 4: Make landing assets respect `/EduComic/`**

Replace every literal `/demo/...` value in `frontend/src/pages/shared/Landing.tsx` with `assetUrl("demo/...")`. Do not change external LinkedIn URLs.

- [ ] **Step 5: Hide write entry points while preserving the tour**

Use direct `!isDemoMode && (...)` guards; do not introduce a permission framework.

- `StudentLogin.tsx`: hide `Create Student Profile` and its empty-state CTA.
- `TeacherDashboard.tsx`: hide both create-classroom CTAs.
- `TeacherSidebar.tsx`: hide the Settings item.
- `ClassroomDetail.tsx`: hide classroom edit/delete, student removal/erasure, upload/delete material, generate-story, and delete-chapter controls. Keep classroom details, roster, material metadata, and completed-story links.
- `StoryViewer.tsx`: hide panel-correction triggers and dialogs. Keep reader layout controls and client-side PDF export.
- `StudentProfile.tsx`: keep the profile and avatar visible; hide avatar generation, editing, and erasure controls.
- `StudentSidebar.tsx`: keep Profile because it is now a read-only showcase screen.

- [ ] **Step 6: Run component tests**

```powershell
cd frontend
npm test -- --run src/App.test.tsx src/pages/shared/Landing.test.tsx src/pages/teacher/TeacherDashboard.test.tsx src/pages/teacher/ClassroomDetail.test.tsx src/pages/teacher/StoryViewer.test.tsx src/pages/shared/StudentLogin.test.tsx src/pages/student/StudentProfile.test.tsx
```

Expected: PASS in normal test mode; demo-specific assertions pass with `VITE_DEMO_MODE=true` stubbed before dynamically importing the tested module.

- [ ] **Step 7: Commit the read-only UI**

```powershell
git add frontend/src/App.tsx frontend/src/components/shared/DemoBanner.tsx frontend/src/components/teacher/TeacherSidebar.tsx frontend/src/pages
git commit -m "feat: make public demo browse-only"
```

---

### Task 3: Add the deterministic GitHub Pages build

**Files:**
- Create: `frontend/.env.demo`
- Modify: `frontend/package.json:6-13`
- Modify: `frontend/vite.config.ts:6-36`
- Create: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: the demo mode from Tasks 1-2
- Produces: `frontend/dist/index.html` deployable below `/EduComic/`

- [ ] **Step 1: Add the demo environment and package command**

Create `frontend/.env.demo`:

```dotenv
VITE_DEMO_MODE=true
```

Add to `frontend/package.json` scripts:

```json
"build:demo": "vite build --mode demo"
```

- [ ] **Step 2: Configure Vite for the repository subpath**

Modify `frontend/vite.config.ts`:

```ts
const isDemo = mode === "demo";
const apiUrl = process.env.VITE_API_URL ?? loadEnv(mode, process.cwd(), "VITE_").VITE_API_URL;

if (command === "build" && !isDemo && !apiUrl?.trim()) {
  throw new Error("VITE_API_URL must be set for production builds.");
}

return {
  base: isDemo ? "/EduComic/" : "/",
  // Preserve the current server, plugin, alias, and test configuration.
};
```

- [ ] **Step 3: Build locally and inspect the artifact**

```powershell
cd frontend
npm run typecheck
npm run build:demo
Test-Path dist\index.html
rg -n "127.0.0.1:8000|BFL_API_KEY|OPENAI_API_KEY|SUPABASE_KEY|sk-" dist
```

Expected: typecheck and build succeed, `dist/index.html` exists, and `rg` returns no matches.

- [ ] **Step 4: Add one Pages workflow triggered only by `redesign`**

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy public demo

on:
  push:
    branches: [redesign]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run build:demo
      - uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/dist
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 5: Commit the Pages build**

```powershell
git add frontend/.env.demo frontend/package.json frontend/vite.config.ts .github/workflows/pages.yml
git commit -m "deploy: publish public demo to GitHub Pages"
```

---

### Task 4: Verify and publish without opening a pull request

**Files:**
- Verify only; no additional source files expected

**Interfaces:**
- Produces: a public URL suitable for BFL, LinkedIn, portfolios, and resumes

- [ ] **Step 1: Run the full frontend gate**

```powershell
cd frontend
npm test -- --run
npm run lint
npm run typecheck
npm run build:demo
```

Expected: all commands PASS.

- [ ] **Step 2: Preview the exact static build**

```powershell
cd frontend
npm run preview -- --host 127.0.0.1 --port 4173
```

Verify these hash routes in a real browser:

```text
/#/
/#/teacher/dashboard
/#/teacher/classroom/class-5b-science
/#/teacher/story/misty-jar
/#/student/select
/#/student/dashboard/maya-rivers
/#/student/classroom/class-5b-science/maya-rivers
/#/student/story/misty-jar/maya-rivers
/#/student/profile/maya-rivers
```

Acceptance criteria:

- Landing artwork loads under the `/EduComic/` base path.
- Teacher dashboard, roster, uploaded material, and completed comic render without FastAPI.
- Student picker, dashboard, classroom, story reader, and profile render without FastAPI.
- No create, upload, generation, correction, settings, edit, or delete action is reachable.
- Browser network activity contains no requests to localhost or third-party AI providers.
- Refreshing or directly opening a hash route works.

- [ ] **Step 3: Push `redesign` only**

```powershell
git push origin redesign
```

Do not open a pull request and do not push `main`.

- [ ] **Step 4: Enable Pages once in GitHub repository settings**

In `BenTheurich/EduComic`:

1. Open **Settings → Pages**.
2. Set **Build and deployment → Source** to **GitHub Actions**.
3. Open the `Deploy public demo` workflow and confirm the deployment succeeds.
4. Visit `https://bentheurich.github.io/EduComic/` and repeat the acceptance route walkthrough.

- [ ] **Step 5: Confirm the public artifact contains no credentials**

Download the deployed Pages artifact from the successful workflow and run:

```powershell
rg -n "BFL_API_KEY|OPENAI_API_KEY|SUPABASE_KEY|sk-|api_key" artifact-directory
```

Expected: no matches. Historical repository secrets still need rotation before BFL receives private repository access; that is independent of this public static artifact.

---

## Deliberately Skipped

- No hosted FastAPI service, database, authentication, or provider integration.
- No second repository and no duplicated React application.
- No `gh-pages` branch containing compiled files; GitHub Actions deploys the artifact directly.
- No custom domain until the GitHub Pages URL has been reviewed and approved.
- No simulated generation animation or fake write success; public-demo writes are unavailable.

