---
name: EduComic
description: A calm comic workshop where lesson planning becomes an authored visual story.
colors:
  workshop-blue: "hsl(200 98% 32%)"
  ink-navy: "hsl(222 47% 11%)"
  paper-sky: "hsl(209 40% 96%)"
  card-paper: "hsl(210 40% 98%)"
  workshop-slate: "hsl(215 24% 26%)"
  border-blue-gray: "hsl(212 26% 83%)"
  story-spark: "#FFF991"
  destructive-red: "hsl(0 72% 43%)"
typography:
  display:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(2.25rem, 5vw, 3.75rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Lora, Georgia, serif"
    fontSize: "clamp(1.75rem, 3vw, 2.5rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Space Mono, ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.04em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.workshop-blue}"
    textColor: "{colors.card-paper}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  button-outline:
    backgroundColor: "{colors.card-paper}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  card:
    backgroundColor: "{colors.card-paper}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input:
    backgroundColor: "{colors.card-paper}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "44px"
---

# Design System: EduComic

## Overview

**Creative North Star: "The Authored Comic Workshop"**

EduComic should feel like a calm workspace where a teacher shapes raw lesson material into a finished visual story. The operational shell stays precise and familiar; story artwork, editorial typography, crisp panel rules, and small production details provide the personality. This is a refinement of the recognizable hackathon interface, not a wholesale rebrand.

Teacher surfaces are primarily **Operate** experiences: structured, scan-friendly, and restrained. Story choice and reading surfaces let the artifact lead. Student surfaces are warmer and more immersive, but they remain part of the same system rather than a second theme.

The anti-reference is the interchangeable early-template SaaS look: centered hype copy, identical feature cards, gratuitous gradients, floating unlabeled actions, excessive rounded containers, and decorative motion. Product specificity comes from real comic previews and the lesson-to-story workflow, not ornamental novelty.

**Key Characteristics:**

- Calm operational structure with authored editorial moments.
- Real comic imagery as the primary visual authority.
- Blue paper-and-ink palette with yellow used as a rare story spark.
- Crisp borders and moderate corners instead of pills and floating cards everywhere.
- Honest, progressive provider states that remain useful with reduced motion.

## Colors

The incumbent cool blue palette remains recognizable, while the warm yellow becomes a deliberate narrative accent rather than a page-wide glow.

### Primary

- **Workshop Blue:** Primary actions, active navigation, links, focus rings, and progress that represents real work.

### Secondary

- **Workshop Slate:** Secondary actions and strong supporting surfaces where blue would overstate priority.
- **Story Spark:** Small moments tied to story creation—selected idea markers, restrained highlights, and celebratory completion details. It is not a general background gradient.

### Neutral

- **Ink Navy:** Primary text, panel rules, and high-confidence iconography.
- **Paper Sky:** Application canvas and quiet page regions.
- **Card Paper:** Content surfaces, controls, and story frames.
- **Border Blue Gray:** Dividers, input boundaries, and card structure.

### Named Rules

**The One Spark Rule.** Yellow should identify one meaningful story moment per region; its rarity gives it value.

**The Artifact Leads Rule.** When comic art is present, surrounding color recedes rather than competing with it.

## Typography

**Display Font:** Lora (with Georgia fallback)

**Body Font:** Inter (with system UI fallback)

**Label/Mono Font:** Space Mono (with system monospace fallback)

**Character:** Lora brings an editorial, storybook voice to product-defining moments already supported by the codebase. Inter remains the efficient working face for forms and dashboards. Space Mono is a production-note accent for statuses, classroom codes, and compact metadata—not a novelty body face.

### Hierarchy

- **Display:** Landing statement and rare empty-state or completion headlines.
- **Headline:** Page titles, story titles, and major section headings.
- **Title:** Operational card and form section titles.
- **Body:** Instructions, full story summaries, lesson provenance, and supporting copy; long reading text should remain comfortably bounded.
- **Label:** Status, codes, dates, and compact production metadata. Avoid all-caps paragraphs.

### Named Rules

**The Two Voices Rule.** Narrative moments use Lora; operating the product uses Inter. Do not apply the display face to dense settings, tables, or form controls.

## Layout

Retain the existing container system and route structure. Use a four-pixel base rhythm, with most component spacing landing at 8, 16, 24, or 32 pixels. Teacher pages favor aligned working columns and clear action regions; avoid introducing dashboard grids where a simple vertical sequence is easier to scan.

Story-option cards use equal media treatment but natural content height so complete summaries remain visible. The media, title, complete summary, and selection action form one semantic choice. Story cards consistently use the selected idea's local preview image, title, and summary; the teacher lesson prompt appears only as labelled secondary provenance where useful.

At narrow widths, primary actions remain at least 44 pixels, toolbars wrap without obscuring content, and comic readers default to fit-to-width. Reader preferences may persist separately for narrow and wide viewports so a desktop scale never makes mobile dialogue unreadable.

## Elevation & Depth

The system is flat by default. Borders, paper-toned surfaces, and spacing establish hierarchy. Small incumbent shadows are reserved for dialogs, menus, lifted drag/hover states, and artwork that must separate from the canvas. Cards do not all need a shadow, and hover should not scale whole content blocks.

### Shadow Vocabulary

- **Resting Paper:** No shadow or the incumbent smallest shadow when a boundary needs help against the canvas.
- **Lifted Tool:** The incumbent medium shadow for menus, dialogs, and actively manipulated objects.
- **Story Artwork:** A restrained low shadow only when the image would otherwise merge into the page.

### Named Rules

**The Flat-Until-Lifted Rule.** Elevation communicates state or physical layering; it is not default decoration.

## Shapes

Moderately curved corners preserve the current friendly character: 4 pixels for compact elements, 6 pixels for controls, and 8 pixels for cards and media frames. Comic previews may use crisp ink-like borders inside those frames. Pills are reserved for statuses, compact filters, and genuinely circular controls with accessible names.

Do not turn every region into an independently rounded card. Adjacent content that belongs together should share one surface or use simple dividers.

## Components

### Buttons

- **Shape:** Restrained rectangular control with gently curved corners and a 44-pixel minimum height.
- **Primary:** Workshop Blue with high-contrast paper text; reserved for the main action in a region.
- **Hover / Focus:** Color shift plus a visible focus ring. Avoid scale, bounce, or glow.
- **Secondary / Ghost:** Preserve layout and hierarchy without competing with the primary action. Icon-only variants require an accessible name and tooltip where meaning is not universal.

### Cards / Containers

- **Corner Style:** Moderate 8-pixel radius.
- **Background:** Card Paper over Paper Sky.
- **Shadow Strategy:** Flat at rest; lift only for state.
- **Border:** Blue-gray boundary or a slightly stronger ink rule for story media.
- **Internal Padding:** Usually 24 pixels on desktop and 16 pixels on narrow screens.

Story cards use one canonical content contract: selected idea preview, selected idea title, and complete selected idea summary. Lesson prompts never substitute for story descriptions.

### Inputs / Fields

- **Style:** Paper background, visible border, comfortable 44-pixel minimum control height, and persistent labels.
- **Focus:** Workshop Blue ring with adequate offset and no layout shift.
- **Error / Disabled:** State is communicated through text and semantics as well as color.

### Navigation

Use the EduComic name consistently. Desktop navigation exposes the active location; mobile navigation preserves role and classroom context. Icons support labels rather than replace them for unfamiliar destinations.

### Story Idea Choice

Each of the exactly three choices contains a square server-owned local preview, title, full unclamped summary, and explicit selection control. Preview loading, failure, and retry are represented per idea without inventing success or accepting a browser-supplied image URL.

### Generation Progress

Keep the existing loading composition and progressively reveal durable temporary panel previews as they are produced. Name the current stage, explain that the user may leave safely when true, and distinguish a ready story from temporary preview media. Failed generation removes temporary previews while preserving any previously completed story revision.

## Do's and Don'ts

### Do:

- **Do** reuse the existing route structure, controls, palette family, and accessibility improvements.
- **Do** use real local comic imagery to explain the product before adding decoration.
- **Do** show complete idea summaries and use the selected summary as canonical story description.
- **Do** keep teacher prompts available as clearly labelled lesson provenance.
- **Do** provide meaningful status, static reduced-motion feedback, and text alternatives for image-based stories.
- **Do** make simulated public-demo behavior unmistakable.

### Don't:

- **Don't** restore caller-controlled URL fetching or persist expiring provider delivery URLs.
- **Don't** clamp the text a teacher needs to compare story ideas.
- **Don't** use the lesson prompt as fallback marketing copy for a story.
- **Don't** reintroduce generic gradients, hover-scale cards, unlabeled floating actions, or a second product name.
- **Don't** create a parallel visual system for the fictional demo.
- **Don't** trade truthful state, accessibility, or data-loss protection for visual polish.
