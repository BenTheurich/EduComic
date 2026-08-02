# Landing Team Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a responsive back-cover team section with five illustrated teammate portraits, LinkedIn links, and a text-only provider credit to the bottom of the EduComic landing page.

**Architecture:** Keep the five static teammate records and section markup in the existing landing-page component, with presentation and a native scroll-linked entrance in the existing landing stylesheet. Store only generated avatar assets under the existing public demo asset tree; the source photographs remain outside the repository.

**Tech Stack:** React 18, TypeScript, CSS, Vitest, Testing Library, Vite

## Global Constraints

- Preserve the existing hero, scrolling process section, copy, sticky behavior, and product imagery.
- Add no dependency and no content-management abstraction.
- Generate each school-age avatar independently from one supplied adult photo with consistent shoulder-up framing, a pale blue background, and the existing student-avatar artwork as a style-only reference.
- Use no provider logos and do not imply sponsorship, partnership, or endorsement.
- All five teammates receive equal visual weight.
- The entrance animation applies to the group together and is disabled for reduced motion.

---

### Task 1: Generate the five teammate avatar assets

**Files:**
- Create: `frontend/public/demo/team/florian-avatar.png`
- Create: `frontend/public/demo/team/pouya-avatar.png`
- Create: `frontend/public/demo/team/anastasia-avatar.png`
- Create: `frontend/public/demo/team/tim-avatar.png`
- Create: `frontend/public/demo/team/ben-avatar.png`

**Interfaces:**
- Consumes: The five user-supplied source photos in `C:/Users/benth/Downloads/`.
- Produces: Five square illustrated portrait files addressed by `/demo/team/<name>-avatar.png`.

- [ ] **Step 1: Generate each portrait independently**

Use one image-edit request per source photo with this shared direction:

```text
Create a square, shoulder-up cartoon avatar imagining the adult identity reference as a child approximately 10 to 12 years old. Preserve recognizable facial structure, hairstyle, skin tone, eye color, glasses when present, and distinguishing features while translating them into natural school-age proportions. Match only the rendering style of the supplied EduComic student-avatar reference: clean dark linework, softly painted color, large expressive eyes, a warm approachable expression, and subtle dimensional shading. Do not copy the style-reference child's identity. Center the face and shoulders precisely left-to-right with even breathing room around the hair. Use a plain pale blue-gray circular-avatar background with no text, props, logos, scenery, border, or frame. Keep the composition consistent with the other team portraits.
```

Run it once for each exact source:

```text
C:/Users/benth/Downloads/Florian Schwieren.jpeg
C:/Users/benth/Downloads/Pouya Shekarchizadeh.jpeg
C:/Users/benth/Downloads/Anastasia Koslova.png
C:/Users/benth/Downloads/TimGaydoul.JPG
C:/Users/benth/Downloads/BenTheurich.jpg
```

- [ ] **Step 2: Inspect the five assets as one set**

Confirm that every output is square, centered horizontally, recognizably based on its teammate, visibly school-age, free of text or logos, and consistent in crop and background. Make at most one corrective edit for any portrait that fails those checks; do not regenerate acceptable portraits.

- [ ] **Step 3: Place the accepted assets at the five paths above**

Keep the source photographs out of `frontend/public` and out of Git.

- [ ] **Step 4: Commit the generated assets**

```bash
git add frontend/public/demo/team
git commit -m "assets: add EduComic team avatars"
```

### Task 2: Add the team-section contract test

**Files:**
- Modify: `frontend/src/pages/shared/Landing.test.tsx`

**Interfaces:**
- Consumes: The existing `Landing` component and Testing Library helpers.
- Produces: A test contract for the team heading, member order, LinkedIn destinations, and provider credit.

- [ ] **Step 1: Add `within` to the Testing Library import**

```tsx
import { act, render, screen, within } from "@testing-library/react";
```

- [ ] **Step 2: Add the failing team-section test**

```tsx
it("credits the five creators and the tools used to build EduComic", () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Landing />
    </MemoryRouter>,
  );

  const team = screen.getByRole("region", { name: "Meet the team behind EduComic." });
  const names = within(team).getAllByTestId("team-member-name").map((node) => node.textContent);
  expect(names).toEqual([
    "Florian Schwieren",
    "Pouya Shekarchizadeh",
    "Anastasia Koslova",
    "Tim Gaydoul",
    "Ben Theurich",
  ]);

  expect(within(team).getByRole("link", { name: "Florian Schwieren on LinkedIn" })).toHaveAttribute(
    "href",
    "https://www.linkedin.com/in/florian-schwieren-618750215/",
  );
  expect(within(team).getByRole("link", { name: "Pouya Shekarchizadeh on LinkedIn" })).toHaveAttribute(
    "href",
    "https://www.linkedin.com/in/pooyash1998/",
  );
  expect(within(team).getByRole("link", { name: "Anastasia Koslova on LinkedIn" })).toHaveAttribute(
    "href",
    "https://www.linkedin.com/in/anastasia-koslova-a329091b7/",
  );
  expect(within(team).getByRole("link", { name: "Tim Gaydoul on LinkedIn" })).toHaveAttribute(
    "href",
    "https://www.linkedin.com/in/tim-gaydoul-048788174/",
  );
  expect(within(team).getByRole("link", { name: "Ben Theurich on LinkedIn" })).toHaveAttribute(
    "href",
    "https://www.linkedin.com/in/ben-theurich/",
  );
  expect(team).toHaveTextContent(
    "Built with FLUX by Black Forest Labs for artwork and OpenAI for story generation.",
  );
});
```

- [ ] **Step 3: Run the focused test and verify failure**

Run:

```bash
npm.cmd test -- --run src/pages/shared/Landing.test.tsx
```

Expected: FAIL because the `Meet the team behind EduComic.` region does not exist.

### Task 3: Implement and style the team section

**Files:**
- Modify: `frontend/src/pages/shared/Landing.tsx`
- Modify: `frontend/src/pages/shared/Landing.css`
- Test: `frontend/src/pages/shared/Landing.test.tsx`

**Interfaces:**
- Consumes: The `/demo/team/<name>-avatar.png` assets and the test contract from Task 2.
- Produces: A semantic landing-page section with five static member entries and a compact provider credit.

- [ ] **Step 1: Define the static team records beside the existing landing data**

```tsx
const teamMembers = [
  { name: "Florian Schwieren", avatar: "/demo/team/florian-avatar.png", linkedin: "https://www.linkedin.com/in/florian-schwieren-618750215/" },
  { name: "Pouya Shekarchizadeh", avatar: "/demo/team/pouya-avatar.png", linkedin: "https://www.linkedin.com/in/pooyash1998/" },
  { name: "Anastasia Koslova", avatar: "/demo/team/anastasia-avatar.png", linkedin: "https://www.linkedin.com/in/anastasia-koslova-a329091b7/" },
  { name: "Tim Gaydoul", avatar: "/demo/team/tim-avatar.png", linkedin: "https://www.linkedin.com/in/tim-gaydoul-048788174/" },
  { name: "Ben Theurich", avatar: "/demo/team/ben-avatar.png", linkedin: "https://www.linkedin.com/in/ben-theurich/" },
] as const;
```

- [ ] **Step 2: Append the semantic section after `#how-it-works`**

Use a labelled `<section>` with the exact heading `Meet the team behind EduComic.`. Map the five records into `<article>` elements containing the generated image, a visible name marked with `data-testid="team-member-name"`, and a `LinkedIn` link with `aria-label={`${member.name} on LinkedIn`}`, `target="_blank"`, and `rel="noreferrer"`.

Add this exact provider sentence below a divider:

```tsx
Built with <a href="https://bfl.ai/">FLUX by Black Forest Labs</a> for artwork and <a href="https://openai.com/">OpenAI</a> for story generation.
```

- [ ] **Step 3: Add the back-cover presentation in `Landing.css`**

Implement:

```css
.landing-team-section { background: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }
.landing-team-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); }
.landing-team-avatar { overflow: hidden; aspect-ratio: 1; border: 7px solid hsl(var(--card)); border-radius: 50%; }
```

Complete the existing visual language with centered Lora heading treatment, equal portrait sizing, restrained shadow, visible link focus, a translucent provider divider, and these responsive arrangements:

```css
@media (max-width: 1023px) { .landing-team-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); } }
@media (max-width: 600px) { .landing-team-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
```

Use explicit grid spans so tablet is three-plus-two and mobile is two-plus-two-plus-one with the final member centered. Add one group-level view-timeline fade/translate inside `@supports (animation-timeline: view())`, and turn it off under `prefers-reduced-motion: reduce`.

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```bash
npm.cmd test -- --run src/pages/shared/Landing.test.tsx
```

Expected: all landing tests PASS.

- [ ] **Step 5: Run type checking and production build**

Run:

```bash
npm.cmd run typecheck
$env:VITE_API_URL='http://127.0.0.1:8000'; npm.cmd run build
```

Expected: both commands exit successfully.

- [ ] **Step 6: Commit the component, styles, and test**

```bash
git add frontend/src/pages/shared/Landing.tsx frontend/src/pages/shared/Landing.css frontend/src/pages/shared/Landing.test.tsx
git commit -m "feat: add landing team credits"
```

### Task 4: Perform the bounded visual and mechanical verification

**Files:**
- Inspect: `frontend/src/pages/shared/Landing.tsx`
- Inspect: `frontend/src/pages/shared/Landing.css`
- Inspect: `frontend/public/demo/team/*.png`

**Interfaces:**
- Consumes: The completed landing page.
- Produces: One verified desktop/mobile implementation with any discovered defects fixed in one batch.

- [ ] **Step 1: Run the Impeccable detector once**

```bash
node C:/Users/benth/.codex/skills/impeccable/scripts/detect.mjs --json frontend/src/pages/shared/Landing.tsx frontend/src/pages/shared/Landing.css
```

Resolve only findings that apply to the new section.

- [ ] **Step 2: Inspect desktop and mobile together**

Open `http://127.0.0.1:8080/` at approximately 1440 by 1000 and 390 by 844. Confirm the five portraits are centered, equal, correctly ordered, and not cropped; the row wraps as specified; all text is legible; keyboard focus is visible; and the provider line remains secondary.

- [ ] **Step 3: Fix all observed section defects in one batch and confirm once**

Rerun the focused landing test after any edit. Stop after one confirmation pass.

- [ ] **Step 4: Commit only if verification required a corrective edit**

```bash
git add frontend/src/pages/shared/Landing.tsx frontend/src/pages/shared/Landing.css frontend/src/pages/shared/Landing.test.tsx frontend/public/demo/team
git commit -m "fix: polish landing team section"
```
